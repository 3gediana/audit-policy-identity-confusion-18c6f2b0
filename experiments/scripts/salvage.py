import json, os, shutil
plan = json.load(open("D:/hermes-data/profiles/lab-executor/cache/scratch/download_plan_min.json"))
root = "D:/hermes-data/research/审计真机基准的策略身份混淆-18c6f2b0/assets/hf"
for short, entry in plan.items():
    for f in entry["files"]:
        wrong = os.path.join(root, "armnetbench_v01_lerobot_" + short, f["path"])
        right = os.path.join(root, short, f["path"])
        expect = int(f["mib"] * 2**20)
        if os.path.exists(wrong) and os.path.getsize(wrong) == expect and not (
                os.path.exists(right) and os.path.getsize(right) == expect):
            os.makedirs(os.path.dirname(right), exist_ok=True)
            shutil.move(wrong, right)
            print("salvaged", f["path"])
print("salvage done")
