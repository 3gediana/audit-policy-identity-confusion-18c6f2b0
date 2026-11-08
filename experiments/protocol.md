# 实验协议：身份盲分层重评（冻结版 design v1）

## 0. 目的、输入与不可改变项

问题：公开 ArmnetBench v0.1 的图像是否携带 `policy_repo_id` 身份信号；去除/控制采集批次与长度后，策略成功率排名是否改变。

输入只用两个 LeRobot v3 仓库：
- `armnet/armnetbench_v01_lerobot_so101`（8 single-arm tasks，2,499 episodes）
- `armnet/armnetbench_v01_lerobot_bimanual_so101`（4 bimanual tasks，1,219 episodes）

只纳入 `policy_repo_id` 非空的 7 个策略 rollout；teleoperated 行不进入身份探针或策略排名。episode 是分析单位，不把帧拆成独立样本。

## 1. 批次/会话轴核验与退化口径

设计核验：HF 数据卡明确 episode-level 字段含 `policy_repo_id`、`policy_type`、`success`、`success_class`；per-frame parquet 有 `next.done`，episode 元数据在 `meta/episodes/*.parquet`。数据卡没有声明可直接恢复的采集 session/batch 列，也没有提供可用的 session 字段名。因此当前冻结判断为：

- 主轴候选：`collection_session`/采集批次（只有在实际 parquet schema 找到非空、跨 episode 稳定且不等同 `episode_index` 的字段时启用）。
- 本阶段可复核的最小字段：`episode_index`、`task`、`policy_repo_id`、`policy_type`、`success`、`success_class`、数据仓库/embodiment；这些不是批次代理，不能冒充 session。
- 若 smoke 前仍无可恢复批次字段：按任务分层作为预注册退化轴，不按（任务×机位单元）声称；由于每任务固定 cell，任务×cell 会退化成任务。退化必须在结果表写 `batch_axis=unavailable_task_fallback`，并把 A 臂解释为“控制任务组成后的重评”，不宣称已控制采集批次。
- 禁止用 `episode_index` 伪造批次；禁止按策略或结果标签构造层。

## 2. 探针 A：身份可分性

### 特征
冻结 `facebook/dinov2-small`（固定 revision，运行时记录完整 commit hash）。每个 episode 从可用视频视图按统一规则抽帧：均匀取 8 帧，包含首帧但不特意取末帧；每帧 resize shortest-side=224、center crop 224×224、RGB、ImageNet mean/std；默认只用 `front`（single-arm）或 `top`（bimanual 的固定公共视图）。若该视图缺失，按同一仓库预注册的主视图替换规则并记录，不临时挑视图。

编码器 eval、无梯度、无增强；取 CLS token，逐 episode 对 8 个向量求均值，再 L2 normalize 一次。特征缓存以数据仓库 revision、视频字段、帧索引、编码器 revision、预处理版本作键。

### 标签、划分与模型
标签为 `policy_repo_id`，7 类。按 episode 做 80/20 stratified split，随机种子 `20261109`；分层键至少为 task×policy，若某 task×policy 测试格不足 1 条则该任务标记 probe_missing，不借用其他任务填补。训练集与测试集 episode 不重叠。

逻辑回归 multinomial、L2、`C=1.0`、`solver=lbfgs`、`max_iter=2000`、`class_weight=balanced`；只在训练集拟合。指标为测试集 one-vs-rest ROC-AUC 的 7 类 macro average（缺失类按任务级缺失规则标记，不填 0.5），并报告逐类 AUC、混淆矩阵、n。

主门线：宏平均留出 AUC `>0.55` 为身份信号通过；`≤0.55` 为混淆量化臂空转，转入长度泄漏审计/收口，不 rescue 式追加种子。

## 3. 正控、负控与重复计算

正控：同一特征管线、同一任务，标签改为 `task`，按 episode split；仅用于证明视觉特征/流程能读出任务，预期 AUC `≥0.90`，结果不作身份混淆证据。

负控：保留特征与 split，使用独立确定性置换 `policy_repo_id`（seed=`20261110`，只置换标签，不重排特征）；预期 macro AUC 在预先写明的有限样本噪声带内接近 0.5。若负控明显高于 0.5，尺子不可用，回炉 design。

同一缓存、同一 split、同一 sklearn 版本下独立执行两次；两次宏 AUC 必须 bitwise 相同（或浮点差≤1e-12），否则 protocol 不满足“算两次同数”，不得进 pilot。主结果额外用 bootstrap episode 重采样给 95% percentile CI，bootstrap seed=`20261111`、B=2000。

## 4. 三臂重评

成功定义：`success == 1`；每个 task×policy 报 n、成功数和成功率。

- C 原始池化排名：任务内各策略 success rate 降序；并列按预注册固定次序 `act, diffusion, smolvla, pi0, pi0.5, grootn1.7, molmoact2`，不得按结果临时破平。
- B 长度截断匹配：每个 task 内以 rollout episode 长度的 50th percentile 为共同截断长度；长度不足者保留全长，长度超过者截到该长度；成功/失败均按同一规则，不能只截失败。截断只影响 B 的输入/可比性分析，成功标签仍使用 episode label。长度字段取 `meta/episodes` 的 episode frame count；缺失则 B 标记 unavailable，不估算。
- A 探针驱动分层：使用探针 AUC 只作审计触发与报告，不把预测标签当成功率；在可用 `task×collection_session` 层内计算各策略成功率，层内仅保留策略数≥2且每个参与策略 n≥10 的层。按层 episode 数加权聚合策略成功率；不满足门槛的层退出并列入缺失表。批次不可恢复时采用上节 task-only fallback，A 与 C 的差异解释为层内/任务内重加权，而非批次校正。

每个 task 对 C vs A、C vs B 报：策略排名、Kendall tau-b（仅完整参与策略；7 策略不足时 n_strategies）、逐对翻转数/总可比对数、翻转率、各策略 bootstrap 95% CI。`tau<1` 或至少一对方向翻转，只在该 task 达到最小可比策略数（≥3）时触发“排名不稳定”；否则 `insufficient_comparison`。

## 5. Pilot 与选择规则

Pilot 固定为 2 个任务：single-arm 的 `cable_clip`（作者点名的前视相机错位相关任务）与 bimanual 的 `fold_tea_towel`（覆盖 right_wrist 风险）。若任一任务不在下载快照，按仓库 README 中任务表的字典序下一个任务替换，并记录替换理由；不得按 AUC 或翻转结果挑任务。

Smoke 先只验证正/负控与重复计算，不提前看结果选择 pilot。Pilot 必须覆盖 2 任务×7 策略，输出 AUC、混淆矩阵、三臂排名和门槛缺失表。

## 6. 完成与失败条件

完成：协议中每个数量有字段、算法、seed、缺失处理和输出路径；同一输入算两次一致；正控≥0.90、负控接近0.5；三臂对所有任务有可审计行。

失败：任何口径无法重算同数；负控暴露流程伪影；批次字段被伪造/误当作可用；数据缺失未显式标记。失败回炉 design，不改门线、不挑种子。

## 7. 复现与输出

执行器必须保存：数据 revision、schema 摘要、环境版本、配置 JSON、逐 episode 特征索引、probe_metrics.json、confusion_matrix.csv、ranking_{A,B,C}.csv、pairwise_flips.csv、缺失/退化报告与命令。协议本身不构成科学结果；真实 AUC/τ 只能来自 results/。
