# -*- coding: utf-8 -*-
"""Pilot probe run on the full pilot feature set (both pilot tasks, all covered episodes).

Usage: python pilot_probe.py <RUNID>   (RUNID in A/B/C; three independent runs)
Frozen gates identical to smoke (experiments/prereg.md / protocol.md sections 2-3):
- main: held-out macro OVR AUC, 7 policy classes, label=policy_type of rollout rows
- positive control: label=task, expect AUC >= 0.90
- negative control: permuted policy labels, seed 20261110, expect macro AUC ~= 0.5 within
  the 95% null band from actual test counts (Hanley-McNeil null variance)
- reliability: three independent runs bitwise identical (|diff| <= 1e-12)
- split: 80/20 stratified by task x policy_type, seed 20261109
- LR: multinomial lbfgs L2 C=1.0 max_iter=2000 class_weight=balanced
- bootstrap CI: B=2000 seed 20261111, resampled test episodes, percentile
Plus the pilot-only negative-control convergence check vs smoke (test set grows
219 -> N episodes): the neg point estimate must move toward 0.5 (or at least not away)
and stay inside its own null band. Reported, never tuned.
"""
import hashlib, json, os, sys, time

import numpy as np
import pandas as pd

RUNID = sys.argv[1] if len(sys.argv) > 1 else "A"
SCRATCH = os.path.dirname(os.path.abspath(__file__))
PROJECT = "D:/hermes-data/research/审计真机基准的策略身份混淆-18c6f2b0"
FRAG_DIR = os.path.join(PROJECT, "experiments", "cache")
RESULTS = os.path.join(PROJECT, "results")
os.makedirs(RESULTS, exist_ok=True)

SPLIT_SEED = 20261109
PERM_SEED = 20261110
BOOT_SEED = 20261111
BOOT_B = 2000

import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, confusion_matrix

parts, metas = [], []
for short in ["so101", "bimanual"]:
    frag = os.path.join(FRAG_DIR, "pilot_%s_.npz" % {"so101": "cable_clip",
                                                     "bimanual": "fold_tea_towel"}[short])
    d = np.load(frag, allow_pickle=False)
    parts.append(d["Z"])
    metas.extend([str(k) for k in d["keys"]])
X = np.concatenate(parts, axis=0).astype(np.float32)
ep_all = np.array(metas)

meta = pd.read_csv(os.path.join(FRAG_DIR, "pilot_episodes.csv"))
meta["row_id"] = meta["repo"].astype(str) + "|" + meta["episode_index"].astype(int).astype(str)
meta = meta.drop_duplicates(subset=["row_id"]).reset_index(drop=True)
mm = meta.set_index(["row_id"])
task = np.array([str(mm.loc[str(e)]["task_str"]) for e in ep_all])
pol = np.array([str(mm.loc[str(e)]["policy_type"]) for e in ep_all])
success = np.array([int(mm.loc[str(e)]["success"]) for e in ep_all])

n = len(X)
strat = np.array([f"{t}||{p}" for t, p in zip(task, pol)])
print(f"X={X.shape} episodes; classes={sorted(set(pol))}; strat cells={len(set(strat))}")

tr, te = train_test_split(np.arange(n), test_size=0.2, random_state=SPLIT_SEED, stratify=strat)
print(f"split: train={len(tr)} test={len(te)}")

t0 = time.time()
fingerprint = hashlib.sha256()
fingerprint.update(X.tobytes())
fingerprint.update(pol.tobytes()); fingerprint.update(task.tobytes())
fingerprint.update(tr.tobytes()); fingerprint.update(te.tobytes())
FP = fingerprint.hexdigest()[:16]


def fit_lr(y_labels, idx_tr):
    clf = LogisticRegression(C=1.0, solver="lbfgs", max_iter=2000,
                             class_weight="balanced")
    clf.fit(X[idx_tr], y_labels[idx_tr])
    return clf


tM = time.time()
clf = fit_lr(pol, tr)
sc = clf.predict_proba(X[te])
auc_main = float(roc_auc_score(pol[te], sc, multi_class="ovr", average="macro"))
per_class = {}
for ci, c in enumerate(clf.classes_):
    yb = (pol[te] == c).astype(int)
    per_class[str(c)] = {"n_test": int(yb.sum()), "auc": float(roc_auc_score(yb, sc[:, ci]))}
cm = confusion_matrix(pol[te], clf.predict(X[te]), labels=list(clf.classes_))
acc = float((clf.predict(X[te]) == pol[te]).mean())
t_main = time.time() - tM

tP = time.time()
clf_p = fit_lr(task, tr)
sc_p = clf_p.predict_proba(X[te])
if len(set(task)) == 2:
    auc_pos = float(roc_auc_score((task[te] == clf_p.classes_[1]).astype(int), sc_p[:, 1]))
else:
    auc_pos = float(roc_auc_score(task[te], sc_p, multi_class="ovr", average="macro"))
t_pos = time.time() - tP

tN = time.time()
rng = np.random.default_rng(PERM_SEED)
perm = rng.permutation(n)
pol_perm = pol[perm]
clf_n = fit_lr(pol_perm, tr)
sc_n = clf_n.predict_proba(X[te])
auc_neg = float(roc_auc_score(pol_perm[te], sc_n, multi_class="ovr", average="macro"))
t_neg = time.time() - tN

ses = []
for c in clf_n.classes_:
    npos = int((pol_perm[te] == c).sum())
    nneg = int((pol_perm[te] != c).sum())
    ntot = npos + nneg
    ses.append((ntot + 1) / (12.0 * npos * nneg))
macro_se = float(np.sqrt(np.mean(ses)))
band_lo, band_hi = 0.5 - 1.96 * macro_se, 0.5 + 1.96 * macro_se

tB = time.time()
rngb = np.random.default_rng(BOOT_SEED)
n_te = len(te)
boot = []
skipped = 0
for b in range(BOOT_B):
    idx = rngb.integers(0, n_te, n_te)
    yb = pol[te][idx]
    if len(set(yb)) < len(clf.classes_):
        skipped += 1
        continue
    boot.append(roc_auc_score(yb, sc[idx], multi_class="ovr", average="macro"))
ci_lo, ci_hi = np.percentile(boot, [2.5, 97.5])
t_boot = time.time() - tB

# ---- negative-control convergence vs smoke (test set growth) ----
conv = {"pilot_test_n": int(len(te)), "pilot_neg_auc": auc_neg,
        "pilot_abs_dev_from_half": abs(auc_neg - 0.5), "pilot_null_band": [band_lo, band_hi]}
try:
    smoke = json.load(open(os.path.join(RESULTS, "smoke_probe_run_A.json"), encoding="utf-8"))
    conv.update({"smoke_test_n": smoke["n_test"], "smoke_neg_auc": smoke["auc_negative_control_permuted"],
                 "smoke_abs_dev_from_half": abs(smoke["auc_negative_control_permuted"] - 0.5),
                 "smoke_null_band": smoke["null_band_95"]})
    conv["dev_shrank_with_bigger_test"] = conv["pilot_abs_dev_from_half"] <= conv["smoke_abs_dev_from_half"]
    conv["band_shrank_with_bigger_test"] = ((band_hi - band_lo) <=
                                            (smoke["null_band_95"][1] - smoke["null_band_95"][0]))
    conv["pilot_neg_within_own_band"] = bool(band_lo <= auc_neg <= band_hi)
except Exception as e:
    conv["smoke_comparison"] = f"unavailable: {e}"

import torch, transformers, PIL
out = {
    "runid": RUNID, "stage": "pilot",
    "n_episodes": int(n), "n_train": int(len(tr)), "n_test": int(len(te)),
    "n_classes": int(len(clf.classes_)),
    "split_seed": SPLIT_SEED, "perm_seed": PERM_SEED, "boot_seed": BOOT_SEED, "boot_B": BOOT_B,
    "auc_main_macro_ovr": auc_main,
    "auc_main_per_class": per_class,
    "auc_main_bootstrap_ci95": [float(ci_lo), float(ci_hi)],
    "boot_skipped_resamples": skipped,
    "test_accuracy": acc,
    "auc_positive_control_task": auc_pos,
    "n_task_classes": int(len(set(task))),
    "auc_negative_control_permuted": auc_neg,
    "null_band_95": [float(band_lo), float(band_hi)],
    "null_macro_se": macro_se,
    "neg_control_convergence": conv,
    "confusion_matrix_test": cm.tolist(),
    "confusion_classes": [str(c) for c in clf.classes_],
    "config_fingerprint": FP,
    "timings_s": {"main": round(t_main, 3), "pos": round(t_pos, 3),
                  "neg": round(t_neg, 3), "boot": round(t_boot, 3)},
    "env": {"sklearn": sklearn.__version__, "numpy": np.__version__,
            "torch": torch.__version__, "transformers": transformers.__version__,
            "pillow": PIL.__version__, "python": sys.version.split()[0]},
    "success_labels_included": True,
}
outp = os.path.join(RESULTS, f"pilot_probe_run_{RUNID}.json")
json.dump(out, open(outp, "w", encoding="utf-8"), indent=1)
print(json.dumps({k: out[k] for k in
                  ["auc_main_macro_ovr", "auc_positive_control_task",
                   "auc_negative_control_permuted", "null_band_95",
                   "auc_main_bootstrap_ci95", "config_fingerprint"]}, indent=1))
print("neg convergence:", json.dumps(conv, indent=1))
print(f"PILOT PROBE RUN {RUNID} DONE -> {outp}")
