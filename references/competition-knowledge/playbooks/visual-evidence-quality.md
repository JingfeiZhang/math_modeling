---
playbook_id: visual-evidence-quality
playbook_version: 1
tags: [visualization, evidence, reader-question, figure-design, paper-quality]
stage_scope: [P3a, P3b, P4, P5]
evidence_status: guidance-only
contest_evidence_eligible: false
allowed_use: [artifact_selection, figure_design, table_design, caption_design, visual_hierarchy]
forbidden_use: [synthetic_evidence, manual_result_creation]
---

# 可视化证据与图表设计手册

本手册不改变现有 `figure_data_manifest → visual_intent → figure_brief → render/QA` 生命周期。它只提升“什么时候该画、该画什么、怎样让图真正证明结论”的决策质量。

## 1. 第一问不是“画什么图”，而是 Reader Question

每个候选图表先写一句：

> 评委看完这个视觉证据后，应该能回答什么问题？

如果无法写出明确 reader question，就不画。

## 2. Figure / Table / Text / None 路由

- **Table**：需要精确读取模型指标、参数、方案明细、排名或多指标比较；
- **Figure**：需要识别趋势、分布、关系、不确定性、空间、网络、调度、权衡或机制；
- **Text**：只有 1–3 个核心数字；
- **None**：不能增加结论信息，只是装饰或重复。

同一批数字不默认同时做表、柱状图和逐项文字复述。

## 3. 三类论文图

### Result Figure
回答“得到了什么”：预测轨迹、方案、资源配置、空间分布、Pareto、状态轨迹。

### Validation Figure
回答“为什么可信”：校准、残差、误差分组、敏感性、鲁棒性、排名稳定性。

### Mechanism Figure
回答“为什么产生这个结果”：特征效应、资源贡献、网络流、机制图、状态转移。

不要求每问三类齐全；优先覆盖最关键证据缺口。

## 4. Reader Question → 推荐视觉

| Reader Question | 优先形式 |
|---|---|
| 哪个模型更好且差异是否稳定？ | dot/interval 或紧凑表 |
| 随时间/有序变量如何变化？ | line + interval |
| 预测值与真实值是否一致？ | observed-vs-predicted + identity line |
| 误差集中在哪些群体/时段？ | error-by-group |
| 两组分布是否真正不同？ | ECDF / box+raw points |
| 分类性能是否适合不平衡数据？ | PR + confusion + calibration |
| 参数影响是否存在阈值/非线性？ | sensitivity curve |
| 多参数谁最重要？ | sensitivity ranking |
| 场景下是否稳健？ | robustness/scenario matrix |
| 多目标如何权衡？ | Pareto scatter |
| 排名是否随权重改变？ | rank-stability |
| 调度方案如何安排？ | Gantt |
| 资源何时拥塞？ | resource profile |
| 网络流量如何变化？ | network flow |
| 空间差异在哪里？ | spatial distribution |
| 算法是否稳定收敛？ | convergence，仅作辅助算法证据 |

## 5. 模型比较不要默认柱状图

有均值与区间时优先 dot-whisker/forest style；它能同时表达中心、不确定性、baseline 和 primary。柱状图只适合无区间的少量非负总量比较，且通常从零开始。

## 6. 预测图主线简化

正文主图优先保留：Observed、Primary、Baseline、Interval。其他模型放比较表，不把 5–10 条模型曲线叠成 spaghetti plot。

预测可信度应由时间外误差、校准/区间覆盖、error-by-group 等证据补充，而不是仅展示拟合曲线。

## 7. 优化结果优先画“方案”，不是只画收敛

优化论文图的优先级：

```text
方案/资源/调度/权衡
> robustness/sensitivity
> convergence
```

收敛曲线说明求解行为，不能替代方案价值。

## 8. 排名/评价优先画稳定性

最终排名通常用表即可。更有论文价值的是：权重/标准化/删项变化后 top-k 是否稳定、何时发生排名翻转。

## 9. 空间和网络图避免“有坐标就画地图”“有边就画网络”

若读者需要精确比较数值，排序表或 dot plot 可能优于地图。高密度网络应优先聚合、top-flow、community summary 或矩阵，避免毛线球。

## 10. Visual hierarchy

默认语义：

- Primary model/推荐方案：主强调；
- Baseline：中性、虚线/方形等第二编码；
- Challenger/context：次强调；
- Failure/violation：仅在表达风险时使用警示语义。

颜色不能是唯一编码，同时利用线型、marker、填充或直接标签，保证灰度打印和色觉异常仍可读。

## 11. 视觉风格

正式论文图默认：白底、2D、少网格、无 3D、无渐变装饰、无阴影、无彩虹色谱、避免过多 legend。

坐标轴必须使用“变量 + 单位”。双 Y 轴默认不用；对数轴必须显式说明。最终尺寸文字优先保持至少 9 pt 可读。

## 12. Annotation

只标真正具有解释价值的点：推荐方案、阈值、knee、约束边界、峰值、异常失败点。不要给每个点都贴数值。

## 13. Multipanel

只有多个 panel 共同证明同一结论时组合，例如 prediction + residual + error distribution。不同问题的图不要仅为省图号强行拼在一起。

## 14. Plot-ready data

绘图脚本只消费从真实实验 artifact 派生的 tidy table，不手填论文数字。转换应为只读：筛选、排序、单位换算、聚合、区间计算等必须可复现并在 figure manifest/brief 中记录。

## 15. Caption 质量

Caption 不只是“图 X 预测结果”。应简洁说明：比较对象、数据/场景、关键视觉编码和读图边界。正文负责给结论与意义。

例如：

> 滚动测试期主模型与季节朴素基线的预测结果，阴影表示95%预测区间；峰值时段仍是主要误差来源。

## 16. 论文中的引用顺序

图前：说明为什么需要该证据。

图后：按“结果 → baseline比较 → 原因/机制 → 实际意义 → 边界”解释。

禁止连续写“如图X所示”而只复述视觉形状。

## 17. 停止规则

一张图如果不能提供表格/正文无法高效提供的信息，删除。每问优先保留少量高信息量主结果和验证图，而不是追求图数。
