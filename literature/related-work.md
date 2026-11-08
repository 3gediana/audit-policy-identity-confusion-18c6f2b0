# 相关工作筛查（screening）— 审计真机基准的策略身份混淆

- 日期：2026-11-09（夜窗 screening 单元）
- 课题：审计真机基准（ArmnetBench v0.1，arXiv:2611.03168）里『从画面认出策略身份』的混淆量化与分层重评协议
- 结论：decision=admitted（admission.json 已过 research-topic-admission/v1 门）；新颖性主张 c4 仍标 unknown（见未知项）

## 1. 检索记录（search_log，全部 2026-11-09 夜）

| # | 查询 | 渠道 | 时间 | 结果 |
|---|---|---|---|---|
| 1 | robot manipulation benchmark "policy identity"/"spurious cues" camera viewpoint linear probe confound | web_search | 00:05 | 命中 2508.06426、2609.37165 两条训练侧近邻；无语料审计工作 |
| 2 | "2611.03168" OR "ArmnetBench" rollout recycle | web_search | 00:06 | 原文 HTML、雷达目录、无跟进论文 |
| 3 | arXiv API all:"ArmnetBench" | arxiv_api | 00:07 | 仅 2607.24481（本体）+ 2611.03168 |
| 4 | arXiv API all:"policy identity" AND all:"robot" | arxiv_api | 00:07 | 零切题命中（1 条无关 INR 个体行为） |
| 5 | arXiv API all:"benchmark" AND all:"spurious" AND all:"camera" AND all:"manipulation" | arxiv_api | 00:07 | AnyWorld / RoboMonitor，均非语料混淆审计 |
| 6 | OpenAlex search（被引核验） | openalex_api | 00:12 | 2611.03168 = W7225193298，cited_by_count=0 |
| 7 | HF LamportRobotics org + armnetbench_block_stack-audited 卡 | huggingface_page | 00:10 | 12 个审计数据集在位且活跃更新 |
| 8 | arXiv HTML 2611.03168v1 全文引语提取 | arxiv_html | 00:09 | §3/§5 逐字 quote 到手 |

另：Semantic Scholar API 两次 429（限流），S2 口径未核验，标 unknown。

## 2. 被审计对象与原文定位（核验范围：全文）

Rollout then Recycle（arXiv:2611.03168v1，2026-11-02，CoRL 2026 Oops-I-Erred workshop，4 页）。
前序单元 2026-11-07 已全文精读（PDF 落 G 盘，图谱 paper node-0d0846f8）；本轮取 HTML 版复核关键段落，逐字引语：

- §5 Collection protocol（身份混淆，本课题第一臂的靶子）：
  "Two camera problems affected every policy except MolmoAct 2 [1]: the front camera on the cable and eye-drops cell was misaligned and the bimanual right_wrist view was slightly blurry. Policy identity may therefore be inferable from the images alone."
- §5 Labels and episode ends（长度泄漏，第二臂对照的靶子）：
  "Because successful and suboptimal rollouts were trimmed at completion while failures ran until the operator stopped them, episode length and trailing idle motion leak the label; models should be trained on length-matched or clipped inputs. For the same reason, next.done on a failure marks an operator stop rather than a terminal state, which matters for offline RL."
- §3 Labels（标签近二值）："724 successful (23.2%), 106 suboptimal (3.4%) and 2,288 failure (73.4%)"
- §3 Source 表（逐策略成功率差异大）：π0.5 171/359 (47.6%) … SmolVLA 63/480 (13.1%)
- §5 Collection protocol（嵌套结构，分层轴设计约束）："All data come from three cells in one room with one cell per task and ambient lighting."

作者只给警告与一句话建议，无任何量化（无可分性度量、无分层重评、无排名稳定性判据）。

## 3. 最近邻与差异（closest_work 对照）

1. **Rollout then Recycle（2611.03168）** — 被审计对象本身。警告级自认，零量化。本课题把它承认可推断的三条缺陷变成测量与判据。
2. **Shortcut Learning in Generalist Robot Policies（2508.06426，CoRL 2025）** — 原文："The camera viewpoint serves as the primary task-irrelevant factor (v)……we construct a training dataset……to create a strong spurious correlation between the task-irrelevant viewpoint and the task-relevant position." 审的是策略训练侧视角捷径（受控构造+策略泛化），不是已发布语料的身份泄漏审计，不重算基准排名。
3. **DILL（2609.37165）** — 原文："This diagnostic intentionally creates a spurious correlation between task identity and camera viewpoint during training, then breaks this correlation at test time……" 同为训练侧缓解方法+自建受控诊断集；不做真实基准语料审计。
4. **LamportRobotics \*-audited 数据集家族（HF，12 个）** — 数据集卡原文："The teleoperated demonstrations of [villekuosmanen/armnetbench_block_stack] after an episode-level audit……49 of 50 episodes are kept; 1 were removed and 2 carry a flag." 本基准家族唯一第三方审计动作，但对象是遥操演示子集质量，不碰 v01 rollout 身份混淆、不探针量化、不重算排名。该 lab 2026-11-07 起上传、5 小时前仍在更新，跟进簇活跃——需跟踪其后续动作是否升级到 rollout 语料。

引文追踪：
- backward：2611.03168 的 12 条引文全为方法/数据论文（ArmnetBench 本体、OXE、DROID、LeRobot、7 个策略、Robometer），无审计/评测有效性前作可套用。
- forward：OpenAlex cited_by_count=0（2026-11-09）；S2 429 未核验；非引文型跟进=Lamport 审计数据集（见上）。

## 4. 判读

- 混淆量化 + 分层重评 + 排名稳定性判据的闭环在检索范围内无人做；c4（无人做过）按纪律标 unknown，不拿检索负结果当证明。
- 新发现的设计约束（本轮增量）：机位缺陷按"单元×采集批次"分布（除 MolmoAct 2 外全受影响）且每任务固定单元 → 分层轴应是（任务×采集会话），不是 brief 里写的（任务×机位单元）；批次信息能否从 parquet 元数据恢复待 design 阶段核验。
- MiTA 式统一理论视角：评估为可选启发、不套用——本课题交付测量与判据，不构建统一解释框架。
- user fit：taste.md 2026-11-05 方向（视觉×RL、网络怎样理解图像）直接对口；审计型小仓库符合小口子/能放 GitHub 口径；模型/免费额度未作兴趣依据。

## 5. 未知项（uncertainties）

1. 新颖性只覆盖 4 渠道 8 查询式；Google Scholar/OpenReview 全组合遍历未做。
2. 机位缺陷逐 episode 批次归属未核验；若 parquet 无批次/时间戳信息，分层退化为按任务分层，判据臂功效需重估。
3. 240p 腕相机画质下冻结特征可分性上限无先验数；探针 AUC 无预注册预期值。
4. 排名是否翻转取决于层内样本量（部分格仅 29 条 rollout），功效预估未做。
5. S2 前向引文口径 429 未核验。

## 6. 下一步（不阻塞本单元）

- 准入后进 design：①探针 pilot（2 任务 × 7 策略，留出 AUC + 混淆矩阵，8G 卡 30 分钟）；②读 parquet 元数据定批次分层轴；③长度截断匹配对照臂。
- 跟踪 LamportRobotics 后续上传（若出现 rollout 语料审计即触发 stop_if_not_novel 复查）。
