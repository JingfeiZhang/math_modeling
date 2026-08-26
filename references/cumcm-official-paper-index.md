# 国赛官方展示论文参考索引

本索引只用于赛前学习论文结构、论证顺序、结果解释和图表职责。论文展示页不是本项目的 Formal evidence，也不能直接提供模型参数、结果数字、代码或论文引用。使用时先看本地卡片，再回到官方页面核对封面和相关页码。

## 官方总入口

- [历年论文展示总入口](https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/qkt_sxjm_lw_lwzs.shtml)
- [2025 全国大学生数学建模竞赛论文展示](https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/2025qgdxssxjmjslwzs/)
- [2024 全国大学生数学建模竞赛论文展示](https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/2024qgdxssxjmjslwzs/)
- [2023 全国大学生数学建模竞赛论文展示](https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/2023qgdxssxjmjslwzs/2023gjsbqgdxssxjmjslwzs.shtml)

## 优先参考的 C 题

| 样本 | 官方展示页 | 本地卡片 | 主要学习用途 |
|---|---|---|---|
| 2025 C132 | [官方页](https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2025qgdxssxjmjslwzs_2025ctlw/251101/2022740.shtml) | `corpus/cards/cumcm-2025-c132.json` | 统计诊断、阈值决策、多模型结果如何分工 |
| 2025 C023 | [官方页](https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2025qgdxssxjmjslwzs_2025ctlw/251101/2022736.shtml) | `corpus/cards/cumcm-2025-c023.json` | 摘要逐问交付、医学流程抽象、风险边界 |
| 2024 C038 | [官方页](https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024ctlw/241104/1977952.shtml) | `corpus/cards/cumcm-2024-c038.json` | 总体路线图、优化模型链、收敛与敏感性证据 |
| 2024 C234 | [官方页](https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024ctlw/241104/1977963.shtml) | `corpus/cards/cumcm-2024-c234.json` | 数据处理、约束建模、方案比较和结论边界 |
| 2024 C094 | [官方页](https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024ctlw/241104/1977961.shtml) | `corpus/cards/cumcm-2024-c094.json` | 长链条问题的章节衔接、表格和流程图取舍 |
| 2024 C063 | [官方页](https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024ctlw/241104/1977958.shtml) | `corpus/cards/cumcm-2024-c063.json` | 多问结构、图表节奏和跨问结果交接 |

## 跨题型结构参考

这些论文不用于把其他题型的方法搬到 C 题，而用于观察不同任务如何组织“问题接口—模型—验证—决策”。

| 样本 | 官方展示页 | 主要学习用途 |
|---|---|---|
| 2025 A196 | [官方页](https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2025qgdxssxjmjslwzs_2025atlw/251101/2022729.shtml) | 机理模型和多阶段问题的递进结构 |
| 2025 B060 | [官方页](https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2025qgdxssxjmjslwzs_2025btlw/251101/2022733.shtml) | 资源分配、约束和方案结果表达 |
| 2025 D037 | [官方页](https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2025qgdxssxjmjslwzs_2025dtlw/251101/2022742.shtml) | 仿真、动态过程和验证证据 |
| 2025 E030 | [官方页](https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2025qgdxssxjmjslwzs_2025etlw/251101/2022744.shtml) | 评价、指标体系和结果解释 |
| 2024 A163 | [官方页](https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024atlw/241104/1977935.shtml) | 机理与优化的组合流程 |
| 2024 B159 | [官方页](https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024btlw/241104/1977943.shtml) | 评价指标、排序和方案比较 |
| 2024 D033 | [官方页](https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024dtlw/241104/1977965.shtml) | 动力/仿真问题的状态和边界表达 |

## 赛中检索顺序

1. 先按题面任务在本索引中选 1--3 篇：预测看 C023/C132，优化看 C038/C234，统计诊断看 C132，机理或动态过程再看 A/D 题。
2. 阅读本地卡片的 `transferable_patterns`、`evidence` 和 `risks`，确认需要回看的官方页码。
3. 只提取结构和审校问题：摘要是否逐问回答、变量和单位是否统一、结果是否有基线、检验是否针对失败风险、结论是否说明边界。
4. 回到题面和自己的实验，不复制论文算法、文字、数字、图件或结论。

新增论文时必须登记官方 URL、题号、展示页面哈希、缓存页数和复核状态；无法确认竞赛身份或页面来源时，保持待核验，不进入优先样本。
