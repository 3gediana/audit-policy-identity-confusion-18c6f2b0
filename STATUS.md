# 状态

- 阶段：candidate/screening（screening 已完成，admission 门 eligible=true，decision=admitted；未进 design，不涉实验）
- 最近更新：2026-11-09T00:25:00+08:00
- 最近产物：admission.json（research-topic-admission/v1，eligible=true，evidence_ledger 11 条）；literature/related-work.md（4 渠道 8 查询式 + 逐字引语 + 未知项）
- 下一步：进 design 阶段——①读 HF parquet 元数据确认采集批次轴可恢复性（§5 引语表明混淆按单元×批次分布、每任务固定单元，brief 旧口径的"任务×机位单元"分层轴已修正，见 DECISIONS）；②探针 pilot 设计（2 任务 × 7 策略，留出 AUC + 混淆矩阵，8G 卡 30 分钟）；③长度截断匹配对照臂协议。跟踪 LamportRobotics 后续上传（跟进簇活跃，5 小时前仍在更新；若出现 rollout 语料审计即触发 stop_if_not_novel 复查）。
- 关键证据锚点：2611.03168 §5 逐字引语（身份可推断/长度泄漏/近二值标签）见 literature/related-work.md §2；OpenAlex 前向被引 0（W7225193298，2026-11-09）；新颖性主张 c4 标 unknown（仅 4 渠道覆盖，Scholar/OpenReview 全遍历未做）。
