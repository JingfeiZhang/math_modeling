# 赛题战术手册索引

L3 战术手册只在 P1–P3 串联多个决策模块，帮助形成“题面映射 → 学术质量标准 → 数据质量 → baseline → 结构匹配主模型 → 高信息量实验”的最短执行路径。它们不是 Formal 证据或论文来源。

## 默认质量入口

所有真实赛题优先读取 [academic-quality-standard](academic-quality-standard.md)。该总标准用于统一题意抽象、模型选择、证据、学术表达和停止规则；它不是官方评分细则，不覆盖当届官方规则。

| 题面结构 / 质量任务 | L3 战术手册 | 主要模块 |
|---|---|---|
| 任意国赛题：统一学术质量标准 | [academic-quality-standard](academic-quality-standard.md) | 题意、数学抽象、证据梯子、自我反驳、论文学术性、边界 |
| 任意国赛题：控制复杂度并提高整体建模质量 | [award-oriented-modeling](award-oriented-modeling.md) | 题意抽象、候选梯子、复杂度升级、结果解释、停止规则 |
| 数据清洗、泄漏、特征工程与模型输入设计 | [data-and-feature-quality](data-and-feature-quality.md) | 数据风险、缺失/异常、尺度、时间/空间泄漏、三级特征工程 |
| 决定该跑什么算法、何时升级模型 | [algorithm-routing-quality](algorithm-routing-quality.md) | 预测、分类、排序、聚类、优化、多目标、机理、网络路由 |
| 决定哪些实验最值得跑 | [experiment-design-quality](experiment-design-quality.md) | baseline、challenger、ablation、robustness、failure case、实验停止 |
| 决定用图、表还是文字以及画什么图 | [visual-evidence-quality](visual-evidence-quality.md) | reader question、证据图型、视觉层级、caption、论文图表信息密度 |
| 复杂优化题：把自然语言规则转成变量、目标、约束和验证 | [constraint-modeling-quality](constraint-modeling-quality.md) | constraint inventory、索引变量、确定性→不确定性、feasibility audit |
| 销售/需求/库存/定价：数据分析最终要落到决策 | [data-to-decision-modeling](data-to-decision-modeling.md) | 数据语义、时间验证、响应关系、预测误差传播、决策评价 |
| 先预测需求/负荷，再配置资源或制定方案 | [predict-then-optimize](predict-then-optimize.md) | forecasting、LP/MILP、不确定性规划 |
| 资源配置同时面对需求、价格或供给波动 | [resource-allocation-under-uncertainty](resource-allocation-under-uncertainty.md) | LP/MILP、不确定性规划 |
| 建立动力学/扩散模型，标定参数并做情景 | [mechanism-fit-and-scenario](mechanism-fit-and-scenario.md) | 机理标定、不确定性规划 |

## 跨阶段质量指南

以下文件不属于 reference-library 的 L3 playbook 层，因此不受 P1–P3 playbook schema 路由；它们用于人工或指定角色审阅：

- [评阅者视角](../guides/contest-paper-reviewer-perspective.md)：objective correctness、constraint completeness、model-code-result parity、feasibility-first、claim boundary。
- [模拟赛与比赛过程控制](../guides/rehearsal-and-contest-control.md)：Smoke / Full Rehearsal、早闭环、团队交叉、论文同步、赛后复盘。

## 默认执行顺序

```text
题意/接口
→ academic-quality-standard
→ data-and-feature-quality
→ （按题面触发 constraint-modeling-quality / data-to-decision-modeling）
→ baseline
→ algorithm-routing-quality
→ experiment-design-quality
→ Candidate / Formal 晋升前人工对抗性复核
→ Formal / frozen claims
→ visual-evidence-quality
→ cumcm-paper-quality-playbook
```

`award-oriented-modeling` 用于控制全局时间、复杂度和候选收敛；`rehearsal-and-contest-control` 只用于赛前演练与过程复盘。专项手册只在题面结构真正触发时使用，不要为了匹配某份手册改变题意。

## 决策优先级

当多份手册同时适用时，统一按以下顺序处理：

1. 题面与官方规则；
2. 语义、单位和指标正确性；
3. 学术质量总标准；
4. 目标/约束/数据接口等结构性正确性；
5. 题型专项模型/验证要求；
6. 可视化和写作表达。

如果题面不满足专项手册触发条件，返回通用质量手册、L1 卡片或单个 L2 模块，不新增无必要流程。

## 培训资料提炼边界

本轮从培训/赛题讲解材料中提炼两份合规 L3 playbook（`constraint-modeling-quality`、`data-to-decision-modeling`）和两份跨阶段 guide。来源与排除规则记录在 `../source-notes/training-materials-curation.md`。

这些材料不把历史题具体解法当成标准答案，也不吸收特定软件偏好、“多算法即加分”、固定灵敏度比例等经验性规则。