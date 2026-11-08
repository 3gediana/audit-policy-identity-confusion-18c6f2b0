# -*- coding: utf-8 -*-
"""Check download/checkpoint status before resuming the smoke pipeline."""
import json, os, sys

PROJECT = "D:/hermes-data/research/审计真机基准的策略身份混淆-18c6f2b0"
SCRIPTS = os.path.join(PROJECT, "experiments", "scripts")
CACHE_ROOT = os.path.join(PROJECT, "assets", "hf")
FRAG_DIR = os.path.join(PROJECT, "experiments", "cache")

plan = json.load(open(os.path.join(SCRIPTS, "download_plan_min.json"), encoding="utf-8"))
print("== plan ==")
tot_mib = 0
for short, entry in plan.items():
    files = entry["files"]
    tot_mib += sum(f["mib"] for f in files)
    print(f"{short}: repo={entry['repo']} rev={entry.get('revision','')[:10]} "
          f"n_files={len(files)} n_mib={sum(f['mib'] for f in files):.0f} "
          f"task={entry.get('task')} camera={entry.get('camera')} eps={entry.get('episodes_covered')}")

print("\n== video files on disk ==")
for short, entry in plan.items():
    ok = part = miss = 0
    part_list = []
    for f in entry["files"]:
        lp = os.path.join(CACHE_ROOT, short, f["path"])
        expect = f["mib"] * 2**20
        if os.path.exists(lp):
            sz = os.path.getsize(lp)
            if sz >= expect:
                ok += 1
            else:
                part += 1
                part_list.append((f["path"], round(sz / 2**20, 1), round(expect / 2**20, 1)))
        else:
            miss += 1
    print(f"{short}: complete={ok} partial={part} missing={miss}")
    for p, sz, exp in part_list[:6]:
        print(f"   partial: {p} have={sz}MiB expect={exp}MiB")

print("\n== meta parquets ==")
for short in ["so101", "bimanual"]:
    d = os.path.join(CACHE_ROOT, short, "meta")
    n = 0
    if os.path.isdir(d):
        for dirpath, _, fns in os.walk(d):
            n += sum(1 for fn in fns if fn.endswith(".parquet"))
    print(f"{short}: meta parquet files = {n}")

print("\n== extraction fragments ==")
if os.path.isdir(FRAG_DIR):
    for fn in sorted(os.listdir(FRAG_DIR)):
        p = os.path.join(FRAG_DIR, fn)
        print(f"  {fn}  {os.path.getsize(p)/2**20:.1f}MiB")
else:
    print("  (no cache dir)")

print("\n== runtime artifacts in scripts dir ==")
for fn in ["fast_dl_report.json", "download_report_min.json", "extract_cost.json"]:
    p = os.path.join(SCRIPTS, fn)
    print(f"  {fn}: {'exists' if os.path.exists(p) else 'MISSING'}")

print("\n== env ==")
try:
    import torch
    print("torch", torch.__version__, "cuda_available", torch.cuda.is_available(),
          "device", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "-")
except Exception as e:
    print("torch FAIL:", e)
try:
    import sklearn, transformers, av, pandas, numpy, PIL
    print("sklearn", sklearn.__version__, "| transformers", transformers.__version__,
          "| av", av.__version__, "| pandas", pandas.__version__, "| numpy", numpy.__version__)
except Exception as e:
    print("deps FAIL:", e)
hf_cache = os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
print("HF_HOME:", hf_cache)
dinov2_cached = False
for root, dirs, files in os.walk(os.path.join(hf_cache, "hub")):
    if "dinov2-small" in root.lower() and any(f.endswith(".safetensors") or f.endswith(".bin") for f in files):
        dinov2_cached = True
        break
print("dinov2-small weights cached:", dinov2_cached)
