---
algorithm_card_id: mechanistic-ode
source_id: github-jingfeizhang-1
source_commit: 8abaef8c9262017925099d1463ebc78c1ab6a956
source_path: "09_机理建模"
entry_points:
  - path: "09_机理建模/01_微分方程模型.py"
    symbol: "solve_logistic"
    kind: function
    purpose: "数值求解带参数的常微分方程状态轨迹"
    input: "时间网格、初值和机理参数"
    output: "状态轨迹和守恒/边界诊断"
    file_sha256: "e17e8d66111b39bd07af2798437af4c70e8eac62d3540bc00d0a30873282ae2a"
    locator_url: "https://github.com/JingfeiZhang/1/blob/8abaef8c9262017925099d1463ebc78c1ab6a956/09_%E6%9C%BA%E7%90%86%E5%BB%BA%E6%A8%A1/01_%E5%BE%AE%E5%88%86%E6%96%B9%E7%A8%8B%E6%A8%A1%E5%9E%8B.py"
skeleton_path: "references/algorithm-sources/skeletons/mechanism/ode_contract.py"
tags: [mechanism, ode, dynamics, calibration, physical-constraints, system-dynamics]
stage_scope: [P1, P2, P3a, P3b]
evidence_status: P1-P3-non-evidence
contest_evidence_eligible: false
allowed_use: [model_direction, assumption_check, baseline_design, risk_probe]
forbidden_use: [formal_evidence, claim_support, figure_contract, submission, release, direct_copy]
language: python
license_status: NO_LICENSE
interface: "states, parameters and differential equations -> trajectories, fitted parameters and scenarios"
baseline_required: [constant-or-linear-baseline, numerical-solver-check]
baseline_options:
  - {id: constant-or-linear-baseline, when: "需要证明机理模型有增益", required: true}
  - {id: numerical-solver-check, when: "所有ODE求解", required: true}
  - {id: limiting-case-check, when: "存在可推导极限情形", required: true}
known_risks: ["固定负荷或外部输入不能误写成决策变量", "初值、边界和终值条件必须来自题面", "量纲错误会被拟合掩盖", "数值稳定不等于机理正确"]
adaptation_required: ["列出状态变量和单位", "检查守恒和边界", "报告参数可辨识性与敏感性", "用简化模型和极限情形回查"]
---

## 适用信号

题面出现增长/衰减、传染、扩散、传热、库存状态、储能状态或其他连续时间机理时使用。若题面只有相关性而没有机理约束，不要强行套 ODE。

## 输入输出

输入包括状态、参数、初始/边界条件、外部输入和时间单位。输出必须包含状态轨迹、参数定义、数值求解设置、守恒和边界检查。

## baseline 与升级

先做常数/线性或离散递推基线，再建立 ODE/系统动力学模型；参数拟合必须与样本外、残差和可辨识性检查一起进行。

## 验证要求

检查量纲、初值、边界、终值、守恒、非负性、极限情形、步长/求解器敏感性和参数扰动。机理解释与拟合效果必须分开报告。

## 已知风险

自由拟合可能掩盖错误机制；固定输入被覆盖、边界条件遗漏或终端状态未核对，会使结果不再回答题面。

## 停止与回退

若参数不可辨识或机理模型不能稳定优于基线，回退到简化机理或数据驱动模型，并明确适用边界。

## 适配步骤

先写状态方程和变量单位，再选求解器、校准方法、基线和守恒诊断；正式数字只来自当前项目运行。

## 来源与边界

参考固定 commit 的 [09_机理建模](https://github.com/JingfeiZhang/1/tree/8abaef8c9262017925099d1463ebc78c1ab6a956/09_%E6%9C%BA%E7%90%86%E5%BB%BA%E6%A8%A1)。源无明确许可证，只读学习；不得执行或直接复制代码。
