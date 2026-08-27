# 数学建模培训资料选择性提炼说明

本文件记录 6 份赛前培训/赛题讲解材料如何进入当前知识库。目的不是保存“标准答案”，而是保留可迁移的建模判断，同时阻止年代化经验、具体实例结论和模板化竞赛技巧污染主线。

## 1. 来源

1. 《全国大学生数学建模竞赛参赛准备》
2. 《数学建模竞赛注意事项与经验分享》
3. 《数学建模竞赛中的优化模型》
4. 《2023C题：蔬菜类商品自动定价与补货决策》
5. 《2024C题：农作物的种植策略》
6. 《数学建模竞赛赛题选讲》

这些材料属于培训/讲解资料，不是 2026 官方规则，不是 Formal Evidence，不进入论文引用链。

## 2. 吸收原则

只吸收满足至少一项的内容：

- 能提高题意到数学结构的映射质量；
- 能减少高频建模错误；
- 能改善 baseline / validation / failure-case 设计；
- 能增强优化约束完整性和可行性审计；
- 能帮助多问之间形成数据/决策接口；
- 能提高评阅者视角下的模型—代码—结果一致性；
- 能改善模拟赛和比赛过程控制。

## 3. 明确排除

不进入主线：

- 特定软件优先级和年代化操作建议；
- “某算法比赛必用”；
- “模型越多越加分”；
- 固定 ±5%、±10% 灵敏度作为通用要求；
- 某历史实例中某模型/聚类方法“最好”向其他题泛化；
- 模仿历史获奖论文的模型名称或结果；
- 以公式数量、图数量或算法数量衡量质量；
- 历史题具体最优方案、具体参数和数值结果。

## 4. 来源 → 知识层映射

| 来源 | 选择性吸收 | Canonical 落地位置 |
|---|---|---|
| 参赛准备 | 现实问题与数学方法的对应关系；模型储备是结构识别能力 | `guides/algorithm-routing-quality.md` / `guides/academic-quality-standard.md` |
| 经验分享 | 选最合适模型；写作者理解模型；完整模拟赛；赛后复盘 | `guides/rehearsal-and-contest-control.md` |
| 优化模型简介 | 决策变量/参数—约束—目标函数的建模骨架；启发式不保证最优 | `playbooks/constraint-modeling-quality.md`、`guides/contest-paper-reviewer-perspective.md` |
| 2023C 讲解 | 异常/时间结构；销量—价格/补货关系；替代/互补；外部数据价值 | `playbooks/data-to-decision-modeling.md` |
| 2024C 讲解 | 多资源/多季次/兼容/跨期约束；确定性→不确定性→关联结构 | `playbooks/constraint-modeling-quality.md` |
| 赛题选讲 | objective correctness；constraint completeness；一般模型优先；模型-程序-结果一致；可行性优先；heuristic 需额外测试 | `guides/contest-paper-reviewer-perspective.md` |

## 5. Playbook 与 Guide 的严格边界

现有 `reference_library.py` 对 L3 Playbook 有明确合同：只用于 P1–P3 探索、固定 non-evidence 权限和固定八段章节结构。因此：

- `constraint-modeling-quality`、`data-to-decision-modeling` 以及三份既有组合题手册：属于 tag-routable L3；
- 学术总标准、数据/算法/实验/可视化质量规范、评阅者视角、模拟赛控制：属于 `guides/`，由 Prompt Policy 或指定角色直接读取。

正式 CLI `scripts/reference-library.ps1` 通过 `src/workflow/reference_library_cli.py` 安装严格的 L3 discovery 边界，只有以下 5 个文件进入 `lookup -Layer playbook`：

```text
constraint-modeling-quality.md
data-to-decision-modeling.md
mechanism-fit-and-scenario.md
predict-then-optimize.md
resource-allocation-under-uncertainty.md
```

历史 `playbooks/<quality-guide>.md` 路径如果因兼容原因仍存在，不再是 canonical 引用，也不会进入上述 routable set；不得新增对这些旧路径的依赖。

这种做法不放宽原有 schema，不新增 Gate，也不让跨 P4–P6 的指南污染 P1–P3 教材速查路由。

## 6. 与现有体系的关系

权威顺序不变：

```text
当届官方规则
→ project contest.yaml
→ prompt_policy / Formal contracts
→ Formal / frozen evidence
→ guides/academic-quality-standard
→ 专项 Guides / L3 Playbooks
→ 原始培训资料
```

原始培训材料不直接参与：

- Formal promotion；
- claims freeze；
- Figure Contract；
- submission audit；
- academic citation。

## 7. 维护规则

如果未来新增培训资料：

1. 先记录来源与年代；
2. 区分“可迁移原则”和“特定实例经验”；
3. 与当前 academic-quality-standard 比较，避免重复；
4. 只新增能改变实际决策的内容；
5. 优先更新已有 Guide / L3 Playbook，而不是不断新增文件；
6. 新 L3 必须同时进入 `reference_library_cli.py` 的 routable set 并通过既有 `validate_playbook`；
7. 若内容与当届官方规则冲突，直接以官方规则为准。
