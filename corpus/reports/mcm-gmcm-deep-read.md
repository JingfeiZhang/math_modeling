# MCM/ICM 获奖论文与 GMCM 样本文献证据研读报告

> 生成日期：2026-08-03。本报告基于固定 Git commit 的 18 篇全文、逐页渲染和页面证据。

## 结论与证据边界

- MCM/ICM：12 篇完成 B 级证据深读。论文控制号、年份、题号和 Outstanding Winner 均在 COMAP 官方结果 PDF 中独立匹配。
- GMCM：6 篇完成 C 级内容深读。全文和 Git blob 可核验，但目前没有独立官方获奖名单定位，因此不得写成‘已核验优秀/获奖论文’。
- 18 篇全文均完成逐页渲染；每篇又选取 4-7 张高清页复核摘要、模型、验证、主图和风险。
- 本批次没有把 PDF 附录中的代码截图认定为可复现实验代码，也没有执行上游 MATLAB/Python 片段。

## 立即可迁移的规则

1. 摘要按‘问题 - 方法 - 量化结果 - 验证 - 边界’展开。美赛执行摘要更像给决策者的短报告；研究生赛长摘要适合逐问汇报，但必须控制模型堆叠。
2. 主结果图优先使用同轴比较、小倍图、空间叠加和‘收敛曲线 + 最终决策’组合。普通图能说清证据时，不使用复杂组合图。
3. 每个主要模型至少绑定一种可比较验证：外部数据拟合、替代模型交叉验证、精确求解器 baseline、参数敏感性或失败模式探针。
4. 空间问题先画真实对象或输入地图，再画计算抽象，最后画结果；预测问题同时给历史拟合、预测区间或重复划分不确定性。
5. 优化论文把决策变量、目标、约束、求解器、收敛、最终方案和业务 KPI 放在同一条证据链上。
6. 结论逐题回扣，不把模型分数自动解释为政策结论；局限必须指出受影响的主张范围。
7. 禁止继承旧论文中的身份封面、第三方水印、彩虹色图、默认 3D 柱图、双轴误导、过小图例和代码截图。

## 图表与验证模式矩阵

| 场景 | 推荐图件 | 应绑定的验证 | 代表页 |
|---|---|---|---|
| 空间优化 | 输入地图 + 响应热图 + 决策叠加 | 极端情景、替代布局、跨地点 | 2006 A p.6/11/13；2007 A p.12/16 |
| 离散仿真 | 状态流程图 + 策略小倍分布 | 重复运行、因素敏感性、失败模式 | 2007 B p.16/23/27；2009 A p.20/21 |
| 预测/分类 | 训练-测试曲线 + 混淆/校准 + 样本量敏感性 | 外部标签、重复划分、分布检查 | 2008 B p.10/11；GMCM C p.20/28 |
| 优化算法 | 收敛曲线 + 最终方案 + KPI 表 | 精确求解器 baseline、参数扫描 | GMCM B p.18/22；GMCM F p.25/41 |
| 物理机理 | 标注示意图 + 参数响应 + 实验对照 | 实测拟合、遗漏机理误差 | 2010 A p.16/39/44 |
| 综合评价 | 原始数据表 + 标准化矩阵 + 排名/政策表 | 权重敏感性、外部事实一致性 | 2010 C p.6/8/10 |

## 逐篇证据卡摘要

### mcm-2006-a-883 | Optimization of irrigation time, pipe set placements, and irrigation uniformity for a hand move system

- 身份：MCM 2006 A 题；真实性 B；状态 `evidence_deep_read`。
- 高清复核页：1, 2, 6, 11, 13, 14, 15。
- 模型链：sprinkler-response -> coverage-and-uniformity -> setup-minimization -> operational-schedule。
- 验证链：iteration-check；constraint-check；limitation-audit。
- 主图：p.6 profile plus heatmap（mechanism-to-field）；p.11 before-after heatmaps（convergence）；p.13 annotated heatmap（main-result）；p.14 table plus placement map（implementation）。
- 可迁移：Explain a spatial objective with a response profile and field map before presenting the optimizer.
- 主要风险：The absence of a result-bearing abstract weakens first-page decision density.

### mcm-2006-b-868 | A Simulation-Driven Approach For A Cost Efficient Airport Wheelchair Assistance Service

- 身份：MCM 2006 B 题；真实性 B；状态 `evidence_deep_read`。
- 高清复核页：1, 8, 9, 10, 12, 19。
- 模型链：network-abstraction -> discrete-event-service -> cost-optimization -> scenario-transfer。
- 验证链：factor-sweep；cross-site-test；demand-scenario。
- 主图：p.12 image plus network graph（model-abstraction）；p.19 two-series line chart（scenario-comparison）；p.8 scenario result tables（decision-table）。
- 可迁移：Display the real object and its graph abstraction together when geometry drives a simulation.
- 主要风险：There is no standalone executive summary with final recommended inventory.

### icm-2006-c-787 | The United Nations and the Quest for the Holy Grail (of AIDS)

- 身份：ICM 2006 C 题；真实性 B；状态 `evidence_deep_read`。
- 高清复核页：1, 2, 5, 16, 23, 26, 30。
- 模型链：epidemiological-base -> education-and-vaccine -> ARV-dynamics -> economic-allocation。
- 验证链：historical-fit；parameter-sensitivity；adherence-sensitivity；scope-audit。
- 主图：p.16 observed-versus-predicted curve（external-validation）；p.23 scenario trajectories（policy-sensitivity）；p.26 multi-series time plot（treatment-sensitivity）。
- 可迁移：A policy abstract should name the horizon, model chain, intervention levers, and decision output.
- 主要风险：Long-horizon forecasts depend on uncertain prospective demographic and epidemiological parameters.

### mcm-2007-a-1034 | Applying Voronoi Diagrams to the Redistricting Problem

- 身份：MCM 2007 A 题；真实性 B；状态 `evidence_deep_read`。
- 高清复核页：1, 6, 10, 12, 16, 17, 20。
- 模型链：design-criteria -> weighted-voronoi -> spatial-data -> case-construction。
- 验证链：criteria-check；case-study；limitation-analysis。
- 主图：p.10 progressive schematic（algorithm-explanation）；p.12 paired map views（input-data）；p.16 overview plus detail maps（main-result）。
- 可迁移：Use a minimal schematic to teach a geometric algorithm before the case-study maps.
- 主要风险：A bright third-party watermark contaminates the archived first page.

### mcm-2007-b-2053 | Boarding at the Speed of Flight

- 身份：MCM 2007 B 题；真实性 B；状态 `evidence_deep_read`。
- 高清复核页：1, 2, 16, 23, 27, 28, 29。
- 模型链：strategy-encoding -> passenger-simulation -> strategy-comparison。
- 验证链：factor-sensitivity；distributional-check；cross-strategy-table。
- 主图：p.16 categorical seat matrix（strategy-definition）；p.23 multi-series line chart（factor-sensitivity）；p.27 small-multiple histograms（robustness）。
- 可迁移：Write the summary as a decision brief for the stated stakeholder.
- 主要风险：The line chart is crowded and its legend is small at print scale.

### icm-2007-c-2052 | Optimizing the Effectiveness of Organ Allocation

- 身份：ICM 2007 C 题；真实性 B；状态 `evidence_deep_read`。
- 高清复核页：1, 4, 6, 7, 9, 16, 21。
- 模型链：network-and-arrivals -> discrete-event-allocation -> policy-comparison -> ethical-extension。
- 验证链：base-case-check；policy-scenario；parameter-sensitivity；scope-audit。
- 主图：p.7 process flowchart（model-architecture）；p.9 aligned scenario curves（policy-comparison）；p.16 parameter-response line chart（sensitivity）。
- 可迁移：For discrete-event policy models, draw the complete state-transition loop before equations.
- 主要风险：Missing abstract delays access to the decision and result.

### mcm-2008-a-3694 | Mathematically Modeling Sea Level Rise

- 身份：MCM 2008 A 题；真实性 B；状态 `evidence_deep_read`。
- 高清复核页：1, 6, 17, 20, 23, 25。
- 模型链：scenario-input -> physical-process -> spatial-inundation -> impact-accounting。
- 验证链：extreme-case-map；external-range-check；structural-limit。
- 主图：p.6 colored flowchart（model-overview）；p.17 matched inundation maps（robustness）；p.20 scenario table（decision-output）。
- 可迁移：For coupled physical models, show forcing, submodels, and outputs before derivation.
- 主要风险：No abstract communicates the final scenario results.

### mcm-2008-b-2858 | hsolve: A Difficulty Metric and Puzzle Generator for Sudoku

- 身份：MCM 2008 B 题；真实性 B；状态 `evidence_deep_read`。
- 高清复核页：1, 2, 10, 11, 16, 17。
- 模型链：search-metric -> rating-calibration -> controlled-generation。
- 验证链：external-label-test；distribution-check；runtime-and-target-test。
- 主图：p.10 contingency table（external-validation）；p.11 histogram plus reference curve（distribution-validation）；p.16 difficulty histogram（generator-output）。
- 可迁移：Put the model, sample size, validation statistic, and practical output in the abstract.
- 主要风险：The benchmark is limited and the authors cannot conclusively establish all difficulty levels.

### mcm-2009-a-4339 | Three steps to make the traffic circle go round

- 身份：MCM 2009 A 题；真实性 B；状态 `evidence_deep_read`。
- 高清复核页：1, 5, 9, 16, 20, 21。
- 模型链：geometry-and-demand -> dual-simulation -> multi-objective-control -> adaptive-policy。
- 验证链：model-cross-check；repeat-and-transfer；failure-mode-probe。
- 主图：p.5 annotated aerial image plus OD table（problem-definition）；p.16 timing strip plus KPI table plus snapshot（main-result）；p.20 layout schematics plus sensitivity table（robustness）；p.21 failure-state snapshot（risk-probe）。
- 可迁移：Use an independently structured second model as a cross-check when direct ground truth is unavailable.
- 主要风险：The summary includes decorative road signs that consume scarce first-page area.

### mcm-2010-a-6749 | Modeling the Sweet Spot of Wood, Corked, and Metal Baseball Bats

- 身份：MCM 2010 A 题；真实性 B；状态 `evidence_deep_read`。
- 高清复核页：1, 5, 16, 39, 43, 44。
- 模型链：collision-mechanics -> corked-bat-extension -> metal-bat-design。
- 验证链：empirical-match；mechanism-review；question-closure；error-audit。
- 主图：p.16 annotated cross-section（mechanism）；p.39 equations plus validation prose（derivation-to-conclusion）；p.43 structured bullet review（result-synthesis）。
- 可迁移：A mechanics abstract should report the physical mechanism, calibrated quantity, and design implication.
- 主要风险：Transverse-wave and hoop-vibration effects are omitted and contribute a stated error.

### mcm-2010-b-7273 | Tracking Serial Criminals with a Road Metric

- 身份：MCM 2010 B 题；真实性 B；状态 `evidence_deep_read`。
- 高清复核页：1, 4, 9, 10, 16, 17, 18。
- 模型链：road-metric -> future-crime-density -> residence-prior -> case-application。
- 验证链：historical-case；computational-test；out-of-sample-use。
- 主图：p.9 road-network schematic（metric-explanation）；p.10 road overlay heatmap（case-result）；p.16 3D probability surface（residence-result）。
- 可迁移：When replacing Euclidean distance, visualize the induced geometry before using it in a model.
- 主要风险：The evaluation uses a limited number of historical cases and lacks a modern out-of-sample benchmark.

### icm-2010-c-6947 | A new method for pollution abatement: different solutions to different types

- 身份：ICM 2010 C 题；真实性 B；状态 `evidence_deep_read`。
- 高清复核页：1, 2, 6, 8, 9, 10。
- 模型链：attribute-selection -> multi-attribute-ranking -> risk-grading -> policy-mapping。
- 验证链：data-selection-check；limitation-audit；decision-consistency。
- 主图：p.6 source table plus decision matrix（data-to-model）；p.8 ranked bar chart（main-result）；p.10 decision table（policy-output）。
- 可迁移：Show the raw data table immediately before the normalized decision matrix.
- 主要风险：Toxicity, shape, species behavior, and other ecological factors are omitted.

### gmcm-2019-a-a19100030004 | 无线智能传播模型

- 身份：GMCM 2019 A 题；真实性 C；状态 `content_extracted`。
- 高清复核页：1, 2, 8, 14, 24, 26, 38。
- 模型链：physical-baseline -> spatial-features -> neural-regression -> tree-ensemble。
- 验证链：feature-diagnostic；train-test-comparison；metric-comparison。
- 主图：p.8 annotated propagation schematic（mechanism）；p.14 small-multiple spatial scatter（feature-diagnostic）；p.24 network diagram（model-architecture）；p.26 paired train-test curves（model-selection）。
- 可迁移：Lead a hybrid model with the physical mechanism and treat machine learning as a correction layer.
- 主要风险：The cover contains direct personal and institutional identifiers and must never enter an anonymous submission.

### gmcm-2018-b-b18102520096 | 光传送网建模与价值评估

- 身份：GMCM 2018 B 题；真实性 C；状态 `content_extracted`。
- 高清复核页：1, 11, 18, 22, 31, 33, 49。
- 模型链：modulation-baseline -> network-value -> routing -> constellation-redesign。
- 验证链：modulation-comparison；optimization-convergence；before-after-performance。
- 主图：p.11 BER-SNR line chart（baseline）；p.18 convergence curve plus network map（optimization-result）；p.31 four-panel constellation plot（design-comparison）；p.33 before-after BER curves（performance-comparison）。
- 可迁移：Define a common operating threshold when comparing communication schemes.
- 主要风险：The paper combines loosely coupled modulation and network-planning tasks, so the narrative is broad.

### gmcm-2020-c-c20102470319 | 面向康复工程的脑电信号分析和判别模型

- 身份：GMCM 2020 C 题；真实性 C；状态 `content_extracted`。
- 高清复核页：1, 2, 16, 20, 24, 28, 34。
- 模型链：signal-preprocessing -> supervised-comparison -> channel-selection -> semi-supervised-learning -> sleep-stage-classification。
- 验证链：train-test-history；algorithm-comparison；sample-size-sensitivity。
- 主图：p.16 five-panel bar charts（feature-selection）；p.20 train-test history（learning-diagnostic）；p.24 small-multiple histories plus table（algorithm-selection）；p.28 sample-ratio line chart（sensitivity）。
- 可迁移：For a long multi-question abstract, keep a strict question-method-result rhythm.
- 主要风险：The cover leaks direct identifiers and is incompatible with anonymous submission.

### gmcm-2019-d-d19102470244 | 汽车行驶工况构建

- 身份：GMCM 2019 D 题；真实性 C；状态 `content_extracted`。
- 高清复核页：1, 2, 14, 22, 26, 29, 30。
- 模型链：data-cleaning -> segment-and-feature -> dimension-reduction -> segment-clustering -> cycle-construction。
- 验证链：data-quality-audit；cluster-inspection；domain-output-check。
- 主图：p.14 annotated anomaly small multiples（data-quality）；p.22 PCA flowchart（method）；p.26 3D scatter plot（cluster-result）；p.29 ranked bar chart（feature-result）。
- 可迁移：Put data-retention counts in the abstract when cleaning materially changes the sample.
- 主要风险：The cover leaks direct identifiers.

### gmcm-2019-e-e19102840016 | 全球变暖气候预测分析

- 身份：GMCM 2019 E 题；真实性 C；状态 `content_extracted`。
- 高清复核页：1, 2, 27, 30, 35, 40, 48。
- 模型链：trend-and-change -> factor-reduction -> time-series-forecast -> driver-classification。
- 验证链：dimension-check；fit-metric；forecast-table；distribution-aware-test。
- 主图：p.27 heatmap plus scree plot（feature-reduction）；p.30 aligned time-series plots（series-comparison）；p.35 history-forecast line plus table（forecast）；p.40 bar chart plus statistical table（feature-importance）。
- 可迁移：Pair a correlation heatmap with a scree or cumulative-variance plot before PCA-based modeling.
- 主要风险：The cover leaks direct identifiers.

### gmcm-2018-f-f18100030032 | 中转航班调度：从 MILP 模型到启发式算法

- 身份：GMCM 2018 F 题；真实性 C；状态 `content_extracted`。
- 高清复核页：1, 9, 25, 36, 41, 43, 59。
- 模型链：binary-assignment -> greedy-fallback -> passenger-flow -> solver-comparison。
- 验证链：parameter-sensitivity；baseline-comparison；question-closure。
- 主图：p.25 flowchart plus parameter table（algorithm）；p.36 dual-axis interval chart（decision-impact）；p.41 solver comparison table（baseline）。
- 可迁移：Put solver names and quantified optimization outputs in the abstract.
- 主要风险：The summary is dense and relies on red inline emphasis rather than a compact result table.

## 赛时使用方式

- 选题后按题型检索卡片中的 `model_chain`、`validation_chain` 和 `figures`，只复用论证结构，不复制旧文数字、文字或图。
- 每个子问题先建立可运行 baseline 和风险探针，再选择图型；没有证据时不得预留‘漂亮主图’。
- Figure Contract 必须绑定冻结主张、实验定位、变量单位、源脚本、图注以及 PDF/SVG/400 dpi PNG 三种导出。
- 正式 CUMCM 稿严格服从当届规则；GMCM 身份封面、旧 MCM Summary Sheet 和历史页式只用于研究，不进入提交模板。

## 限制

本报告评价的是可见论文的论证和呈现方式，不对全部数学推导作重新证明。GMCM 六篇的内容可学习，但获奖状态仍未独立核验。18 篇均未绑定独立源码仓库，因此不计入‘论文-代码可复现配对’指标。
