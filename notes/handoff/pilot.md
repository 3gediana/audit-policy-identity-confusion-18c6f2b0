---
stage: pilot
kind: experiment
status: ok
did: pilot 三臂排名重评全部跑完并双重验证：570 eps 三臂排名/翻转/tau/门槛 + 扩量探针三跑负控收敛复核落 results/，第二单元独立重算逐格一致、字节复现通过。
why: 检验策略排名在长度截断重评下稳不稳、身份信号扩量后是否复现、负控是否随测试集向 0.5 收敛，为 12 任务全量 experiment 放行提供判据。
how: 按 protocol §4 冻结口径实现 C/B/A 三臂（B 截断窗成功=success==1∧length≤L50，frozen-labels 读法留审计列）；verify 56/56 Content-Range 后才提取；三臂双跑同指纹、探针 3 次同数；验证单元再独立重算 14 格对账 + 重跑 ranking/probe 做字节对比，全部一致才算数。
result: verdict=supported 五门全过：AUC 0.8773×3（CI [0.836,0.915]），负控 0.5569→0.4811 向 0.5 收敛且带宽收窄；fold_tea_towel C_vs_B tau-b=0.95、1 平局对翻转（0 严格反转）判 ranking_unstable；C_vs_A 结构恒等（fallback 无重加权）不作稳定证据；cable_clip 全员 success=0 全平局判 insufficient_comparison。
next: researcher 判读 pilot 回执（B 臂口径裁决、平局级翻转解读、A 臂空转是否按退化出口接受），通过后派 experiment（12 任务全量三臂，>40min 部分 detach supervisor）。
artifacts: [results/ranking_A.csv, results/ranking_B.csv, results/ranking_C.csv, results/pairwise_flips.csv, results/kendall_tau.csv, results/cell_gates.csv, results/probe_metrics.json, results/pilot_summary.json, results/pilot_episodes_all.csv, results/degradations.json, results/confusion_matrix.csv, results/ranking_reproducibility.json, results/executor_verification.json, results/README.md]
info_need: 无
---
时序注记：本阶段由两个单元接力完成且未撞车——前身 detached 进程（482s 等待上限截断后未死）执行全部管线；驱动器 05:39:48 又派发的第二单元按「不重复开跑」让位，改做独立验证（meta 重算 14 格对账、重跑 ranking 10 文件字节一致、重跑 probe A 科学字段逐位一致，见 results/executor_verification.json）并打包本交接。勿再派续跑单元；同阶段双派发为调度层新 bug 源（与投影层重放同族），已记 RETRO/DECISIONS 供晨会。
