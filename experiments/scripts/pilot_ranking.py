# -*- coding: utf-8 -*-
"""Pilot three-arm ranking re-evaluation (2 tasks x 7 policies), frozen protocol
experiments/protocol.md sections 4-5. Deterministic: the whole computation runs twice
and the two canonical fingerprints must match.

Arms (protocol.md section 4):
- C raw pooled ranking: per task, per-policy success rate (success == 1), descending;
  ties broken by the preregistered fixed order
  [act, diffusion, smolvla, pi0, pi0.5, grootn1.7, molmoact2].
- B length-median truncation pooled re-evaluation: per task, common truncation length
  L50 = 50th percentile of rollout episode length (meta/episodes frame count); episodes
  shorter than L50 keep full length, longer ones are truncated to L50; the same rule for
  successes and failures (never truncate failures only). Success ground truth stays the
  episode label (no re-judging); because successful rollouts were trimmed at completion
  (2611.03168 section 5), success within the common window = (success == 1) AND
  (length <= L50). Missing length -> B unavailable for that cell, never estimated.
  The frozen-label audit rate (episode labels unchanged, = C's rate) is reported alongside.
- A probe-driven stratified re-evaluation: probe AUC is only an audit trigger (see
  probe outputs); strata would be task x collection_session, but batch_axis is
  unavailable_task_fallback (schema_snapshot.json), so layers = task. Within a layer a
  policy enters only with n >= 10 (prereg: "each cell needs n >= 10 to enter the A
  layer"); a layer is retained only with >= 2 participating policies, otherwise it exits
  to the missing table. Layer rates are aggregated with layer episode-count weights.

Per task x comparison we report strategy rankings, Kendall tau-b (complete participating
strategies only), pairwise flips / comparable pairs, flip rate, per-strategy bootstrap
95% CI (B=2000, seed 20261111, percentile), and the section 4 verdict:
  n_comparable < 3                -> insufficient_comparison
  tau_b < 1 or >= 1 flip          -> ranking_unstable
  else                            -> no_flip_observed
"""
import hashlib, json, os, sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(line_buffering=True)
SCRATCH = os.path.dirname(os.path.abspath(__file__))
PROJECT = "D:/hermes-data/research/审计真机基准的策略身份混淆-18c6f2b0"
CACHE_ROOT = os.path.join(PROJECT, "assets", "hf")
RESULTS = os.path.join(PROJECT, "results")
os.makedirs(RESULTS, exist_ok=True)

POLICY_ORDER = ["act", "diffusion", "smolvla", "pi0", "pi0.5", "grootn1.7", "molmoact2"]
ORDER_IDX = {p: i for i, p in enumerate(POLICY_ORDER)}
TASKS = [("so101", "cable_clip", "Push the Displayport cable into the cable holder on the white block"),
         ("bimanual", "fold_tea_towel", "Fold the brown tea towel")]
GATE_N = 10
BOOT_SEED = 20261111
BOOT_B = 2000
EPS_TOL = 1e-12


def task_str(v):
    if isinstance(v, (list, np.ndarray)):
        return "|".join(map(str, v))
    return str(v)


def load_pilot_episodes():
    rows = []
    for short, tname, tdesc in TASKS:
        fs = []
        for dirpath, _, filenames in os.walk(os.path.join(CACHE_ROOT, short, "meta", "episodes")):
            for fn in filenames:
                if fn.endswith(".parquet"):
                    fs.append(pd.read_parquet(os.path.join(dirpath, fn)))
        e = pd.concat(fs, ignore_index=True)
        e["task_str"] = e["tasks"].map(task_str)
        roll = e[e["policy_repo_id"].astype(str).str.len() > 0].copy()
        sub = roll[roll["task_str"] == tdesc].copy()
        for _, r in sub.iterrows():
            rows.append({"repo": short, "task": tname, "episode_index": int(r["episode_index"]),
                         "policy_type": str(r["policy_type"]),
                         "policy_repo_id": str(r["policy_repo_id"]),
                         "success": int(r["success"]) == 1,
                         "success_raw": r["success"],
                         "length": (int(r["length"]) if pd.notna(r["length"]) else None)})
        print(f"[{short}/{tname}] rollout episodes: {len(sub)} "
              f"(success mean {sub['success'].astype(float).mean():.3f})")
    df = pd.DataFrame(rows)
    df = df.sort_values(["task", "episode_index"]).reset_index(drop=True)
    return df


def rates_by_policy(df, value_col):
    """{task: {policy: (n, n_succ_or_value_sum, rate)}} over ALL episodes of the cell."""
    out = {}
    for t, g in df.groupby("task"):
        d = {}
        for p, gp in g.groupby("policy_type"):
            n = len(gp)
            s = int(gp[value_col].sum())
            d[p] = (n, s, s / n if n else float("nan"))
        out[t] = d
    return out


def rank_policies(rate_dict):
    """Descending rate, ties by fixed policy order. Returns {policy: rank} (1-based)."""
    items = sorted(rate_dict.items(), key=lambda kv: (-kv[1], ORDER_IDX.get(kv[0], 99)))
    return {p: i + 1 for i, (p, _) in enumerate(items)}


def boot_ci(values_by_policy, seed_base, task_idx, policy_idx, arm_code):
    """Percentile bootstrap CI of the mean of a per-episode 0/1 vector.
    Deterministic per (task, policy, arm) via seeded seed sequence."""
    v = np.asarray(values_by_policy, dtype=np.float64)
    n = len(v)
    if n == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng([BOOT_SEED, task_idx, policy_idx, arm_code])
    idx = rng.integers(0, n, size=(BOOT_B, n))
    means = v[idx].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return (float(lo), float(hi))


def kendall_tau_b(x, y):
    """Manual tau-b over score vectors (ties in either variable handled per formula)."""
    n = len(x)
    C = D = Tx = Ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx, dy = x[i] - x[j], y[i] - y[j]
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                Ty += 1
            elif dy == 0:
                Tx += 1
            elif (dx > 0) == (dy > 0):
                C += 1
            else:
                D += 1
    denom = np.sqrt((C + D + Tx) * (C + D + Ty))
    if denom == 0:
        return float("nan")
    return (C - D) / denom


def canonical_fingerprint(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                     default=str).encode("utf-8")).hexdigest()


def nan_to_none(o):
    if isinstance(o, dict):
        return {k: nan_to_none(v) for k, v in o.items()}
    if isinstance(o, list):
        return [nan_to_none(v) for v in o]
    if isinstance(o, float) and np.isnan(o):
        return None
    return o


def compute():
    df = load_pilot_episodes()
    # audit: frozen-label quantities
    df["success_int"] = df["success"].astype(int)
    L50 = {}
    df["success_horizon"] = 0
    df["truncated"] = False
    for t, g in df.groupby("task"):
        lens = g["length"].dropna().astype(float)
        l50 = float(np.median(lens)) if len(lens) else float("nan")
        L50[t] = l50
        m = df["task"] == t
        ok_len = df.loc[m, "length"].notna()
        df.loc[m & ok_len, "truncated"] = df.loc[m & ok_len, "length"].astype(float) > l50
        df.loc[m & ok_len, "success_horizon"] = (
            (df.loc[m & ok_len, "success_int"] == 1)
            & (df.loc[m & ok_len, "length"].astype(float) <= l50)).astype(int)

    rc = rates_by_policy(df, "success_int")            # C and B frozen-label audit
    rh = rates_by_policy(df, "success_horizon")        # B primary (truncated-window success)
    task_order = [t for _, t, _ in TASKS]
    task_idx = {t: i for i, t in enumerate(task_order)}

    ranking_C, ranking_B, ranking_A, cell_gates = [], [], [], []
    rate_store = {}   # (task, arm, policy) -> rate
    ci_store = {}
    excluded = []

    for t in task_order:
        g = df[df["task"] == t]
        # ---------- C ----------
        c_rates = {p: rc[t][p][2] for p in rc[t]}
        rC = rank_policies(c_rates)
        for p in POLICY_ORDER:
            if p not in rc[t]:
                cell_gates.append({"task": t, "policy_type": p, "n": 0, "n_success": 0,
                                   "success_rate": None, "gate_n_ge10": False,
                                   "n_policies_passing_in_layer": 0, "layer_valid": False,
                                   "participates_in_A": False,
                                   "reason": "no rollout episodes for this policy in task"})
                ranking_C.append({"task": t, "policy_type": p, "n": 0, "n_success": 0,
                                  "success_rate": None, "rank": None, "ci95_lo": None,
                                  "ci95_hi": None, "tie_order_idx": ORDER_IDX[p],
                                  "population": "all rollout episodes of the task (meta/episodes)"})
                ranking_B.append({"task": t, "policy_type": p, "n": 0, "n_success_episode_label": 0,
                                  "success_rate_episode_label_audit": None,
                                  "n_success_at_horizon": 0, "success_rate_at_horizon": None,
                                  "L50_trunc_len": L50[t], "n_truncated": 0,
                                  "rank": None, "ci95_lo": None, "ci95_hi": None,
                                  "tie_order_idx": ORDER_IDX[p], "status": "no episodes"})
                excluded.append({"task": t, "arm": "A/B/C", "policy_type": p,
                                 "reason": "cell absent (n=0)"})
                continue
            n, s, rate = rc[t][p]
            vals_c = g[g["policy_type"] == p]["success_int"].to_numpy()
            ci = boot_ci(vals_c, BOOT_SEED, task_idx[t], ORDER_IDX[p], 1)
            ci_store[(t, "C", p)] = ci
            rate_store[(t, "C", p)] = rate
            ranking_C.append({"task": t, "policy_type": p, "n": n, "n_success": s,
                              "success_rate": rate, "rank": rC[p], "ci95_lo": ci[0],
                              "ci95_hi": ci[1], "tie_order_idx": ORDER_IDX[p],
                              "population": "all rollout episodes of the task (meta/episodes)"})
            # ---------- B ----------
            gp = g[g["policy_type"] == p]
            nh, sh, _ = rh[t][p]
            n_len_missing = int(gp["length"].isna().sum())
            vals_h = gp["success_horizon"].to_numpy()
            if n_len_missing > 0:
                b_rate, b_ci, b_status = None, (None, None), "unavailable: missing length, not estimated"
                b_rank = None
            else:
                b_rate = sh / nh if nh else float("nan")
                b_ci = boot_ci(vals_h, BOOT_SEED, task_idx[t], ORDER_IDX[p], 2)
                b_status = "ok"
                b_rank = None  # filled after all policies known
            rate_store[(t, "B", p)] = b_rate
            ci_store[(t, "B", p)] = b_ci
            ranking_B.append({"task": t, "policy_type": p, "n": n, "n_success_episode_label": s,
                              "success_rate_episode_label_audit": rate,
                              "n_success_at_horizon": sh, "success_rate_at_horizon": b_rate,
                              "L50_trunc_len": L50[t],
                              "n_truncated": int(gp["truncated"].sum()),
                              "rank": b_rank, "ci95_lo": b_ci[0], "ci95_hi": b_ci[1],
                              "tie_order_idx": ORDER_IDX[p], "status": b_status})
        # B ranks (available policies only)
        b_avail = {p: rate_store[(t, "B", p)] for p in POLICY_ORDER
                   if rate_store.get((t, "B", p)) is not None and p in rc[t]}
        rB = rank_policies(b_avail)
        for row in ranking_B:
            if row["task"] == t and row["policy_type"] in rB:
                row["rank"] = rB[row["policy_type"]]

        # ---------- A ----------
        passing = [p for p in POLICY_ORDER if p in rc[t] and rc[t][p][0] >= GATE_N]
        layer_valid = len(passing) >= 2
        for p in POLICY_ORDER:
            if p not in rc[t]:
                continue
            n, s, rate = rc[t][p]
            participates = layer_valid and (p in passing)
            reason = ("ok" if participates else
                      (f"gate fail: n={n} < {GATE_N}" if p not in passing else
                       f"layer invalid: only {len(passing)} policies pass n>={GATE_N} (<2)"))
            ci = ci_store[(t, "C", p)] if participates else (None, None)
            ranking_A.append({"task": t, "layer": f"{t} (task-only fallback)", "policy_type": p,
                              "n": n, "n_success": s,
                              "success_rate": rate if participates else None,
                              "gate_n_ge10": p in passing, "layer_valid": layer_valid,
                              "participates": participates, "rank": None,
                              "ci95_lo": ci[0], "ci95_hi": ci[1],
                              "aggregate_rate_global": None, "aggregate_rank_global": None,
                              "aggregate_ci95_lo": None, "aggregate_ci95_hi": None,
                              "reason": reason})
            rate_store[(t, "A", p)] = rate if participates else None
            if not participates:
                excluded.append({"task": t, "arm": "A", "policy_type": p, "reason": reason})
        a_avail = {p: rate_store[(t, "A", p)] for p in POLICY_ORDER
                   if rate_store.get((t, "A", p)) is not None}
        rA = rank_policies(a_avail)
        for row in ranking_A:
            if row["task"] == t and row["policy_type"] in rA:
                row["rank"] = rA[row["policy_type"]]
        # cell gates table
        for p in POLICY_ORDER:
            if p not in rc[t]:
                continue
            n, s, rate = rc[t][p]
            cell_gates.append({"task": t, "policy_type": p, "n": n, "n_success": s,
                               "success_rate": rate, "gate_n_ge10": n >= GATE_N,
                               "n_policies_passing_in_layer": len(passing),
                               "layer_valid": layer_valid,
                               "participates_in_A": layer_valid and p in passing,
                               "reason": "ok" if (layer_valid and p in passing) else
                                         (f"gate fail: n={n} < {GATE_N}" if n < GATE_N else
                                          f"layer invalid ({len(passing)} passing <2)")})

    # ---------- A global layer-weighted aggregate ----------
    for p in POLICY_ORDER:
        num = den = 0.0
        per_layer = {}
        for t in task_order:
            r = rate_store.get((t, "A", p))
            if r is None:
                continue
            layer_n = sum(rc[t][q][0] for q in POLICY_ORDER
                          if rate_store.get((t, "A", q)) is not None)
            per_layer[t] = layer_n
            num += layer_n * r
            den += layer_n
        agg = num / den if den > 0 else None
        # stratified bootstrap over layers (resample within layer x policy, fixed layer weights)
        if den > 0:
            rng = np.random.default_rng([BOOT_SEED, 777, ORDER_IDX[p]])
            draws = np.zeros(BOOT_B)
            wsum = np.zeros(BOOT_B)
            for t in task_order:
                r = rate_store.get((t, "A", p))
                if r is None:
                    continue
                vals = df[(df["task"] == t) & (df["policy_type"] == p)]["success_int"].to_numpy()
                n = len(vals)
                idx = rng.integers(0, n, size=(BOOT_B, n))
                draws += per_layer[t] * vals[idx].mean(axis=1)
                wsum += per_layer[t]
            agg_ci = tuple(float(x) for x in np.percentile(draws / wsum, [2.5, 97.5]))
        else:
            agg_ci = (None, None)
        for row in ranking_A:
            if row["policy_type"] == p:
                row["aggregate_rate_global"] = agg
                row["aggregate_ci95_lo"], row["aggregate_ci95_hi"] = agg_ci
    agg_rates = {p: next((r["aggregate_rate_global"] for r in ranking_A
                          if r["policy_type"] == p), None) for p in POLICY_ORDER}
    agg_avail = {p: v for p, v in agg_rates.items() if v is not None}
    rAgg = rank_policies(agg_avail)
    for row in ranking_A:
        if row["policy_type"] in rAgg:
            row["aggregate_rank_global"] = rAgg[row["policy_type"]]

    # ---------- pairwise flips + Kendall tau-b ----------
    comparisons = [("C_vs_A", "A"), ("C_vs_B", "B"), ("C_vs_B_frozen_labels_audit", "B_frozen")]
    pairwise_rows, kendall_rows = [], []
    struct_audit = {}
    for t in task_order:
        for comp, arm in comparisons:
            if arm == "B_frozen":
                alt = {p: rate_store[(t, "C", p)] for p in POLICY_ORDER
                       if rate_store.get((t, "C", p)) is not None}
                caveat = "structural_identity: frozen episode labels + unchanged membership make B == C by construction"
            elif arm == "B":
                alt = {p: rate_store[(t, "B", p)] for p in POLICY_ORDER
                       if rate_store.get((t, "B", p)) is not None}
                caveat = ("truncated-window success = (success==1) AND (length<=L50); "
                          "episode label is the ground truth, no re-judging")
            else:
                alt = {p: rate_store[(t, "A", p)] for p in POLICY_ORDER
                       if rate_store.get((t, "A", p)) is not None}
                caveat = ("structural_no_power: task-only fallback -> A layer rates == C rates "
                          "on common support (same episodes, same labels)")
            c_common = {p: rate_store[(t, "C", p)] for p in POLICY_ORDER
                        if rate_store.get((t, "C", p)) is not None and p in alt}
            common = [p for p in POLICY_ORDER if p in c_common]
            n_cmp = len(common)
            x = [c_common[p] for p in common]
            y = [alt[p] for p in common]
            tau = kendall_tau_b(x, y) if n_cmp >= 2 else float("nan")
            try:
                from scipy.stats import kendalltau
                tau_sc = float(kendalltau(x, y, variant="b").statistic) if n_cmp >= 2 else float("nan")
            except Exception:
                tau_sc = float("nan")
            n_pairs = n_flips = n_ties = n_strict = 0
            max_rate_diff = 0.0
            for i in range(n_cmp):
                for j in range(i + 1, n_cmp):
                    pi, pj = common[i], common[j]
                    ci_, cj_ = c_common[pi], c_common[pj]
                    ai, aj = alt[pi], alt[pj]
                    dir_c = 0 if ci_ == cj_ else (1 if ci_ > cj_ else -1)
                    dir_a = 0 if ai == aj else (1 if ai > aj else -1)
                    ord_c = pi if (ci_ > cj_ or (ci_ == cj_ and ORDER_IDX[pi] < ORDER_IDX[pj])) else pj
                    ord_a = pi if (ai > aj or (ai == aj and ORDER_IDX[pi] < ORDER_IDX[pj])) else pj
                    flipped = int(ord_c != ord_a)
                    strict_rev = int(dir_c != 0 and dir_a != 0 and dir_c != dir_a)
                    n_pairs += 1
                    n_flips += flipped
                    n_strict += strict_rev
                    n_ties += int(dir_c == 0) + int(dir_a == 0)
                    max_rate_diff = max(max_rate_diff, abs(ci_ - ai))
                    pairwise_rows.append({"task": t, "comparison": comp,
                                          "policy_i": pi, "policy_j": pj,
                                          "rate_i_C": ci_, "rate_j_C": cj_, "dir_C": dir_c,
                                          "rate_i_alt": ai, "rate_j_alt": aj, "dir_alt": dir_a,
                                          "order_C": ord_c, "order_alt": ord_a,
                                          "flipped": flipped, "strict_direction_reversal": strict_rev,
                                          "tie_in_either": int(dir_c == 0 or dir_a == 0)})
            flip_rate = n_flips / n_pairs if n_pairs else float("nan")
            if n_cmp < 3:
                verdict = "insufficient_comparison"
                caveat += " | fewer than 3 comparable strategies"
            elif np.isnan(tau):
                verdict = "insufficient_comparison"
                caveat += (" | tau-b undefined: one arm has zero variance (all comparable pairs "
                           "tied), ranking is pure tie-break order, zero discriminating power")
            elif (tau < 1 - EPS_TOL) or n_flips >= 1:
                verdict = "ranking_unstable"
            else:
                verdict = "no_flip_observed"
            kendall_rows.append({"task": t, "comparison": comp, "n_strategies_comparable": n_cmp,
                                 "tau_b": tau, "tau_b_scipy_check": tau_sc,
                                 "n_pairs": n_pairs, "n_flips": n_flips,
                                 "n_strict_direction_reversals": n_strict, "flip_rate": flip_rate,
                                 "n_ties_involving": n_ties,
                                 "max_abs_rate_diff_C_vs_alt": max_rate_diff,
                                 "verdict": verdict, "caveat": caveat})
            struct_audit[f"{t}|{comp}"] = {"max_abs_rate_diff": max_rate_diff, "tau_b": tau}

    # ---------- structural identity checks ----------
    a_identity = all(v["max_abs_rate_diff"] < EPS_TOL
                     for k, v in struct_audit.items() if k.endswith("C_vs_A"))
    b_frozen_identity = all(v["max_abs_rate_diff"] < EPS_TOL
                            for k, v in struct_audit.items() if k.endswith("C_vs_B_frozen_labels_audit"))

    out = {
        "population": "all rollout episodes (policy_repo_id non-empty) of the two design-frozen "
                      "pilot tasks from meta/episodes: cable_clip + fold_tea_towel",
        "n_episodes_total": int(len(df)),
        "n_by_task": {t: int((df["task"] == t).sum()) for t in task_order},
        "L50_by_task": L50,
        "estimands": {
            "C": "success_rate = mean(success == 1) per task x policy over all rollout episodes",
            "B_primary": "success_rate_at_horizon = mean((success == 1) AND (length <= L50_task)); "
                         "episode label is ground truth (no re-judging); successes were trimmed at "
                         "completion (2611.03168 section 5) so success lands at the episode end",
            "B_frozen_labels_audit": "mean(success == 1) on unchanged membership (= C by construction), "
                                     "reported to audit the 'labels stay episode labels' clause",
            "A": "task-only fallback layers; per-cell n>=10 gate; layer kept with >=2 participating "
                 "policies; layer rate = in-layer success rate; global aggregate weighted by layer "
                 "episode count",
        },
        "seeds": {"boot_seed": BOOT_SEED, "boot_B": BOOT_B, "gate_n": GATE_N,
                  "tie_break_order": POLICY_ORDER},
        "structural_checks": {
            "A_equals_C_on_common_support": bool(a_identity),
            "B_frozen_labels_equals_C": bool(b_frozen_identity),
            "note": "expected by construction under batch_axis=unavailable_task_fallback and frozen "
                    "episode labels; recorded as measured facts (max abs diffs above)",
        },
        "kendall": kendall_rows,
    }
    return df, ranking_A, ranking_B, ranking_C, cell_gates, pairwise_rows, kendall_rows, out


def main():
    res1 = compute()
    res2 = compute()
    names = ["df", "ranking_A", "ranking_B", "ranking_C", "cell_gates", "pairwise", "kendall", "summary"]
    fp = []
    for run in (res1, res2):
        canon = {n: (r.to_dict("records") if isinstance(r, pd.DataFrame) else r)
                 for n, r in zip(names, run)}
        fp.append(canonical_fingerprint(canon))
    reproducible = fp[0] == fp[1]
    print(f"double-run fingerprints: {fp[0][:16]} / {fp[1][:16]} -> reproducible={reproducible}")
    if not reproducible:
        print("ERROR: double-run mismatch; refusing to write results")
        sys.exit(2)

    df, ranking_A, ranking_B, ranking_C, cell_gates, pairwise_rows, kendall_rows, summary = res1
    df.to_csv(os.path.join(RESULTS, "pilot_episodes_all.csv"), index=False)
    pd.DataFrame(ranking_A).to_csv(os.path.join(RESULTS, "ranking_A.csv"), index=False)
    pd.DataFrame(ranking_B).to_csv(os.path.join(RESULTS, "ranking_B.csv"), index=False)
    pd.DataFrame(ranking_C).to_csv(os.path.join(RESULTS, "ranking_C.csv"), index=False)
    pd.DataFrame(cell_gates).to_csv(os.path.join(RESULTS, "cell_gates.csv"), index=False)
    pd.DataFrame(pairwise_rows).to_csv(os.path.join(RESULTS, "pairwise_flips.csv"), index=False)
    pd.DataFrame(kendall_rows).to_csv(os.path.join(RESULTS, "kendall_tau.csv"), index=False)
    missing_rows = [r for r in cell_gates if not r["participates_in_A"]]
    pd.DataFrame(missing_rows).to_csv(os.path.join(RESULTS, "degradation_missing.csv"), index=False)
    summary["double_run_fingerprint"] = fp[0]
    summary["double_run_reproducible"] = True
    summary["result_files"] = ["results/ranking_A.csv", "results/ranking_B.csv",
                               "results/ranking_C.csv", "results/cell_gates.csv",
                               "results/pairwise_flips.csv", "results/kendall_tau.csv",
                               "results/degradation_missing.csv", "results/pilot_episodes_all.csv"]
    json.dump(nan_to_none(summary), open(os.path.join(RESULTS, "ranking_summary.json"), "w",
                                         encoding="utf-8"), indent=1, ensure_ascii=False)
    json.dump({"fingerprint_runs": fp, "reproducible": reproducible,
               "formula": "sha256 over canonical json of all output tables (sorted keys)",
               "double_run": "compute() executed twice in-process with fresh state"},
              open(os.path.join(RESULTS, "ranking_reproducibility.json"), "w", encoding="utf-8"),
              indent=1)
    print(json.dumps({k: summary[k] for k in
                      ["n_episodes_total", "n_by_task", "L50_by_task", "structural_checks"]},
                     indent=1, ensure_ascii=False))
    for r in kendall_rows:
        print(f"  {r['task']:>14s} {r['comparison']:<28s} n_cmp={r['n_strategies_comparable']} "
              f"tau_b={r['tau_b']:.4f} flips={r['n_flips']}/{r['n_pairs']} -> {r['verdict']}")
    print("PILOT RANKING DONE")


if __name__ == "__main__":
    main()
