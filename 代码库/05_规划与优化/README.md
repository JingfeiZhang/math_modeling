# 05 规划与优化

> 本目录用于学习把现实决策转成目标、变量和约束。优化题的质量首先取决于**模型语义和可行性**，其次才是求解算法。

## 文件地图

| 文件 | 方法 |
|---|---|
| `01_线性规划LP.py` | LP |
| `02_整数规划与0-1规划.py` | MILP / binary |
| `03_非线性规划NLP.py` | NLP |
| `04_多目标规划.py` | weighted / epsilon / compromise |
| `05_动态规划DP.py` | DP |
| `06_蒙特卡洛模拟.py` | simulation / uncertainty probe |

## 建模顺序

```text
决策变量与单位
→ 目标函数
→ 硬约束/软约束
→ 时间/资源/逻辑关系
→ 简单 rule/greedy baseline
→ 选择最简单可表达该结构的求解模型
```

## 默认算法梯子

```text
rule / greedy
→ LP
→ MILP / QP
→ NLP / network / DP
→ decomposition
→ 只有结构或规模确实需要时才使用 metaheuristic
```

能精确建模和求解时，不因为“智能算法更高级”优先使用 GA/PSO/SA。

## 必查正确性

- 每个题面约束是否有数学和程序定位；
- 变量类型、上下界和单位是否正确；
- 求解后逐项回查约束；
- 报告 solver status；
- MILP/精确求解报告 gap（可取得时）；
- 非凸/启发式问题用小规模精确解、松弛下界或其他 reference 判断解的质量。

## 多目标

一个固定加权解只是“给定偏好下方案”，不是完整 Pareto 前沿。若论文讨论权衡，应通过权重 sweep、epsilon-constraint 或非支配搜索得到多个不同方案，并说明覆盖范围。

## 不确定性

Monte Carlo 是场景评估工具，不自动等于 robust/stochastic optimization。若不确定参数影响决策，应区分：

- 方案固定后的风险评估；
- 场景优化；
- robust/stochastic 决策模型。

## 高价值实验

优先：可行性、baseline、gap/小实例、压力场景、关键参数敏感性。收敛曲线通常是辅助证据，不应压过最终资源配置、调度或 Pareto 权衡本身。

## 论文证据

主结果优先展示最优/推荐方案、资源利用、瓶颈、成本—服务权衡和 failure scenario；算法迭代过程只有在确实说明求解质量时才进入正文。

## 停止规则

若复杂求解器只带来微小改善、无法稳定复现或无法解释其代价，优先保留更简单且可验证的方案。
