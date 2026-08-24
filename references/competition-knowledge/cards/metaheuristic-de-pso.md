---
card_id: metaheuristic-de-pso
tags: [optimization, metaheuristic, differential-evolution, pso, continuous]
source_id: operations-algorithms
source_sha256: FDB62419200DAA506578167E70E72BDFC38AFC20780EC412EB2D41B97E8FF63C
pdf_page: 待人工核验
printed_page: 待人工核验
chapter: 群体智能优化
section: 差分进化与粒子群
locator_confidence: low
visual_verification: pending
formula_manual_check_required: true
---

# 群体智能优化

## 适用信号
连续黑箱参数优化且变量边界明确

## 必要前提
给出边界、尺度和约束处理，离散变量须有舍入规则

## 最小建模骨架
DE用差分试探向量择优；PSO用位置速度和个体/群体历史更新

## 算法/代码入口
固定种群、评估预算和 DE/PSO 参数，记录每代最优

## 同输出 baseline
网格、随机采样加局部改进或坐标下降

## 验证与敏感性
多种子比较分位数，改变边界、种群和预算检查早熟

## 停止条件
低维平滑目标优先梯度或确定性局部法

## 误用风险
尺度差异、巨大惩罚、高维小预算却宣称全局

## 原书回退定位
回看 operations-research-algorithms 的差分进化和粒子群章节。当前页码仅作章节级定位，精确页码和公式使用前必须人工对照 PDF。

## 决策判断
采用条件：变量主要连续、有明确上下界且评价函数可黑箱调用；DE 适合差分尺度有意义的连续向量，PSO 适合变量相关性较弱、希望快速寻找区域的情形。排除条件：强离散排列结构、不可修复的组合约束或变量尺度差异几个数量级而未标准化。

## 关键量与诊断
记录每代全局最好值、种群半径/方差、越界修复比例、有效评估数和多种子分位数。DE 重点监控差分因子与交叉率，PSO 重点监控惯性/收缩系数和速度上限；种群半径过快归零通常是早熟信号。

## 赛中最小试验
先把变量缩放到 `[0,1]`，用相同评估预算比较 DE、PSO 与随机采样+局部改进。对 5 个种子记录中位数和最差值，再将预算加倍看是否仍改善；若边界修复比例超过 30% 或离散化改变可行性，退回结构化算法。
