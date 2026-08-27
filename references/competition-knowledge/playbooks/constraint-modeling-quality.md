---
playbook_id: constraint-modeling-quality
playbook_version: 1
tags: [optimization, constraints, milp, scheduling, formulation, uncertainty, feasibility]
modules: [optimization-lp-milp, optimization-network-scheduling, optimization-uncertainty-planning]
stage_scope: [P1, P2, P3a, P3b]
evidence_status: P1-P3-non-evidence
contest_evidence_eligible: false
allowed_use: [model_direction, assumption_check, baseline_design, risk_probe]
forbidden_use: [academic_citation, formal_evidence, claim_support, figure_contract, submission]
---

# 自然语言约束 → 数学规划：约束建模质量手册

> 来源基础：《数学建模竞赛中的优化模型》中“决策变量和参数—约束—目标函数”的建模骨架，以及 CUMCM-2024C 讲解中“多类型资源/季次/兼容/跨期规则 → 确定性规划 → 不确定性 → 关联结构”的可迁移模式。历史题具体解法和软件操作不作为规则。

## 触发与排除

**触发**：资源分配、种植/生产计划、排程、选址、库存、路径/网络设计等题面中存在大量自然语言规则，尤其包含多索引、整数/0-1、跨期、兼容、轮换、服务水平或不确定参数。

**排除**：题目只需简单闭式计算、单变量无约束优化或纯描述统计；此时不应为了“规划模型”强行引入整数变量或复杂求解器。

首要原则：

```text
先定义数学对象
→ 再建约束
→ 再决定求解器
```

而不是先选 MILP/GA，再把题目塞进去。

## 输入输出合同

### 输入

至少建立：

```text
Sets / Index
Parameters
Decision variables
Derived variables
Objective(s)
Hard constraints
Soft preferences
Uncertainty
```

每个决策变量必须声明：含义、单位、索引、变量域；每个参数必须声明来源、单位、是否确定/随机。

### Constraint Inventory

先给每条题面规则编号：

```text
C01 容量
C02 兼容性
C03 时间/季次
C04 互斥/联动
C05 最低服务/覆盖
C06 轮换/间隔
C07 数量/整数性
C08 风险/情景
...
```

每条至少记录：题面原意、索引范围、数学表达、代码位置、最小测试实例、是否允许 slack。

### 输出

输出不能只有目标值，至少应包含：

- 可执行决策方案；
- 目标分解；
- 关键约束余量/绑定情况；
- 可行性审计；
- 必要的不确定性/压力场景结果。

## 分阶段行动

### P1

1. 从题面抽取 sets / parameters / decisions / outputs。
2. 建 Constraint Inventory。
3. 区分 hard constraint 与 soft preference。
4. 检查变量域：连续、整数、0-1、非负。
5. 设计一个人工可算/枚举的小实例。

对“多地块 × 多作物 × 多年份 × 多季次”等结构优先用索引变量，而不是复制粘贴大量约束。

### P2

建立同输出 baseline：当前方案、greedy、每期独立、简单 LP 或确定性规则之一。

在小实例上验证：

- 目标方向；
- 约束是否写反；
- 变量域；
- 总量/单位；
- 输出解释。

### P3a

建立最窄主模型，只加入题目确实需要的结构：

- 容量；
- 兼容；
- 时间/季次；
- 轮换/间隔；
- 逻辑；
- 服务水平。

求解后独立重算约束，不把 `solver success` 当作业务可行证明。

### P3b

只有确定性模型在合理扰动下出现不可行、收益显著下降、服务水平失控或推荐方案频繁改变时，才升级：

```text
确定性模型
→ 场景/区间压力测试
→ 必要时 robust / stochastic
→ 必要时加入参数关联/耦合
```

## baseline 与升级

推荐梯子：

```text
当前/规则方案
→ 简单确定性 LP/MILP
→ 完整结构主模型
→ 情景压力测试
→ 有证据时才做 robust/stochastic
```

复杂度升级必须回答：

1. baseline 因哪条真实结构失败？
2. 新约束/耦合具体修复什么？
3. 方案改善多少？
4. 计算/解释代价是什么？

预测值进入优化时必须记住：

```text
forecast ≠ known constant
```

若上游预测误差会改变方案，至少做场景传播或敏感性。

## 联合诊断

### 1. 约束完整性

逐类检查：容量、兼容、时间、逻辑、服务、风险、变量域。

### 2. 可行性审计

正式候选至少回查：

```text
constraint_id
max_violation
n_violations
worst_index
status
```

同时重算目标值、整数性、上下界、守恒/总量。

### 3. Big-M / 逻辑约束

Big-M 必须有可解释上界、尽量紧，并检查 LP relaxation 是否过松。能用允许集合或直接变量固定表达时，不优先 Big-M。

### 4. 跨期约束

“连续”“至少每 N 年一次”“不能连续”“先后关系”等必须在模型中直接耦合时间索引，不能靠求解后人工修补。

### 5. 不确定性

优先扰动最可能改变决策的参数，如 demand / yield / price / cost / capacity。不要机械所有参数统一 ±5% / ±10%。

需要观察：方案是否改变、可行率、目标/服务水平、哪个约束首先绑定、failure threshold。

### 6. 参数关联

相关关系只有在能进入参数生成、情景或约束并改变最终方案时才值得保留；样本相关不自动成为因果机制。

## 停止与回退

满足以下条件即可停止升级：

- 关键题面约束均已映射；
- 小实例正确；
- 主模型可行；
- 相对 baseline 有明确价值或简单模型已足够；
- 关键扰动不改变主要结论，或失败边界已明确；
- 更复杂模型只带来微小/不稳定收益。

回退：

- 整数模型复杂但整数性无价值 → LP/规则模型；
- robust/stochastic 不改变方案 → 保留确定性主模型 + 场景说明；
- 关联结构证据弱 → 删除关联项，保留独立场景；
- metaheuristic 无 exact/bound 支撑 → 回到可解释精确/近似模型或缩小 claim。

## Candidate 交接

Candidate 至少交接：

- sets / parameters / decision-variable ledger；
- objective 定义与题面对应；
- Constraint Inventory；
- baseline 与主模型方案；
- known-answer / 小实例结果；
- solver status；
- 独立 feasibility audit；
- 关键参数压力测试；
- 当前允许的最优性措辞；
- failure boundary。

历史 CUMCM-2024C 只用于说明“多类型资源 + 多季次 + 兼容 + 跨期 → 确定性 → 不确定性”的结构，不携带具体作物、地块或历史解。

## 禁止事项

- 不因“MILP 看起来高级”无意义增加二进制变量；
- 不在求解后人工修补本应进入模型的硬约束；
- 不把 solver `success` 等同业务可行；
- 不把一次启发式最好结果写成全局最优；
- 不把固定权重单解写成完整 Pareto 前沿；
- 不机械统一 ±5% / ±10% 灵敏度；
- 不引用本手册或历史培训资料作为 Formal/论文证据。