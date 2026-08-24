---
card_id: numerical-root-linear
tags: [numerical, root-finding, linear-system, conditioning, convergence]
source_id: numerical-methods
source_sha256: FC04602C520994954F3FCCC31B4899C27DA6B43C4D99D4265462EBD2A826A8F8
pdf_page: 待人工核验
printed_page: 待人工核验
chapter: 方程求根与线性方程组
section: 迭代、消元与条件数
locator_confidence: low
visual_verification: pending
formula_manual_check_required: true
---

# 方程求根与线性方程组

## 适用信号
需解非线性方程或参数化线性系统

## 必要前提
根区间/初值、可逆性、尺度和条件数可检查

## 最小建模骨架
标量根先括区间；Ax=b 用稳定分解，停止同时看残差和步长

## 决策判断
- 单变量连续方程且可找到异号端点时，二分/Brent 类括根法是首选基线；牛顿法只在导数可靠、初值位于目标根吸引域且可回退到括根时作为加速方案。
- 多根、切根或不连续点会使符号变化和牛顿收敛都失效；必须先画函数或扫描残差，报告找到的是哪一支解及其初值/区间。
- 线性系统先判断是方阵精确解、超定拟合还是欠定选择问题。超定系统使用最小二乘，欠定系统必须声明最小范数或其他选择准则；不能把通用求逆当作默认算法。
- 条件数很大、变量尺度跨数量级或微小扰动改变结论时，应缩放、改用 QR/SVD 或正则化，并把解解释限制为稳定的聚合量。

## 关键量与诊断
对根 \(x^*\)，同时记录方程残差 \(|f(x^*)|\)、相邻迭代差和初始区间/初值；只有三者与问题量纲相容才可停止。对 \(Ax=b\)，报告相对残差 \(\lVert Ax-b\rVert/(\lVert A\rVert\lVert x\rVert+\lVert b\rVert)\)、条件数估计、缩放方式及微扰后的解变化。残差很小但条件数高不等于分量可信，应区分“方程拟合好”与“参数可识别”。

## 赛中最小试验
根问题先用网格扫描定位可行区间，以二分法作为同输出 baseline，再从多个初值比较加速方法的收敛根、迭代次数和失败率。线性系统以稳定直接分解为 baseline，向 \(A\) 或 \(b\) 施加与测量精度相当的小扰动；若关键决策翻转，停止报告精确分量，改报告区间、正则化结果或稳定聚合指标。

## 算法/代码入口
scipy.optimize/root、numpy.linalg.solve 或 MATLAB fzero/linsolve

## 同输出 baseline
二分法或直接求解器，输出同一根/解向量和残差

## 验证与敏感性
改变初值、容差和扰动，报告条件数、迭代和失败率

## 停止条件
不收敛、病态或多根未区分时回退括区间/正则化

## 误用风险
牛顿无括区间、显式求逆、只看步长

## 原书回退定位
回看 numerical-methods 的非线性方程、线性方程组和误差分析章节。当前页码仅作章节级定位，精确页码和公式使用前必须人工对照 PDF。
