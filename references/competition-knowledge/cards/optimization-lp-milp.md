---
card_id: optimization-lp-milp
tags: [optimization, lp, milp, allocation, integer]
source_id: operations-research
source_sha256: AE13246DD5988138AF19FC1644346596D4B159D4E600019C0A6425A862CBD132
pdf_page: 待人工核验
printed_page: 待人工核验
chapter: 线性规划与整数规划
section: 模型建立、对偶与分支定界
locator_confidence: low
visual_verification: pending
formula_manual_check_required: true
---

# 线性规划与混合整数规划

## 适用信号
资源分配、产量组合、选址开关、人员或设备启用，且目标和约束可用变量的线性组合表达。

## 必要前提
统一单位和时间粒度；整数变量对应不可分割决策。收益、容量或需求明显非线性时，先证明线性化合理或换模型。

## 最小建模骨架
令决策变量为 x，优化 c^T x，满足 Ax <= b、Aeq x = beq 和变量上下界；二元变量 z 表示启用或逻辑条件。Big-M 必须由业务上界推导。

## 算法/代码入口
Python 可用 `scipy.optimize.linprog`，整数问题用 OR-Tools、HiGHS 或 Pyomo（以环境实际安装为准）；MATLAB 用 `linprog`、`intlinprog`。先求 LP 松弛检查可行性和界。

## 同输出 baseline
按容量比例分配、最近可行分配或贪心排序；输出相同的分配或排程对象，并用同一目标和约束审计。

## 验证与敏感性
报告目标值、最大约束违反量、整数性、资源守恒和 LP 松弛差距；扰动需求、容量、Big-M 和成本。

## 停止条件
若精确模型已在预算内给出稳定可行解，不引入启发式；若 MILP 无可行解，先缩紧 Big-M、修正尺度或定位冲突。

## 误用风险
Big-M 过大；把软偏好写成硬约束；忽略不可行状态；将 LP 解四舍五入后当作整数最优。

## 原书回退定位
回看 `operations-research` 中线性规划、整数规划、对偶与敏感性、分支定界章节；页码未完成视觉核验，公式使用前必须复核 PDF。

## 决策判断
采用条件：变量之间的增益、资源消耗和逻辑关系在题目精度下可近似为线性，且整数/二元决策确实对应不可分割动作。先解 LP 松弛；若松弛解有明显分数变量或逻辑条件，升级为 MILP。排除条件：乘积、比值或阈值效应是结论核心且无法可靠线性化；或 Big-M 只能凭经验取值。此时分别尝试 NLP、分段线性化或枚举小规模结构。

## 关键量与诊断
最少记录目标值、每类约束最大违反量、变量上下界命中率、整数间隙 `(z_MILP-z_LP)/|z_MILP|`、求解状态和运行时间。若状态为 infeasible，按约束组逐步放松定位冲突；若 gap 长时间不降，检查 Big-M、变量尺度和对称性。Big-M 应由可行域上界推导，例如若 `x<=U z`，则 `M=U` 而非任意大数。

## 赛中最小试验
取 10% 规模数据，运行 LP 松弛、MILP 和贪心 baseline 三个版本；核对同一输出、同一目标和硬约束。再将一个容量或需求扰动 ±10%，观察可行性和解结构是否突变。若 LP 已整数且 MILP 无额外收益，保留 LP；若 MILP 超时，记录当前可行解、gap 和可解释的降阶 fallback。
