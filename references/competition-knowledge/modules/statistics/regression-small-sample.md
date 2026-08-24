---
module_id: statistics-regression-small-sample
module_version: 1
family: statistics
tags: [regression, small-sample, regularization, leakage, diagnostics]
source_cards: [statistics-regression, statistics-preprocess, statistics-uncertainty]
stage_scope: [P1, P2, P3a, P3b]
evidence_status: P1-P3-non-evidence
contest_evidence_eligible: false
allowed_use: [model_direction, assumption_check, baseline_design, risk_probe]
forbidden_use: [academic_citation, formal_evidence, claim_support, figure_contract, submission]
---

# 小样本回归与解释决策模块

> 用于把“相关因素/预测变量/影响程度”题面转成可运行的回归探针。它只辅助模型方向和风险诊断，不提供正式显著性、系数或性能结论。

## 用途与排除

适用于连续、计数、比例或二元响应，样本量有限、变量较多、存在分组/重复观测，或题目同时要求预测和因素解释的场景。

排除或改道：

- 结果变量是明确的时间未来值：先使用 forecasting 模块的时间切分。
- 目标是资源分配或组合决策：回归可生成参数，但主问题仍应进入优化模型。
- 研究设计无法排除关键混杂：只做关联/预测表述，不写因果效应。
- `n` 极小且每个观测都具独立业务含义：优先规则、分层汇总或机制模型，避免伪精确回归。

## 题面句子到数据/变量/约束映射

| 题面信号 | 数据结构 | 变量映射 | 首要约束 |
|---|---|---|---|
| “哪些因素影响/解释 Y” | 行为观测、响应 `y` | `X` 为候选因素，明确观测单位 | 混杂、共线、因果边界 |
| “预测下一次/未知样本” | 训练表+未来表 | 目标 `y`、可用特征 `X` | 时间/组泄漏、部署可用性 |
| “成功/失败、是否达标” | 二元响应 | `P(y=1|X)` | 类别不平衡、阈值和校准 |
| “次数/数量/到达量” | 非负计数 | Poisson/负二项响应 | 过度离散、暴零 |
| “比例、合格率、占比” | `[0,1]` 响应 | 二项/变换回归 | 分母、边界值和权重 |
| “多地区/多设备/多批次” | 组内重复观测 | `group_id`、组效应或分层截距 | 组间泄漏、伪重复 |

启动前写清：观测单位、目标类型、候选特征的可获得时点、是否需要解释还是预测、分组结构、缺失处理和评价指标。

## 最小可运行模型

连续响应先从低维线性模型开始：

\[
y_i=\beta_0+x_i^\top\beta+\varepsilon_i,
\qquad \hat\beta=\arg\min_\beta\|y-X\beta\|_2^2.
\]

小样本/共线时同时跑岭回归：

\[
\hat\beta_\lambda=\arg\min_\beta\|y-X\beta\|_2^2+\lambda\|\beta\|_2^2.
\]

二元、计数、比例响应才切换到对应 GLM；不要仅因为软件方便而改变响应分布。所有预处理（标准化、缺失填补、特征选择）必须在训练折内拟合。

## baseline 到主模型升级路径

```text
训练均值/业务规则
  -> 单变量或预注册低维线性模型
  -> 岭/Lasso（小样本、共线或 p 接近 n）
  -> GLM（响应分布明确支持时）
  -> 受限非线性/分层模型（只有残差和分组证据支持时）
```

推荐把“解释模型”和“预测模型”分开记录：解释模型保留可读变量和方向，预测模型可使用正则化，但不能把预测增益包装为因果发现。

## 三项关键诊断与可观测门槛

1. **样本信息量与共线性**：记录有效样本数 `n_eff`、特征数 `p`、`n_eff/p`、VIF/条件数。`p/n_eff` 接近或超过 0.3 时减少变量或正则化；VIF > 5 触发合并/降维审查，VIF > 10 不解释单个系数。阈值是风险提示，不是自动判决。
2. **泛化与泄漏**：使用按时间、组或个体隔离的验证；对小样本重复 K 折或留一法并报告离散度。若任何预处理在全数据拟合、或随机切分把同组样本分到两侧，则结果无效，必须重跑。
3. **残差/校准与稳定性**：连续模型检查残差趋势、异方差和高杠杆点；分类/GLM检查概率评分、校准和基率。重采样中系数频繁变号、指标置信区间跨越 baseline 或性能由单个点贡献时，只保留弱解释或回退。

## 失败回退树

```text
响应类型不匹配
  -> 明确计数/二元/比例分布与评价指标
  -> 仍无依据：回到描述统计或任务专用 baseline

p 接近/超过 n，或 VIF/条件数过高
  -> 预注册变量组、岭/降维、减少交互
  -> 系数仍不稳定：只报告预测表现与方向性，不作单变量解释

验证误差不优于均值/业务 baseline
  -> 检查切分、泄漏、特征可用性和异常点
  -> 仍失败：保留 baseline，停止增加复杂度

残差有结构或强异方差
  -> 变换响应、加有机理依据的特征或采用稳健损失
  -> 结构仍无法解释：改为分组描述/机制模型

训练性能很好、留出性能崩溃
  -> 减少特征、提高正则化、锁定模型族
  -> 仍崩溃：结论限于样本内关联，不能推广
```

## 赛中最小实验序列

1. 画出观测单位和数据流，删除结果发生后才知道的字段；固定任务指标和分组切分规则。
2. 跑训练均值/业务规则、低维线性两个同输出 baseline；保存逐折指标。
3. 对标准化、缺失填补和特征选择建立折内管道，比较岭与一个受限非线性候选。
4. 进行一次重采样稳定性检查：记录指标均值、标准差、系数方向频率和高杠杆观测。
5. 只针对诊断触发的问题做一次改变（响应变换、正则化强度、变量组或分层结构）。
6. 依据“留出稳定改善/仅解释需求/无可靠改善”选择主模型、解释模型或 baseline，并记录放弃原因。

## 必须记录的字段

`unit_of_observation`、`target_type`、`target_column`、`feature_columns`、`available_at`、`group_column`、`time_column`、`n_raw`、`n_eff`、`p_raw`、`p_used`、`split_rule`、`preprocess_fit_scope`、`missing_rule`、`outlier_rule`、`baseline_name`、`model_family`、`regularization`、`lambda_grid`、`metric`、`fold_metrics`、`calibration_or_residual_diagnostics`、`vif_or_condition_number`、`coefficient_stability`、`rejected_candidates`。

## 论文交接边界

可以交接题面变量定义、数据处理口径、模型族选择理由、baseline 可比性、Formal 冻结的性能和经过核验的系数/区间。不能交接本模块的经验阈值作为论文定理，也不能把相关性写成因果性；正式数字、显著性、区间和图表必须来自 Formal 或合格 Paper Evidence，并能回溯到同一数据与代码哈希。

## 原书回退定位

优先回看 applied-statistics 的回归、诊断和区间估计章节，以及 statistics-regression、statistics-preprocess 相关卡。本模块不提供精确页码；教材示例、经验阈值和未经项目复跑的系数不得进入论文或 claims。
