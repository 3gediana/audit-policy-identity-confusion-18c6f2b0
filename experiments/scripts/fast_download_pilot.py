# -*- coding: utf-8 -*-
"""Resumable parallel downloader for the pilot expansion (exact byte sizes, no mib rounding).

Reads download_plan_pilot.json (missing files only; `bytes` is the authoritative HF size).
Idempotent: reruns resume via Range requests. Writes fast_dl_report_pilot.json.
"""
import json, os, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

sys.stdout.reconfigure(line_buffering=True)
SCRATCH = os.path.dirname(os.path.abspath(__file__))
PROJECT = "D:/hermes-data/research/审计真机基准的策略身份混淆-18c6f2b0"
CACHE_ROOT = os.path.join(PROJECT, "assets", "hf")
plan = json.load(open(os.path.join(SCRATCH, "download_plan_pilot.json"), encoding="utf-8"))
DEADLINE = time.time() + float(os.environ.get("DL_DEADLINE_S", "4200"))
CONNECT_T, READ_T = 10, 25

REPO_SHORT = {"armnet/armnetbench_v01_lerobot_so101": "so101",
              "armnet/armnetbench_v01_lerobot_bimanual_so101": "bimanual"}


def dl_one(repo, f):
    url = f"https://huggingface.co/datasets/{repo}/resolve/main/{f['path']}"
    local = os.path.join(CACHE_ROOT, REPO_SHORT[repo], f["path"])
    os.makedirs(os.path.dirname(local), exist_ok=True)
    expect = int(f["bytes"])
    attempt = 0
    while time.time() < DEADLINE:
        cur = os.path.getsize(local) if os.path.exists(local) else 0
        if cur >= expect:
            return ("ok", f["path"], cur)
        if attempt >= 25:
            return ("attempts_exhausted", f["path"], cur)
        attempt += 1
        headers = {"Range": f"bytes={cur}-"} if cur else {}
        try:
            with requests.get(url, headers=headers, stream=True, timeout=(CONNECT_T, READ_T),
                              allow_redirects=True) as r:
                if r.status_code == 416:
                    # offset beyond EOF: if we already hold >= remote size we are done
                    cr = r.headers.get("Content-Range", "")
                    total = cr.split("/")[-1] if "/" in cr else "-1"
                    if total.isdigit() and cur >= int(total):
                        return ("ok", f["path"], cur)
                    time.sleep(4)
                    continue
                if r.status_code not in (200, 206):
                    time.sleep(4)
                    continue
                mode = "ab" if (cur and r.status_code == 206) else "wb"
                with open(local, mode) as fh:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        fh.write(chunk)
        except requests.RequestException as e:
            print(f"  {f['path']}: retry after {type(e).__name__} at offset {cur}")
            time.sleep(2)
    cur = os.path.getsize(local) if os.path.exists(local) else 0
    return ("deadline", f["path"], cur)


def main():
    jobs = []
    for short in ["so101", "bimanual"]:
        entry = plan[short]
        for f in entry["files"]:
            jobs.append((entry["repo"], f))
    results = {}
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(dl_one, repo, f): f["path"] for repo, f in jobs}
        done_ct = 0
        for fut in as_completed(futs):
            status, path, size = fut.result()
            results[path] = {"status": status, "bytes": size}
            done_ct += 1
            print(f"[{done_ct}/{len(jobs)}] {status} {path} {size/2**20:.1f}MiB "
                  f"({(time.time()-t0):.0f}s)")
    ok = sum(1 for v in results.values() if v["status"] == "ok")
    json.dump({"ok": ok, "total": len(jobs), "results": results,
               "seconds": round(time.time() - t0, 1)},
              open(os.path.join(SCRATCH, "fast_dl_report_pilot.json"), "w"), indent=1)
    print(f"FAST DL PILOT DONE ok={ok}/{len(jobs)} in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
