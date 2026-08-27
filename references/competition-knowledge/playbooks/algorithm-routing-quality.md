---
playbook_id: algorithm-routing-quality
playbook_version: 1
tags: [model-selection, algorithm-routing, baseline, challenger, competition-quality]
stage_scope: [P1, P2, P3a, P3b]
evidence_status: P1-P3-non-evidence
contest_evidence_eligible: false
allowed_use: [task_routing, baseline_design, main_model_selection, challenger_selection, complexity_control]
forbidden_use: [academic_citation, formal_evidence, claim_support]
---

# 算法路由与模型升级手册

本手册不自动执行 AutoML。它用于帮助 Solver 在有限比赛时间内构造“baseline → 结构匹配主模型 → 必要升级”的模型梯子。

## 1. 路由前先识别数学结构

算法名称之前先识别：

- 输出：数值预测、概率、排序、方案、轨迹、分配、网络流或政策建议；
- 变量域：连续、整数、0-1、类别、状态变量；
- 关系：线性/非线性、动态、空间、网络、层级、随机；
- 约束：容量、逻辑、平衡、时序、守恒、风险；
- 不确定性：参数误差、需求波动、场景、随机过程；
- 规模：变量/约束/样本数量及比赛时间预算。

### 1.1 Formulation-first：先把问题建对，再讨论求解器

对于包含决策、约束或多阶段接口的题目，至少先写清：

```text
Sets / indices
Parameters
Observed states
Decision variables
Derived quantities
Objective / evaluation target
Hard constraints
Soft preferences
Information timing
Output contract
```

其中必须优先核对两件事：

1. **Objective correctness**：优化/评价的量是否真的是题目要求的目标，而不是方便计算的替代指标；
2. **Constraint completeness**：容量、兼容、时间、守恒、逻辑、服务水平、变量域等题面硬条件是否完整进入模型。

先写“使用 MILP/GA/XGBoost”再补变量和约束，属于错误路由顺序。

## 2. 默认复杂度预算

每问默认最多维护：

```text
1 baseline
1 main
1 challenger
1 fallback
```

新增第四种实质不同的模型前，必须回答“现有模型无法回答题目中的哪个问题”。答不出则停止扩张。

## 3. 预测与时间序列

默认梯子：

```text
Mean/Persistence/Seasonal Naive
→ Linear/Ridge/ETS/ARIMA
→ Dynamic Regression/GAM/Lag-feature Boosting
→ 更复杂时序模型
```

保留复杂模型的条件：样本规模足够、简单模型存在稳定结构残差、滚动样本外指标稳定改善且改善对题目有实际意义。

深度模型不是默认终点。数据很小、时间很短、解释要求高时，经典模型通常更有比赛价值。

### 3.1 Estimate → Decide：只有下游决策真正依赖上游估计时才串联

当预测、参数估计、分类概率或评价得分会成为后一问的成本、需求、容量、风险或约束参数时，使用：

```text
upstream estimate
→ uncertainty/error representation
→ downstream decision
→ end-to-end decision evaluation
```

此时模型选择不能只看上游 MAE/RMSE/AUC。若更复杂的上游模型虽然提高统计指标，却不改变方案、成本、服务水平、风险或可行率，则通常不值得继续增加复杂度。

反之，如果总体误差改善不大，但明显减少高代价时段/关键场景误差，并稳定改善最终决策指标，则可以保留。若上游结果根本不影响下游方案，不为“跨问联动”强行串联。

## 4. 回归与解释型分析

默认梯子：

```text
简单相关/均值 baseline
→ OLS
→ Ridge/Lasso
→ GAM
→ Tree Boosting
```

若题目重在解释，优先效应方向、大小、区间和边界；不要用单一 feature importance 代替解释。

## 5. 分类

默认梯子：

```text
Prevalence/规则 baseline
→ Logistic Regression
→ Random Forest
→ XGBoost/LightGBM/CatBoost
```

若输出概率用于后续决策，校准和阈值选择与分类器本身同等重要。类别不平衡时优先 PR-AUC、Recall/Precision、F1、校准与混淆成本，不以 Accuracy 主导。

## 6. 评价与排序

默认梯子：

```text
等权/单指标 baseline
→ 合理标准化
→ Entropy/CRITIC/PCA 等权重或降维
→ TOPSIS/综合评分
→ 权重敏感性与排名稳定性
```

不要同时堆 AHP、熵权、TOPSIS、灰关联、PCA 只为显得丰富。评价问题的核心质量来自指标语义、权重依据和排名稳定性。

## 7. 聚类

默认梯子：

```text
必要尺度处理
→ KMeans baseline
→ Hierarchical/GMM
→ DBSCAN/HDBSCAN（存在非球状/噪声结构依据时）
```

验证不仅看 silhouette，还看初始化/抽样稳定性和簇的实际可解释性。t-SNE/UMAP 主要用于展示，不单独证明聚类正确。

## 8. 优化与调度

默认优先级：

```text
规则/Greedy baseline
→ LP
→ MILP/QP
→ NLP
→ Network/Dynamic/Decomposition
→ Metaheuristic
```

能精确建模并求解时，不先使用 GA/PSO/SA/ACO。启发式只在强非凸、组合爆炸、黑箱目标、大规模或精确求解器在预算内不可用时进入主候选。

### 8.1 Feasibility first

优化结果统一按以下顺序解释：

```text
模型语义正确
→ 硬约束完整
→ 解可行
→ 与 baseline 比较
→ 再讨论 objective / optimality
```

因此：

- solver success 不等于业务可行；
- feasible 不等于已证明最优；
- heuristic 最好一次不等于全局最优；
- objective 更好但违反硬约束的方案没有比较资格。

使用启发式时必须保留至少一种可信坐标：小规模精确解、松弛下界、规则 baseline、solver gap/界、重复种子或可行率。

### 8.2 确定性模型先闭合，再按失败证据升级不确定性

存在未来波动并不自动意味着必须上 robust/stochastic。优先：

```text
完整确定性 formulation
→ 合理场景/参数压力测试
→ 观察方案翻转、不可行、尾部损失或服务失控
→ 有证据时才升级 robust/stochastic/recourse
```

如果压力测试不改变主要方案或结论，保留简单确定性主模型并报告边界即可。若不确定性的来源、范围或概率没有依据，不以复杂概率模型掩盖信息缺口。

## 9. 多目标

单个固定权重解不是完整 Pareto 前沿。需要权衡结论时优先：

```text
weight sweep
或 epsilon-constraint
或真正的非支配搜索
```

论文必须区分“给定偏好下的方案”和“已覆盖的权衡范围”。推荐方案需解释 knee/边际交换或实际偏好，而不是只把一个点染红。

## 10. 机理与动力学

先建立状态变量、守恒、边界、参数和机制，再选择数值求解器。模型质量主要由机理闭合、参数可辨识性和边界验证决定，而不是 solver 名称。

## 11. 网络、路径与调度

存在明确图结构时优先利用网络结构：最短路、最大流/最小费用流、匹配、VRP、调度或时空网络。只有基础结构无法表达题目约束时才升级为更一般 MILP 或启发式。

## 12. 模型升级触发器

只有出现以下证据之一才升级：

- baseline 在特定场景有系统偏差；
- 非线性/交互在残差或诊断中稳定存在；
- 名义方案在扰动下不可行；
- 简单权重导致排名明显不稳定；
- 机理模型在某边界存在系统偏差；
- 当前模型无法表达题面必须满足的离散/网络/动态约束。

升级后必须重新比较同输出 baseline，并验证它确实修复了原失败点。

## 13. 模型选择的停止规则

满足以下条件后停止找新模型：

- 主模型稳定优于合理 baseline；
- challenger 没有推翻主要结论；
- 题型专项验证通过或边界已明确；
- 新复杂度的收益小于验证、解释和论文完善的收益；
- fallback 已足够支持按时交付。
