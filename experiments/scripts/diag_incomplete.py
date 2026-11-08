# -*- coding: utf-8 -*-
"""Diagnose attempts_exhausted files: exact bytes vs plan expect."""
import json, os

PROJECT = "D:/hermes-data/research/审计真机基准的策略身份混淆-18c6f2b0"
SCRIPTS = os.path.join(PROJECT, "experiments", "scripts")
CACHE_ROOT = os.path.join(PROJECT, "assets", "hf")

plan = json.load(open(os.path.join(SCRIPTS, "download_plan_min.json"), encoding="utf-8"))
rep = json.load(open(os.path.join(SCRIPTS, "fast_dl_report.json"), encoding="utf-8"))

for short, entry in plan.items():
    for f in entry["files"]:
        st = rep["results"].get(f["path"], {}).get("status")
        if st == "ok":
            continue
        lp = os.path.join(CACHE_ROOT, short, f["path"])
        have = os.path.getsize(lp) if os.path.exists(lp) else -1
        expect = int(f["mib"] * 2**20)
        print(f"{st:20s} {short}/{f['path']}  have={have}  expect={expect}  diff={expect-have}")
