# -*- coding: utf-8 -*-
"""Smoke feature extraction: DINOv2-small CLS mean-pool over 8 uniform frames/episode.

Frozen pipeline per experiments/protocol.md:
- frame rule: idx_k = floor(k*N/8), k=0..7 (N = episode length, fps=20); includes first frame,
  does not deliberately include the last frame.
- target timestamp in concatenated video file: from_ts + idx_k / fps; nearest decoded frame
  within tolerance 1.5 frame periods (0.075 s), two-pointer first-match.
- preprocessing: RGB -> resize shortest side 224 (PIL bilinear) -> center crop 224x224 ->
  float32 /255 -> ImageNet mean/std.
- encoder: facebook/dinov2-small, CLS token, fp32, cuda, eval mode, deterministic algorithms.
- episode feature: mean of the 8 CLS vectors, then L2 normalize.
"""
import os, sys, json, time
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
sys.stdout.reconfigure(line_buffering=True)

import numpy as np
import pandas as pd
from PIL import Image
import torch
from huggingface_hub import HfApi, hf_hub_download

SCRATCH = os.path.dirname(os.path.abspath(__file__))
PROJECT = "D:/hermes-data/research/审计真机基准的策略身份混淆-18c6f2b0"
CACHE_ROOT = os.path.join(PROJECT, "assets", "hf")
FRAG_DIR = os.path.join(PROJECT, "experiments", "cache")
os.makedirs(FRAG_DIR, exist_ok=True)

FPS = 20
N_FRAMES = 8
TOL = 1.5 / FPS  # 0.075 s
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

REPOS = {
    "so101": "armnet/armnetbench_v01_lerobot_so101",
    "bimanual": "armnet/armnetbench_v01_lerobot_bimanual_so101",
}
PILOT = {
    "so101": ("cable_clip", "Push the Displayport cable into the cable holder on the white block",
              "observation.images.front"),
    "bimanual": ("fold_tea_towel", "Fold the brown tea towel", "observation.images.top"),
}
REVSNAP = json.load(open(os.path.join(SCRATCH, "download_plan_min.json"), encoding="utf-8"))

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
    return torch.from_numpy(a.transpose(2, 0, 1).copy())  # 3x224x224


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


def extract_file(short, repo, camera, chunk, file_index, rows, model, buf):
    """Decode one video file, match target frames, fill buf[epkey] with frame tensors."""
    local = os.path.join(CACHE_ROOT, short)
    vpath = os.path.join(local, "videos", camera, f"chunk-{int(chunk):03d}", f"file-{int(file_index):03d}.mp4")
    # epkey -> list of (target_ts, k)
    targets = {}
    for _, r in rows.iterrows():
        n = int(r["length"])
        from_ts = float(r[f"videos/{camera}/from_timestamp"])
        key = (int(r["episode_index"]), r["task_str"], str(r["policy_type"]))
        targets[key] = [(from_ts + (k * n // N_FRAMES) / FPS, k) for k in range(N_FRAMES)]
    import av
    cont = av.open(vpath, "r")
    st = cont.streams.video[0]
    matched = {k: {} for k in targets}  # key -> {frame_k: np.array}
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
            ti += 1  # missed target (no frame within tolerance before t)
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
        toks = []
        for k in range(N_FRAMES):
            toks.append(preprocess(frames[k]))
        buf.append((key, toks, (int(chunk), int(file_index))))
    return {k: len(v) for k, v in matched.items()}


@torch.inference_mode()
def encode_all(buf, model, out_X, out_meta, frag_name):
    # row_slices: (key, start, end) absolute row indices into the concatenated frame matrix X
    row_slices, batch, meta_rows = [], [], []
    row_base = 0
    enc_t0 = time.time()

    def flush():
        nonlocal row_base
        if not batch:
            return
        x = torch.stack(batch).to(DEV)
        out = model(pixel_values=x).last_hidden_state[:, 0, :]
        out_X.append(out.cpu().numpy().astype(np.float32))
        for key, ntok, _ in meta_rows:
            row_slices.append((key, row_base, row_base + ntok))
            row_base += ntok
        meta_rows.clear()
        batch.clear()

    covered = set()
    for key, toks, fidx in buf:
        batch.extend(toks)
        meta_rows.append((key, len(toks), fidx))
        covered.add(key)
        if len(batch) >= 64:
            flush()
    flush()
    dt = time.time() - enc_t0
    X = np.concatenate(out_X, axis=0)
    assert X.shape[0] == row_base, (X.shape, row_base)
    # mean over the 8 CLS vectors of each episode, then L2 normalize
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
    api = HfApi()
    model_rev = api.model_info("facebook/dinov2-small").sha
    t_model = time.time()
    from transformers import AutoModel, AutoImageProcessor
    proc = AutoImageProcessor.from_pretrained("facebook/dinov2-small")
    model = AutoModel.from_pretrained("facebook/dinov2-small").to(DEV).eval()
    print(f"model facebook/dinov2-small rev={model_rev} loaded in {time.time()-t_model:.1f}s; "
          f"processor={proc.__class__.__name__} (protocol uses manual PIL pipeline, processor unused)")
    if DEV == "cuda":
        torch.cuda.reset_peak_memory_stats()

    meta_all = []
    t_all = time.time()
    for short in ["so101", "bimanual"]:
        repo = REPOS[short]
        sub, shortname, task, camera = load_episodes(short)
        print(f"[{short}] {shortname}: {len(sub)} rollout episodes, camera={camera}")
        rev = REVSNAP.get(short, {}).get("revision", "")
        frag = f"smoke_{shortname}_{rev[:8]}.npz"
        frag_path = os.path.join(FRAG_DIR, frag)
        if os.path.exists(frag_path):
            print(f"  fragment exists, skip: {frag}")
            continue
        groups = sub.groupby(["videos/%s/chunk_index" % camera, "videos/%s/file_index" % camera])
        buf = []
        coverage = {}
        dropped_files = []
        for (ck, fi), rows in groups:
            vpath = os.path.join(CACHE_ROOT, short, "videos", camera,
                                 f"chunk-{int(ck):03d}", f"file-{int(fi):03d}.mp4")
            exp = None
            for f in REVSNAP[short]["files"]:
                if f["file_index"] == int(fi):
                    exp = f["mib"]
                    break
            if not os.path.exists(vpath) or (exp and abs(os.path.getsize(vpath) / 2**20 - exp) > max(1.0, exp * 0.02)):
                dropped_files.append((int(ck), int(fi), len(rows)))
                continue
            cov = extract_file(short, repo, camera, ck, fi, rows, model, buf)
            for key, n in cov.items():
                coverage[str(key)] = n
        if dropped_files:
            print(f"  [WARN] skipped incomplete/absent files: {dropped_files}")
        keys, miss = encode_all(buf, model, [], meta_all, frag)
        # rebuild meta rows from sub
        keep = sub[[c for c in ["episode_index", "task_str", "policy_type", "policy_repo_id",
                                "success", "success_class", "length"] if c in sub.columns]].copy()
        keep["repo"] = short
        keep["shortname"] = shortname
        keep["camera"] = camera
        keep["frames_matched"] = keep["episode_index"].map(
            lambda ei: coverage.get(str((int(ei), keep.loc[keep["episode_index"] == ei, "task_str"].iloc[0], keep.loc[keep["episode_index"] == ei, "policy_type"].iloc[0])), 0))
        before = len(keep)
        keep = keep[keep["frames_matched"] == N_FRAMES].reset_index(drop=True)
        print(f"  episodes in scope after file completeness filter: {len(keep)}/{before}")
        meta_all.append(keep)

    meta = pd.concat(meta_all, ignore_index=True)
    meta.to_csv(os.path.join(FRAG_DIR, "smoke_episodes.csv"), index=False)
    total_s = time.time() - t_all
    print(f"TOTAL extraction time {total_s:.1f}s")
    peak = torch.cuda.max_memory_allocated() / 2**20 if DEV == "cuda" else 0
    print(f"peak GPU mem allocated: {peak:.0f} MiB")
    json.dump({"model_revision": model_rev, "total_seconds": round(total_s, 1),
               "peak_gpu_mib": round(float(peak), 0), "device": DEV,
               "frames_per_episode": N_FRAMES, "camera": {s: PILOT[s][2] for s in PILOT}},
              open(os.path.join(SCRATCH, "extract_cost.json"), "w", encoding="utf-8"), indent=1)
    zero = meta[meta["frames_matched"] < N_FRAMES]
    print(f"episodes with <{N_FRAMES} matched frames: {len(zero)}")
    if len(zero):
        print(zero.to_string())
        sys.exit(3)
    print("EXTRACTION DONE")


if __name__ == "__main__":
    main()
