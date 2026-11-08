# -*- coding: utf-8 -*-
"""Show the pilot three-arm result tables (fold_tea_towel focus + flipped pair)."""
import pandas as pd

base = "D:/hermes-data/research/审计真机基准的策略身份混淆-18c6f2b0/results/"
b = pd.read_csv(base + "ranking_B.csv")
print("== ranking_B (fold_tea_towel) ==")
print(b[b.task == "fold_tea_towel"][["policy_type", "n", "n_success_episode_label",
      "success_rate_episode_label_audit", "n_success_at_horizon", "success_rate_at_horizon",
      "L50_trunc_len", "n_truncated", "rank", "ci95_lo", "ci95_hi"]].to_string(index=False))
print("== ranking_C (fold_tea_towel) ==")
c = pd.read_csv(base + "ranking_C.csv")
print(c[c.task == "fold_tea_towel"][["policy_type", "n", "n_success", "success_rate",
      "rank", "ci95_lo", "ci95_hi"]].to_string(index=False))
print("== ranking_A (fold_tea_towel) ==")
a = pd.read_csv(base + "ranking_A.csv")
print(a[a.task == "fold_tea_towel"][["policy_type", "n", "gate_n_ge10", "layer_valid",
      "participates", "rank", "aggregate_rate_global", "aggregate_rank_global"]].to_string(index=False))
print("== flipped pairs (all) ==")
pf = pd.read_csv(base + "pairwise_flips.csv")
fl = pf[pf["flipped"] == 1]
print(fl.to_string(index=False))
print("== cable_clip ranking_C head ==")
print(c[c.task == "cable_clip"].head(3).to_string(index=False))
print("== kendall_tau.csv ==")
print(pd.read_csv(base + "kendall_tau.csv").to_string(index=False))
print("== cell_gates ==")
print(pd.read_csv(base + "cell_gates.csv").to_string(index=False))
