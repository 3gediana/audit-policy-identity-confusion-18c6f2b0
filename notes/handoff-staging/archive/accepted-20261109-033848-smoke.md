---
stage: smoke
kind: experiment
status: partial
did: 完成 smoke 第①步 schema 复核并落盘 results/schema_snapshot.json（两仓均无 session/batch 采集字段→batch_axis=unavailable_task_fallback 固化）；第②③④步（两次同数/正控/负控）因 HF 数据下载未完成未跑，已写断点与全套续跑脚本。
why: smoke 要先验「尺子」稳不准再谈主探针，但尺子验证依赖冻结特征缓存；视频语料 99GB 全量不可行，按 prereg 决策价值第3行只取 2 个 pilot 任务最小集（25 文件/2.78GiB），当晚网络 2-3MB/s 且两次断流，单元 90 分钟硬顶内只够完成 schema 步与下载断点。
how: schema 判读=对两仓 meta/episodes 全列做非空/唯一值 census，词边界匹配 session/batch/rig/collect/take 类字段名，排除按大小切块的 chunk/file_index 假批次代理；标签落地=policy_type（7类，rollout 行）；范围选文件=每 (task,policy_type) 格≥10eps 按 eps/MB 贪心（纯 meta 清单规则，无结果性挑选）；续跑链=fast_download.py→prefetch_model.py→smoke_extract.py→probe_run.py A/B/C→aggregate_smoke.py，门线全部照 prereg 冻结口径判。
result: 尚无论证性结果（探针门线未测）。已固化事实：batch_axis=unavailable_task_fallback（schema 证据落盘）；数据 revision so101=1db69c82、bimanual=c4841758；scope=2 任务×7 策略×219 eps 计划；下载断点 1.4GiB/2.78GiB 在盘，断点续传可续。
next: 下一单元按 STATUS 断点 1-5 执行：续传 25 个视频文件→缓存 DINOv2-small→抽特征→三次独立探针（同缓存同 split seed 20261109）→aggregate 判四门（两次同数≤1e-12、正控≥0.90、负控在 95% null 带、成本≤估算×2）→真实 results/ 回执。
artifacts: [results/schema_snapshot.json, experiments/scripts/fast_download.py, experiments/scripts/scope_reduce.py, experiments/scripts/download_plan_min.json, experiments/scripts/smoke_extract.py, experiments/scripts/probe_run.py, experiments/scripts/aggregate_smoke.py, experiments/scripts/prefetch_model.py, STATUS.md, notes/DECISIONS.md]
info_need: 无（断点自足；网络仍是瓶颈，若 fast_download 仍断流按 STATUS 记录的速率与并发参数调 DL_DEADLINE_S 分晚跑）
---
