---
stage: pilot
kind: experiment
status: ok
did: 跑完 pilot 三臂排名重评：570 eps 全量元数据算三臂排名/翻转/tau/门槛，扩量下载 56 文件提取特征跑三遍探针复核负控收敛，全部落 results/。
why: 检验策略排名在长度截断重评下稳不稳、身份信号扩量后是否复现、负控是否随测试集向 0.5 收敛，为 12 任务全量放行提供判据。
how: 按 protocol §4 冻结口径实现 C/B/A 三臂（B 截断窗成功=success==1∧length≤L50，frozen-labels 读法留审计列）；三臂双跑同指纹、探针 3 次同数；verify 56/56 Content-Range 后才提取；每格 n≥10 门槛显式判定。
result: verdict=supported 五门全过：AUC 0.8773×3（CI [0.836,0.915]），负控 0.5569→0.4811 向 0.5 收敛且带宽收窄；fold_tea_towel C_vs_B tau-b=0.95、1 平局对翻转（0 严格反转）判 ranking_unstable；C_vs_A 结构恒等（fallback 无重加权）不作稳定证据；cable_clip 全员 success=0 全平局判 insufficient_comparison。
next: researcher 判读 pilot 回执（B 臂实例化口径裁决、平局级翻转解读、A 臂空转是否按退化出口接受），通过后派 experiment（12 任务全量三臂）。
artifacts: [results/ranking_A.csv, results/ranking_B.csv, results/ranking_C.csv, results/pairwise_flips.csv, results/kendall_tau.csv, results/cell_gates.csv, results/probe_metrics.json, results/pilot_summary.json, results/pilot_episodes_all.csv, results/degradations.json, results/confusion_matrix.csv, results/ranking_reproducibility.json, results/README.md]
info_need: 无
---
时序注记：本单元即 batch-20261109T053542 续跑契约的执行者，驱动器 482s 等待上限产生的 auto partial 交接为误判，勿再派续跑单元。B 臂口径实例化两种读法数字都在盘（主口径截断窗重评，审计列 frozen-labels），等 researcher 裁决。
