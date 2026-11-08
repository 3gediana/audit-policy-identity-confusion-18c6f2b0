---
stage: smoke
kind: experiment
status: ok
did: 跑完 smoke 全流程：续传 25 个视频并核验完整、提取 219 eps 冻结特征、三次独立探针判门——四门全过，verdict=supported，尺子可用放行 pilot。
why: smoke 要先判探针这把尺子稳不稳、准不准、多贵，才能信任后续身份混淆量化与排名重评的任何数字。
how: 门线全按 prereg 冻结口径判：两次同数≤1e-12、正控≥0.90、负控落 95% null 带、成本≤估算×2；视频完整性用 HF Content-Range 权威字节数对账；发现的实现 bug 只修实现不改协议，全部记 DECISIONS。
result: 主探针（policy_type 7 类，219 eps）宏 OVR AUC=0.8896，CI [0.8288,0.9402]；正控=1.0；负控=0.5569 落 null 带 [0.249,0.751]；3 次重算指纹全同、AUC 极差 0.0；提取 117.1s/GPU 491MiB。批注：负控点估计略高属小测试集噪声，pilot 复核。
next: researcher 判读后派 pilot：三臂排名重评（A 探针分层/B 长度截断/C 原始成功率），产 ranking_A/B/C.csv+pairwise_flips.csv+Kendall tau-b 判翻转。
artifacts: [results/smoke_summary.json, results/smoke_probe_run_A.json, results/smoke_probe_run_B.json, results/smoke_probe_run_C.json, results/smoke_config.json, results/smoke_cost.json, results/schema_snapshot.json, results/smoke_episodes.csv, results/confusion_matrix.csv, results/README.md, experiments/scripts/size_verification.json, notes/DECISIONS.md, notes/RETRO.md, STATUS.md]
info_need: 无
plain_summary: 我们先验证审计尺子：冻结视觉特征的线性探针能在留出录像上以 AUC 0.89 识别 7 个策略身份（正控满分、负控随机），三次独立重算完全一致，成本远低于预算，身份泄漏的量化测量地基成立。
---
