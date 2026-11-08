# 决策台账 — 审计真机基准的策略身份混淆

- 用户批准候选方向（审批 auto:cand-18c6f2b0fcf58abc，2026-11-08T17:30:55+08:00）。
- [2026-11-09 夜 screening] decision=admitted（admission 门首轮 eligible=true）。依据：被审计对象全文逐字引语在盘 + 四渠道检索无占位 + 前向被引 0 + Lamport 审计簇不占空位；新颖性主张 c4 按纪律标 unknown。
- [2026-11-09 夜 screening] 分层轴修正：由 brief 旧口径的（任务×机位单元）改为（任务×采集批次/会话）。证据=§5 原文"每任务固定一个单元"（任务与单元嵌套，按单元分层退化为按任务分层）+"机位缺陷影响除 MolmoAct 2 外所有策略"（缺陷归属是批次不是策略）。待 design 读 parquet 元数据核验批次可恢复性。
- [2026-11-09 夜 screening] MiTA 式统一理论视角评估为可选启发、不套用：本课题交付测量与判据，不构建统一解释框架（记入 uncertainties，防为新颖性包装概念）。
- [2026-11-09 夜 researcher 判读 screening 回执 3e3528c8] 判读=通过放行：admission.json（admitted，evidence_ledger 11 条，c1-c7 含 c4=unknown）、literature/related-work.md（8 式 5 渠道+双向引文追踪+§5 逐字引语）、STATUS 三件与回执一致；按判读速度纪律抽样核对关键锚点（c4/分层轴/stop_if_not_novel/引语），不重跑 screening。
- [2026-11-09 夜 researcher 判读] 实例化 workflow.json（模板 new_measurement v2：design→smoke→pilot→experiment→analysis）。现场定制记档：①design 第①步=Scholar/OpenReview 新颖性收口（stop_if_not_novel 要求 design 前清，c4 的 unknown 由此步收口）；②smoke.wake 模板默认 user→null（夜班自主流，判读走 unit.receipt 事件；analysis 保留 wake=user 作自然收口点）；③五节点任务书按课题改写：smoke 正控=探针分任务 AUC≈1.0、负控=策略标签置换≈0.5，B 臂长度截断规则必须在协议写死；④design.night_dispatch=true（2026-11-01 r24 判读放行授权，防 analysis/design 判读类阶段被 P3 门控丢弃）。
- [2026-11-09 夜 researcher 判读] 工具时刻评估：本判读无量化指标进结论（admission 为定性证据账本，无 metrics.json）→ repr_analyze 不适用；准入干净通过且无 replicate/redesign 分岔，c4 风险有更便宜的直接验证路径（遍历本身）→ 不开 roundtable/debate。
- [2026-11-09 夜 researcher 判读] brief 自创方法段分层轴残留「任务×机位单元」同步修正为「任务×采集批次/会话（含退化口径）」，与预测②及 screening 修正条一致。
- [2026-11-09 design 可预见性自检] 干预量级：冻结特征+线性探针是低位移、可直接测的审计干预；可判性：AUC 门线 0.55 与正/负控分别远离/贴近随机基线，2 任务 smoke 足以先判尺子，不先跑全量；读码：固定 episode split、独立标签置换和两次同缓存重算能检出 RNG/缓存覆盖问题。三项通过，允许进入 smoke。
- [2026-11-09 design] Scholar/OpenReview 定向收口未发现同一公开语料的身份探针量化或分层排名重算；c4 仍 unknown，stop_if_not_novel 未触发。HF 数据卡/API 未声明可恢复 session/batch 字段，协议冻结 task-only fallback，禁止用 episode_index 冒充批次。
- [2026-11-09 夜 researcher 判读 design 回执（batch-20261109T013318）] 判读=通过放行 smoke：prereg 冻结 + 协议严到两次同数（≤1e-12）+ 批次轴退化口径落盘 + novelty c4 收口未触发 stop_if_not_novel，抽样核验未重跑；smoke 任务书增补 schema 复核步（meta/episodes 是否存在非空 session/batch 字段，无→固化 task-only fallback 并标 batch_axis=unavailable_task_fallback）。
- [2026-11-09 夜 组合层去重拍板（batch-20261109T013318）] 同题姊妹 438aa6b2（screening admitted 2026-11-09T01:30）按 duplicate-merged 归档，本课题为唯一推进线：同问题/同语料/同三臂方法，双线只重复消耗且会产生两个同题仓库；对方严格领先性不成立（本课题 design 已冻结），故留本弃彼。其独立筛查的 4 条近邻（RoboArena 2506.18123 / Eval-Actions 2601.18723 / RoboView-Bias 2509.22356 / leaderboard-τ 2605.15761，均判不占位）与 ev-2611-metadata（2,518 条基准 rollout 无归属标注 → leaderboard 不可精确复现）已并入 literature/related-work.md。保留 pivot（要开须走新 candidate）：①leaderboard 不可复现审计；②长度泄漏量化单臂；③Lamport 跟进簇升级到 rollout 审计时重筛。
