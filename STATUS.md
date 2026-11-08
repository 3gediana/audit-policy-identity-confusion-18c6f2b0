# 状态

- 阶段：smoke **完成（verdict=supported，尺子可用）**（2026-11-09 夜 executor 单元）；workflow：design→smoke→pilot→experiment→analysis，下一步=pilot（三臂排名重评）。
- 最近更新：2026-11-09T23:45:00+08:00（executor 夜间单元，smoke 全流程完成 + 判门 supported）
- 最近产物：results/（smoke_summary.json、smoke_probe_run_A/B/C.json、smoke_config.json、smoke_cost.json、schema_snapshot.json、smoke_episodes.csv、confusion_matrix.csv、README.md）。
- smoke 判门结果（四门全过）：主探针（标签=policy_type，7 类，219 eps）留出宏 OVR AUC=0.8896，bootstrap 95% CI [0.8288, 0.9402]；正控（标签=task）AUC=1.0（≥0.90）；负控（置换，seed 20261110）AUC=0.5569 落在 95% null 带 [0.249, 0.751] 内；三次独立重算 config_fingerprint 全同、AUC 极差=0.0（≤1e-12）；成本=提取 117.1s + 探针 ~6s/次，远低于估算 40min×2。
- 本单元修复记录（实现层，门线/种子/切分/标签未动，已记 DECISIONS）：①probe_run 多类 AUC：decision_function→predict_proba（sklearn 多类只收概率矩阵，原实现无法运行）；②smoke_extract episode→帧索引映射 bug（特征=全局第 i 帧的错位单帧）修复后重提取，degraded 124/95→0；③download_plan mib 一位小数舍入造成「差尾部 3-50KB」假缺口，以 HF Content-Range 权威字节数修正（size_verification.json）；④aggregate 的 batch_like 匹配器「rig」子串误命中 right_wrist 列，排除 videos/ 存储列后 batch_axis=unavailable_task_fallback 与 schema census 一致。
- 如实注记：负控点估计 0.5569 略高于 0.5，但测试集每类仅 5-9 例、null 带 ±0.25，预注册判据即「落在 null 带内」；pilot 全量后应复核负控点估计。smoke 范围=2 个 pilot 任务（cable_clip 124 eps + fold_tea_towel 95 eps，25 文件/2.78GiB），按 prereg 决策价值第 3 行执行。
- 下一步（pilot 要点，供 researcher 判读后派发）：同一特征管线扩到 pilot 三臂：A 臂=探针分层重评、B 臂=长度中位数截断、C 臂=原始成功率排名，产出 ranking_A/B/C.csv + pairwise_flips.csv + Kendall tau-b，判「原始排名不稳定/未观察到翻转」。数据下载按 download_plan_min.json 扩展清单（fast_download.py/verify_files.py/export_cm.py 可复用；尺寸核验必做，防 mib 舍入假缺口）。
- 组合层去重（2026-11-09 判读拍板）：同题姊妹 438aa6b2 已 duplicate-merged 归档，本课题为唯一推进线；保留 pivot 三条见 notes/DECISIONS.md。
- 研究员唤醒点：smoke 回执判读（verdict=supported 放行 pilot 或要求补强）；持续跟踪 LamportRobotics 上传（若出现 rollout 语料审计即触发 stop_if_not_novel 复查）。
- 关键证据锚点：2611.03168 §5 逐字引语（身份可推断/长度泄漏/近二值标签）见 literature/related-work.md §2；OpenAlex 前向被引 0（W7225193298，2026-11-09）；Eval-Actions 2601.18723（策略 vs 遥操源头判别 99.6%）为身份信号存在的旁证（姊妹筛查并入，§7）。smoke 实测 AUC 0.89 是身份信号存在的首个量化直接证据（2 任务范围）。
