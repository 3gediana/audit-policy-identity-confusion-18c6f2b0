# design 阶段复盘

- 做对了什么：先做新颖性收口，再冻结批次轴退化口径，避免在前提未清时搭特征缓存或跑全量。
- 证据在哪：`literature/novelty-c4-check.md`、`experiments/protocol.md`、`experiments/prereg.md`；HF 数据卡与 first-rows API 的真实响应支持字段边界。
- 关键判断：c4 未发现占位但仍为 unknown；数据卡未声明 session/batch，因此协议禁止用 episode_index 冒充批次，并冻结 task-only fallback。
- 下一个最小同类改进：smoke 只用两任务验证同缓存两次同数、正控和置换负控，30–40 分钟内可判断尺子是否可用。
- 可复用路径：新颖性查询表 + schema 证据 + 明确退化标签 + 三臂预注册，适合其他基准审计，暂不回写模板。
- 本阶段没有科学结果；没有启动长实验，也没有需要替代方向的失败证据。
