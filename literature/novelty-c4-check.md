# 新颖性收口检查（c4）

- 课题：审计真机基准的策略身份混淆-18c6f2b0
- 检查时间：2026-11-09 夜间 design
- 门：若发现已发表工作同时对公开真机基准语料做策略身份探针量化，或按机位/批次分层重算该基准排名，则 stop_if_not_novel；不能把检索阴性当成“无人做过”的证明。

## 查询与观察

| 查询 | 渠道 | 观察 | 判定 |
|---|---|---|---|
| policy identity probe robot benchmark confound camera stratified evaluation | OpenReview/web search | 命中 FLEET-TOOLS、视角鲁棒性和评测论文；未见对 ArmnetBench 已发布 rollout 语料做身份探针或排名重算 | 未命中占位 |
| robot benchmark policy identity images probe camera confound | Google Scholar/web search | 返回作者主页与通用机器人论文，未返回切题的基准语料身份审计工作；Scholar 页面受索引结果限制 | 覆盖有限 |
| ArmnetBench policy identity camera | web search | 命中 ArmnetBench 本体（2607.24481）、Rollout then Recycle（2611.03168）及 HF 数据卡；未见后续身份审计论文 | 未命中占位 |
| 2611.03168 | web search/arXiv | 被审计论文本身，明确说 policy identity may be inferable from images alone，但没有量化、分层重评或 Kendall 判据 | 被审计对象，不占位 |
| robot benchmark camera confound stratified reevaluation policy identity | web search | 命中 ManipArena、RoboChallenge、相机视角捷径/稳健性工作；对象是受控评测或策略训练，不是该公开语料的身份审计 | 近邻但不占位 |
| citation/follow-up of 2611.03168 | OpenAlex（前序证据） | cited_by_count=0；HF LamportRobotics 的 *-audited 是遥操演示质量审计，不是 rollout 身份混淆 | 不占位 |

## 覆盖边界

本阶段补做了定向 Google Scholar 与 OpenReview/web 组合检索，并记录了真实返回结果；Scholar 不能保证完整遍历，OpenReview 搜索返回的是相关机器人工作而非本课题占位。前序 arXiv/OpenAlex/HF 证据已见 `literature/related-work.md` 与 `admission.json`。因此 c4 仍为 `unknown`，不是 supported；未发现触发 stop_if_not_novel 的命中。

## 结论

- `stop_if_not_novel`：未触发。
- 新颖性状态：`unknown`（在已覆盖范围内未命中；不宣称无人做过）。
- 允许继续：批次轴退化方案、协议冻结与 smoke；若后续出现同一语料的身份探针量化或分层排名论文，立即复查并停止。

## 直接来源

- https://arxiv.org/html/2611.03168
- https://arxiv.org/html/2607.24481
- https://openreview.net/
- https://scholar.google.com/
- https://openalex.org/W7225193298
- https://huggingface.co/datasets/LamportRobotics/armnetbench_block_stack-audited
