# -*- coding: utf-8 -*-
"""Verify the FULL pilot expansion manifest (download_plan.json, both tasks, all files)
against HF authoritative Content-Range byte totals. Same rule as smoke verify_files.py.

Writes size_verification_pilot.json. Exit code 1 if any file is not byte-complete.
"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor

import requests

sys.stdout.reconfigure(line_buffering=True)
SCRATCH = os.path.dirname(os.path.abspath(__file__))
PROJECT = "D:/hermes-data/research/审计真机基准的策略身份混淆-18c6f2b0"
CACHE_ROOT = os.path.join(PROJECT, "assets", "hf")

REPOS = {"so101": "armnet/armnetbench_v01_lerobot_so101",
         "bimanual": "armnet/armnetbench_v01_lerobot_bimanual_so101"}
plan = json.load(open(os.path.join(SCRATCH, "download_plan.json"), encoding="utf-8"))


def remote_size(repo, path):
    url = f"https://huggingface.co/datasets/{repo}/resolve/main/{path}"
    for _ in range(3):
        try:
            r = requests.get(url, headers={"Range": "bytes=0-0"}, timeout=(10, 25),
                             allow_redirects=True)
            if r.status_code == 206 and "Content-Range" in r.headers:
                return int(r.headers["Content-Range"].split("/")[-1])
            if r.status_code == 200:
                return int(r.headers.get("Content-Length", -1))
        except requests.RequestException:
            pass
    return -1


jobs = []
for short, entry in plan.items():
    for f in entry["files"]:
        jobs.append((short, REPOS[short], f["path"]))

with ThreadPoolExecutor(max_workers=6) as ex:
    sizes = dict(zip([j[2] for j in jobs],
                     list(ex.map(lambda j: remote_size(j[1], j[2]), jobs))))

verdict = {}
for short, entry in plan.items():
    for f in entry["files"]:
        lp = os.path.join(CACHE_ROOT, short, f["path"])
        local = os.path.getsize(lp) if os.path.exists(lp) else -1
        remote = sizes.get(f["path"], -1)
        status = "ok" if (remote >= 0 and local == remote) else (
            "incomplete" if remote >= 0 else "remote_unreachable")
        verdict[f"{short}/{f['path']}"] = {"local": local, "remote": remote, "status": status,
                                           "task": entry["shortname"], "eps": f.get("eps", -1)}

json.dump({"verified_with": "HTTP Range Content-Range total against huggingface.co/datasets/resolve",
           "manifest": "download_plan.json (full pilot expansion, 2 tasks)",
           "verdict": verdict},
          open(os.path.join(SCRATCH, "size_verification_pilot.json"), "w"), indent=1)
n_ok = sum(1 for v in verdict.values() if v["status"] == "ok")
print(f"verified {n_ok}/{len(verdict)} files complete")
for k, v in verdict.items():
    if v["status"] != "ok":
        print("NOT COMPLETE:", k, v)
sys.exit(0 if n_ok == len(verdict) else 1)
