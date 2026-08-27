# 赛题战术手册索引

战术手册只在 P1–P5 串联多个决策模块，帮助形成“题面映射 → 学术质量标准 → 数据质量 → baseline → 结构匹配主模型 → 高信息量实验 → 证据表达”的最短执行路径。它们不是 Formal 证据或论文来源。

## 默认质量入口

所有真实赛题优先读取 [academic-quality-standard](academic-quality-standard.md)。该总标准提炼仓库内 2021–2025 年公开优秀/展示论文的稳定共性，用于统一题意抽象、模型选择、证据、学术表达和停止规则；它不是官方评分细则，不覆盖当届官方规则。

| 题面结构 / 质量任务 | 战术手册 | 主要模块 |
|---|---|---|
| 任意国赛题：统一学术质量标准 | [academic-quality-standard](academic-quality-standard.md) | 题意、数学抽象、证据梯子、自我反驳、论文学术性、边界 |
| 任意国赛题：控制复杂度并提高整体建模质量 | [award-oriented-modeling](award-oriented-modeling.md) | 题意抽象、候选梯子、复杂度升级、结果解释、停止规则 |
| 数据清洗、泄漏、特征工程与模型输入设计 | [data-and-feature-quality](data-and-feature-quality.md) | 数据风险、缺失/异常、尺度、时间/空间泄漏、三级特征工程 |
| 决定该跑什么算法、何时升级模型 | [algorithm-routing-quality](algorithm-routing-quality.md) | 预测、分类、排序、聚类、优化、多目标、机理、网络路由 |
| 决定哪些实验最值得跑 | [experiment-design-quality](experiment-design-quality.md) | baseline、challenger、ablation、robustness、failure case、实验停止 |
| 决定用图、表还是文字以及画什么图 | [visual-evidence-quality](visual-evidence-quality.md) | reader question、证据图型、视觉层级、caption、论文图表信息密度 |
| 先预测需求/负荷，再配置资源或制定方案 | [predict-then-optimize](predict-then-optimize.md) | forecasting、LP/MILP、不确定性规划 |
| 资源配置同时面对需求、价格或供给波动 | [resource-allocation-under-uncertainty](resource-allocation-under-uncertainty.md) | LP/MILP、不确定性规划 |
| 建立动力学/扩散模型，标定参数并做情景 | [mechanism-fit-and-scenario](mechanism-fit-and-scenario.md) | 机理标定、不确定性规划 |

## 默认执行顺序

```text
题意/接口
→ academic-quality-standard
→ data-and-feature-quality
→ baseline
→ algorithm-routing-quality
→ experiment-design-quality
→ Formal / frozen claims
→ visual-evidence-quality
→ cumcm-paper-quality-playbook
```

`award-oriented-modeling` 用于控制全局时间、复杂度和候选收敛；专项手册只在题面结构真正触发时使用。不要为了匹配某份手册改变题意。

## 决策优先级

当多份手册同时适用时，统一按以下顺序处理：

1. 题面与官方规则；
2. 语义、单位和指标正确性；
3. 学术质量总标准；
4. 题型专项模型/验证要求；
5. 可视化和写作表达。

如果题面不满足专项手册触发条件，返回通用质量手册、L1 卡片或单个 L2 模块，不新增无必要流程。
