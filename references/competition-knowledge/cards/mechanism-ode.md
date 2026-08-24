---
card_id: mechanism-ode
tags: [mechanism, ode, continuous-time, compartment, calibration]
source_id: ode
source_sha256: 0C47A6E1130FFFFB2AAF3063156E1BB9F063A7E0C6C8445C7C53D1E193DEF4F9
pdf_page: 待人工核验
printed_page: 待人工核验
chapter: 常微分方程
section: 初值问题、系统与参数估计
locator_confidence: low
visual_verification: pending
formula_manual_check_required: true
---

# 常微分方程

## 适用信号
连续变化由速率、守恒、反馈或 compartment 机理决定

## 必要前提
状态、参数、初值和单位一致，说明可辨识性和边界

## 最小建模骨架
建立 y'=f(t,y;theta)，由机理写状态方程并计算观测量

## 算法/代码入口
scipy solve_ivp 或 MATLAB ode45/ode15s；拟合用最小二乘/似然

## 同输出 baseline
线性趋势、指数/Logistic 简化或持久性预测

## 验证与敏感性
步长/容差收敛、留出时间、参数扰动和守恒检查

## 停止条件
不可辨识或机制不可验证时降阶并限定区间

## 误用风险
单位错配、过多参数拟合噪声、刚性求解器错误

## 原书回退定位
回看 ordinary-differential-equations 的初值问题、方程组、稳定性和数值解章节。当前页码仅作章节级定位，精确页码和公式使用前必须人工对照 PDF。

## 决策判断
当题面给出速率、守恒、反馈或 compartment 关系，且状态随时间连续变化时优先 ODE；若只有离散观测而没有机理约束，先用时间序列/回归作为基线。参数数量必须能由观测识别：先做参数-输出敏感性或 profile 探针，无法区分的参数应合并、固定或只报告组合量。

## 关键量与诊断
模型写作 $\dot y=f(t,y;\theta)$，参数拟合可用加权残差 $\min_\theta\sum_i w_i\lVert y(t_i;\theta)-y_i\rVert^2$，权重必须对应观测误差尺度。记录求解器退出状态、最大守恒误差、步长/容差收敛、留出时间误差、参数相关性和状态边界违反量；出现刚性迹象时比较显式与刚性求解器，而不是盲目减小步长。

## 赛中最小试验
用线性趋势或 Logistic/持久性模型做同输出基线；候选 ODE 只拟合训练时间段，用末段留出验证。分别把相对容差收紧 10 倍、把初值扰动到观测误差范围，并固定一组参数起点；若参数估计随起点大幅变化而预测不改善，停止增加机制参数。
