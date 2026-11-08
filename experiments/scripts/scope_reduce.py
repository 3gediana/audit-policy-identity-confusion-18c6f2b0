# -*- coding: utf-8 -*-
"""Scope-reduce: minimal video file set covering >=MIN_EPS episodes per (task,policy) cell,
greedy by episodes-per-MB (meta inventory only; no result-based selection)."""
import json, os
import numpy as np
import pandas as pd
from huggingface_hub import HfApi

SCRATCH = os.path.dirname(os.path.abspath(__file__))
PROJECT = "D:/hermes-data/research/审计真机基准的策略身份混淆-18c6f2b0"
CACHE_ROOT = os.path.join(PROJECT, "assets", "hf")
REPOS = {
    "so101": "armnet/armnetbench_v01_lerobot_so101",
    "bimanual": "armnet/armnetbench_v01_lerobot_bimanual_so101",
}
PILOT = {
    "so101": ("cable_clip", "Push the Displayport cable into the cable holder on the white block",
              "observation.images.front"),
    "bimanual": ("fold_tea_towel", "Fold the brown tea towel", "observation.images.top"),
}
MIN_EPS = 10
api = HfApi()


def repo_info_retry(repo, attempts=5):
    import time as _t
    last = None
    for i in range(attempts):
        try:
            return api.repo_info(repo, repo_type="dataset", files_metadata=True, timeout=60)
        except Exception as e:
            last = e
            print(f"  repo_info attempt {i+1} failed: {type(e).__name__}; retry in 6s")
            _t.sleep(6)
    # fallback: re-exec via mirror endpoint
    print("  origin API failed repeatedly; retrying once via HF_ENDPOINT=hf-mirror.com")
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    os.execve(sys.executable, [sys.executable, os.path.abspath(__file__)],
              {**os.environ})

plan_min = {}
for short, repo in REPOS.items():
    shortname, task, camera = PILOT[short]
    lp = os.path.join(CACHE_ROOT, short)
    fs = []
    for dirpath, _, filenames in os.walk(os.path.join(lp, "meta", "episodes")):
        for fn in filenames:
            if fn.endswith(".parquet"):
                fs.append(pd.read_parquet(os.path.join(dirpath, fn)))
    e = pd.concat(fs, ignore_index=True)
    e["task_str"] = e["tasks"].map(lambda v: "|".join(map(str, v)) if isinstance(v, (list, np.ndarray)) else str(v))
    roll = e[e["policy_repo_id"].astype(str).str.len() > 0]
    sub = roll[roll["task_str"] == task].copy()
    sub["vfile"] = sub["videos/%s/file_index" % camera].astype(int)
    # already-complete local files (from earlier probes) count as free
    def have_eps_of_file(fi):
        p = os.path.join(lp, "videos", camera, "chunk-000", f"file-{int(fi):03d}.mp4")
        if not os.path.exists(p):
            return 0
        # count episodes of THIS task in that file
        return 0  # placeholder; handled below via sizes=0
    rinfo = repo_info_retry(repo)
    sizes = {s.rfilename: (s.size or 0) for s in (rinfo.siblings or [])}
    # per cell: file -> eps count
    cells = {}
    for pt, g in sub.groupby("policy_type"):
        by_file = g.groupby("vfile").size().to_dict()
        cells[pt] = by_file
    chosen = set()
    cell_report = {}
    for pt, by_file in sorted(cells.items()):
        got, pick = 0, []
        # files already fully present locally cost 0 bytes
        cand = []
        for fi, n in by_file.items():
            p = os.path.join(lp, "videos", camera, "chunk-000", f"file-{int(fi):03d}.mp4")
            local_mb = os.path.getsize(p) / 2**20 if os.path.exists(p) else None
            remote_mb = sizes.get(f"videos/{camera}/chunk-000/file-{int(fi):03d}.mp4", 0) / 2**20
            eff_mb = 0 if (local_mb and abs(local_mb - remote_mb) < max(1.0, remote_mb * 0.02)) else remote_mb
            cand.append((fi, int(n), eff_mb))
        cand.sort(key=lambda x: (-(x[1] / max(x[2], 0.1))))  # eps per MB desc
        for fi, n, mb in cand:
            if got >= MIN_EPS:
                break
            pick.append((fi, n, mb))
            got += n
        cell_report[pt] = {"cell_total": int(sum(by_file.values())), "picked_eps": int(got),
                           "files": [[int(fi), int(n), round(mb, 1)] for fi, n, mb in pick]}
        for fi, n, mb in pick:
            chosen.add(int(fi))
    files = []
    total_mb = 0.0
    for fi in sorted(chosen):
        p = f"videos/{camera}/chunk-000/file-{int(fi):03d}.mp4"
        local_mb = os.path.getsize(os.path.join(lp, p)) / 2**20 if os.path.exists(
            os.path.join(lp, p)) else 0
        remote_mb = sizes.get(p, 0) / 2**20
        need_mb = 0 if (local_mb and abs(local_mb - remote_mb) < max(1.0, remote_mb * 0.02)) else remote_mb
        eps_here = sum(int(n) for pt in cells for fi2, n in cells[pt].items() if int(fi2) == fi)
        files.append({"path": p, "file_index": fi, "mib": round(remote_mb, 1),
                      "need_mib": round(need_mb, 1), "eps": eps_here})
        total_mb += need_mb
    eps_covered = len(sub[sub["vfile"].isin(chosen)])
    print(f"[{short}] chosen {len(chosen)} files, need {total_mb/1024:.2f} GiB new, "
          f"covers {eps_covered}/{len(sub)} episodes (>= {MIN_EPS}/cell)")
    for pt, r in sorted(cell_report.items()):
        print(f"   {pt:10s} cell={r['cell_total']:3d} picked={r['picked_eps']:3d} files={len(r['files'])}")
    plan_min[short] = {"repo": repo, "shortname": shortname, "task": task, "camera": camera,
                       "episodes_covered": int(eps_covered), "episodes_total": int(len(sub)),
                       "min_eps_per_cell": MIN_EPS, "files": files,
                       "need_gib": round(total_mb / 1024, 2)}

json.dump(plan_min, open(os.path.join(SCRATCH, "download_plan_min.json"), "w"), indent=1)
print("total new download needed:", sum(v["need_gib"] for v in plan_min.values()), "GiB")
