# 状态

- 阶段：design 已判读放行（2026-11-09 夜 batch-20261109T013318）→ smoke 待跑；workflow：design→smoke→pilot→experiment→analysis。
- 最近更新：2026-11-09T02:15:00+08:00（researcher 判读 design 回执：PASS）
- 最近产物：experiments/prereg.md（门线/seed/三臂冻结）；experiments/protocol.md（批次轴冻结 task-only fallback + 正/负控口径）；literature/novelty-c4-check.md（c4=unknown，stop_if_not_novel 未触发）；姊妹课题 438aa6b2 的 4 条近邻证据已并入 literature/related-work.md §7。
- 下一步：smoke——①meta/episodes parquet schema 复核 session/batch 字段（无 → 固化 task-only fallback 并标 batch_axis=unavailable_task_fallback）；②同特征缓存+固定 split（seed 20261109）主探针重算两次差≤1e-12；③正控（标签=task）AUC≥0.90；④负控（seed 20261110 置换 policy_repo_id）≈0.5 且在预注册噪声带内；结果落 results/。任一门失败按预注册回炉 design，不解释主探针。
- 组合层去重（2026-11-09 判读拍板）：同题姊妹 438aa6b2 已 duplicate-merged 归档，本课题为唯一推进线；保留 pivot 三条见 notes/DECISIONS.md。
- 研究员唤醒点：smoke 回执（判正/负控与两次同数）；负控偏离或正控失败 → 回炉 design 即时唤醒；持续跟踪 LamportRobotics 上传（若出现 rollout 语料审计即触发 stop_if_not_novel 复查）。
- 关键证据锚点：2611.03168 §5 逐字引语（身份可推断/长度泄漏/近二值标签）见 literature/related-work.md §2；OpenAlex 前向被引 0（W7225193298，2026-11-09）；Eval-Actions 2601.18723（策略 vs 遥操源头判别 99.6%）为身份信号存在的旁证（姊妹筛查并入，§7）。
