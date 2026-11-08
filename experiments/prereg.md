# 预注册：身份混淆探针与三臂排名重评

- 项目：审计真机基准的策略身份混淆-18c6f2b0
- 版本：design v1；冻结时间：2026-11-09 夜间 design；结果出现后不得改门线、seed、任务选择规则或缺失处理。
- 公开对象：ArmnetBench v0.1，HF 两个 LeRobot v3 仓库，8 single-arm + 4 bimanual tasks，7 policy rollout；teleoperation 排除。

## 研究问题

一句话：从画面能否在留出 episode 上识别策略身份，以及控制采集批次/任务组成和长度后，原始策略排名是否稳定？

## 预测

1. 主探针留出宏平均 AUC > 0.55。
2. 至少一个任务的原始 C 排名与 A 分层排名 Kendall tau-b < 1，或出现至少一对方向翻转；这只是待测对象，不把翻转当作先验事实。
3. 正控任务探针 AUC ≥ 0.90；策略标签置换负控 AUC 接近 0.5，且不超过由实际测试样本量报告的 95% null 带上界。

## 主要判据与决策

- `AUC ≤ 0.55`：身份混淆量化臂空转；不加种子/容量救援，改以长度泄漏审计或收口，下一步为 `redesign`。
- 负控明显偏离 0.5，或正控 <0.90：尺子无效，`redesign`；不解释主探针。
- 批次字段不可恢复：不停止项目；A 臂使用 task-only fallback，并在所有报告标注 `batch_axis=unavailable_task_fallback`，重估“批次校正”功效，不将结果写成采集批次因果校正。
- 某任务可比策略 <3：只报 `insufficient_comparison`，不触发排名不稳定。
- 达到可比门槛且 tau-b<1 或存在逐对翻转：该任务判为“原始排名不稳定”；否则判为“未观察到翻转”，不宣称无混淆。
- 新颖性若出现已发表的同语料身份探针量化或按机位/批次排名重算：`stop_if_not_novel`，停止实验并保留证据。

## 三臂和数据处理冻结

- A：冻结 DINOv2-small，逐 episode 均值池化 8 个均匀帧；逻辑回归 multinomial/L2/C=1.0/class_weight=balanced；80/20 task×policy 分层 episode split，seed 20261109；按可用 session 分层，缺失则 task-only fallback。
- B：每 task 以 rollout episode length 的中位数统一截断，成功/失败同规则；缺长度则 unavailable。
- C：原始 episode success rate 排名。
- 每格至少 n=10 才进入 A 层；并列用固定策略顺序破平。bootstrap B=2000，seed 20261111，报 95% percentile CI。
- 两次独立计算必须同数（浮点差≤1e-12）；所有缺失、退化、替换写入结果表。

## 最小实验与选择

Smoke：同一输入主探针重算两次 + 正控 + 置换负控；不根据结果挑任务。Pilot 固定 `cable_clip`（single-arm）和 `fold_tea_towel`（bimanual），若缺失只按 README 任务表字典序替换并记录。Pilot 完成后再决定是否进入 12 任务全量，禁止预先承诺补跑。

## 决策价值三行

1. 这条 run 出来后我会因为哪个数字改哪个决定：若主 AUC≤0.55 或负控/正控失败，就改设计或停止身份探针臂；若 AUC>0.55 且排名触发不稳定判据，就放行全量三臂并把“不稳定任务”列为基准审计结论。
2. `stop_if`：发现同一公开真机语料已有身份探针量化/机位或批次分层排名重算；或尺子负控偏离、正控失败且协议无法修复；项目级停止只按预注册证据执行，不因一次零翻转停止。
3. 预期信息量 ÷ GPU·小时：Smoke 只需冻结特征缓存上的线性探针和两个控，能一次判定“尺子是否可用”与批次字段是否真实存在，避免先做 12 任务长特征提取；若门通过，pilot 的 2×7 结果直接区分“身份信号存在/不存在”和“排名轴是否有可比性”，信息量高于盲跑全量。

## 结果登记模板

执行器不得把本文件中的预测填成结果。真实结果必须另存 `results/`，包含：`schema_snapshot.json`、`config.json`、`probe_metrics.json`、`confusion_matrix.csv`、`ranking_A.csv`、`ranking_B.csv`、`ranking_C.csv`、`pairwise_flips.csv`、环境版本、数据 revision、复现命令和 `README`。
