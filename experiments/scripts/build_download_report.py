# -*- coding: utf-8 -*-
"""Build download_report_min.json (aggregate input) from fast_dl logs + disk truth.

Contract required by aggregate_smoke.py: {short: {"got_gib": ..., "download_seconds": ...},
"total_seconds": ...} — no other top-level keys (aggregate iterates all keys except
total_seconds as shorts).
"""
import json, os, re, sys

PROJECT = "D:/hermes-data/research/审计真机基准的策略身份混淆-18c6f2b0"
SCRIPTS = os.path.join(PROJECT, "experiments", "scripts")
CACHE_ROOT = os.path.join(PROJECT, "assets", "hf")

plan = json.load(open(os.path.join(SCRIPTS, "download_plan_min.json"), encoding="utf-8"))

# measured downloader wall time: sum of every finished fast_download round this unit
dl_seconds = 0.0
for log in ["fast_dl_log.txt", "fast_dl_log2.txt"]:
    p = os.path.join(SCRIPTS, log)
    if os.path.exists(p):
        txt = open(p, encoding="utf-8", errors="replace").read()
        for m in re.findall(r"FAST DL DONE ok=\d+/\d+ in ([\d.]+)s", txt):
            dl_seconds += float(m)

out = {"total_seconds": round(dl_seconds, 1)}
all_ok = True
for short, entry in plan.items():
    got_bytes = 0
    ok = part = 0
    for f in entry["files"]:
        lp = os.path.join(CACHE_ROOT, short, f["path"])
        expect = f["mib"] * 2**20
        if os.path.exists(lp):
            sz = os.path.getsize(lp)
            got_bytes += sz
            if sz >= expect:
                ok += 1
            else:
                part += 1
        else:
            part += 1
    out[short] = {
        "got_gib": round(got_bytes / 2**30, 3),
        "files_complete": ok,
        "files_total": len(entry["files"]),
        "download_seconds": round(dl_seconds, 1),
    }
    if part:
        all_ok = False

with open(os.path.join(SCRIPTS, "download_report_min.json"), "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=1)
print(json.dumps(out, indent=1))
if not all_ok:
    print("INCOMPLETE FILES PRESENT")
    sys.exit(2)
print("DOWNLOAD REPORT OK")
