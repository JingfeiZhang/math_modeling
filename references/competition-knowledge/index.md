# 国赛教材资料速查库

这是数学建模竞赛 P1-P3 的共享、只读**三级决策资料库**。它不是教材摘要，而是把教材知识组织成快速路由、可执行模型决策和跨模块战术路径；它不是学术文献、竞赛论文语料或 Formal 证据。

```text
全局 Guides：统一质量、数据、算法、实验与可视化原则
  ↓
L1 路由卡：30 秒筛出 3-5 个方向
  ↓
L2 决策模块：完成变量映射、baseline、一次升级、关键诊断和回退
  ↓
L3 Playbook：仅在存在跨模块结构时串联专项路径
```

## 使用规则

1. 先读取与当前角色相关的全局 Guide，再按任务、数据特征和约束检索 L1，最多保留 3-5 张卡；不要按书名通读。
2. 选一个最匹配的 L2 模块执行 P2/P3：写变量账本，跑最窄 baseline，只做一次有诊断依据的升级，再决定保留、降阶或回退。
3. 只有题目存在“预测→优化”“分配→不确定性”“机理→标定→情景”“规则密集跨期规划”“数据→响应→决策”等跨模块结构时，才进入一个最匹配的 L3 Playbook。
4. 卡片、模块和 L3 Playbook 只支撑候选模型、假设检查、baseline 设计和风险探针；数值结果必须来自本项目 Scratch/Candidate/Formal 运行。
5. `locator_confidence: low` 或 `formula_manual_check_required: true` 时，回看本机 PDF 对应页后再写公式或页码。
6. P4 以后不把教材速查层自动升级为模型知识来源，不把任何资料项写入论文 BibTeX、claims、Figure Contract 或附件；跨阶段 Guides 只能作为内容审阅/演练参考。
7. 原始 PDF 不在仓库中。配置 `MATHMODEL_REFERENCE_LIBRARY_ROOT` 或维护 `work/reference-library/sources.local.yaml` 后可运行本地校验；未配置时仍可检索 Markdown 索引。
8. 培训/赛题讲解材料只经过选择性提炼进入专项 Playbook 或 Guide；它们不是官方规则、不是标准答案，来源和排除规则见 `source-notes/training-materials-curation.md`。

## 全局质量 Guides

统一入口见 [guides/index.md](guides/index.md)。核心指南包括：

- [学术质量总标准](guides/academic-quality-standard.md)：题意、数学抽象、证据梯子、论文与 claim 边界。
- [高质量建模总则](guides/award-oriented-modeling.md)：baseline、主模型、challenger、复杂度与停止规则。
- [数据与特征质量](guides/data-and-feature-quality.md)：缺失、异常、泄漏、尺度、时间/空间结构、特征工程。
- [算法路由与模型升级](guides/algorithm-routing-quality.md)：预测、分类、评价、聚类、优化、多目标、机理和网络模型梯子。
- [高信息量实验设计](guides/experiment-design-quality.md)：baseline comparison、专项验证、robustness、failure case、消融与停止。
- [可视化证据设计](guides/visual-evidence-quality.md)：reader question、figure/table/text 路由、图型选择、视觉层级和 publication rendering。
- [评阅者视角](guides/contest-paper-reviewer-perspective.md)：目标定义、约束完整性、模型-代码-结果一致、可行性优先和 claim 边界。
- [模拟赛与过程控制](guides/rehearsal-and-contest-control.md)：Smoke / Full Rehearsal、早闭环、团队交叉、论文同步和赛后复盘。

这些 Guides 不属于 reference-library L3 schema，不参与 `lookup -Layer playbook`。

## 按任务检索 L1

| 题面信号 | 优先卡片 |
|---|---|
| 资源分配、选址、排程、路径、匹配 | [optimization-lp-milp](cards/optimization-lp-milp.md), [optimization-network-flow](cards/optimization-network-flow.md), [optimization-scheduling](cards/optimization-scheduling.md), [optimization-dp](cards/optimization-dp.md) |
| 多目标、软约束、分层偏好 | [optimization-goal-programming](cards/optimization-goal-programming.md), [uncertainty-fuzzy](cards/uncertainty-fuzzy.md) |
| 非线性、黑箱、组合搜索 | [metaheuristic-selection](cards/metaheuristic-selection.md), [metaheuristic-ga](cards/metaheuristic-ga.md), [metaheuristic-de-pso](cards/metaheuristic-de-pso.md), [metaheuristic-aco-sa-tabu](cards/metaheuristic-aco-sa-tabu.md) |
| 需求、收益、风险、概率约束 | [uncertainty-stochastic](cards/uncertainty-stochastic.md), [uncertainty-robust](cards/uncertainty-robust.md), [uncertainty-fuzzy](cards/uncertainty-fuzzy.md), [statistics-uncertainty](cards/statistics-uncertainty.md) |
| 预测、回归、因素影响、实验比较 | [statistics-preprocess](cards/statistics-preprocess.md), [statistics-regression](cards/statistics-regression.md), [statistics-anova](cards/statistics-anova.md), [statistics-time-series](cards/statistics-time-series.md), [ml-small-sample](cards/ml-small-sample.md) |
| 插值、拟合、根、积分、线性方程 | [numerical-interpolation-fitting](cards/numerical-interpolation-fitting.md), [numerical-root-linear](cards/numerical-root-linear.md), [numerical-integration](cards/numerical-integration.md) |
| 动态演化、迭代、增长、离散时间 | [dynamics-difference](cards/dynamics-difference.md), [dynamics-stability](cards/dynamics-stability.md) |
| 扩散、传热、波动、边界条件、空间机制 | [mechanism-ode](cards/mechanism-ode.md), [mechanism-pde](cards/mechanism-pde.md) |

## 按约束检索

`整数/二元` → `optimization-lp-milp`；`网络守恒` → `optimization-network-flow`；`时间窗/资源容量` → `optimization-scheduling`；`非线性且可微` → `optimization-nonlinear`；`随机分布明确` → `uncertainty-stochastic`；`分布不可靠但有界` → `uncertainty-robust`；`语言性等级/模糊偏好` → `uncertainty-fuzzy`；`小样本` → `statistics-preprocess`、`ml-small-sample`；`高维共线` → `statistics-regression`；`数据有时间依赖` → `statistics-time-series`。

## 工具入口

- Python：`scipy.optimize`、`scipy.integrate`、`statsmodels`、`scikit-learn`、`networkx`、`pulp`/`ortools`（以环境实际安装为准）。
- MATLAB：`linprog`、`intlinprog`、`quadprog`、`fmincon`、`ga`、`particleswarm`、`ode45`、`interp1`、`lsqcurvefit`。
- 先用最窄的精确/可解释模型建立同输出 baseline，再考虑启发式或机器学习；每张卡的“停止条件”是淘汰候选的依据。

## L2 决策模块

| 触发信号 | 模块 | 赛中输出 |
|---|---|---|
| 资源分配、选址、整数/开关、固定成本 | [LP/MILP](modules/optimization/lp-milp.md) | 变量账本、LP baseline、整数价值、可行性和 gap |
| 路径、运输、匹配、任务排程、时间窗 | [网络与排程](modules/optimization/network-scheduling.md) | 守恒/覆盖、规则 baseline、瓶颈扰动 |
| 需求/价格波动、概率/区间/语言偏好 | [不确定性规划](modules/optimization/uncertainty-planning.md) | 名义方案、情景风险、保守性与回退 |
| 未来需求、负荷、价格或客流预测 | [预测](modules/statistics/forecasting.md) | 滚动切分、朴素 baseline、残差与区间诊断 |
| 小样本因素分析、回归或分类概率 | [小样本回归](modules/statistics/regression-small-sample.md) | 防泄漏切分、正则化、稳定性与解释边界 |
| ODE/PDE、守恒方程、参数反推 | [机理标定](modules/statistics/mechanism-calibration.md) | 量纲/守恒、少参数标定、可辨识和数值收敛 |

模块的目标不是替队伍选模型，而是强制完成：`题面映射 -> 同输出 baseline -> 一次可解释升级 -> 关键诊断 -> 停止/回退决定`。

## L3 可自动路由 Playbooks

严格 schema 和完整列表见 [playbooks/index.md](playbooks/index.md)。当前只有五个顶层 L3：

- [constraint-modeling-quality](playbooks/constraint-modeling-quality.md)：自然语言约束 → 索引变量/目标/约束 → 独立可行性审计。
- [data-to-decision-modeling](playbooks/data-to-decision-modeling.md)：运营数据语义 → 时间验证 → 预测/响应 → 决策与误差传播。
- [predict-then-optimize](playbooks/predict-then-optimize.md)：上游预测 → 下游优化 → 端到端评价。
- [resource-allocation-under-uncertainty](playbooks/resource-allocation-under-uncertainty.md)：资源分配 → 场景/随机/鲁棒升级 → 成本-风险比较。
- [mechanism-fit-and-scenario](playbooks/mechanism-fit-and-scenario.md)：机理方程 → 参数标定 → 可辨识/数值诊断 → 情景。

### 触发原则

```text
全局 Guides
→ L1/L2
→ 题面确有跨模块结构？
    ├─ 否：停在 L2
    └─ 是：只选最匹配的一个 L3 Playbook
→ Candidate
```

不要为了匹配某个 Playbook 改变题意，也不要把多个重叠 Playbook 同时加载成“流程复杂度”。

## 检索命令

```powershell
# 默认同时返回最相关的模块、L3 Playbook 和路由卡
scripts/reference-library.ps1 -Action lookup -Tags optimization,milp

# 只看可执行决策模块
scripts/reference-library.ps1 -Action lookup -Tags forecasting,uncertainty -Layer module

# 只看严格 L3 Playbook
scripts/reference-library.ps1 -Action lookup -Tags forecasting,optimization -Layer playbook

# 检查来源、卡片、模块和 L3 状态
scripts/reference-library.ps1 -Action status
```

## 卡片目录

本库当前包含 29 张卡：运筹优化 8 张、元启发式 4 张、不确定性 3 张、统计与试验 5 张、数值计算 3 张、机器学习 2 张、差分与机制 4 张。所有卡均包含固定的适用性、baseline、验证、停止与误用栏目，并增加“决策判断”“关键量与诊断”“赛中最小试验”三个栏目。章节级定位尚未人工逐页视觉核验的卡，会继续标注为 `locator_confidence: low`，不得据此直接引用精确公式或页码。
