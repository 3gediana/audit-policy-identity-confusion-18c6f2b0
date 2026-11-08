# results/ — smoke 阶段产物（探针尺子信度+效度最小检查）

判门结论：verdict = supported（四门全过，见 smoke_summary.json）。尺子可用，放行 pilot。

## 文件

- smoke_summary.json —— 判门汇总（主探针 3 次 AUC、正控、负控、null 带、成本、verdict）
- smoke_probe_run_A/B/C.json —— 三次独立探针的完整指标（per-class AUC、bootstrap CI、混淆矩阵、指纹、环境）
- smoke_config.json —— 冻结配置（编码器/帧规则/预处理/探针/种子/数据 revision/门线原文）
- smoke_cost.json —— 成本实测（提取 117.1s、GPU 峰值 491MiB、下载 2.78GiB）与估算对比
- schema_snapshot.json —— 两仓 meta/episodes 全列 census（batch_axis=unavailable_task_fallback 的证据）
- smoke_episodes.csv —— 入选 219 条 episode 的元数据（task/policy_type/length/success 等）
- confusion_matrix.csv —— 测试集 7 类混淆矩阵（run A，三次同数）

## 关键数字（2026-11-09 夜，8G 卡）

- 主探针（标签=policy_type，7 类）：留出宏平均 OVR AUC = 0.8896，bootstrap 95% CI [0.8288, 0.9402]（B=2000，跳过 28 个缺类重采样）
- per-class AUC：act 0.981 / diffusion 0.974 / smolvla 0.923 / pi0 0.897 / grootn1.7 0.846 / molmoact2 0.803 / pi0.5 0.803
- 正控（标签=task）：AUC = 1.0（≥0.90 门线）
- 负控（策略标签置换，seed 20261110）：AUC = 0.5569，落在 95% null 带 [0.249, 0.751] 内
- 两次同数：3 次独立执行 config_fingerprint 全同（841f40fe3efcc9f1），AUC 极差 = 0.0（≤1e-12）
- 成本：特征提取 117.1s（解码 25 文件 219 eps + DINOv2-small 编码），探针单次 ~6s，远低于估算 40min×2
- 测试集准确率 28/44 = 63.6%（7 类随机 14.3%）；AUC 为预注册主指标

## 如实注记

- 负控 0.5569 点估计高于 0.5，但测试集每类仅 5-9 例，Hanley-McNeil null 带宽 ±0.25——预注册判据即为
  「落在 null 带内」而非「±0.02 噪声带」，此设计在小测试集下是保守的。pilot 全量后应复核负控点估计。
- 批次轴：两仓 meta/episodes 全列 census 无 session/batch/采集字段（chunk/file_index 为按大小存储切块），
  batch_axis=unavailable_task_fallback，A 臂解释为「控制任务组成后的重评」，不写采集批次因果校正。
- smoke 范围=2 个 pilot 任务（cable_clip front 视图 124 eps + fold_tea_towel top 视图 95 eps），
  按 prereg「smoke 不做 12 任务长特征提取」执行；任务选择是 design 冻结的 pilot 对，无结果性挑选。
- 修复记录（实现层，门线/种子/切分未动）：①probe_run 多类 AUC 由 decision_function 改 predict_proba
  （sklearn 多类只收概率矩阵）；②smoke_extract 的 episode→帧索引映射 bug（单帧错位）修复后重提取，
  degraded=124/95 → 0；③download_plan 的 mib 一位小数舍入导致「差尾部 3-50KB」假缺口，
  以 HF Content-Range 权威字节数修正（experiments/scripts/size_verification.json）。

## 复现

    cd <课题目录>
    python experiments/scripts/fast_download.py        # 断点续传（幂等；plan 已含精确字节数）
    python experiments/scripts/verify_files.py         # HF Content-Range 完整性核验
    python experiments/scripts/smoke_extract.py        # 解码+DINOv2-small 特征（幂等：fragment 在则跳过）
    python experiments/scripts/probe_run.py A          # 三次独立执行 A/B/C
    python experiments/scripts/probe_run.py B
    python experiments/scripts/probe_run.py C
    python experiments/scripts/build_download_report.py
    python experiments/scripts/aggregate_smoke.py      # 判门，重写本目录 smoke_summary.json 等

数据：armnet/armnetbench_v01_lerobot_so101 (rev 1db69c82) +
armnet/armnetbench_v01_lerobot_bimanual_so101 (rev c4841758)，25 个视频文件/2.78GiB/219 eps。
编码器 facebook/dinov2-small rev=ed25f3a31f01632728cabb09d1542f84ab7b0056。
环境：python 3.11.9 / torch 2.10.0+cu128 / sklearn 1.8.0 / transformers 4.57.6 / av 16.1.0（见 smoke_config.json）。
