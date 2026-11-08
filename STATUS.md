# 状态

- 阶段：design（ready，night_dispatch=true 已放行）。screening 已由 researcher 判读收口（通过放行）；workflow.json 已实例化（模板 new_measurement v2：design→smoke→pilot→experiment→analysis，五节点任务书已按课题定制）。
- 最近更新：2026-11-09T01:23:00+08:00（researcher 判读 screening 回执 3e3528c8：PASS）
- 最近产物：admission.json（admitted，evidence_ledger 11 条，c4=unknown）；literature/related-work.md；workflow.json（实例化+定制）；notes/researcher-interventions/a1d6c5c881005957a1323a6fe91f25ad.md（判读记录）
- 下一步：design 单元（estimate 75min，profile=lab-planner，reasoning=xhigh，model_override=null→调度器按责任路由选非 GPT、支持工具的 worker）：①Scholar/OpenReview 新颖性收口（命中即按 stop_if_not_novel 停，写 RETRO+求助）；②HF parquet 元数据批次轴核验（不可恢复则分层退化按任务并重估功效，回填 admission uncertainties[1]）；③experiments/protocol.md（探针/分层/判据/三臂严格定义，口径算两次同数）；④experiments/prereg.md+决策价值三行。回执到达后 researcher 判读 novelty-c4 结论与批次轴结论，通过则放行 smoke（8G 卡；正控=探针分任务≈1.0 / 负控=策略标签置换≈0.5 已冻结在 workflow）。
- 研究员唤醒点：design 回执（判读 novelty/批次轴后放行 smoke）；novelty 命中重叠或 HF 语料不可达 → help.request_researcher 即时唤醒。持续跟踪 LamportRobotics 上传（若出现 rollout 语料审计即触发 stop_if_not_novel 复查）。
- 关键证据锚点：2611.03168 §5 逐字引语（身份可推断/长度泄漏/近二值标签）见 literature/related-work.md §2；OpenAlex 前向被引 0（W7225193298，2026-11-09）；新颖性主张 c4 标 unknown（4 渠道覆盖，Scholar/OpenReview 全遍历已列为 design 第①步）。
