# -*- coding: utf-8 -*-
"""Verify local file completeness against HF real Content-Length (Content-Range total).

Root cause hypothesis for the 6 attempts_exhausted files: download_plan_min.json stores
`mib` rounded to 1 decimal; int(mib * 2**20) overshoots the true byte size by 3-50KB,
so `cur >= expect` can never trigger and the trailing Range request gets 416.
This script fetches the authoritative size (Content-Range: bytes 0-0/TOTAL) for every
planned file and compares with local size; fixes the plan's mib to the exact value.
"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor

import requests

PROJECT = "D:/hermes-data/research/审计真机基准的策略身份混淆-18c6f2b0"
SCRIPTS = os.path.join(PROJECT, "experiments", "scripts")
CACHE_ROOT = os.path.join(PROJECT, "assets", "hf")

REPOS = {"so101": "armnet/armnetbench_v01_lerobot_so101",
         "bimanual": "armnet/armnetbench_v01_lerobot_bimanual_so101"}
plan = json.load(open(os.path.join(SCRIPTS, "download_plan_min.json"), encoding="utf-8"))


def remote_size(repo, path):
    url = f"https://huggingface.co/datasets/{repo}/resolve/main/{path}"
    r = requests.get(url, headers={"Range": "bytes=0-0"}, timeout=(10, 25), allow_redirects=True)
    if r.status_code == 206 and "Content-Range" in r.headers:
        return int(r.headers["Content-Range"].split("/")[-1])
    if r.status_code == 200:
        return int(r.headers.get("Content-Length", -1))
    return -1


jobs = []
for short, entry in plan.items():
    for f in entry["files"]:
        jobs.append((short, REPOS[short], f["path"]))

with ThreadPoolExecutor(max_workers=6) as ex:
    sizes = dict(zip([j[2] for j in jobs], list(ex.map(lambda j: remote_size(j[1], j[2]), jobs))))

changed = 0
verdict = {}
for short, entry in plan.items():
    for f in entry["files"]:
        lp = os.path.join(CACHE_ROOT, short, f["path"])
        local = os.path.getsize(lp) if os.path.exists(lp) else -1
        remote = sizes.get(f["path"], -1)
        status = "ok" if (remote >= 0 and local == remote) else ("incomplete" if remote >= 0 else "remote_unreachable")
        verdict[f"{short}/{f['path']}"] = {"local": local, "remote": remote, "status": status,
                                           "plan_mib": f["mib"]}
        if remote >= 0 and local == remote and f["mib"] * 2**20 != remote:
            f["mib"] = remote / 2**20  # exact bytes from HF, removes rounding overshoot
            changed += 1

json.dump(plan, open(os.path.join(SCRIPTS, "download_plan_min.json"), "w", encoding="utf-8"), indent=1)
json.dump({"verified_with": "HTTP Range Content-Range total against huggingface.co/datasets/resolve",
           "plan_mib_fixed_entries": changed, "verdict": verdict},
          open(os.path.join(SCRIPTS, "size_verification.json"), "w", encoding="utf-8"), indent=1)
n_ok = sum(1 for v in verdict.values() if v["status"] == "ok")
print(f"verified {n_ok}/{len(verdict)} files complete (plan mib fixed on {changed})")
for k, v in verdict.items():
    if v["status"] != "ok":
        print("NOT COMPLETE:", k, v)
