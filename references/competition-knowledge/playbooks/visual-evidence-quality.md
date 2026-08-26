# 学术化可视化与证据设计手册

正式可视化帮助评委完成一个判断，不展示绘图能力。

## 1. 先写 Reader Question

任何正式图前先回答：读者看完应能判断什么？无法回答时优先 table/text/none。

## 2. 图表职责

Result Figure 展示预测、方案、空间结构、调度、状态轨迹、Pareto；Validation Figure 展示 residual、calibration、sensitivity、robustness、group error；Mechanism Figure 展示变量关系、状态转移、网络流、资源瓶颈、贡献结构。一图最好一个主职责。

## 3. Figure / Table / Text / None

精确数字/指标/参数 → Table；趋势、分布、关系、不确定性、空间、网络、权衡 → Figure；1–3 个数字 → Text；不增加理解 → None。避免同一数据“表 + 柱状图 + 正文逐项复述”。

## 4. 图型路由

模型优于 baseline → dot-whisker/紧凑表；预测一致性 → observed-vs-predicted/prediction interval；失败群体 → error-by-group；完整分布 → ECDF/box+raw points；参数影响 → sensitivity；场景稳健 → heatmap；多目标 → Pareto；排名稳定 → rank-stability；调度 → Gantt；资源瓶颈 → resource-profile；网络 → network flow；空间 → map/spatial residual；收敛 → convergence（辅助）。

## 5. 视觉语义

baseline 中性/弱化，main 主强调，challenger 次强调，violation/failure 警示，uncertainty 用 band/interval。颜色不是唯一编码，同时用 line style/marker/shape。

## 6. 学术图形规范

白底、2D、少量网格、无装饰性 3D、无彩虹 colormap、无渐变阴影、字体最终版面可读、轴写变量与单位、图例不遮挡数据。

## 7. 不确定性

有重复实验、估计区间或模型不确定性时优先 confidence/credible interval、quantile band、multi-seed distribution、scenario range。没有统计含义的误差棒不画。

## 8. 模型比较与预测

有估计与区间时优先 dot-whisker；指标多时优先紧凑表或 small multiples。预测主图通常只保留 Observed + Main + Baseline + Interval（需要时），其他候选进表。

## 9. 优化

优先展示方案、资源、调度、路径、Pareto 和压力场景，收敛曲线只说明求解行为。

## 10. 排序/聚类/网络/空间

排名最终值适合表格，稳定性更适合图；聚类投影不能替代稳定性；网络节点多时聚合或筛关键边；地图只在空间位置本身有解释作用时使用。

## 11. Annotation 与 Multi-panel

只标推荐方案、knee、阈值、峰值、约束边界、重要异常。多 panel 只有共同回答一个 reader question 才组合。

## 12. Caption 与图前图后

高质量 caption 包含对象 + 条件 + 编码/区间 + 主要比较。图前说明为什么需要证据；图后写结果、比较、原因、意义、边界。避免连续“由图 X 可知”。

## 13. 数据完整性

正式图只读真实 artifact，不手填论文数字、不 synthetic fallback；源数据、脚本、claim locator 可追溯。

## 14. 信息密度检查

删掉只重复表格的柱状图、装饰流程图、无 reader question 热力图、不能改变判断的相关图、只有算法迭代没有方案质量的收敛图。
