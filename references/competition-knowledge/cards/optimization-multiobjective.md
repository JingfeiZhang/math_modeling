---
card_id: optimization-multiobjective
tags: [optimization, pareto, epsilon-constraint, tradeoff]
source_id: operations-algorithms
source_sha256: FDB62419200DAA506578167E70E72BDFC38AFC20780EC412EB2D41B97E8FF63C
pdf_page: 待人工核验
printed_page: 待人工核验
chapter: 多目标优化
section: Pareto 解、加权和与约束法
locator_confidence: low
visual_verification: pending
formula_manual_check_required: true
---

# 多目标与 Pareto 选择

## 适用信号
需要同时兼顾成本、收益、均衡、风险或环境影响，且不存在唯一自然目标。

## 必要前提
统一目标方向和尺度；分清“展示权衡”与“必须推荐一个方案”。

## 最小建模骨架
用 ε-约束法固定次目标阈值并优化主目标，或对归一化目标加权；记录非支配解和选择规则。

## 算法/代码入口
小规模重复调用 LP/MILP/NLP；仅在必要时使用多目标启发式。先观察目标空间和膝点。

## 同输出 baseline
只优化核心目标并报告其他目标，或使用等权归一化方案；输出完整决策向量。

## 验证与敏感性
检查非支配关系、归一化和膝点；扰动 ε、权重和尺度，观察推荐是否稳定。

## 停止条件
权衡曲线已足以支撑结论时停止加点；推荐点依赖偏好时交根 Agent 决策。

## 误用风险
未归一化直接加权；把随机样本称为 Pareto 前沿；遗漏约束导致虚假前沿。

## 原书回退定位
回看 `operations-algorithms` 多目标优化及 `operations-research` 目标规划章节；公式须人工复核。

## 决策判断
采用条件：目标之间确有冲突，且题目没有给出唯一优先级；先用 ε-约束或词典序保留权衡含义，再在需要推荐单点时引入明确偏好。排除条件：目标可由题面自然排序，或所谓多目标只是同一指标的重复变换。

## 关键量与诊断
统一最大化/最小化方向并记录归一化基准、非支配解数量、每个目标的原始值和约束可行性。检查候选点是否被另一点逐目标不差且至少一项更好；检查 ε/权重改变后推荐点是否跳变。

## 赛中最小试验
在小规模上分别运行核心单目标、等权归一化和 3 个 ε 水平；画目标空间散点并剔除被支配点。若前沿仅有一个有效区域或推荐点对偏好极敏感，正文应报告权衡区间并把单点选择交由根 Agent 决策。
