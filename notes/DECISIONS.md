# 决策台账 — 审计真机基准的策略身份混淆

- 用户批准候选方向（审批 auto:cand-18c6f2b0fcf58abc，2026-11-08T17:30:55+08:00）。
- [2026-11-09 夜 screening] decision=admitted（admission 门首轮 eligible=true）。依据：被审计对象全文逐字引语在盘 + 四渠道检索无占位 + 前向被引 0 + Lamport 审计簇不占空位；新颖性主张 c4 按纪律标 unknown。
- [2026-11-09 夜 screening] 分层轴修正：由 brief 旧口径的（任务×机位单元）改为（任务×采集批次/会话）。证据=§5 原文"每任务固定一个单元"（任务与单元嵌套，按单元分层退化为按任务分层）+"机位缺陷影响除 MolmoAct 2 外所有策略"（缺陷归属是批次不是策略）。待 design 读 parquet 元数据核验批次可恢复性。
- [2026-11-09 夜 screening] MiTA 式统一理论视角评估为可选启发、不套用：本课题交付测量与判据，不构建统一解释框架（记入 uncertainties，防为新颖性包装概念）。
- [2026-11-09 夜 researcher 判读 screening 回执 3e3528c8] 判读=通过放行：admission.json（admitted，evidence_ledger 11 条，c1-c7 含 c4=unknown）、literature/related-work.md（8 式 5 渠道+双向引文追踪+§5 逐字引语）、STATUS 三件与回执一致；按判读速度纪律抽样核对关键锚点（c4/分层轴/stop_if_not_novel/引语），不重跑 screening。
- [2026-11-09 夜 researcher 判读] 实例化 workflow.json（模板 new_measurement v2：design→smoke→pilot→experiment→analysis）。现场定制记档：①design 第①步=Scholar/OpenReview 新颖性收口（stop_if_not_novel 要求 design 前清，c4 的 unknown 由此步收口）；②smoke.wake 模板默认 user→null（夜班自主流，判读走 unit.receipt 事件；analysis 保留 wake=user 作自然收口点）；③五节点任务书按课题改写：smoke 正控=探针分任务 AUC≈1.0、负控=策略标签置换≈0.5，B 臂长度截断规则必须在协议写死；④design.night_dispatch=true（2026-11-01 r24 判读放行授权，防 analysis/design 判读类阶段被 P3 门控丢弃）。
- [2026-11-09 夜 researcher 判读] 工具时刻评估：本判读无量化指标进结论（admission 为定性证据账本，无 metrics.json）→ repr_analyze 不适用；准入干净通过且无 replicate/redesign 分岔，c4 风险有更便宜的直接验证路径（遍历本身）→ 不开 roundtable/debate。
- [2026-11-09 夜 researcher 判读] brief 自创方法段分层轴残留「任务×机位单元」同步修正为「任务×采集批次/会话（含退化口径）」，与预测②及 screening 修正条一致。
