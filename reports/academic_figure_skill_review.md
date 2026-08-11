# academic-figure-skill 来源审查

- 来源：https://github.com/TingxiYu/academic-figure-skill
- 固定提交：`1df9940dd01ac939f072b12fe28d6353b79b90f9`
- 许可证：Apache-2.0
- 文件数：217
- 静态风险项：35（全部默认禁止直接执行）

## 吸收内容

问题驱动的 Figure Brief、最终物理尺寸优先、矢量优先导出、统计与数据完整性说明、反模式/代码/视觉/渲染四轮 QA。

## 本地改写

赛事图件使用 `journal-spectrum-v2`、CUMCM 正文尺寸、8 pt 最小字号、PDF/SVG/400 dpi PNG；Python 为默认数据后端，MATLAB 按任务选用。

## 风险处理

上游代码只做静态索引。包含网络、进程、删除、动态执行、GUI 或绝对路径的脚本必须人工审查后才能提取构图规则，不能直接作为竞赛证据。

机器清单：`D:/数学建模/reports/academic_figure_skill_source_manifest.json`
