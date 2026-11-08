# 状态

- 阶段：pilot **完成（verdict=supported，五门全过）**（2026-11-09 夜 executor 长时单元，即 batch-20261109T053542 续跑契约的执行者，全部在本单元内跑完）。workflow：design→smoke→pilot→experiment→analysis，下一步=researcher 判读 pilot 回执后决定是否放行 experiment（12 任务全量）。
- 最近更新：2026-11-09T06:25:00+08:00（executor 夜间单元，pilot 三臂排名重评 + 探针扩量 + 负控收敛复核全部完成）
- 最近产物：results/（ranking_A/B/C.csv、pairwise_flips.csv、kendall_tau.csv、cell_gates.csv、probe_metrics.json、pilot_probe_run_A/B/C.json、pilot_summary.json、pilot_episodes_all.csv、degradations.json、degradation_missing.csv、confusion_matrix.csv、ranking_reproducibility.json、README.md）。
- pilot 判门（五门全过）：主探针（7 类，570 eps，train 456/test 114）宏 OVR AUC=0.8773，95% CI [0.8361,0.9148]，3 次 bitwise 同数（指纹 e3c7c892299d25e3）；正控 1.0；负控 0.4811∈null 带 [0.337,0.663]；负控收敛复核**成立**：|dev-0.5| 0.0569→0.0189、null 带收窄，随测试集 44→114 向 0.5 收敛；14/14 格 n≥10 过门槛。
- 三臂排名判定：fold_tea_towel C_vs_B（长度中位数截断，L50=740.5 帧）tau-b=0.95、1/21 对翻转（diffusion↔pi0，C 中 0.50 平局破平变化；严格方向反转 0 对）→ 判 ranking_unstable（tau<1 触发，解读带平局敏感性限定）；C_vs_A tau-b=1.0（task-only fallback 结构恒等，实测 max|Δrate|=0，无检出力，不作稳定性证据）；cable_clip 270 条 success 全为 0（7 策略全平局）→ 三对比均 insufficient_comparison（基准数据性质）。
- 长度泄漏量化（fold_tea_towel episode 级）：成功均长 589 帧 vs 失败 830 帧，corr(success,length)=-0.524，作者 §5 泄漏主张首次量化。
- 扩量下载核验：download_plan.json 全量 56 文件/8.55GiB/570 eps；fast_download_pilot.py 38 缺文件 732s 下完，verify_pilot.py Content-Range 权威字节数 **56/56 全过**（mib 假缺口防线生效）；提取 288.5s degraded=0。
- B 臂口径实例化（已记 DECISIONS，两种读法数字都在盘上）：主口径=截断窗内成功 (success==1 ∧ length≤L50)（episode 标签为真值、不重判；成功按 §5 裁剪于完成点）；frozen-labels 读法（B≡C 恒等）作为 C_vs_B_frozen_labels_audit 对照行保留。
- 时序注记：驱动器 482s 等待上限把本单元记为 partial（auto 交接单 stub 在 notes/handoff/pilot.md），但进程未死、单元持续运行直至全部完成；续跑契约①-③（存活核实→下载完→verify→扩量提取→探针→三臂）已全部履行，**勿再派续跑单元**。fb-31d8953534：本单元无 supervisor 发车（全部工作单元内完成），无自检行适用。
- 下一步：①researcher 判读 pilot 回执（重点：B 臂实例化口径是否认可、fold_tea_towel 平局翻转解读、A 臂空转是否按 prereg 退化出口 #2 接受）；②判读通过则派 experiment（12 任务全量三臂）——先算下载量/窗口，>40min 部分按 fb-31d8953534 一步到位 detach supervisor；③analysis 阶段按任务书逐一实测失效情形（240p 腕相机、单策略格、小样本格）。
- 组合层去重（2026-11-09 判读拍板）：同题姊妹 438aa6b2 已 duplicate-merged 归档，本课题为唯一推进线；保留 pivot 三条见 notes/DECISIONS.md。
- 研究员唤醒点：pilot 回执判读；持续跟踪 LamportRobotics 上传（若出现 rollout 语料审计即触发 stop_if_not_novel 复查）。
- 关键证据锚点：2611.03168 §5 逐字引语（身份可推断/长度泄漏/近二值标签）见 literature/related-work.md §2；OpenAlex 前向被引 0（W7225193298，2026-11-09）；Eval-Actions 2601.18723 旁证。smoke AUC 0.8896（219 eps）→ pilot AUC 0.8773（570 eps）：身份信号在扩量后稳定复现。
- smoke 阶段存档（verdict=supported，四门全过）：AUC 0.8896 / 正控 1.0 / 负控 0.5569∈带 / 3 次同数；4 处实现修复见 DECISIONS。
- 批次判读记录：batch-20261109T043017（smoke ok 放行 pilot）、batch-20261109T053542（pilot partial 放行 continue + 续跑契约，判读全文 _state/researcher-interventions/）。
