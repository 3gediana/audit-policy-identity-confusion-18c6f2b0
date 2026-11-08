# 状态

- 阶段：smoke 进行中（2026-11-09 夜 checkpointed 单元）——①schema 复核已完成并落盘（batch_axis=unavailable_task_fallback 固化）；②③④（两次同数/正控/负控）**待跑**：数据下载未完成，按断点续跑；workflow：design→smoke→pilot→experiment→analysis。
- 最近更新：2026-11-09T04:02:00+08:00（executor 夜间单元，schema 结果落盘 + 下载断点）
- 最近产物：results/schema_snapshot.json（两仓 meta/episodes 全列 census：无 session/batch/采集字段，chunk/file_index 是存储切块不是采集批次；task-only fallback 按预注册固化）；experiments/scripts/（全套可续跑脚本：scope_reduce.py→fast_download.py→smoke_extract.py→probe_run.py×3→aggregate_smoke.py + download_plan_min.json）。
- smoke 范围拍板（executor，预注册内）：为守成本门（estimate 40min×2），smoke 跑 design 冻结的 2 个 pilot 任务（cable_clip=front 视图 + fold_tea_towel=top 视图）而非全 12 任务——prereg 决策价值第 3 行明文 smoke 不做 12 任务长特征提取；视频文件按「每 (task,policy_type) 格 ≥10 eps、文件按 eps/MB 贪心」最小集选（25 文件/2.78GiB/219 eps，纯 meta 清单规则，无结果性挑选）。标签=policy_type（7 类）：policy_repo_id 内嵌任务 slug（56 变体+空=teleop），7 类粒度的身份标签按协议落地为 policy_type（rollout 行），已记 DECISIONS。
- 断点（下一单元从这里续）：
  1. `python experiments/scripts/fast_download.py`（断点续传：.mp4 按大小补齐 25 个文件；网络实测单连接 0.3-0.7MB/s、多连接 2-3MB/s、会中途断流，脚本带读超时+Range 续传；DL_DEADLINE_S 可调）；
  2. `python experiments/scripts/prefetch_model.py`（DINOv2-small ~90MB 入 HF 缓存，可与 1 并行）；
  3. `python experiments/scripts/smoke_extract.py`（只解码完整文件，缺文件自动收缩范围并打印 WARN）；
  4. `python experiments/scripts/probe_run.py A`（B、C 同理，三次独立执行，读同一特征缓存）；
  5. `python experiments/scripts/aggregate_smoke.py`（判门线：两次同数≤1e-12、正控≥0.90、负控在 95% null 带内、成本≤估算×2，写 results/smoke_summary.json 等）。
  assets/hf/armnetbench_v01_lerobot_*/ 下的残留半截文件是旧下载器路径 bug 的产物，可删；salvage.py 已把完整文件搬回正位。
- 组合层去重（2026-11-09 判读拍板）：同题姊妹 438aa6b2 已 duplicate-merged 归档，本课题为唯一推进线；保留 pivot 三条见 notes/DECISIONS.md。
- 研究员唤醒点：smoke 回执（判正/负控与两次同数）；负控偏离或正控失败 → 回炉 design 即时唤醒；持续跟踪 LamportRobotics 上传（若出现 rollout 语料审计即触发 stop_if_not_novel 复查）。
- 关键证据锚点：2611.03168 §5 逐字引语（身份可推断/长度泄漏/近二值标签）见 literature/related-work.md §2；OpenAlex 前向被引 0（W7225193298，2026-11-09）；Eval-Actions 2601.18723（策略 vs 遥操源头判别 99.6%）为身份信号存在的旁证（姊妹筛查并入，§7）。
