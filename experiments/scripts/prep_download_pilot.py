# -*- coding: utf-8 -*-
"""Build the pilot expansion download plan: full download_plan.json minus complete local files.

Fetches the authoritative remote byte size (HTTP Range Content-Range total) for every file
BEFORE download so fast_download_pilot.py never hits the mib-rounding 416 trap (smoke
implementation fix (3)). Writes download_plan_pilot.json (missing files only, exact bytes).
"""
import json, os, sys, time
from concurrent.futures import ThreadPoolExecutor

import requests

sys.stdout.reconfigure(line_buffering=True)
SCRATCH = os.path.dirname(os.path.abspath(__file__))
PROJECT = "D:/hermes-data/research/审计真机基准的策略身份混淆-18c6f2b0"
CACHE_ROOT = os.path.join(PROJECT, "assets", "hf")

REPO_SHORT = {"armnet/armnetbench_v01_lerobot_so101": "so101",
              "armnet/armnetbench_v01_lerobot_bimanual_so101": "bimanual"}

full = json.load(open(os.path.join(SCRATCH, "download_plan.json"), encoding="utf-8"))


def remote_size(repo, path):
    url = f"https://huggingface.co/datasets/{repo}/resolve/main/{path}"
    for attempt in range(3):
        try:
            r = requests.get(url, headers={"Range": "bytes=0-0"}, timeout=(10, 25),
                             allow_redirects=True)
            if r.status_code == 206 and "Content-Range" in r.headers:
                return int(r.headers["Content-Range"].split("/")[-1])
            if r.status_code == 200:
                return int(r.headers.get("Content-Length", -1))
        except requests.RequestException:
            time.sleep(2)
    return -1


t0 = time.time()
jobs = []
for short, entry in full.items():
    repo = entry["repo"]
    for f in entry["files"]:
        jobs.append((short, repo, f))

with ThreadPoolExecutor(max_workers=6) as ex:
    sizes = list(ex.map(lambda j: remote_size(j[1], j[2]["path"]), jobs))

out = {}
missing_bytes = 0
missing_files = 0
complete_files = 0
bad_remote = []
for (short, repo, f), remote in zip(jobs, sizes):
    out.setdefault(short, {"repo": repo, "shortname": full[short]["shortname"],
                           "task": full[short]["task"], "camera": full[short]["camera"],
                           "files": []})
    local = os.path.join(CACHE_ROOT, short, f["path"])
    lsize = os.path.getsize(local) if os.path.exists(local) else 0
    if remote < 0:
        bad_remote.append(f["path"])
        remote = int(f["mib"] * 2 ** 20)  # fall back to plan value, flagged
    if lsize == remote:
        complete_files += 1
        continue
    missing_files += 1
    missing_bytes += max(remote - lsize, 0)
    out[short]["files"].append({"path": f["path"], "bytes": remote, "local_bytes": lsize,
                               "eps": f.get("eps", -1), "file_index": f.get("file_index", -1)})

for short in out:
    out[short]["missing_files"] = len(out[short]["files"])
    out[short]["missing_gib"] = round(sum(x["bytes"] - x["local_bytes"]
                                          for x in out[short]["files"]) / 2**30, 3)
out["_summary"] = {"complete_files": complete_files, "missing_files": missing_files,
                   "missing_gib": round(missing_bytes / 2**30, 3),
                   "remote_size_unreachable_fallback_plan_mib": bad_remote,
                   "built_unix": int(time.time()),
                   "built_seconds": round(time.time() - t0, 1)}

json.dump(out, open(os.path.join(SCRATCH, "download_plan_pilot.json"), "w"), indent=1)
print(json.dumps(out["_summary"], indent=1))
print("PLAN PILOT WRITTEN:", {k: (len(v["files"]) if isinstance(v, dict) and "files" in v else v)
                              for k, v in out.items()})
