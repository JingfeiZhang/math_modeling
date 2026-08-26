# 赛题战术手册索引

战术手册只在 P1-P5 串联多个决策模块，帮助形成“题面映射 -> 数据质量 -> baseline -> 结构匹配主模型 -> 高信息量实验 -> 证据表达”的最短执行路径。它们不是 Formal 证据或论文来源。

| 题面结构 / 质量任务 | 战术手册 | 主要模块 |
|---|---|---|
| 任意国赛题：控制复杂度并提高整体建模质量 | [award-oriented-modeling](award-oriented-modeling.md) | 题意抽象、候选梯子、复杂度升级、结果解释、停止规则 |
| 数据清洗、泄漏、特征工程与模型输入设计 | [data-and-feature-quality](data-and-feature-quality.md) | 数据风险、缺失/异常、尺度、时间/空间泄漏、三级特征工程 |
| 决定该跑什么算法、何时升级模型 | [algorithm-routing-quality](algorithm-routing-quality.md) | 预测、分类、排序、聚类、优化、多目标、机理、网络路由 |
| 决定哪些实验最值得跑 | [experiment-design-quality](experiment-design-quality.md) | baseline、challenger、ablation、robustness、failure case、实验停止 |
| 决定用图、表还是文字以及画什么图 | [visual-evidence-quality](visual-evidence-quality.md) | reader question、证据图型、视觉层级、caption、论文图表信息密度 |
| 先预测需求/负荷，再配置资源或制定方案 | [predict-then-optimize](predict-then-optimize.md) | forecasting、LP/MILP、不确定性规划 |
| 资源配置同时面对需求、价格或供给波动 | [resource-allocation-under-uncertainty](resource-allocation-under-uncertainty.md) | LP/MILP、不确定性规划 |
| 建立动力学/扩散模型，标定参数并做情景 | [mechanism-fit-and-scenario](mechanism-fit-and-scenario.md) | 机理标定、不确定性规划 |

默认顺序：先用 `award-oriented-modeling` 确定总体质量策略；遇到数据、算法、实验或图表决策时读取对应质量手册；再按题面结构选择专项手册。不要为了匹配手册改变题意。

最短质量链：

```text
题意/接口
→ data-and-feature-quality
→ baseline
→ algorithm-routing-quality
→ experiment-design-quality
→ Formal/claims
→ visual-evidence-quality
→ paper
```

如果题面不满足专项手册触发条件，返回通用质量手册、L1 卡片或单个 L2 模块，不新增无必要流程。
