---
algorithm_card_id: optimization-programming
source_id: github-jingfeizhang-1
source_commit: 8abaef8c9262017925099d1463ebc78c1ab6a956
source_path: "05_规划与优化"
entry_points:
  - path: "05_规划与优化/04_多目标规划.py"
    symbol: "epsilon_constraint"
    kind: function
    purpose: "将一个目标优化并用其余目标作 epsilon 约束"
    input: "目标函数、主目标索引、epsilon、变量边界和约束"
    output: "单个 epsilon 场景的优化结果"
    file_sha256: "4398cb2820fe77bd43292e2f7ac088b911385043f46b5fd6be0e671bdee5a10a"
    locator_url: "https://github.com/JingfeiZhang/1/blob/8abaef8c9262017925099d1463ebc78c1ab6a956/05_%E8%A7%84%E5%88%92%E4%B8%8E%E4%BC%98%E5%8C%96/04_%E5%A4%9A%E7%9B%AE%E6%A0%87%E8%A7%84%E5%88%92.py"
skeleton_path: "references/algorithm-sources/skeletons/optimization/multiobjective_contract.py"
tags: [optimization, lp, milp, nonlinear, dynamic-programming, multiobjective]
stage_scope: [P1, P2, P3a, P3b]
evidence_status: P1-P3-non-evidence
contest_evidence_eligible: false
allowed_use: [model_direction, assumption_check, baseline_design, risk_probe]
forbidden_use: [formal_evidence, claim_support, figure_contract, submission, release, direct_copy]
language: python
license_status: NO_LICENSE
interface: "objective + variables + constraints -> solver result and feasibility status"
baseline_required: [greedy-or-rule, small-instance-exact]
baseline_options:
  - {id: greedy-or-rule, when: "全规模快速可行方案", required: true}
  - {id: small-instance-exact, when: "存在可枚举或小规模精确实例", required: true}
  - {id: epsilon-constraint, when: "题面要求多目标权衡", required: true}
known_risks: ["SLSQP 局部搜索不证明全局最优", "示例尺度不能直接沿用", "单一固定权重不能宣称 Pareto", "缺少 solver status 时无法解释失败"]
adaptation_required: ["变量角色账本", "硬约束逐项回查", "小规模精确实例", "目标方向和单位合同", "gap 或枚举覆盖"]
---

## 适用信号

题面要求资源分配、选址、排程、路径、库存、容量或多目标决策时优先查看。能写成 LP/MILP/DP 的问题，不应先使用群智能算法。

## 输入输出

输入必须明确决策变量、固定输入、派生量、目标方向、单位和所有硬约束。输出不仅是目标值，还要有变量方案、约束余量、求解状态和必要的 gap。

## baseline 与升级

先跑贪心/规则 baseline 和小规模精确实例，再从 LP 升级到 MILP、NLP、DP 或 epsilon-constraint。多目标必须报告权重、epsilon 或多个非支配方案。

## 验证要求

逐项检查容量、守恒、整数性、边界、时间窗和互斥约束；用人工可算或穷举小实例验证；记录 solver status、optimality gap、可行率或覆盖范围。

## 已知风险

单一局部解不等于全局最优，固定权重不等于完整 Pareto，示例中的手工归一化尺度不能当作题目参数。

## 停止与回退

若精确模型已经在题目规模内稳定求解，停止引入启发式。若模型不可行，先定位冲突约束，不要用惩罚函数掩盖错误。

## 适配步骤

先建立变量账本和约束清单，再重写目标函数和数据接口；对整数/二元变量选择匹配求解器；保存可行性报告、状态和小实例对照结果。

## 来源与边界

参考 [05_规划与优化](https://github.com/JingfeiZhang/1/tree/8abaef8c9262017925099d1463ebc78c1ab6a956/05_%E8%A7%84%E5%88%92%E4%B8%8E%E4%BC%98%E5%8C%96)。该源无明确许可证，只读学习，不直接复制或再发布。
