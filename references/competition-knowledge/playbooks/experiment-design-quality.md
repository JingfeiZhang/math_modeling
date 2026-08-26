---
playbook_id: experiment-design-quality
playbook_version: 1
tags: [experiment-design, information-gain, ablation, robustness, failure-analysis]
stage_scope: [P2, P3a, P3b, P4]
evidence_status: P2-P3-guidance
contest_evidence_eligible: false
allowed_use: [experiment_prioritization, validation_design, ablation_design, robustness_design, stopping_rule]
forbidden_use: [academic_citation, direct_claim_support]
---

# 高信息量实验设计手册

实验的目标不是“跑得多”，而是用最少实验回答最关键的不确定性：模型是否正确、是否优于 baseline、为什么优、在哪里会失败。

## 1. 默认实验预算

每问优先组织为：

```text
1 baseline comparison
+ 1 task-specific validation
+ 1 robustness/sensitivity experiment
+ 1 failure-case analysis
```

存在模块化创新时再增加必要 ablation；存在随机算法时增加多种子；存在多目标时增加偏好/前沿覆盖。不要默认进行大规模模型网格和超参搜索。

## 2. 实验优先级

按以下顺序投入时间：

1. **Correctness**：known-answer、约束、单位、边界、信息合法性；
2. **Incremental value**：相对同输出 baseline 的真实改善；
3. **Failure risk**：模型最可能失败的场景；
4. **Robustness**：扰动后主结论是否保持；
5. **Mechanism**：为什么产生改善或失败；
6. **Hyperparameter tuning**：最后才是精细调参。

可用启发式：实验优先级 ≈ 结论变化概率 × 论文价值 / 计算成本。无需计算数值，只用于排序。

## 3. Baseline comparison

比较必须满足：同输出、同样本/场景、同指标、同单位、同决策时点信息。优先报告绝对差和相对差，并检查改善是否集中在少数样本或极端场景。

如果主模型只提升极小且不稳定，应优先回退简单模型或说明复杂度的其他价值（可行性、风险、解释性）。

## 4. Challenger 的职责

Challenger 只验证一个关键替代解释，例如：

- 非线性是否真的必要；
- 鲁棒模块是否比名义模型有价值；
- 复杂权重是否真的改善排名稳定性；
- 机理结构是否优于纯数据拟合。

Challenger 不应成为第二个需要完整调优的主模型。

## 5. Ablation

只有模型由多个有明确作用的模块组成时才做。推荐：

```text
Base
Base + A
Base + A + B
Full
```

每个模块必须对应一个预先声明的失败点或机制。若删除模块没有稳定影响，应从最终模型删除，或降低其论文地位。

## 6. 超参数优化

三步足够：

1. 默认/经验参数跑通；
2. 粗粒度 Random/Bayesian Search 找敏感区域；
3. 仅对最敏感的少量参数局部细调。

搜索过程必须嵌在合法验证结构中，不能使用最终测试集反复选择参数。不要在模型价值尚未确认前消耗大量算力。

## 7. 预测/回归实验

优先：

```text
rolling/out-of-sample validation
→ baseline comparison
→ error by horizon/time/group
→ residual/calibration/interval coverage
→ feature or module ablation
```

重点检查峰值、高代价区间、趋势转折、不同 horizon 和数据漂移。平均指标不能掩盖关键时段系统失败。

## 8. 分类实验

优先：

```text
prevalence baseline
→ PR-AUC / ROC-AUC
→ threshold-specific confusion costs
→ calibration
→ error by subgroup
```

阈值由题意代价或验证集确定，不能只使用默认 0.5。类别不平衡时必须报告实际基率。

## 9. 优化/调度实验

优先：

```text
feasibility audit
→ rule/greedy baseline
→ small exact instance / lower bound / gap
→ scenario stress
→ parameter sensitivity
→ multi-seed if stochastic
```

收敛曲线只证明算法行为，不能替代方案质量、可行性或业务价值。

## 10. 多目标实验

重点不是多跑种子，而是覆盖权衡空间：权重 sweep、epsilon 约束或非支配解。报告边际交换、可行区域和推荐点的理由。若只探索局部窗口，必须限制结论范围。

## 11. 评价/排序实验

优先：

- 标准化方案替换；
- 权重扰动；
- 删除高冗余指标；
- top-k 稳定性；
- 排名翻转阈值。

若排名高度敏感，不应隐藏，而应把稳定区间作为主要结论。

## 12. 机理/仿真实验

机理：量纲、守恒、初/边值、参数校准-验证分离、极限情形、参数可辨识性与敏感性。

随机仿真：区分预热期与统计期；有足够重复；报告均值和区间；因素实验围绕真正影响决策的变量，而不是无目的画曲线。

## 13. Robustness 与 Stress Test

扰动优先来自实际不确定来源：需求、成本、容量、权重、测量误差、时间窗口、参数估计。优先找“结论在哪个扰动范围内保持”和“在哪个阈值后改变”，而不是机械所有参数 ±10%。

## 14. Failure-case analysis

每个主模型至少主动寻找一种失败情形：高峰、边界、稀有类别、极端场景、密集网络、参数漂移等。失败分析的目的不是证明模型差，而是给论文提供可信边界和改进方向。

## 15. 实验停止规则

当以下问题都有答案时停止扩张实验：

- 模型是否正确？
- 比 baseline 好在哪里？
- 最可能在哪里失败？
- 主要结论对合理扰动是否稳定？
- 为什么产生主要改善？

之后优先把证据转换为 Formal、图表和论文，不继续为了“实验数量”消耗时间。
