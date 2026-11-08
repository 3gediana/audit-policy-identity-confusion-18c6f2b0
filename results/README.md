# results/ — pilot 三臂排名重评 + smoke 尺子信度检查

判门结论：pilot verdict = supported（五门全过，见 pilot_summary.json）。身份信号在 570 eps 全量坐实
（AUC 0.877），负控随测试集增大向 0.5 收敛（0.5569→0.4811，dev 0.057→0.019），排名三臂产出齐全。

## pilot 文件（2 任务×7 策略，全量 rollout episodes：cable_clip 270 + fold_tea_towel 300）

- ranking_C.csv —— C 臂原始池化排名：每 task×policy 的 n/成功数/成功率/排名/bootstrap 95% CI
- ranking_B.csv —— B 臂长度中位数截断池化重评：L50 截断（cable_clip 905.0 帧 / fold_tea_towel 740.5 帧），
  截断窗内成功=（success==1 且 length≤L50）；含 *_episode_label_audit 列（标签不改口径的审计对照）
- ranking_A.csv —— A 臂探针驱动分层重评：task-only fallback 层（batch_axis=unavailable_task_fallback），
  每格 n≥10 门槛判定 + 层内/跨层加权聚合率
- cell_gates.csv —— 每格门槛判定（14/14 格 n≥10 过关，两层均 valid）
- pairwise_flips.csv —— 逐对翻转清单（C_vs_A / C_vs_B / C_vs_B_frozen_labels_audit，含严格方向反转列）
- kendall_tau.csv —— 每 task×对比 Kendall tau-b（含 scipy 交叉核对）+ 翻转率 + 判定 + caveat
- probe_metrics.json —— 探针三次独立运行指标（主 AUC/per-class/正控/负控/null 带/收敛检查/门判定）
- pilot_probe_run_A/B/C.json —— 三次独立探针完整输出（同数：AUC 极差 0.0，指纹 e3c7c892299d25e3）
- pilot_summary.json —— pilot 判门汇总（预测对照、臂判定、长度泄漏审计、成本、verdict）
- pilot_episodes_all.csv —— 570 条 episode 全量元数据（含 success_horizon/truncated 派生列）
- degradation_missing.csv / degradations.json —— 缺失表（无缺失格）+ 退化/实现实例化报告
- confusion_matrix.csv —— 测试集 7 类混淆矩阵（pilot run A，三次同数）
- ranking_reproducibility.json —— 三臂计算双跑同指纹（a780d88eed247ebc）
- README.md —— 本文件

## pilot 关键数字（2026-11-09 夜，RTX 5060 Laptop 8G）

- 主探针（标签=policy_type，7 类，570 eps，train 456/test 114）：留出宏 OVR AUC = 0.8773，
  bootstrap 95% CI [0.8361, 0.9148]（B=2000），3 次独立运行 bitwise 同数
- per-class AUC：act 0.953 / diffusion 0.929 / smolvla 0.918 / grootn1.7 0.882 / molmoact2 0.876 /
  pi0.5 0.799 / pi0 0.783
- 正控（标签=task）：AUC = 1.0；测试集准确率 65/114 = 57.0%（7 类随机 14.3%）
- 负控收敛复核（预测项）：测试集 44→114，负控点估计 0.5569→0.4811，|dev-0.5| 0.0569→0.0189（收窄），
  null 带 [0.249,0.751]→[0.337,0.663]（收窄），点估计落在自身带内 —— 向 0.5 收敛成立
- 三臂排名（fold_tea_towel，n=300，7 策略）：
  - C vs B（长度中位数截断）：tau-b = 0.95，1/21 对翻转（diffusion↔pi0，C 中 0.50 平局靠固定序破平，
    截断后 pi0 0.50 > diffusion 0.467）；严格方向反转 0 对 → 判定 ranking_unstable（tau<1 触发），
    但注意：翻转发生在统计上不可分的平局对（bootstrap CI 大幅重叠），属并列破平敏感性
  - C vs A（task-only fallback 分层）：tau-b = 1.0，0 翻转 —— 结构恒等（fallback 层=任务，
    同 episode 同标签），该对比在 pilot 无检出力，「未观察到翻转」不作稳定性证据
  - C vs B（frozen-labels 审计口径）：tau-b = 1.0（按构造恒等，仅审计用）
- cable_clip（n=270）：全部 7 策略 success=0（success_class 全为 failure）——三臂零判别力，
  排名为纯固定序破平，tau-b 未定义 → 三对比均判 insufficient_comparison（基准数据性质，非 bug）
- 长度泄漏量化（fold_tea_towel）：成功 episode 平均 589 帧 vs 失败 830 帧（中位 566 vs 871），
  corr(success, length) = -0.524 —— 作者 §5 所述「失败跑到操作员叫停、长度泄漏标签」在 episode 级坐实
- 成本：下载 5.75GiB/38 文件 732s（fast_download_pilot.py 6 并发），verify 56/56 Content-Range 全过，
  提取 570 eps 288.5s（degraded=0），探针单次 ~4s（bootstrap 主导）

## B 臂口径实例化（重要，protocol.md §4 的实现对照）

protocol §4 写「成功标签仍使用 episode label」且「成功/失败均按同一规则，不能只截失败」。实现取：
成功真值仍来自 episode 标签（不重看视频重判）；因 2611.03168 §5 明确 successful rollout 在完成时被裁剪
（成功发生在 episode 末端），共同截断窗内的成功 = (success==1) 且 (length≤L50)。此谓「截断影响 B 的输入」。
若采「标签与入组都不变」的另一读法，B 与 C 按构造恒等（对比行 C_vs_B_frozen_labels_audit 即该读法，
tau≡1）——两种读法的数字都在盘上，主口径取截断窗重评（否则 B 臂无估计量、「重评」落空）。
无 success 时点字段，长度缺失则 B 标 unavailable 不估算（本次无缺失）。

## smoke 文件（尺子信度检查，219 eps 子集）——保留存档

- smoke_summary.json / smoke_probe_run_A/B/C.json / smoke_config.json / smoke_cost.json /
  schema_snapshot.json / smoke_episodes.csv —— 数字见 git 历史 smoke 段与各 json
- smoke 判门：主 AUC 0.8896、正控 1.0、负控 0.5569∈null 带、3 次同数（verdict=supported）

## 如实注记（pilot）

- C_vs_A 的结构性恒等已实测（max|rate_A-rate_C|=0）：批次轴不可恢复时 A 臂无法产生重加权，
  排名稳定性的分层检验在 pilot 是「不可测」而非「测了没翻」；全量 12 任务前需要 session 字段
  或接受该臂空转（prereg 退化出口 #2）。
- fold_tea_towel 的 C_vs_B 翻转是平局对破平变化（0 个严格方向反转），报告按预注册判定记
  ranking_unstable，但解读必须带平局敏感性限定，不夸大成「名次互换」。
- cable_clip 全员 0 成功使该任务三臂全平局；它仍是身份探针的有效样本（270 eps 全部进探针）。

## 复现（pilot 全链）

    cd <课题目录>
    G:/ai/python11/python.exe experiments/scripts/prep_download_pilot.py   # 缺文件清单+权威字节数
    G:/ai/python11/python.exe experiments/scripts/fast_download_pilot.py   # 断点续传（幂等）
    G:/ai/python11/python.exe experiments/scripts/verify_pilot.py          # Content-Range 尺寸核验 56/56
    G:/ai/python11/python.exe experiments/scripts/pilot_extract.py         # 570 eps 特征
    G:/ai/python11/python.exe experiments/scripts/pilot_probe.py A         # 三次独立 A/B/C
    G:/ai/python11/python.exe experiments/scripts/pilot_probe.py B
    G:/ai/python11/python.exe experiments/scripts/pilot_probe.py C
    G:/ai/python11/python.exe experiments/scripts/pilot_ranking.py         # 三臂排名（内建双跑同指纹）
    G:/ai/python11/python.exe experiments/scripts/aggregate_pilot.py       # 判门，重写 probe_metrics 等

数据：armnet/armnetbench_v01_lerobot_so101 (rev 1db69c82) +
armnet/armnetbench_v01_lerobot_bimanual_so101 (rev c4841758)，56 个视频文件/8.55GiB/570 eps。
编码器 facebook/dinov2-small rev=ed25f3a31f01632728cabb09d1542f84ab7b0056。
种子：split 20261109 / perm 20261110 / boot 20261111 (B=2000)；门线见 prereg.md（零改动）。
环境：python 3.11.9 / torch 2.10.0+cu128 / sklearn 1.8.0 / transformers 4.57.6 / av 16.1.0。
