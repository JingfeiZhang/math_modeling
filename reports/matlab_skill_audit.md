# MATLAB 数学建模 Skills 与环境审计

审计更新：2026-08-05。当前唯一 MATLAB 后端为正版 `26.1.0.3312084 (R2026a) Update 4`，用于 CUMCM/MCM/ICM 的统计建模、优化、符号计算和论文级绘图。

## 当前结论

| Skill | 竞赛职责 | R2026a 验证 |
|---|---|---|
| `matlab-build-chart` | 多面板、统计图、注释、配色与出版导出 | `tiledlayout`、`exportgraphics`、PDF/SVG/400 dpi PNG 通过 |
| `matlab-solve-optimization` | 问题分类、建模、求解器选择与结果验证 | Optimization Toolbox 二次规划和 Global Optimization Toolbox 遗传算法通过 |
| `matlab-performance-optimizer` | 向量化、预分配、性能与内存分析 | Skill 校验通过，无额外运行时依赖 |
| `matlab-symbolic-math` | 符号推导、方程求解与数值函数生成 | Symbolic Math Toolbox 微分测试通过 |

## 安装与解析

- 安装目录：`D:\MATLAB\R2026a`；可执行文件：`D:\MATLAB\R2026a\bin\matlab.exe`。
- 机器 PATH 包含 R2026a 的 `bin` 和 `runtime\win64`。
- `contest.yaml` 是工作区 MATLAB 路径的权威来源。
- `scripts/_matlab.ps1` 统一处理配置、注册表、环境变量、机器 PATH 和版本目录探测；缺少 `bin\matlab.exe` 的卸载残留目录不会被选中。
- `scripts/run_matlab.ps1` 只刷新子进程 PATH，不写永久 PATH。
- `scripts/run_experiment.ps1` 将实际 MATLAB root、release 和产品版本写入运行清单。

## 工具箱与冒烟测试

已实际运行并通过：

- Statistics and Machine Learning Toolbox：`fitlm` 线性回归和 `fitctree` 分类；
- Optimization Toolbox：`quadprog`；
- Global Optimization Toolbox：`ga`；
- Symbolic Math Toolbox：符号微分；
- Parallel Computing Toolbox、Mapping Toolbox 等产品存在；
- 现有敏感性与优化收敛绘图配方可生成 PDF、SVG 和 400 dpi PNG。

机器可读证据为 `output/matlab_environment.json`，聚合环境记录为 `output/environment.json`。两份报告必须指向同一个 R2026a 根目录，否则环境审计标记为不匹配。

## 论文级绘图约束

1. 绘图函数显式传入 axes，多面板使用 `tiledlayout`/`nexttile`。
2. 坐标轴必须包含变量名和单位。
3. 颜色与线型/点型双重编码，统一使用 `journal-safe-v1`。
4. 统计标注、置信区间和敏感性指标必须由实验代码计算。
5. 同时导出矢量 PDF/SVG 和 400 dpi PNG。
6. 图件绑定 Figure Contract、源数据、脚本、证据定位和哈希。
7. MATLAB 导出成功后仍需执行 PDF 页面视觉检查。

R2025b 已卸载，不再作为回退版本；相关旧报告或旧 SVG 中的版本字符串仅属于历史产物，不得作为当前环境证据。
