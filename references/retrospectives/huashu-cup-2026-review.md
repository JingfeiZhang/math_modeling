# 2026 华数杯论文评语复盘

本报告将评审意见转化为新项目的建模、证据和论文控制项。它是工作流改进资料，不是竞赛证据，不进入 literature、claims、Figure Contract、论文、附件或发布包。

## 评语摘要

- 摘要偏薄，工程化表达较重，缺少按问题组织的研究发现。
- Q1 的预测指标与题目要求存在偏差，预测效果较弱，且运行成本没有进入评价口径。
- Q2 能完成全量调度并展示成本、碳排和时延权衡，但多目标搜索有限，新能源利用率和迁移率偏离参考范围，也缺少算法收敛证据。
- Q3 的储能物理模型较完整，但固定负荷没有按题面规定处理。
- Q4 具备任务与储能联动思路，但只覆盖小范围局部联合搜索，场景没有完整对应题目要求。
- 全文结构和图表总体较好，但结果表述在摘要、正文、表格和图件之间存在一致性风险。

## 根因与控制映射

| 反馈 | 合同字段 | 转换门禁 | 论文动作 | 回归测试 |
|---|---|---|---|---|
| Q1 指标偏题、缺运行成本 | `task`、`outputs`、`metrics[].target_definition/horizon/time_window`、题面指标映射 | checkpoint 阻断缺指标、单位、分母或预测窗口；G3 比对实际快照 | 明确预测对象、窗口、评分和运行成本 | `test_question_required_metric...`、`test_prediction_contract...` |
| Q2 多目标不足 | `objective_mode`、`scenario_coverage[].parameter_value/objective_vector/non_dominated/result_locator` | Formal 至少要求三个真实、不同且可定位的方案 | 给出 Pareto/epsilon 结果；固定权重只写固定偏好下单方案 | `test_pareto_contract...` |
| Q2 无收敛证据 | `evidence_type`、`trace_locator`、`solver_evidence_locator`、`seed_runs` | Formal 校验轨迹、多种子或求解器 gap/status 文件 | 把收敛作为算法诊断，并另做模型检验 | `test_formal_transition...`、`test_exact_solver...` |
| Q3 固定负荷错误 | `inputs[].role/fixed_by_statement`、`model_variable_map`、`state_conditions` | checkpoint/promote 比对运行的 `input_roles` 与 `model_variables` | 逐项说明固定负荷、初态、终态和边界 | `test_fixed_load...`、`test_checkpoint_blocks_fixed_input...` |
| Q4 场景不完整 | `scenarios[].coverage_mode`、运行 `scenario_coverage`、`scope.window/claim_language` | checkpoint/G3 阻断缺场景或范围过窄；G5 禁止全局外推 | 标注 `full/sampled/local-window` 并使用相同边界措辞 | `test_checkpoint_blocks_uncovered...`、`test_local_window...` |
| 摘要偏薄 | 共享 `abstract_contract` 的 Q1–Qn 方法、对象、结论、验证、边界和 `claim_ids` | G5 对实际 `abstract.tex` 与冻结 claim allowlist 执行检查 | 背景 3–4 行，逐问分段，末段总结贡献和限制 | `test_abstract_contract...`、跨问 question-set 漂移测试 |
| 结果不一致 | `metric definition_sha256`、`run_metric_locator`、`claim_ids/table_ids/figure_ids` | G3 比对指标名、单位、快照和合同 hash；G4/G5 闭合 claim 与表图映射，并要求表格/正文使用冻结 claim、图件合同使用同一 claim 与单位 | 摘要、正文、表格和图件消费同一冻结证据 | `test_checkpoint_blocks_metric_unit_mismatch`、`test_metric_table_and_body_must_use_the_mapped_frozen_claim`、`test_metric_figure_claim_and_unit_must_match_the_contract` |

## 已覆盖与新增缺口

V7 原有 Formal manifest、冻结 claims、Figure Contract、Paper Evidence 和 G5/G6 发布审计继续负责证据与交付。本次新增的质量合同补上了题面语义、指标口径、算法搜索证据和摘要综合四个转换前检查；它们不替代原有实验或论文审计，也不会使 Scratch 因合同草稿未完成而停止。

## 通用反模式

1. 用预测后处理指标代替题目要求的预测评分。
2. 只有一个固定权重解却写成 Pareto 前沿或完整多目标优化。
3. 用一张收敛图代替 baseline、可行性和稳健性验证。
4. 将题面固定量重新设为决策变量。
5. 用局部窗口或少数场景结果外推全时域、全场景或全局最优。
6. 摘要堆叠 runner、代码、流程和工程字段，却没有逐问研究对象与结论。
7. 正文、摘要、表格、图件使用不同分母、单位或时间范围。

## 使用边界

P1–P3 可把本报告用于风险探针和合同草案；它不替代题面、学术文献或 Formal 实验。只有通过 G3/G4 的项目证据才能进入 claims 和论文。
