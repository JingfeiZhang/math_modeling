---
card_id: metaheuristic-selection
tags: [optimization, metaheuristic, black-box, combinatorial]
source_id: operations-algorithms
source_sha256: FDB62419200DAA506578167E70E72BDFC38AFC20780EC412EB2D41B97E8FF63C
pdf_page: 待人工核验
printed_page: 待人工核验
chapter: 启发式与元启发式
section: 方法选择与比较
locator_confidence: low
visual_verification: pending
formula_manual_check_required: true
---

# 启发式与元启发式

## 适用信号
目标不可微、组合空间大或精确模型超时

## 必要前提
先定义编码、评价、约束修复并保留精确或贪心基线

## 最小建模骨架
解 s、目标 f(s) 与约束违反惩罚组成统一评价

## 算法/代码入口
按结构选择 GA、DE/PSO、ACO、SA 或禁忌搜索，固定种子和预算

## 同输出 baseline
贪心、局部搜索或 LP/MILP 松弛，输出同一决策对象

## 验证与敏感性
多种子报告最优、均值、离散度和可行率，改变预算与惩罚权重

## 停止条件
精确模型可在预算内稳定求解时不引入元启发式

## 误用风险
一次最好结果、惩罚掩盖不可行和不同输出比较

## 原书回退定位
回看 operations-research-algorithms 的启发式、局部搜索和算法比较章节。当前页码仅作章节级定位，精确页码和公式使用前必须人工对照 PDF。

## 决策判断
采用条件：精确 LP/MILP/NLP 在比赛规模和时间内无法稳定给出可行解，且解空间有可编码结构；元启发式必须作为有预算的近似搜索，而不是“高级模型”标签。排除条件：小规模精确模型可解、目标可微且局部法稳定，或没有可比 baseline 和可行性修复规则。

## 关键量与诊断
固定总函数评估预算，报告多种子下最好值、中位数、四分位距、可行率、首次可行时间和相对 baseline 改善。另记录惩罚项占目标比例和重复解比例；若只提升惩罚后的代理目标，不能宣称原目标改善。

## 赛中最小试验
在 10% 规模上用贪心、局部搜索和一个结构匹配的元启发式做同预算比较，至少 5 个种子。若元启发式没有稳定超过 baseline，保留 baseline；若超过但方差大，增加重启或收紧编码，仍不写全局最优。
