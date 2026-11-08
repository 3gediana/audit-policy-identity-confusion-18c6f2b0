# -*- coding: utf-8 -*-
"""Diagnostic: per task x policy label/length census on the full pilot metadata.
Answers: is cable_clip really all-zero success? how are success_class values distributed?
"""
import os, sys
import numpy as np
import pandas as pd

sys.stdout.reconfigure(line_buffering=True)
CACHE_ROOT = "D:/hermes-data/research/审计真机基准的策略身份混淆-18c6f2b0/assets/hf"
TASKS = [("so101", "Push the Displayport cable into the cable holder on the white block"),
         ("bimanual", "Fold the brown tea towel")]


def task_str(v):
    if isinstance(v, (list, np.ndarray)):
        return "|".join(map(str, v))
    return str(v)


rows = []
for short, tdesc in TASKS:
    fs = []
    for dirpath, _, filenames in os.walk(os.path.join(CACHE_ROOT, short, "meta", "episodes")):
        for fn in filenames:
            if fn.endswith(".parquet"):
                fs.append(pd.read_parquet(os.path.join(dirpath, fn)))
    e = pd.concat(fs, ignore_index=True)
    e["task_str"] = e["tasks"].map(task_str)
    roll = e[e["policy_repo_id"].astype(str).str.len() > 0].copy()
    sub = roll[roll["task_str"] == tdesc].copy()
    sub["repo"] = short
    rows.append(sub)
    print(f"== {short} == total rows {len(e)}, rollout {len(roll)}, task {len(sub)}")
    print("success dtype:", sub["success"].dtype, "unique:", sorted(sub["success"].unique().tolist()))
    print("success_class dtype:", sub["success_class"].dtype, "unique:",
          sorted(sub["success_class"].astype(str).unique().tolist()))

df = pd.concat(rows, ignore_index=True)
g = df.groupby(["repo", "task_str", "policy_type"]).agg(
    n=("success", "size"), succ=("success", "sum"),
    succ_rate=("success", "mean"),
    len_med=("length", "median"), len_min=("length", "min"), len_max=("length", "max"))
print(g.to_string())
print("\nsuccess_class x task_str:")
print(df.groupby(["task_str", "success_class"]).size().to_string())
print("\nsuccess vs success_class crosstab:")
print(pd.crosstab(df["success"].astype(str), df["success_class"].astype(str)).to_string())
print("\nteleop rows excluded count:", 0)
