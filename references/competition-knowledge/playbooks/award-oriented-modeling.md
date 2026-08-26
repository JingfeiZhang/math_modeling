---
playbook_id: award-oriented-modeling
playbook_version: 3
tags: [model-selection, experiment-design, interpretation, academic-quality, competition-quality]
stage_scope: [P1, P2, P3a, P3b]
evidence_status: P1-P3-non-evidence
contest_evidence_eligible: false
allowed_use: [problem_abstraction, model_direction, baseline_design, challenger_design, experiment_design, stopping_rule, interpretation]
forbidden_use: [academic_citation, formal_evidence, claim_support, submission]
---

# 国赛高质量学术化建模战术手册

本手册把优秀竞赛论文中稳定出现的论证结构，转化为 P1–P3 可执行的建模策略。它不增加 Gate，而是提升每一步的研究质量。

基础标准：

- `academic-quality-standard.md`
- `end-to-end-quality-standard.md`
- `academic-modeling-and-writing.md`
- `data-and-feature-quality.md`
- `algorithm-routing-quality.md`
- `experiment-design-quality.md`
- `visual-evidence-quality.md`

## 1. 总原则：先保证研究问题正确，再优化模型

默认路线：题意与交付 → 数学对象/变量角色/信息时点 → 数据生成结构与风险 → 同输出 baseline → 结构匹配主模型 → 主动寻找反例/失败点 → 只针对失败点升级 → 高信息量验证 → 复杂度收益评估 → Formal / claims。

模型复杂度的合法来源只有：题目结构本身需要；baseline 暴露明确结构性失败；新结构在公平验证中产生稳定、可解释、具有实际意义的增益。“算法先进、论文好看、看起来创新”都不是升级理由。

## 2. P1：问题抽象必须像研究设计

每问先回答研究对象与交付、变量角色、观测单位与依赖结构、信息时点、硬约束、主要不确定性、跨问接口与误差传播、最重要失败代价。

主动排除固定量误作决策变量、未来信息泄漏、输出和题面不同、单位/分母/窗口不一致、看到熟悉算法后反向解释题意。

## 3. 假设：少、必要、可讨论

每个核心假设至少绑定：现实依据 → 模型中的公式/约束 → 若不成立会怎样 → 可否通过场景/敏感性/替代模型检查。不为排版凑“若干假设”。

## 4. P2：baseline 是学术比较坐标

baseline 保持同输入信息、同输出、同评价窗口/分母、同硬约束口径，而且不能故意做弱。它用于验证任务接口、量化复杂模型增益、形成论文的统一比较坐标。

## 5. P2：先验证实现，再讨论优劣

优先级：小实例/手算/穷举 → 单位与符号 → 数据切分和泄漏 → 硬约束/不变量 → baseline 指标。实现正确性不确定时，不进入大规模调参。

## 6. P3a：模型选择形成“研究假说—证据”关系

候选不超过 `Baseline + Main + Challenger + Fallback`。Main 必须说明表达什么结构、相比 baseline 新增什么、预期修复什么失败，以及最能证伪这个假设的实验。

模型选择优先顺序：题意适配 > 信息合法 > 假设可接受 > 可验证性 > 稳定增益 > 解释与决策价值 > 可复现性 > 计算代价 > 算法新颖度。

## 7. 参数估计考虑可辨识性

模型含待估参数时至少考虑参数来源、合理范围、目标/似然、参数间补偿、多组参数产生相似输出的可能性，以及参数变化是否改变主要结论。弱可辨识参数应降低机制解释强度。

## 8. P3a/P3b：实验以证伪和信息增益为核心

默认实验预算：baseline comparison + 一项题型专项验证 + 一项现实有意义的 robustness/uncertainty + 一项 failure-case。

新增实验前问：如果结果相反会不会改变模型选择或 claim？是否攻击真实假设？是否能发现新失败边界？都是否时不做。

## 9. 统计证据：效应量和区间优先

涉及统计推断时优先报告方向 + 效应大小 + 区间 + 实际意义 + 稳健性。p 值只辅助。相关、特征重要性、Granger、SHAP 不自动等于因果。

## 10. 预测专项

最低链：seasonal/persistence baseline → 无泄漏 rolling/out-of-time → 主指标 → error-by-time/group/horizon → residual bias → 必要时 interval coverage + width。训练内拟合不写成预测能力。

## 11. 分类专项

根据任务考虑基率、PR-AUC、Recall/Precision/F1、threshold、confusion matrix、subgroup error、probability calibration。阈值由代价/应用目标驱动。

## 12. 评价排序专项

重点是指标方向与标准化、权重来源、冗余、equal-weight baseline、权重扰动、删指标、top-k/rank stability。排名不稳定本身是结果。

## 13. 聚类专项

除内部指标外，检查尺度、距离、多初始化、参数/样本扰动稳定性与簇的现实解释。t-SNE/UMAP 只辅助展示。

## 14. 优化专项

区分“模型正确”与“求解器成功”。最低证据包括可行性、规则/松弛 baseline、精确 solver status/gap 或启发式的 exact-small-case/lower-bound reference、压力场景和最终方案实际代价。收敛图只辅助。

## 15. 多目标专项

固定权重解不是 Pareto 前沿。讨论权衡时要产生多个非支配或不同偏好方案并说明搜索范围，推荐点有 knee、边际交换或现实偏好依据。

## 16. 机理专项

核心验证：量纲、初值/边界、守恒/容量、极限情形、参数可辨识性、校准与验证分离、敏感性。拟合漂亮不等于机制正确。

## 17. 组合模型与创新

组合只在组件职责互补且单模型缺口明确时成立。创新表达采用“发现问题 → 新增结构 → 作用机制 → 稳定改善 → 失败边界”，不靠重命名。

## 18. 跨问误差传播

若 Q1 输出进入 Q2，检查预测误差、排名不确定性、参数区间或场景不确定性如何影响后问。多问应像统一模型系统而不是独立算法作业。

## 19. 停止规则

Main 稳定优于 baseline、关键失败风险已覆盖、Challenger 不改主结论、新复杂度收益小于解释/复现成本时，停止扩模型，把资源转向 Formal、图表和论文。

## 20. 结果解释标准

每个主要结果按：结果 → baseline/参考比较 → 原因或机制 → 实际意义 → 不确定性/边界。只能写“效果较好”通常意味着证据或解释不足。
