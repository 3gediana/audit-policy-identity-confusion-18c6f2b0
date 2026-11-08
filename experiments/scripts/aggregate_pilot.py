# -*- coding: utf-8 -*-
"""Aggregate pilot results: probe gates, negative-control convergence, three-arm outputs,
length-leakage audit, degradations, pilot_summary.json + probe_metrics.json + confusion csv.

Gates are frozen (experiments/prereg.md); this script only evaluates them.
"""
import json, os, sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(line_buffering=True)
SCRATCH = os.path.dirname(os.path.abspath(__file__))
PROJECT = "D:/hermes-data/research/审计真机基准的策略身份混淆-18c6f2b0"
RESULTS = os.path.join(PROJECT, "results")

runs = [json.load(open(os.path.join(RESULTS, f"pilot_probe_run_{r}.json"), encoding="utf-8"))
        for r in ["A", "B", "C"]]
main = [r["auc_main_macro_ovr"] for r in runs]
pos = [r["auc_positive_control_task"] for r in runs]
neg = [r["auc_negative_control_permuted"] for r in runs]
band = runs[0]["null_band_95"]
auc_range = max(main) - min(main)
twice_same = max(auc_range, max(pos) - min(pos), max(neg) - min(neg)) <= 1e-12
fps = sorted(set(r["config_fingerprint"] for r in runs))
conv = runs[0]["neg_control_convergence"]

g_main = float(np.mean(main)) > 0.55
g_pos = min(pos) >= 0.90
g_neg = (band[0] <= float(np.mean(neg)) <= band[1]) and max(neg) <= band[1]
g_reliab = (auc_range <= 1e-12) and len(fps) == 1
g_conv = bool(conv.get("dev_shrank_with_bigger_test", False)
              and conv.get("pilot_neg_within_own_band", False))

# ---- length-leakage audit (full metadata population) ----
eps = pd.read_csv(os.path.join(RESULTS, "pilot_episodes_all.csv"))
leak = {}
for t, g in eps.groupby("task"):
    s = g[g["success_int"] == 1]["length"]
    f = g[g["success_int"] == 0]["length"]
    leak[t] = {"n": int(len(g)), "n_success": int(len(s)),
               "mean_len_success": float(s.mean()) if len(s) else None,
               "mean_len_failure": float(f.mean()) if len(f) else None,
               "median_len_success": float(s.median()) if len(s) else None,
               "median_len_failure": float(f.median()) if len(f) else None,
               "L50_task": float(np.median(g["length"].astype(float))),
               "pearson_corr_success_vs_length": float(np.corrcoef(
                   g["success_int"].astype(float), g["length"].astype(float))[0, 1])
               if g["length"].notna().all() and g["success_int"].nunique() > 1 else None}

# ---- three-arm outputs presence + verdicts ----
kendall = pd.read_csv(os.path.join(RESULTS, "kendall_tau.csv"))
arm_files = ["ranking_A.csv", "ranking_B.csv", "ranking_C.csv", "pairwise_flips.csv",
             "kendall_tau.csv", "cell_gates.csv", "ranking_summary.json",
             "ranking_reproducibility.json"]
arm_present = {f: os.path.exists(os.path.join(RESULTS, f)) for f in arm_files}
gates = pd.read_csv(os.path.join(RESULTS, "cell_gates.csv"))
cells_pass = int(gates["gate_n_ge10"].sum())
cells_total = int(len(gates))
rank_repro = json.load(open(os.path.join(RESULTS, "ranking_reproducibility.json"),
                           encoding="utf-8"))["reproducible"]

arm_verdicts = [{"task": r["task"], "comparison": r["comparison"],
                 "tau_b": (None if pd.isna(r["tau_b"]) else float(r["tau_b"])),
                 "n_flips": int(r["n_flips"]), "n_pairs": int(r["n_pairs"]),
                 "n_strict_direction_reversals": int(r["n_strict_direction_reversals"]),
                 "verdict": r["verdict"]} for _, r in kendall.iterrows()]

degradations = [
    {"scope": "cable_clip", "item": "all 270 rollout episodes have success==0 (success_class='failure') "
     "for all 7 policies",
     "impact": "all three arms have zero discriminating power on this task; rankings are pure "
     "fixed-order tie-break; Kendall tau-b undefined; verdict=insufficient_comparison",
     "evidence": "results/cell_gates.csv, results/pilot_episodes_all.csv, diag_labels.py output"},
    {"scope": "A arm", "item": "batch_axis=unavailable_task_fallback (no session/batch field): "
     "layers degenerate to task",
     "impact": "A layer rates equal C rates on common support (same episodes, same labels); "
     "C_vs_A has zero re-weighting power at pilot; 'no_flip_observed' there is uninformative",
     "evidence": "results/schema_snapshot.json, results/kendall_tau.csv caveat column"},
    {"scope": "B arm", "item": "protocol.md section 4 instantiated: success ground truth = episode "
     "label, truncation window L50 per task; success within window = (success==1) AND (length<=L50) "
     "because successful rollouts were trimmed at completion (2611.03168 section 5)",
     "impact": "B primary ranking is the truncated-window re-evaluation; the frozen-label reading "
     "(labels and membership unchanged -> B==C identically) is preserved as the "
     "C_vs_B_frozen_labels_audit comparison and the *_episode_label_audit column",
     "evidence": "results/ranking_B.csv, results/kendall_tau.csv"},
    {"scope": "B arm", "item": "no success-timing field in meta/episodes (only episode-level "
     "success/success_class)",
     "impact": "horizon success derived from episode label + length under the trimmed-at-completion "
     "termination property; not re-judged from video; if that property does not hold the B primary "
     "number must be re-derived (unavailable, never estimated)",
     "evidence": "results/schema_snapshot.json columns_nonstats"},
]
json.dump(degradations, open(os.path.join(RESULTS, "degradations.json"), "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)

# ---- probe_metrics.json (preregistered name) ----
probe_metrics = {
    "stage": "pilot", "scope": "2 design-frozen pilot tasks x 7 policies, all covered rollout episodes",
    "runs": {r["runid"]: {"auc_main_macro_ovr": r["auc_main_macro_ovr"],
                          "auc_main_bootstrap_ci95": r["auc_main_bootstrap_ci95"],
                          "auc_positive_control_task": r["auc_positive_control_task"],
                          "auc_negative_control_permuted": r["auc_negative_control_permuted"],
                          "null_band_95": r["null_band_95"],
                          "test_accuracy": r["test_accuracy"],
                          "config_fingerprint": r["config_fingerprint"],
                          "n_episodes": r["n_episodes"], "n_test": r["n_test"]}
             for r in runs},
    "auc_main_runs": main, "auc_main_mean": float(np.mean(main)), "auc_main_range": float(auc_range),
    "auc_main_ci95": runs[0]["auc_main_bootstrap_ci95"],
    "auc_main_per_class": runs[0]["auc_main_per_class"],
    "positive_control_runs": pos, "negative_control_runs": neg,
    "null_band_95": [float(band[0]), float(band[1])],
    "neg_control_convergence": conv,
    "twice_same_1e-12": bool(twice_same), "single_config_fingerprint": len(fps) == 1,
    "confusion_classes": runs[0]["confusion_classes"],
    "confusion_matrix_test": runs[0]["confusion_matrix_test"],
    "test_accuracy": runs[0]["test_accuracy"],
    "gates": {"main_auc_gt_0.55": bool(g_main), "positive_ge_0.90": bool(g_pos),
              "negative_in_null_band": bool(g_neg), "reliability_bitwise": bool(g_reliab),
              "neg_convergence_toward_half": bool(g_conv)},
}
json.dump(probe_metrics, open(os.path.join(RESULTS, "probe_metrics.json"), "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)

# ---- confusion_matrix.csv (preregistered name) from run A ----
import csv
classes = runs[0]["confusion_classes"]
cm = runs[0]["confusion_matrix_test"]
with open(os.path.join(RESULTS, "confusion_matrix.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["true\\pred"] + classes)
    for c, row in zip(classes, cm):
        w.writerow([c] + list(row))

# ---- cost ----
try:
    cost = json.load(open(os.path.join(SCRATCH, "extract_cost_pilot.json"), encoding="utf-8"))
except Exception:
    cost = {}
try:
    dlrep = json.load(open(os.path.join(SCRATCH, "fast_dl_report_pilot.json"), encoding="utf-8"))
except Exception:
    dlrep = {}
try:
    ver = json.load(open(os.path.join(SCRATCH, "size_verification_pilot.json"), encoding="utf-8"))
    n_ok = sum(1 for v in ver["verdict"].values() if v["status"] == "ok")
    ver_ok = f"{n_ok}/{len(ver['verdict'])}"
except Exception:
    ver_ok = "not run"

scientific_verdict = ("supported" if (all(arm_present.values()) and rank_repro and twice_same
                                      and g_main and g_pos and g_neg and g_reliab and g_conv)
                      else ("inconclusive" if (all(arm_present.values()) and rank_repro) else "failed"))

pilot_summary = {
    "stage": "pilot", "result_kind": "scientific_result", "source_mode": "live",
    "prediction": "ranking_A/B/C + pairwise_flips + Kendall tau-b + per-cell gates complete and "
                  "same-口径 reproducible; negative-control point estimate re-check converges "
                  "toward 0.5 as the test set grows",
    "arms_present": arm_present, "ranking_double_run_reproducible": bool(rank_repro),
    "probe_gates": probe_metrics["gates"],
    "cells_gate_n_ge10": {"passing": cells_pass, "total": cells_total},
    "arm_verdicts": arm_verdicts,
    "length_leakage_audit": leak,
    "degradations_file": "results/degradations.json",
    "size_verification_pilot": ver_ok,
    "cost": {"extract_seconds": cost.get("total_seconds"), "download_seconds": dlrep.get("seconds"),
             "download_files_ok": f"{dlrep.get('ok')}/{dlrep.get('total')}",
             "probe_timings_s": runs[0]["timings_s"]},
    "verdict": scientific_verdict,
    "reproduction": "G:/ai/python11/python.exe experiments/scripts/prep_download_pilot.py; "
                    "fast_download_pilot.py; verify_pilot.py; pilot_extract.py; "
                    "pilot_probe.py A/B/C; pilot_ranking.py; aggregate_pilot.py",
}
json.dump(pilot_summary, open(os.path.join(RESULTS, "pilot_summary.json"), "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)

print(json.dumps({"auc_main_mean": float(np.mean(main)), "pos_min": min(pos),
                  "neg": [min(neg), max(neg)], "band": band,
                  "neg_convergence": conv,
                  "gates": probe_metrics["gates"], "cells": [cells_pass, cells_total],
                  "verdict": scientific_verdict}, indent=1, ensure_ascii=False))
print("AGGREGATE PILOT DONE, verdict =", scientific_verdict)
