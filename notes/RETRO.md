# design 阶段复盘

- 做对了什么：先做新颖性收口，再冻结批次轴退化口径，避免在前提未清时搭特征缓存或跑全量。
- 证据在哪：`literature/novelty-c4-check.md`、`experiments/protocol.md`、`experiments/prereg.md`；HF 数据卡与 first-rows API 的真实响应支持字段边界。
- 关键判断：c4 未发现占位但仍为 unknown；数据卡未声明 session/batch，因此协议禁止用 episode_index 冒充批次，并冻结 task-only fallback。
- 下一个最小同类改进：smoke 只用两任务验证同缓存两次同数、正控和置换负控，30–40 分钟内可判断尺子是否可用。
- 可复用路径：新颖性查询表 + schema 证据 + 明确退化标签 + 三臂预注册，适合其他基准审计，暂不回写模板。
- 本阶段没有科学结果；没有启动长实验，也没有需要替代方向的失败证据。

# smoke 阶段复盘（2026-11-09 夜）

- 做对了什么：断点续跑链一步到位（fast_download→verify_files→smoke_extract→probe×3→aggregate）在 40 分钟预算内跑完并判门；degraded 计数当警报用，抓出特征错位 bug 后重提取而不是带着脏缓存探针。
- 证据在哪：results/smoke_summary.json（四门全过）、experiments/scripts/size_verification.json（18/18 Content-Range 核验）、experiments/cache/_buggy_encoder_index/（bug 产物隔离）、experiments/scripts/extract_log.txt 前后两次 degraded 124→0。
- 关键判断：看到 degraded=124/95「全部 episode」没有当成日志噪声，回读 encode_all 索引映射才发现 X 行是帧而 keys 是 episode——「异常计数=边界信号」这次直接拦住了假特征；同样地 6 文件「差尾部 3-50KB」不像网络故障更像判据问题，用 Content-Range 权威字节数一次证伪。
- 失败归类（本单元内部，未影响结果）：实现层三处 bug（AUC 分数类型、帧索引映射、mib 舍入）+ 匹配器假阳性一处，全部在产生任何科学数字之前修掉；负控点估计 0.5569 略高是小测试集噪声，不是流程伪影（在 null 带内）。
- 下一个最小同类改进：pilot 下载扩量前先跑 verify_files.py 拿 Content-Length 对账（30 秒）；特征提取脚本加「每 episode 帧数恒等断言」进 encode_all（已加 assert X.shape[0]==row_base）；pilot 评测时复核负控点估计是否随测试集增大向 0.5 收敛。
- 可复用路径：①「日志里的全量异常计数=先停后查」；②下载判据与权威字节数对账（Content-Range 而非本地估算）；③聚合脚本的输入契约要逐键核对（download_report_min.json 险些因多余键 KeyError）。适合其他基准审计/探针类实验，不回写模板。
