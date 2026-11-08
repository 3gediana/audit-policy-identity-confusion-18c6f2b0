# -*- coding: utf-8 -*-
"""Print pilot_summary.json key sections (leak audit + arm verdicts + cost)."""
import json

base = "D:/hermes-data/research/审计真机基准的策略身份混淆-18c6f2b0/results/"
s = json.load(open(base + "pilot_summary.json", encoding="utf-8"))
print("== length_leakage_audit ==")
print(json.dumps(s["length_leakage_audit"], indent=1, ensure_ascii=False))
print("== arm_verdicts ==")
print(json.dumps(s["arm_verdicts"], indent=1, ensure_ascii=False))
print("== cost ==")
print(json.dumps(s["cost"], indent=1, ensure_ascii=False))
pm = json.load(open(base + "probe_metrics.json", encoding="utf-8"))
print("== per-class AUC ==")
print(json.dumps(pm["auc_main_per_class"], indent=1))
print("test_accuracy:", pm["test_accuracy"])
