---
stage: design
kind: design
status: ok
did: 完成新颖性收口、HF 字段核验，并冻结探针、分层退化、三臂和预注册协议。
why: 把身份混淆问题压成可证伪、可复算且能区分排名是否稳定的最小实验。
how: 定向 Scholar/OpenReview/web 检索；核对 HF 数据卡与 first-rows API；为 AUC、控实验、tau、翻转、缺失和重复计算写死规则。
result: 尚无论证性结果；c4 未发现占位但仍为 unknown；公开 schema 未声明 session/batch，已冻结 task-only fallback。
next: researcher 判读后执行 smoke：两次同缓存探针、正控≥0.90、置换负控接近0.5；通过再跑预注册 pilot。
artifacts: [literature/novelty-c4-check.md, experiments/protocol.md, experiments/prereg.md, admission.json, brief.md, notes/DECISIONS.md, notes/RETRO.md, STATUS.md]
info_need: 无
plain_summary: 这个项目检查机器人基准的录像是否带有能识别策略身份的相机或采集痕迹。我们用冻结视觉特征的线性探针量化这种泄漏，再比较原始排名与分层、长度匹配后的排名是否改变。
why_it_matters: 立项依据是 2611.03168 第5节作者承认身份可能从图像推断、长度会泄漏标签，但没有量化或重算排名；本项目填补真实公开基准审计的具体测量缺口。
question: 画面中的策略身份信号有多强，控制采集轴和长度后原始策略排名是否仍稳定？
---
