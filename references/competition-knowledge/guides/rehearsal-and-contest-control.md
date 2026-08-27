# 模拟赛与比赛过程控制指南

> 定位：P0–P6 的赛前演练与比赛节奏参考，不属于 reference-library 的 P1–P3 playbook 层，不新增 Gate、不规定死板小时表。
>
> 来源基础：《数学建模竞赛注意事项与经验分享》《全国大学生数学建模竞赛参赛准备》中关于模型储备、团队交叉能力、模拟赛、论文写作和过程控制的经验，经当前工作流 progress-first / evidence-first 原则筛选。

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

历史经验中最值得保留的是：按真实比赛节奏完成完整论文，并在赛后分析优缺点。当前工作流进一步将其转化为可量化的工程演练。

## 2. 过程指标

每次 rehearsal 记录：

| 指标 | 含义 |
|---|---|
| time_to_problem_map | 从拿题到 Q1–Qn 和接口明确 |
| time_to_first_baseline | 第一条可运行同输出 baseline |
| time_to_first_main_result | 第一版主模型结果 |
| time_to_first_formal | 第一问可晋升 Formal |
| time_to_paper_skeleton | 章节/图表位置可编译 |
| time_to_first_full_pdf | 第一份完整 PDF |
| time_to_release_audit | 第一次完整发布审计 |
| manual_rework_count | 因路径/格式/手工复制造成的返工 |
| evidence_gap_count | 论文 claim 缺 evidence 数量 |

不要只记录最终模型指标。

## 3. 团队职责应交叉

历史经验强调：写作者必须真正理解模型；建模、代码、写作完全割裂会导致模型意图和论文表述不一致。

推荐能力覆盖：

```text
成员 A：论文 + 建模
成员 B：建模 + 代码
成员 C：代码 + 论文
```

这不是固定角色，而是避免任何关键环节只有一个人会。

对应工作流要求：

- Paper 只消费 Formal/frozen evidence，不自行补模型逻辑；
- 关键模型说明由建模者复核；
- 核心表/图由第二人核对单位、场景和 run_id；
- submission operator 之外至少一人能完成 package/verify。

## 4. 比赛节奏：尽早闭环

历史经验常用“第一天框架、第二天求解、第三天修改”表达节奏。当前工作流不固化具体天数，只保留原则：

```text
尽早形成第一条端到端闭环
→ 再提高模型质量
→ 再冻结
→ 最后集中压缩和发布
```

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

满足以下大部分条件时停止扩展算法：

- 主模型稳定优于合理 baseline，或已证明简单模型足够；
- 硬约束/样本外/压力风险已覆盖；
- challenger 不改变主要结论；
- 继续调参的边际收益小于验证、解释和论文收益。

“模型储备多”只保留为眼界要宽，不转化成“比赛时多用算法”。

## 6. 论文必须同步生长

P1：

- 问题重述；
- 数学结构；
- 符号/接口；
- 假设草案；
- 章节骨架。

P2/P3：

- baseline；
- 主模型选择理由；
- 关键公式；
- 主结果；
- 图表 reader question。

P4 后才允许正式冻结数字进入最终论文。

## 7. 摘要在模型冻结后重写

摘要至少包含：

```text
问题对象
+ 核心方法
+ 最关键定量结果
+ baseline/reference 比较
+ 可信验证
+ 主要边界（必要时）
```

避免算法名堆叠和“结果良好”式空话。

## 8. 复盘必须产生少量真实流程改动

### Modeling

- 哪一步选型浪费时间？
- 哪个 baseline 应更早出现？
- 哪个关键约束发现太晚？

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

每类只保留 1–3 个最高收益改动，避免模拟赛后无止境重构。

## 9. Smoke 与 Full Rehearsal 分开

### Smoke Full-Chain

目的：发现 P0/P1 工程 bug。

- 历史题；
- 简单 baseline；
- 每问最小 candidate；
- 只挑一问完整 Formal；
- 粗论文；
- 完整发布链。

### Full Rehearsal

目的：测试真实比赛质量与节奏。

- 严格比赛时间窗口；
- 全问题完整建模；
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
