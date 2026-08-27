# 跨阶段质量指南索引

`guides/` 用于**全局质量标准、角色指南和跨阶段过程控制**。这些文档不会被 `reference_library.py` 当成 L3 Playbook 自动路由，也不需要满足 P1–P3 Playbook 的八段 schema。

它们与 `playbooks/` 的区别是：

```text
Guides    = 跨题型/跨阶段的质量与角色指导
Playbooks = P1–P3 按题面 tags 自动路由的跨模块战术路径
```

两者都属于 non-evidence guidance，不能替代 Formal 运行、frozen claims 或学术文献。

## 全局质量 Guides

| Guide | 主要职责 | 主要阶段/角色 |
|---|---|---|
| [academic-quality-standard](academic-quality-standard.md) | 统一题意、模型、证据、论文和 claim 边界 | P1–P5；Solver/Literature/Visualization/Paper/Reviewer |
| [award-oriented-modeling](award-oriented-modeling.md) | 控制模型梯子、复杂度、验证与停止规则 | P1–P3；Solver/Reviewer |
| [data-and-feature-quality](data-and-feature-quality.md) | 数据语义、缺失/异常、泄漏、尺度和特征工程 | P1–P3；Solver/Reviewer |
| [algorithm-routing-quality](algorithm-routing-quality.md) | 题型→算法梯子、升级触发和 fallback | P1–P3；Solver/Reviewer |
| [experiment-design-quality](experiment-design-quality.md) | baseline、challenger、robustness、failure case 与实验停止 | P2–P4；Solver/Reviewer |
| [visual-evidence-quality](visual-evidence-quality.md) | reader question、图/表/文路由、证据图型和 publication rendering | P3–P5；Visualization/Paper/Reviewer |

## 专项跨阶段 Guides

| Guide | 主要职责 |
|---|---|
| [contest-paper-reviewer-perspective](contest-paper-reviewer-perspective.md) | objective correctness、constraint completeness、model-code-result parity、feasibility-first、claim boundary |
| [rehearsal-and-contest-control](rehearsal-and-contest-control.md) | Smoke / Full Rehearsal、早闭环、团队交叉、论文同步和赛后复盘 |

## 使用边界

Guides 可以：

- 改善模型方向和审阅质量；
- 提醒数据、实验、图表和论文风险；
- 帮助决定何时停止扩模型；
- 给 Reviewer 提供对抗性问题。

Guides 不可以：

- 作为 Formal evidence；
- 直接支撑 claims；
- 充当学术引用；
- 产生或修改正式实验数字；
- 绕过当届官方规则、Prompt Policy、quality contracts 或 Gate。

## 权威顺序

```text
当届官方规则
→ project contest profile
→ prompt_policy / quality contracts
→ Formal / frozen evidence
→ academic-quality-standard 与专项 Guides
→ L3 Playbooks / Cards / Modules
→ 原始培训资料
```

当 Guide 与当届官方规则或项目合同冲突时，以更高层权威为准。
