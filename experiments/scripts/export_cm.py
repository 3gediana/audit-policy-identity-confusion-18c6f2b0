# -*- coding: utf-8 -*-
"""Export confusion_matrix.csv from smoke_probe_run_A.json (runs are bitwise identical)."""
import csv, json, os

PROJECT = "D:/hermes-data/research/审计真机基准的策略身份混淆-18c6f2b0"
RESULTS = os.path.join(PROJECT, "results")

run = json.load(open(os.path.join(RESULTS, "smoke_probe_run_A.json"), encoding="utf-8"))
classes = run["confusion_classes"]
cm = run["confusion_matrix_test"]

with open(os.path.join(RESULTS, "confusion_matrix.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["true\\pred"] + classes)
    for c, row in zip(classes, cm):
        w.writerow([c] + row)
print("confusion_matrix.csv written:", len(classes), "classes, test n =", run["n_test"])
