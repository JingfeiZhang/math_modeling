# 01 数据预处理与可视化

> 拿到 C 题数据后的**第一步工具箱**：清洗、变换、诊断、出图。
> 所有文件 UTF-8 编码、全中文注释、自带示例数据和 `__main__` 演示，`python xxx.py` 直接跑通。
> matplotlib 已统一设置 `SimHei` 中文字体。

## 文件总览

| 文件 | 解决什么问题 | 何时用 |
|------|-------------|--------|
| `01_缺失值与异常值处理.py` | 数据有空值、有离群点 | 数据清洗，几乎必用 |
| `02_数据标准化与变换.py` | 量纲不一、指标方向不一、数据偏态 | 评价/回归/聚类前 |
| `03_相关性与共线性.py` | 变量间关系、多重共线性诊断 | 特征筛选、回归前 |
| `04_常用可视化模板.py` | 论文配图 | 全流程，写论文时 |

---

## 01_缺失值与异常值处理.py

| 函数 | 功能简介 | 核心参数与调参建议 |
|------|---------|-------------------|
| `detect_missing` | 统计各列缺失数量与比例 | 无。缺失>30% 的列考虑直接删 |
| `drop_missing` | 删除含缺失的行/列 | `axis`(0行/1列)、`how`(any/all)、`thresh` |
| `fill_stat` | 均值/中位数/众数填充 | `method`：正态用 mean，有异常用 median，分类用 mode |
| `fill_ffill_bfill` | 前向/后向填充 | `method`(ffill/bfill)，时间序列首选，可两者连用补首尾 |
| `fill_interpolate` | 线性/二次/三次插值 | `method`(linear/quadratic/cubic/polynomial)，有趋势数据更贴合 |
| `detect_outlier_3sigma` | 3σ 准则检测异常 | `n_sigma`(默认3)，要求数据近似正态 |
| `detect_outlier_iqr` | 箱线图 IQR 准则 | `k`(默认1.5，极端异常用3)，最稳健、无分布假设 |
| `detect_outlier_lof` | LOF 局部离群因子 | `n_neighbors`(默认20，样本少调小)、`contamination` |
| `remove_outlier_iqr` | 按 IQR 逐列剔除异常行 | `k`，同上 |

- 适用 C 题场景：几乎所有 C 题（2020 信贷、2023 蔬菜定价、2025 数据挖掘）第一步都要清洗真实数据。
- 输入：`DataFrame`（数值列，含缺失/异常）。输出：处理后 `DataFrame` / 异常布尔掩码 + 箱线图与 3σ 散点图。
- 依赖：`numpy pandas matplotlib scikit-learn`

## 02_数据标准化与变换.py

| 函数 | 功能简介 | 核心参数与调参建议 |
|------|---------|-------------------|
| `min_max_scale` | 归一化到 [0,1] | 无。对异常值敏感，先清洗再用 |
| `z_score_scale` | z-score 标准化(均值0方差1) | 无。回归/聚类/PCA 首选 |
| `vector_normalize` | 向量归一化(占比) | 无。TOPSIS 专用，避免除零 |
| `to_max` | 极小型指标正向化 | 无。成本、能耗类"越小越好"指标 |
| `to_middle` | 中间型指标正向化 | `best` 最优值(默认中位数) |
| `to_interval` | 区间型指标正向化 | `a,b` 最优区间上下界 |
| `log_transform` | 对数变换 | `shift`(有非正值时平移)，压缩右偏长尾 |
| `boxcox_transform` | Box-Cox 自动寻优变换 | 要求数据>0，返回最优 lambda |

- 适用 C 题场景：评价类模型（熵权法/TOPSIS，2020信贷评级）需先正向化+无量纲化；回归/机器学习前需标准化；数据偏态时用 log/Box-Cox 改善。
- 输入：向量(1D array/list) 或矩阵(2D array，行样本列指标)。输出：变换后数组（Box-Cox 附带 lambda）+ 变换前后偏度直方图。
- 依赖：`numpy scipy scikit-learn matplotlib`

## 03_相关性与共线性.py

| 函数 | 功能简介 | 核心参数与调参建议 |
|------|---------|-------------------|
| `corr_matrix` | 相关系数矩阵 | `method`：pearson(线性/正态)、spearman(单调/抗异常) |
| `corr_heatmap` | 相关系数热力图 | `method`、`cmap`；\|r\|>0.8 提示强相关 |
| `corr_test` | 单对变量相关+p值 | `method`；p<0.05 显著相关 |
| `calc_vif` | 计算各变量 VIF | 无。VIF<10 可接受，>100 严重共线 |
| `plot_vif` | VIF 柱状图+阈值线 | 无。直观看哪些变量共线 |
| `drop_high_vif` | 逐步剔除高 VIF 变量 | `thresh`(默认10) |

- 适用 C 题场景：回归建模前判断自变量是否共线（2022玻璃成分相关性、2023销量影响因素分析）；特征筛选去冗余。
- 输入：`DataFrame`（数值型自变量）。输出：相关矩阵 / VIF 表 + 热力图与 VIF 柱状图。
- 依赖：`numpy pandas matplotlib seaborn statsmodels`

## 04_常用可视化模板.py

| 函数 | 图型 | 核心参数 | 典型用途 |
|------|------|---------|---------|
| `plot_line` | 折线图 | `x, ys, labels` | 趋势/时间序列，支持多条线 |
| `plot_bar` | 柱状图 | `categories, values, labels` | 分类对比，支持分组簇状 |
| `plot_scatter` | 散点图 | `x, y, c` | 两变量关系，c 分类着色 |
| `plot_box` | 箱线图 | `df` | 分布与异常值 |
| `plot_heatmap` | 热力图 | `matrix, cmap, annot` | 相关矩阵/二维强度 |
| `plot_radar` | 雷达图 | `values, dims, labels` | 多维指标对比(评价类) |
| `plot_dual_axis` | 双轴图 | `x, y1, y2` | 两个不同量纲指标同图 |

- 适用 C 题场景：全流程论文配图。雷达图配合评价类模型展示方案对比，双轴图展示销量-价格等关系，热力图展示相关性。
- 输入：见各函数 docstring（array/list/DataFrame）。输出：matplotlib 图窗（可加 `plt.savefig` 导出 svg/png）。
- 依赖：`numpy pandas matplotlib seaborn`

---

## 如何换成国赛附件数据

国赛数据通过题目附件（`.csv` / `.xlsx`）给出。每个模板的 `if __name__ == '__main__':` 里都有一段自造的**示例数据**用于演示，比赛时把它换成读取你自己附件的代码即可。通用三步：

1. **找示例数据**：打开目标 `.py`，翻到文件末尾 `if __name__ == '__main__':`，里面有醒目的 `👉 用你自己的国赛附件数据` 注释块，紧跟其后的就是【示例数据】。
2. **注释掉示例**：选中【示例数据】整段按 `Ctrl+/` 注释掉。
3. **换 read_csv 并对齐变量名**：取消注释注释块里给的模板代码，把 `pd.read_csv('附件1.csv', encoding='gbk')` 的文件名改成你的附件，再按提示把列名换成你附件里的真实列名——注释块里用的变量名（如 `df`、`X`、`data`、各列名列表）已和该模板后续代码完全一致，改完即可运行。

小贴士：读入乱码就把 `encoding` 在 `gbk` / `utf-8` / `gb18030` 之间换；后续演示里若直接引用了某列名（如 `df_filled['销量']`），也要一并改成自己的列名。完整的读取姿势、Excel/多表/中文表头等各种坑，详见 `00_CSV数据导入完全指南.py`（可直接运行看演示）。

---

## 环境依赖

```bash
pip install numpy pandas scipy scikit-learn matplotlib seaborn statsmodels
```

Python 3.7+（本库在 Python 3.7 / numpy 1.21 / pandas 1.3 / sklearn 1.0 / statsmodels 0.13 下验证通过）。

## 使用流程

1. 复制目标 `.py`，把 `__main__` 里的示例数据换成自己的（`pd.read_csv('data.csv', encoding='gbk')`）。
2. 先 `01` 清洗（缺失+异常）→ 再 `03` 看相关性/共线性筛变量 → 需要评价/建模时用 `02` 标准化正向化 → 全程用 `04` 出图。
3. 直接 `python xxx.py` 跑通验证，再改参数套自己的数据。
