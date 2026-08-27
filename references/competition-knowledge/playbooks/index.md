# L3 赛题战术手册索引

`playbooks/` 顶层现在只承载 **reference-library 可自动路由的 P1–P3 L3 战术手册**。除本 `index.md` 外，每个 `.md` 都必须满足 `src/workflow/reference_library.py` 的严格 playbook 合同：

- `playbook_version: 1`；
- `stage_scope` 仅包含 `P1 / P2 / P3a / P3b`；
- `evidence_status: P1-P3-non-evidence`；
- `contest_evidence_eligible: false`；
- `allowed_use` 固定为 `model_direction / assumption_check / baseline_design / risk_probe`；
- `forbidden_use` 至少禁止 academic citation、Formal evidence、claim support、Figure Contract 和 submission；
- 必须包含“触发与排除、输入输出合同、分阶段行动、baseline 与升级、联合诊断、停止与回退、Candidate 交接、禁止事项”八段。

因此，本目录不再放学术总标准、通用数据/算法/实验质量指南、可视化规范、评阅指南或模拟赛指南；这些统一放到 [`../guides/`](../guides/index.md)。

## 当前可路由 L3 Playbook

| 触发结构 | Playbook | 连接模块 |
|---|---|---|
| 规则密集、跨期、整数/0-1、兼容性、容量、轮作 | [constraint-modeling-quality](constraint-modeling-quality.md) | LP/MILP、网络/排程、不确定性规划 |
| 销售/需求/库存/定价/补货，数据分析最终落到决策 | [data-to-decision-modeling](data-to-decision-modeling.md) | 预测、小样本回归、LP/MILP、不确定性规划 |
| 前一问预测需求/负荷/价格，后一问据此做配置或方案 | [predict-then-optimize](predict-then-optimize.md) | 预测、LP/MILP、不确定性规划 |
| 资源配置同时面对需求、价格或供给波动 | [resource-allocation-under-uncertainty](resource-allocation-under-uncertainty.md) | LP/MILP、不确定性规划 |
| 动力学/扩散方程 + 参数标定 + 情景分析 | [mechanism-fit-and-scenario](mechanism-fit-and-scenario.md) | 机理标定、不确定性规划 |

## 路由原则

```text
题面结构
→ L1 路由卡 / L2 决策模块
→ 只有存在跨模块结构时触发一个最匹配 L3 playbook
→ Candidate
```

不要为了使用 Playbook 改变题意，也不要同时加载多个高度重叠的 L3。若单个 L2 模块已经足够回答问题，就停在 L2。

## 与 Guides 的关系

全局质量链不属于 L3 schema：

```text
academic-quality-standard
→ award-oriented-modeling
→ data-and-feature-quality
→ algorithm-routing-quality
→ experiment-design-quality
→ [按题面触发一个 L3 playbook]
→ Formal / claims
→ visual-evidence-quality
```

这些全局指南由 Prompt Policy 或指定角色直接读取，入口见 [`../guides/index.md`](../guides/index.md)。

## 证据边界

L3 Playbook 只用于 P1–P3 的模型方向、假设检查、baseline 设计和风险探针；其中任何文字、历史题经验或示例都不能作为：

- 学术引用；
- Formal evidence；
- claim support；
- Figure Contract 数据；
- submission / release 材料。

正式数字仍必须来自当前项目的 Scratch / Candidate / Formal 实际运行和冻结证据。
