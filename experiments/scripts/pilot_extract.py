# -*- coding: utf-8 -*-
"""Pilot feature extraction: ALL rollout episodes of the two design-frozen pilot tasks.

Frozen pipeline is byte-identical to smoke_extract.py (experiments/protocol.md section 2):
- frame rule: idx_k = floor(k*N/8), k=0..7 (N = episode length, fps=20)
- target timestamp in concatenated video: from_ts + idx_k / fps; nearest decoded frame within
  1.5 frame periods (0.075 s), two-pointer first-match
- preprocessing: RGB -> resize shortest side 224 (PIL bilinear) -> center crop 224x224 ->
  float32 /255 -> ImageNet mean/std
- encoder: facebook/dinov2-small CLS token, fp32, cuda, eval, deterministic algorithms
- episode feature: mean of the 8 CLS vectors, then L2 normalize

Differences from smoke_extract (scope only, no pipeline change):
- population = every rollout episode of the task (cable_clip 270 / fold_tea_towel 300)
- file completeness verified against size_verification_pilot.json (HF Content-Range bytes)
- outputs pilot_{shortname}_{rev8}.npz + pilot_episodes.csv + extract_cost_pilot.json
"""
import os, sys, json, time
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
sys.stdout.reconfigure(line_buffering=True)

import numpy as np
import pandas as pd
from PIL import Image
import torch

SCRATCH = os.path.dirname(os.path.abspath(__file__))
PROJECT = "D:/hermes-data/research/审计真机基准的策略身份混淆-18c6f2b0"
CACHE_ROOT = os.path.join(PROJECT, "assets", "hf")
FRAG_DIR = os.path.join(PROJECT, "experiments", "cache")
os.makedirs(FRAG_DIR, exist_ok=True)

FPS = 20
N_FRAMES = 8
TOL = 1.5 / FPS
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

REPOS = {"so101": "armnet/armnetbench_v01_lerobot_so101",
         "bimanual": "armnet/armnetbench_v01_lerobot_bimanual_so101"}
PILOT = {"so101": ("cable_clip", "Push the Displayport cable into the cable holder on the white block",
                   "observation.images.front"),
         "bimanual": ("fold_tea_towel", "Fold the brown tea towel", "observation.images.top")}
REVSNAP = json.load(open(os.path.join(SCRATCH, "download_plan.json"), encoding="utf-8"))
try:
    SIZEV = json.load(open(os.path.join(SCRATCH, "size_verification_pilot.json"), encoding="utf-8"))["verdict"]
except Exception:
    SIZEV = {}

torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False
try:
    torch.use_deterministic_algorithms(True)
    print("deterministic algorithms: ON")
except Exception as e:
    print("deterministic algorithms OFF:", e)
DEV = "cuda" if torch.cuda.is_available() else "cpu"
print("device:", DEV, torch.cuda.get_device_name(0) if DEV == "cuda" else "")


def task_str(v):
    if isinstance(v, (list, np.ndarray)):
        return "|".join(map(str, v))
    return str(v)


def preprocess(frame_rgb_uint8):
    im = Image.fromarray(frame_rgb_uint8, mode="RGB")
    w, h = im.size
    s = 224 / min(w, h)
    nw, nh = int(round(w * s)), int(round(h * s))
    im = im.resize((nw, nh), Image.Resampling.BILINEAR)
    left = (nw - 224) // 2
    top = (nh - 224) // 2
    im = im.crop((left, top, left + 224, top + 224))
    a = np.asarray(im, dtype=np.float32) / 255.0
    a = (a - IMAGENET_MEAN) / IMAGENET_STD
    return torch.from_numpy(a.transpose(2, 0, 1).copy())


def load_episodes(short):
    lp = os.path.join(CACHE_ROOT, short)
    fs = []
    for dirpath, _, filenames in os.walk(os.path.join(lp, "meta", "episodes")):
        for fn in filenames:
            if fn.endswith(".parquet"):
                fs.append(pd.read_parquet(os.path.join(dirpath, fn)))
    e = pd.concat(fs, ignore_index=True)
    e["task_str"] = e["tasks"].map(task_str)
    roll = e[e["policy_repo_id"].astype(str).str.len() > 0].copy()
    shortname, task, camera = PILOT[short]
    sub = roll[roll["task_str"] == task].sort_values("episode_index").reset_index(drop=True)
    return sub, shortname, task, camera


def extract_file(short, camera, chunk, file_index, rows, buf):
    vpath = os.path.join(CACHE_ROOT, short, "videos", camera,
                         f"chunk-{int(chunk):03d}", f"file-{int(file_index):03d}.mp4")
    targets = {}
    for _, r in rows.iterrows():
        n = int(r["length"])
        from_ts = float(r[f"videos/{camera}/from_timestamp"])
        key = f"{short}|{int(r['episode_index'])}"
        targets[key] = [(from_ts + (k * n // N_FRAMES) / FPS, k) for k in range(N_FRAMES)]
    import av
    cont = av.open(vpath, "r")
    st = cont.streams.video[0]
    matched = {k: {} for k in targets}
    tlist = sorted((ts, key, k) for key, ts_k in targets.items() for ts, k in ts_k)
    ti = 0
    n_decoded = 0
    t0 = time.time()
    for frame in cont.decode(st):
        t = frame.time
        if t is None:
            continue
        n_decoded += 1
        while ti < len(tlist) and tlist[ti][0] < t - TOL:
            ti += 1
        if ti < len(tlist):
            ts, key, k = tlist[ti]
            if abs(t - ts) <= TOL:
                matched[key][k] = frame.to_ndarray(format="rgb24")
                ti += 1
        if ti >= len(tlist):
            break
    cont.close()
    dt = time.time() - t0
    full = sum(1 for k in matched if len(matched[k]) == N_FRAMES)
    print(f"  file {chunk}/{file_index}: decoded {n_decoded} frames in {dt:.1f}s, "
          f"episodes full={full}/{len(matched)}")
    for key, frames in matched.items():
        if len(frames) < N_FRAMES:
            continue
        toks = [preprocess(frames[k]) for k in range(N_FRAMES)]
        buf.append((key, toks))
    return {k: len(v) for k, v in matched.items()}


@torch.inference_mode()
def encode_all(buf, model, frag_name):
    row_slices, batch, meta_rows, out_X = [], [], [], []
    row_base = 0
    enc_t0 = time.time()

    def flush():
        nonlocal row_base
        if not batch:
            return
        x = torch.stack(batch).to(DEV)
        out = model(pixel_values=x).last_hidden_state[:, 0, :]
        out_X.append(out.cpu().numpy().astype(np.float32))
        for key, ntok in meta_rows:
            row_slices.append((key, row_base, row_base + ntok))
            row_base += ntok
        meta_rows.clear()
        batch.clear()

    for key, toks in buf:
        batch.extend(toks)
        meta_rows.append((key, len(toks)))
        if len(batch) >= 64:
            flush()
    flush()
    dt = time.time() - enc_t0
    X = np.concatenate(out_X, axis=0)
    assert X.shape[0] == row_base, (X.shape, row_base)
    per = {}
    for key, s, e in row_slices:
        per.setdefault(key, []).extend(range(s, e))
    feats, miss = [], []
    for key in sorted(per):
        idxs = per[key]
        if len(idxs) != N_FRAMES:
            miss.append((key, len(idxs)))
        v = X[idxs].mean(axis=0)
        nv = np.linalg.norm(v)
        feats.append(v / (nv + 1e-12))
    Z = np.stack(feats).astype(np.float32)
    np.savez_compressed(os.path.join(FRAG_DIR, frag_name), Z=Z,
                        keys=np.array([str(k) for k in sorted(per)]))
    print(f"  encoded {row_base} frames -> {len(feats)} episode vectors in {dt:.1f}s "
          f"({len(feats)/max(dt,1e-9):.0f} eps/s), degraded={len(miss)}")
    return sorted(per), miss


def main():
    from huggingface_hub import HfApi
    api = HfApi()
    model_rev = api.model_info("facebook/dinov2-small").sha
    t_model = time.time()
    from transformers import AutoModel, AutoImageProcessor
    proc = AutoImageProcessor.from_pretrained("facebook/dinov2-small")
    model = AutoModel.from_pretrained("facebook/dinov2-small").to(DEV).eval()
    print(f"model facebook/dinov2-small rev={model_rev} loaded in {time.time()-t_model:.1f}s; "
          f"processor={proc.__class__.__name__} (manual PIL pipeline, processor unused)")
    if DEV == "cuda":
        torch.cuda.reset_peak_memory_stats()

    meta_all = []
    t_all = time.time()
    coverage_all = {}
    for short in ["so101", "bimanual"]:
        sub, shortname, task, camera = load_episodes(short)
        print(f"[{short}] {shortname}: {len(sub)} rollout episodes, camera={camera}")
        rev = ""
        frag = f"pilot_{shortname}_{rev[:8]}.npz"
        groups = sub.groupby([f"videos/{camera}/chunk_index", f"videos/{camera}/file_index"])
        buf = []
        coverage = {}
        dropped_files = []
        for (ck, fi), rows in groups:
            vpath = os.path.join(CACHE_ROOT, short, "videos", camera,
                                 f"chunk-{int(ck):03d}", f"file-{int(fi):03d}.mp4")
            key = f"{short}/{os.path.relpath(vpath, os.path.join(CACHE_ROOT, short)).replace(os.sep, '/')}"
            remote = SIZEV.get(key, {}).get("remote", -1)
            if not os.path.exists(vpath) or (remote >= 0 and os.path.getsize(vpath) != remote):
                dropped_files.append((int(ck), int(fi), len(rows)))
                continue
            cov = extract_file(short, camera, ck, fi, rows, buf)
            for k, n in cov.items():
                coverage[k] = n
        if dropped_files:
            print(f"  [WARN] skipped incomplete/absent files: {dropped_files}")
        keys, miss = encode_all(buf, model, frag)
        keep = sub[[c for c in ["episode_index", "task_str", "policy_type", "policy_repo_id",
                               "success", "success_class", "length"] if c in sub.columns]].copy()
        keep["repo"] = short
        keep["shortname"] = shortname
        keep["camera"] = camera
        keep["row_id"] = keep["repo"] + "|" + keep["episode_index"].astype(int).astype(str)
        keep["frames_matched"] = keep["row_id"].map(lambda k: coverage.get(k, 0))
        before = len(keep)
        keep = keep[keep["frames_matched"] == N_FRAMES].reset_index(drop=True)
        print(f"  episodes with full {N_FRAMES}-frame coverage: {len(keep)}/{before}")
        coverage_all[shortname] = {"in_scope": int(before), "covered": int(len(keep)),
                                   "dropped_files": dropped_files}
        meta_all.append(keep)

    meta = pd.concat(meta_all, ignore_index=True)
    meta.to_csv(os.path.join(FRAG_DIR, "pilot_episodes.csv"), index=False)
    total_s = time.time() - t_all
    print(f"TOTAL extraction time {total_s:.1f}s")
    peak = torch.cuda.max_memory_allocated() / 2**20 if DEV == "cuda" else 0
    print(f"peak GPU mem allocated: {peak:.0f} MiB")
    json.dump({"model_revision": model_rev, "total_seconds": round(total_s, 1),
               "peak_gpu_mib": round(float(peak), 0), "device": DEV,
               "frames_per_episode": N_FRAMES, "camera": {s: PILOT[s][2] for s in PILOT},
               "coverage": coverage_all},
              open(os.path.join(SCRATCH, "extract_cost_pilot.json"), "w", encoding="utf-8"), indent=1)
    zero = meta[meta["frames_matched"] < N_FRAMES]
    print(f"episodes with <{N_FRAMES} matched frames: {len(zero)}")
    if len(zero):
        print(zero.head(20).to_string())
    print("PILOT EXTRACTION DONE")


if __name__ == "__main__":
    main()
