# -*- coding: utf-8 -*-
"""Aggregate smoke results: schema snapshot, config, controls verdict, cost, README.

Reads: results/smoke_probe_run_{A,B,C}.json, meta parquets, download_plan_min.json,
download_report_min.json, extraction log figures passed via extract_cost.json.
Writes the preregistered results files into the project results/ dir.
Gates are frozen in experiments/prereg.md and are NOT recomputed here beyond evaluating them.
"""
import hashlib, json, os, platform, sys, time

import numpy as np
import pandas as pd

SCRATCH = os.path.dirname(os.path.abspath(__file__))
PROJECT = "D:/hermes-data/research/审计真机基准的策略身份混淆-18c6f2b0"
RESULTS = os.path.join(PROJECT, "results")
CACHE_ROOT = os.path.join(PROJECT, "assets", "hf")
REPOS = {"so101": "armnet/armnetbench_v01_lerobot_so101",
         "bimanual": "armnet/armnetbench_v01_lerobot_bimanual_so101"}
plan = json.load(open(os.path.join(SCRATCH, "download_plan_min.json"), encoding="utf-8"))
report = json.load(open(os.path.join(SCRATCH, "download_report_min.json"), encoding="utf-8"))
cost = json.load(open(os.path.join(SCRATCH, "extract_cost.json"), encoding="utf-8"))

runs = [json.load(open(os.path.join(RESULTS, f"smoke_probe_run_{r}.json"), encoding="utf-8"))
        for r in ["A", "B", "C"]]
main = [r["auc_main_macro_ovr"] for r in runs]
pos = [r["auc_positive_control_task"] for r in runs]
neg = [r["auc_negative_control_permuted"] for r in runs]
band = runs[0]["null_band_95"]
auc_range = max(main) - min(main)
twice_same = max(max(main) - min(main), max(pos) - min(pos), max(neg) - min(neg)) <= 1e-12
fps = sorted(set(f.split("||")[0] for f in [json.dumps(0)][:0]))  # noop keep lint quiet

# ---- schema snapshot ----
def load_eps(short):
    fs = []
    for dirpath, _, filenames in os.walk(os.path.join(CACHE_ROOT, short, "meta", "episodes")):
        for fn in filenames:
            if fn.endswith(".parquet"):
                fs.append(pd.read_parquet(os.path.join(dirpath, fn)))
    return pd.concat(fs, ignore_index=True)

schema = {}
for short in ["so101", "bimanual"]:
    e = load_eps(short)
    keycols = [c for c in e.columns if not c.startswith("stats/")]
    census = {}
    for c in keycols:
        s = e[c]
        try:
            nu = int(s.astype(str).nunique(dropna=True))
        except Exception:
            nu = -1
        census[c] = {"nonnull": int(s.notna().sum()), "n_rows": int(len(s)), "nunique": nu}
    batch_like = [c for c in keycols if not c.startswith("videos/")
                  and any(k in c.lower() for k in
                  ["session", "batch", "collect", "capture", "record_session", "rig"])]
    schema[short] = {
        "repo": REPOS[short], "revision": plan[short].get("revision", ""),
        "n_rows": int(len(e)),
        "columns_nonstats": keycols,
        "census": census,
        "batch_like_columns": batch_like,
    }
    print(f"[{short}] batch-like columns: {batch_like}")

batch_axis = ("unavailable_task_fallback"
              if all(not s["batch_like_columns"] for s in schema.values()) else "schema_present_check_manually")

# ---- cells / episodes ----
meta = pd.read_csv(os.path.join(PROJECT, "experiments", "cache", "smoke_episodes.csv"))
cells = meta.groupby(["shortname", "policy_type"]).size()
cell_ok = bool((cells >= 5).all())
cells_dict = {f"{i[0]}|{i[1]}": int(v) for i, v in cells.items()}

# ---- verdicts (frozen gates) ----
g_reliab = (auc_range <= 1e-12) and (auc_range < max(0.05, np.mean(main) - 0.55))
g_pos = min(pos) >= 0.90
g_neg = (band[0] <= np.mean(neg) <= band[1]) and max(neg) <= band[1]
est_min = 40
cost_min = cost["total_seconds"] / 60.0
g_cost = cost_min <= est_min * 2
verdict = "supported" if (twice_same and g_pos and g_neg and g_reliab and g_cost and cell_ok) else "falsified"

summary = {
    "stage": "smoke",
    "scope": "pilot-task minimal ruler check (cable_clip + fold_tea_towel, policy-rollout episodes)",
    "scope_rule": "design-frozen pilot tasks; per (task,policy_type) cell greedy video-file "
                  "selection by eps/MB (meta inventory only, no result-based choice), >=10 eps/cell",
    "main_auc_runs": main,
    "main_auc_range": float(auc_range),
    "main_auc_mean": float(np.mean(main)),
    "gate_distance_AUC_minus_0.55": float(np.mean(main) - 0.55),
    "twice_same_1e-12": bool(twice_same),
    "positive_control_runs": pos,
    "positive_control_pass": bool(g_pos),
    "negative_control_runs": neg,
    "null_band_95": [float(band[0]), float(band[1])],
    "negative_control_pass": bool(g_neg),
    "reliability_pass": bool(g_reliab),
    "cells": cells_dict,
    "cells_min_ge5": cell_ok,
    "batch_axis": batch_axis,
    "cost": cost,
    "cost_pass_2x_of_40min": bool(g_cost),
    "verdict": verdict,
}
json.dump(summary, open(os.path.join(RESULTS, "smoke_summary.json"), "w", encoding="utf-8"), indent=1)

# ---- config json ----
import sklearn, torch, transformers, PIL, av as avlib
cfg = {
    "encoder": "facebook/dinov2-small", "encoder_revision": cost.get("model_revision", ""),
    "frames_per_episode": 8, "frame_rule": "idx_k = floor(k*N/8), k=0..7, N=episode length, fps=20",
    "match_tolerance_s": 0.075,
    "preprocess": "RGB -> resize shortest side 224 (PIL bilinear) -> center crop 224x224 -> /255 -> ImageNet mean/std",
    "feature": "CLS token (last_hidden_state[:,0]), mean over 8 frames, L2 normalized, float32",
    "probe": "LogisticRegression(multinomial lbfgs, L2, C=1.0, max_iter=2000, class_weight=balanced)",
    "split": "80/20 stratified by task x policy_type, seed 20261109",
    "perm_seed": 20261110, "boot_seed": 20261111, "boot_B": 2000,
    "label_main": "policy_type (7 classes, rollout rows only; policy_repo_id non-empty)",
    "label_positive_control": "task (2 pilot tasks)",
    "label_negative_control": "policy_type permuted with seed 20261110",
    "data": {s: {"repo": REPOS[s], "revision": plan[s].get("revision", ""),
                 "camera": plan[s]["camera"], "task": plan[s]["task"],
                 "episodes_in_scope": plan[s]["episodes_covered"],
                 "files": len(plan[s]["files"])} for s in REPOS},
    "env": {"sklearn": sklearn.__version__, "torch": torch.__version__,
            "transformers": transformers.__version__, "pillow": PIL.__version__,
            "av": avlib.__version__, "numpy": np.__version__,
            "python": sys.version.split()[0], "platform": platform.platform()},
    "smoke_estimate_min": est_min,
    "gates": {"twice_same": "max pairwise |diff| <= 1e-12",
              "positive": "AUC >= 0.90", "negative": "macro AUC within prereg 95% null band",
              "reliability": "range < max(0.05, AUC-0.55) and <= 1e-12",
              "cost": "extraction+probe wall <= 2x estimate"},
}
json.dump(cfg, open(os.path.join(RESULTS, "smoke_config.json"), "w", encoding="utf-8"), indent=1)

# ---- schema snapshot json ----
json.dump({"repos": schema, "batch_axis": batch_axis,
           "verdict": "no session/batch/collection field in meta/episodes for either repo"
                      if batch_axis == "unavailable_task_fallback" else "see batch_like_columns"},
          open(os.path.join(RESULTS, "schema_snapshot.json"), "w", encoding="utf-8"), indent=1)

# ---- episodes csv ----
meta.to_csv(os.path.join(RESULTS, "smoke_episodes.csv"), index=False)

# ---- cost json ----
json.dump({"smoke_estimate_min": est_min, **cost,
           "download_gib": {s: report[s]["got_gib"] for s in report if s != "total_seconds"},
           "download_seconds": {s: report[s]["download_seconds"] for s in report if s != "total_seconds"},
           "pass_2x": bool(g_cost)},
          open(os.path.join(RESULTS, "smoke_cost.json"), "w", encoding="utf-8"), indent=1)

print(json.dumps(summary, indent=1)[:2000])
print("AGGREGATE DONE, verdict =", verdict)
