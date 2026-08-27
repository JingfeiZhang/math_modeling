---
playbook_id: rehearsal-and-contest-control
playbook_version: 1
tags: [rehearsal, contest-control, workflow, paper, team, release]
modules: []
stage_scope: [P0, P1, P2, P3a, P3b, P4, P5, P6]
evidence_status: P0-P6-non-evidence
contest_evidence_eligible: false
allowed_use: [rehearsal_design, process_metrics, team_handoff, paper_timing, postmortem]
forbidden_use: [academic_citation, formal_evidence, claim_support, figure_contract, submission]
---

# 模拟赛与比赛过程控制手册

> 定位：P0–P6 的赛前演练与比赛节奏参考，不新增 Gate、不规定死板小时表。
>
> 来源基础：《数学建模竞赛注意事项与经验分享》《全国大学生数学建模竞赛参赛准备》中关于模型储备、团队交叉能力、模拟赛、论文写作和过程控制的经验，经当前工作流“progress-first / evidence-first”原则筛选。

## 1. 模拟赛的目标不是“做出往年高分解”

模拟赛首先验证：

```text
题面进入
→ 拆题
→ 数据读取
→ baseline
→ candidate
→ 至少一问 Formal
→ claims
→ 图表/论文
→ build/audit/package/seal
```

只有全链路能按时间完成，赛前工作台才算真正可用。

历史资料强调：模拟赛要按真实比赛时间要求完成完整论文，并在赛后分析优缺点。当前工作流进一步把它转化为可量化的工程演练。

## 2. 最重要的过程指标

每次 rehearsal 记录：

| 指标 | 含义 |
|---|---|
| time_to_problem_map | 从拿题到 Q1–Qn 和接口明确 |
| time_to_first_baseline | 第一条可运行同输出 baseline |
| time_to_first_main_result | 第一版主模型结果 |
| time_to_first_formal | 第一问可晋升 Formal |
| time_to_paper_skeleton | 摘要/章节/图表位置可编译 |
| time_to_first_full_pdf | 第一份完整 PDF |
| time_to_release_audit | 第一次完整发布审计 |
| manual_rework_count | 因路径/格式/复制数字产生的返工 |
| evidence_gap_count | 论文 claim 缺对应 evidence 的数量 |

不要只记录最终模型指标。

## 3. 团队职责应交叉，不应形成单点故障

历史经验强调：写作者必须真正理解模型，建模/代码/写作完全割裂会导致模型意图与论文表述不一致。

推荐能力覆盖：

```text
成员 A：论文 + 建模
成员 B：建模 + 代码
成员 C：代码 + 论文
```

并非固定分工，而是确保每个关键环节至少两人能接手。

工作流上的对应要求：

- Paper 只能消费 Formal/frozen evidence，不自行发明模型逻辑；
- 关键模型说明至少由建模者复核；
- 关键结果表/图至少由第二人核对单位、场景和 run_id；
- 提交 operator 之外至少一人能完成 package/verify。

## 4. 比赛节奏：早闭环，而不是最后一天才写论文

历史经验常用“第一天框架、第二天求解、第三天修改”表达比赛节奏。当前工作流不把它写成死时间表，而提炼为：

```text
尽早形成第一条端到端闭环
→ 再提高模型质量
→ 再冻结
→ 最后集中压缩和发布
```

推荐顺序：

### Early

- 快速选题；
- 题意/数据/风险映射；
- 每问 baseline；
- 论文骨架同步建立。

### Middle

- 主模型和 challenger；
- 最高信息量验证；
- 图表 reader question；
- 形成可引用的结果段草稿。

### Late

- 停止无边际价值的模型扩张；
- Formal/rerun/freeze；
- 论文压缩；
- build/audit/package/seal。

## 5. 何时停止继续找模型

如果已经满足：

- 主模型稳定优于合理 baseline 或明确解释为什么不需要更复杂模型；
- 关键硬约束/样本外/压力风险已覆盖；
- challenger 不改变主要结论；
- 继续调参的边际收益小于验证和论文收益；

则停止扩展算法。

历史资料中“模型储备多、算法多”只保留为“眼界要宽”；不吸收为“比赛时多用算法”。

## 6. 论文必须从比赛早期同步生长

不是最后集中生成全文。

P1 就建立：

- 问题重述；
- 数学结构；
- 符号/接口；
- 假设草案；
- 章节骨架。

P2/P3 持续填：

- baseline；
- 主模型选择理由；
- 关键公式；
- 主结果；
- 图表 reader question。

P4 后才允许把数字正式冻结进入最终论文。

## 7. 摘要在模型冻结后重写

历史经验指出摘要应体现方法和结果。当前标准进一步要求摘要至少包含：

```text
问题对象
+ 核心方法
+ 最关键定量结果
+ baseline/reference 比较
+ 可信验证
+ 一条主要边界（有必要时）
```

不写：

- “建立了若干模型，结果良好”；
- 算法名堆叠；
- 没有数字的“精度高/鲁棒性好”。

## 8. 模拟赛复盘必须产生“流程改动”，不只写心得

赛后复盘按四类：

### Modeling

- 哪一步选型浪费时间？
- 哪个 baseline 应更早出现？
- 哪个关键约束直到后期才发现？

### Engineering

- 哪个命令最容易出错？
- 是否有手工复制数字？
- 路径/环境/依赖是否脆弱？

### Evidence / Paper

- 哪个 claim 缺证据？
- 哪张图没有回答 reader question？
- 摘要是否能独立回答各问？

### Release

- build/package/audit/seal 花了多久？
- 是否出现匿名性、页数、附件、AI 声明问题？

每类最多提出 1–3 个真实改动，避免模拟赛后无止境重构。

## 9. 低 Token Smoke 与完整模拟赛分开

### Smoke Full-Chain

目的：发现 P0/P1 工程 bug。

- 历史题；
- 简单 baseline；
- 每问只做最小 candidate；
- 只挑一问完整 Formal；
- 粗论文；
- 完整发布链。

### Full Rehearsal

目的：测试真实比赛质量与节奏。

- 严格比赛时间窗口；
- 所有问题完整建模；
- 正式论文；
- 团队协作；
- 赛后复盘。

先 Smoke，再 Full Rehearsal。

## 10. 不吸收的历史经验

不固化：

- 某天必须完成某固定任务；
- 某软件必须掌握；
- “三分建七分写”作为定量规则；
- 多模型/多算法本身作为加分项；
- 统一固定灵敏度扰动比例。

保留的只是：**早闭环、交叉协作、完整模拟、赛后复盘、提前形成论文和提交链。**