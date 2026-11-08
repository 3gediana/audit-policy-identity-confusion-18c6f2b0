# -*- coding: utf-8 -*-
"""Bulk download of scope-reduced pilot video files (background job, resumable, retried)."""
import json, os, sys, time

sys.stdout.reconfigure(line_buffering=True)
SCRATCH = os.path.dirname(os.path.abspath(__file__))
PROJECT = "D:/hermes-data/research/审计真机基准的策略身份混淆-18c6f2b0"
CACHE_ROOT = os.path.join(PROJECT, "assets", "hf")
plan = json.load(open(os.path.join(SCRATCH, "download_plan_min.json"), encoding="utf-8"))
t_start = time.time()
from huggingface_hub import snapshot_download

report = {}
for short in ["so101", "bimanual"]:
    entry = plan[short]
    patterns = [f["path"] for f in entry["files"]]
    local = os.path.join(CACHE_ROOT, short)
    need = sum(f["need_mib"] for f in entry["files"])
    print(f"downloading {short}: {len(patterns)} files, {need/1024:.2f} GiB new")
    dt = 0.0
    for attempt in range(4):
        t0 = time.time()
        try:
            snapshot_download(entry["repo"], repo_type="dataset", local_dir=local,
                              allow_patterns=patterns, max_workers=6, etag_timeout=30)
            dt += time.time() - t0
            break
        except Exception as e:
            dt += time.time() - t0
            print(f"  attempt {attempt+1} failed ({type(e).__name__}: {str(e)[:120]}), retrying...")
            time.sleep(5)
    ok, missing, size_mismatch = 0, [], []
    got_bytes = 0
    for f in entry["files"]:
        p = os.path.join(local, f["path"])
        if os.path.exists(p):
            sz = os.path.getsize(p) / 2**20
            got_bytes += sz
            if f["mib"] and abs(sz - f["mib"]) > max(1.0, f["mib"] * 0.02):
                size_mismatch.append((f["path"], round(sz, 1), f["mib"]))
            else:
                ok += 1
        else:
            missing.append(f["path"])
    report[short] = {"files_ok": ok, "missing": missing, "size_mismatch": size_mismatch,
                     "download_seconds": round(dt, 1), "got_gib": round(got_bytes / 1024, 2)}
    print(f"[{short}] ok={ok}/{len(patterns)} missing={len(missing)} "
          f"mismatch={len(size_mismatch)} in {dt:.0f}s")
    if missing or size_mismatch:
        print(f"  missing: {missing[:4]}")
        print(f"  mismatch: {size_mismatch[:4]}")

report["total_seconds"] = round(time.time() - t_start, 1)
json.dump(report, open(os.path.join(SCRATCH, "download_report_min.json"), "w"), indent=1)
print("BULK DOWNLOAD DONE", json.dumps(report))
