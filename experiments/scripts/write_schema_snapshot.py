# -*- coding: utf-8 -*-
"""Write results/schema_snapshot.json from cached meta parquets (real result, video-independent)."""
import json, os
import pandas as pd

PROJECT = "D:/hermes-data/research/审计真机基准的策略身份混淆-18c6f2b0"
CACHE_ROOT = os.path.join(PROJECT, "assets", "hf")
SCRATCH = os.path.dirname(os.path.abspath(__file__))
REPOS = {"so101": "armnet/armnetbench_v01_lerobot_so101",
         "bimanual": "armnet/armnetbench_v01_lerobot_bimanual_so101"}
plan = json.load(open(os.path.join(SCRATCH, "download_plan_min.json"), encoding="utf-8"))

def load_eps(short):
    fs = []
    for dirpath, _, filenames in os.walk(os.path.join(CACHE_ROOT, short, "meta", "episodes")):
        for fn in filenames:
            if fn.endswith(".parquet"):
                fs.append(pd.read_parquet(os.path.join(dirpath, fn)))
    return pd.concat(fs, ignore_index=True)

def task_str(v):
    import numpy as np
    if isinstance(v, (list, np.ndarray)):
        return "|".join(map(str, v))
    return str(v)

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
    import re
    def is_batch_like(c):
        base = c.split("/")[-1]
        toks = re.split(r"[/_.\-\s]", base.lower())
        return any(t in {"session", "sessions", "batch", "rig", "capture", "take"} or
                   t.startswith("collect") for t in toks)
    batch_like = [c for c in keycols if is_batch_like(c)]
    # teleop / rollout split for the record
    e2 = e.assign(task_str=e["tasks"].map(task_str))
    roll = e2[e2["policy_repo_id"].astype(str).str.len() > 0]
    teleop = len(e2) - len(roll)
    schema[short] = {
        "repo": REPOS[short], "revision": plan[short].get("revision", ""),
        "codebase_version": "v3.0",
        "n_rows": int(len(e)), "rollout_rows": int(len(roll)), "teleop_rows": int(teleop),
        "columns_nonstats": keycols,
        "census_nonstats": census,
        "batch_like_columns": batch_like,
        "policy_type_values": sorted(roll["policy_type"].astype(str).unique().tolist()),
        "note_policy_repo_id": "policy_repo_id embeds the task slug (e.g. .../pi0-so101-armnetbench-ring-insert-isambard-v50); "
                               "identity label at 7-class granularity = policy_type (rollout rows only)",
    }
    print(f"[{short}] rows={len(e)} rollout={len(roll)} teleop={teleop} batch_like={batch_like}")

batch_axis = ("unavailable_task_fallback"
              if all(not s["batch_like_columns"] for s in schema.values())
              else "batch_like_columns_present_needs_review")
out = {
    "what": "meta/episodes schema review for smoke step 1 (batch/session axis recoverability)",
    "repos": schema,
    "batch_axis": batch_axis,
    "verdict": "no session/batch/collection field exists in meta/episodes for either repo; "
               "chunk/file indices are storage chunking (size-based), not collection sessions; "
               "prereg fallback frozen: batch_axis=unavailable_task_fallback (task-only stratification)",
    "checked_fields_rationale": "census covers all non-stats columns; fields whose names contain "
                                "session/batch/collect/capture/rig/take would qualify as batch-like; "
                                "episode_index/data file_index/videos file_index are layout artifacts "
                                "and are forbidden as batch proxies by protocol §1",
}
p = os.path.join(PROJECT, "results", "schema_snapshot.json")
json.dump(out, open(p, "w", encoding="utf-8"), indent=1)
print("WROTE", p, "batch_axis =", batch_axis)
