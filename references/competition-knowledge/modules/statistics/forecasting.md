---
module_id: statistics-forecasting
module_version: 1
family: statistics
tags: [forecasting, time-series, rolling-validation, leakage, uncertainty]
source_cards: [statistics-time-series, statistics-preprocess, statistics-uncertainty]
stage_scope: [P1, P2, P3a, P3b]
evidence_status: P1-P3-non-evidence
contest_evidence_eligible: false
allowed_use: [model_direction, assumption_check, baseline_design, risk_probe]
forbidden_use: [academic_citation, formal_evidence, claim_support, figure_contract, submission]
---

# 预测问题决策模块

> 这是赛中模型探索用的决策辅助，不是 Formal 证据、学术引用或论文数字来源。所有阈值是探针门槛，不是统计定理；正式结论必须回到项目自己的 Formal/Paper Evidence。

## 用途与排除

适用于按时间产生观测、题目要求预测未来值/区间/情景，或要求评估预测策略的 Qx。优先处理单变量序列、带外生变量的序列、季节性需求和多步预测。

排除或暂缓：

- 观测没有可靠时间顺序、时间戳重复且无法定义聚合口径；先回到数据预处理或横截面回归。
- 题目实际要求“最优决策”而非预测；预测只能作为优化模型的输入模块。
- 未来不可获得的解释变量被当作已知输入；必须改成情景输入、滞后变量或仅用可用信息。
- 序列过短，无法覆盖至少两个完整周期；不要强行估季节模型。

## 题面句子到数据/变量/约束映射

| 题面信号 | 数据结构 | 首要变量 | 约束/风险 |
|---|---|---|---|
| “预测未来若干天/周/月” | 时间索引 `t`、响应 `y_t` | 预测起点、步长 `h` | 只能使用起点前信息 |
| “存在周期/旺季/工作日效应” | 周期长度 `s` 或日历特征 | `y_{t-s}`、季节哑变量 | 周期必须由历史或业务规则支持 |
| “受价格、天气、政策影响” | 外生变量 `x_t` | 预测时点可见的 `x_{t+h}` 或 `x_t` | 未来可用性、单位和滞后关系 |
| “分区域/分产品预测” | 组索引 `g` | 每组序列或层级总量 | 组间信息泄漏、层级守恒 |
| “需求稀疏/大量为零” | 计数或间歇序列 | 非零间隔、非零大小 | 不能仅用 RMSE 掩盖零值偏差 |

初始化时应明确：观测频率、预测 horizon、可用信息截点、是否需要点预测/区间预测、缺失和异常处理口径。

## 最小可运行模型

先实现滚动预测接口：给定训练窗口 `[1:t]`，输出 `\hat y_{t+1:t+h}`，并返回每个起点的误差。

```text
持久性:          \hat y_{t+h} = y_t
季节朴素:        \hat y_{t+h} = y_{t+h-s}       (有可信周期时)
漂移/均值:        训练窗口均值或线性趋势外推
```

候选低复杂度模型依次选择：

1. ETS/局部水平状态空间：趋势或季节缓慢变化；
2. AR/ARIMA：差分后残差仍有滞后结构；
3. 动态回归：外生变量在预测时可获得且增量解释稳定；
4. 分层/全局模型：多组序列共享规律，但要保留组级验证。

预测区间可先用滚动残差分位数构造，避免在早期为了形式完整引入未经验证的复杂分布。

## baseline 到主模型升级路径

```text
持久性/季节朴素
  -> 移动平均或局部水平
  -> ETS/ARIMA（只在残差仍有结构时）
  -> 带可用外生变量的动态回归
  -> 分层/组合预测（只在组级证据支持时）
```

升级必须回答：候选模型是否在多个滚动起点、多个 horizon、关键分组上稳定优于 baseline？如果只改善训练误差或单个起点，不升级。

## 三项关键诊断与可观测门槛

1. **滚动泛化**：报告每个起点和 horizon 的 MAE/RMSE/业务指标。候选模型至少在多数起点不劣于 baseline，且平均改善不应由单一异常区间贡献；否则保留 baseline。
2. **残差结构**：检查残差 ACF、季节滞后和残差均值漂移。若显著滞后仍存在，模型尚未提取主要结构；若只在最后窗口出现，优先缩短窗口或分段，而非盲目加阶。
3. **可用性与区间**：逐条记录预测时点实际可见字段；区间报告覆盖率和平均宽度。明显低覆盖或依赖未来字段时，结论只能是点预测探针，不能宣称稳健预测。

## 失败回退树

```text
数据时间顺序/频率不可靠
  -> 先做聚合、去重、缺失审计
  -> 仍不可修复：转横截面模型或仅做描述统计

复杂模型不优于朴素 baseline
  -> 降阶、缩短窗口、去除不可靠外生变量
  -> 仍无改善：采用 baseline + 区间

残差有强季节结构
  -> 检查周期 s 与日历特征
  -> 加季节项/季节朴素对照

结构突变或滚动性能崩溃
  -> 分段/干预变量/变点探针
  -> 无法解释：缩短预测 horizon 并收窄结论边界

大量零值或间歇需求
  -> 非零到达与非零大小分开建模
  -> 样本不足：使用零值比例、分组汇总或区间描述
```

## 赛中最小实验序列

1. 固定时间排序、频率、预测 horizon 和信息截点；形成可复用滚动评估函数。
2. 跑持久性、季节朴素（若适用）、窗口均值三个 baseline。
3. 选择一个低复杂度候选（ETS 或 ARIMA），至少使用 3 个滚动起点；记录逐点误差而非只留平均数。
4. 仅在候选明显失败模式存在时添加一个改变（季节项、外生变量或窗口长度），一次只改一个因素。
5. 在最后一段未参与调参的数据上复核；检查残差 ACF、偏差、区间覆盖和分组误差。
6. 依据“稳定改善/无改善/数据不支持”三类结果停止，不继续无目的调阶。

## 必须记录的字段

`time_column`、`target_column`、`group_column`、`frequency`、`season_length`、`forecast_horizon`、`information_cutoff`、`training_window`、`split_timestamps`、`exogenous_columns`、`missing_rule`、`outlier_rule`、`baseline_name`、`candidate_name`、`seed`、`metrics_by_origin`、`residual_diagnostics`、`interval_method`、`coverage`、`runtime_seconds`、`rejected_candidates`。

## 论文交接边界

可交接给 Paper 的只有：预测任务定义、数据截点与单位、模型选择理由、baseline 可比性、Formal 冻结的指标和经过 Figure Contract 的图表需求。教材卡本身不进入 BibTeX；本模块的阈值和探针结果不得直接写成论文结论。任何正式预测数字必须来自 Formal 或合格 Paper Evidence，并绑定输入、代码和哈希。

## 原书回退定位

优先回看 applied-statistics 的时间序列、相关分析、预测和区间估计章节；本模块不提供未经逐页核验的精确页码或公式。原书示例、阈值和数据不得复制为项目证据。
