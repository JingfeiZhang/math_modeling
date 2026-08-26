# 赛题战术手册索引

战术手册只在 P1-P3 串联多个决策模块，帮助形成“题面映射 -> baseline -> 一次升级 -> 联合诊断 -> 回退/保留”的最短执行路径。它们不是 Formal 证据或论文来源。

| 题面结构 | 战术手册 | 主要模块 |
|---|---|---|
| 任意国赛题：需要在有限时间内提高建模质量、控制复杂度并形成高价值实验 | [award-oriented-modeling](award-oriented-modeling.md) | 题意抽象、候选梯子、复杂度升级、实验设计、结果解释、停止规则 |
| 先预测需求/负荷，再配置资源或制定方案 | [predict-then-optimize](predict-then-optimize.md) | forecasting、LP/MILP、不确定性规划 |
| 资源配置同时面对需求、价格或供给波动 | [resource-allocation-under-uncertainty](resource-allocation-under-uncertainty.md) | LP/MILP、不确定性规划 |
| 建立动力学/扩散模型，标定参数并做情景 | [mechanism-fit-and-scenario](mechanism-fit-and-scenario.md) | 机理标定、不确定性规划 |

默认先读取 `award-oriented-modeling` 确定“简单 baseline → 结构匹配主模型 → 针对失败点升级 → 验证后保留/回退”的质量策略，再按题面结构选择专项手册。不要为了匹配手册改变题意。若题面不满足专项手册触发条件，返回 L1 卡片或单个 L2 模块。
