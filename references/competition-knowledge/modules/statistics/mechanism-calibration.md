---
module_id: statistics-mechanism-calibration
module_version: 1
family: statistics
tags: [mechanism, calibration, ode, identifiability, conservation, uncertainty]
source_cards: [mechanism-ode, mechanism-pde, statistics-uncertainty, statistics-regression]
stage_scope: [P1, P2, P3a, P3b]
evidence_status: P1-P3-non-evidence
contest_evidence_eligible: false
allowed_use: [model_direction, assumption_check, baseline_design, risk_probe]
forbidden_use: [academic_citation, formal_evidence, claim_support, figure_contract, submission]
---

# 机理模型参数标定决策模块

> 用于判断“已有机理方程 + 观测数据”是否值得标定参数。它帮助建立最小可运行模型、识别不可辨识和数值失败，不替代 Formal 复跑或论文证据。

## 用途与排除

适用于题面给出守恒、动力学、扩散/传热、反应、人口或库存机理，要求估计参数、解释机制、预测未观测状态或比较情景的 Qx。可覆盖 ODE、低维 PDE 降阶和带观测误差的状态空间模型。

排除或降阶：

- 只有相关数据、没有可辩护的状态变量和过程方程；先做经验回归或时间序列。
- 观测点太少而待估参数太多，或参数只以乘积形式进入方程；先做可辨识性探针。
- 边界/初值/单位不清，守恒量无法核验；不得直接拟合。
- PDE 网格、边界条件和计算时间无法在比赛窗口内稳定控制；优先降维、稳态或代理模型。

## 题面句子到数据/变量/约束映射

| 题面信号 | 状态/观测 | 参数与约束 | 首要风险 |
|---|---|---|---|
| “随时间演化/增长衰减” | 状态 `z(t)`、观测 `y(t)` | 速率、容量、初值 | 时间单位、初值误差、刚性 |
| “守恒/质量平衡/能量平衡” | 流入、流出、储量 | 非负、守恒方程 | 单位不一致、漏项 |
| “扩散/传热/空间分布” | `z(x,t)`、边界观测 | 扩散率、边界通量 | 网格收敛、边界条件 |
| “由实验数据反推参数” | 多时点/多条件观测 | `theta` 物理范围 | 可辨识性、噪声和局部极小 |
| “改变控制量后预测” | 状态+输入 `u(t)` | 控制边界、情景范围 | 训练范围外外推 |

先画状态—参数—观测图，列出每个参数的单位、符号、允许范围、可观测状态和初始条件来源。

## 最小可运行模型

对 ODE：

\[
\dot z=f(t,z,u;\theta),\qquad y_k=h(z(t_k),u_k;\theta)+\epsilon_k.
\]

先固定或粗略给定初值，使用有界最小二乘：

\[
\min_{\theta\in[\ell,u]}\sum_k w_k\,r_k(\theta)^2,
\quad r_k=y_k-h(z_\theta(t_k)).
\]

若观测量纲不同，用物理量纲明确的标准化或测量误差权重 `w_k`；不要无说明地把每个变量缩放为 z-score。先用确定性 RK45/刚性探针求解，再考虑更复杂的滤波或贝叶斯标定。

## baseline 到主模型升级路径

```text
观测均值/最后值/经验回归 baseline
  -> 固定参数的机理仿真
  -> 单条件、有界最小二乘标定
  -> 多条件联合标定（共享参数 + 条件特异初值）
  -> 误差模型、稳健损失或状态空间扩展
  -> PDE/高维模型（仅在网格和边界证据充分时）
```

升级必须同时满足：机理仿真比 baseline 有额外解释价值；参数在合理范围内；多初值/多条件结果相近；残差、守恒和数值误差都可接受。只降低训练残差不能证明机理模型正确。

## 三项关键诊断与可观测门槛

1. **参数可辨识性**：记录不同初值、参数扰动和多条件拟合结果。若多个参数组合给出近乎相同目标值、轮廓似然平坦或参数相关性极高，合并参数、固定弱可辨识参数或降低结论强度；不报告唯一参数解释。
2. **残差与守恒**：报告观测残差的量纲、相对误差、分时段/分状态分布，并计算守恒残差或边界通量误差。若守恒误差与观测噪声同量级以上、残差有明显趋势，先修正方程/边界/单位，再谈标定。
3. **数值收敛与外推**：逐步收紧 ODE 容差或 PDE 网格，比较参数和关键输出变化；同时做未参与标定时段/情景验证。若减半步长或加密网格导致关键输出变化超过业务容许误差，或外推情景远离训练范围，则回退到低阶/代理模型并限制边界。

## 失败回退树

```text
方程、单位、初值或边界不闭合
  -> 建立量纲表和守恒账，补齐可观测输入
  -> 仍不闭合：退回经验模型，不做机理参数结论

优化不收敛/多初值差异大
  -> 参数重标度、合理边界、对数参数化、减少自由参数
  -> 仍失败：固定弱参数，使用单条件或局部线性近似

拟合好但参数不可辨识
  -> 增加条件/观测组合或报告参数组合而非单参数
  -> 无法增加信息：只交接可预测状态和情景差异

守恒误差或数值误差过大
  -> 修复单位/边界、提高求解器稳定性或网格
  -> 仍过慢：降阶、稳态化或代理模型

训练情景好、未见情景失败
  -> 收窄情景范围，做敏感性与边界说明
  -> 仍无法外推：主模型只用于解释已观测区间
```

## 赛中最小实验序列

1. 建立变量、单位、守恒和输入输出清单；用固定参数或文献量级跑一次正向仿真。
2. 用最后值/均值/经验回归生成同输出 baseline，固定同一观测切分和误差指标。
3. 只标定 1–3 个最有信息量参数，使用有界多初值优化；记录目标值、参数边界命中和运行时间。
4. 做一次参数扰动/轮廓探针和一次容差或网格减半试验；检查残差、守恒和关键输出稳定性。
5. 若通过，再加入第二个观测条件或未见时间段；否则按失败树降阶并停止增加参数。
6. 记录采用、固定、合并和放弃的参数及理由，形成候选决策而非正式 claim。

## 必须记录的字段

`state_variables`、`observed_variables`、`inputs`、`parameters`、`parameter_units`、`parameter_bounds`、`initial_conditions`、`boundary_conditions`、`equations_hash`、`solver`、`tolerances_or_grid`、`objective`、`weights`、`start_points`、`converged_runs`、`boundary_hits`、`residual_by_observable`、`conservation_residual`、`identifiability_probe`、`unseen_condition_metrics`、`runtime_seconds`、`rejected_parameters`、`fallback_reason`。

## 论文交接边界

可交接：方程和变量定义、单位/边界假设、参数标定方法、baseline 对照、Formal 冻结的参数区间和验证结果、适用边界。不可交接：教材卡的经验门槛、未复核页码、未确定性复跑的参数或他人数字。正式机理结论必须由 Formal 或合格 Paper Evidence 支撑，并保留方程、输入、代码、环境和输出哈希。

## 原书回退定位

优先回看 ode、pde 的初值问题、方程组、边界条件和数值解章节，并以 statistics-uncertainty 卡辅助不确定性探针。本模块仅提供章节级回退方向；原书公式、示例参数和图表必须人工对照后再用于建模。
