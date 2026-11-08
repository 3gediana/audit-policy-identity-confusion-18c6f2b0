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

# pilot 阶段复盘（2026-11-09 夜）

- 做对了什么：①排名三臂只依赖元数据，先离线算完落盘（ranking_*、kendall_tau、cell_gates），把下载不确定性从关键路径上摘掉——下载 12 分钟里产出已定；②下载前置权威字节数（prep_download_pilot.py 预取 Content-Range）使 38/38 一次下完、零 416 假缺口；③协议歧义（B 臂估计量）不猜不漂，双口径都算、审计列留盘，把裁量权留给 researcher。
- 证据在哪：results/ranking_reproducibility.json（双跑同指纹）、experiments/scripts/size_verification_pilot.json（56/56）、results/degradations.json（实例化与退化显式登记）、results/kendall_tau.csv caveat 列。
- 关键判断：cable_clip success 全 0 先诊断（diag_labels.py）再定判定桶（insufficient_comparison），没有把它当 bug 乱修标签，也没有硬报「未观察到翻转」；fold_tea_towel 的翻转对在 C 是平局，按预注册记 ranking_unstable 但把「0 个严格方向反转」同表报出，防夸大。
- 失败/受限归类（不影响本阶段结论）：①A 臂在 task-only fallback 下零检出力（结构性，非实现问题）——排名稳定性的分层检验需要 session/batch 字段，否则全量 12 任务也只是重复恒等；②驱动器 482s 等待上限与长时单元矛盾，造出假 partial——时序注记已写 STATUS，防重复派活。
- ≥3 条替代方向（若 researcher 不认可 B 臂实例化或需更强排名结论）：①改用 frozen-labels 口径（30 分钟：ranking_B 里 *_episode_label_audit 列已是现成数字，直接换判定列重跑 aggregate；失败条件=同样结构恒等无翻转）；②找/推断 success 时点做真截断重判（30 分钟：查 frames parquet 的 next.done/终止帧分布验证「成功在末端」假设；失败条件=无时点信号且假设被证伪，则 B 标 unavailable）；③A 臂换可恢复的层（30 分钟：再 census 一次 meta/episodes 及 videos 时间戳分布，看 chunk/file_index 之外是否有跨 episode 稳定的采集序列信号；失败条件=仍无合法层轴，A 臂在全量阶段按退化出口 #2 收口）。
- 下一个最小同类改进：探针扩量复核写成独立小脚本（neg_control_convergence 现在内嵌在 pilot_probe.py），并把「任务级标签退化检测」（全平局任务）加进 cell_gates 前置断言，30 秒可判。
- 可复用路径：①「元数据臂先落盘、下载臂后接」的双轨推进；②协议歧义双口径并算留审计列；③下载前置权威字节数。适合其他基准审计三臂类实验，暂不回写模板。

# pilot 复盘补记（验证单元，2026-11-09 夜）

- 可复用路径（撞车协调）：同阶段出现「在跑 detached 进程 + 新派发单元」双进程时，先用 mtime/ps/_state 事件日志给产物归属（谁在写什么、何时起），再定角色分工：执行位跑管线、验证位做独立重算+字节复现，绝不并行双跑同一管线写同一缓存。验证位的复现检查顺手满足协议「算两次同数」的外部独立复核，比自证更硬。
- 下一个最小同类改进：驱动器侧对 error_kind=still-running 的 partial 阶段加「detached 进程存活期内禁止再派发」互斥（派发前探 _detached_pid 在不在 tasklist），30 分钟可验；这是投影层重放 bug 之外的独立双派发源。
- 失败归类：调度层双派发（非科学失败、零数据损失、零重复计算）。现场证据：night-active-unit.json 先后两个 run 指向同一 stage；WINPID 16472 自 05:26:39 存活至 05:59；05:36-05:41 两套写盘痕迹（前身写脚本/结果，后继只写独立验证脚本于 scratch）。本阶段科学结论不受影响（全部经独立复算与字节复现验证）。
