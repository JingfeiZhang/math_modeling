# 07 统计分析算法模板库

面向数学建模国赛的统计分析模板库，用于**数据规律挖掘、显著性检验、降维**。
每个文件独立可运行（UTF-8 编码），自带示例数据与 `if __name__=='__main__'` 演示，
全中文注释，检验类文件均**清晰输出统计量、p 值、以及 α=0.05 下的结论解释**。

## 文件总览

| 文件 | 核心算法 | 功能简介 | 适用 C 题场景 |
|------|---------|---------|--------------|
| `01_描述性统计与分布检验.py` | 描述统计、Shapiro/K-S/D'Agostino、分布拟合 | 均值/方差/偏度/峰度、正态性检验、最优分布拟合 | 任意题目 EDA 第一步，判断是否正态→定参数/非参数 |
| `02_假设检验.py` | t 检验、卡方、Mann-Whitney、Wilcoxon、Fisher | 单/双/配对 t 检验，卡方独立性/拟合优度，非参数检验 | 组间差异比较、分类变量关联、处理效果显著性 |
| `03_方差分析ANOVA.py` | One-way/Two-way ANOVA、Tukey HSD、Kruskal-Wallis | 单/双因素方差分析、事后多重比较、非参数替代 | 多组/多因素效果差异（工艺参数、类别指标差异） |
| `04_相关分析.py` | Pearson/Spearman/Kendall、偏相关 | 相关系数矩阵、显著性 p 值矩阵、偏相关、热力图 | 特征筛选、共线性诊断、指标关联（2022C 成分相关） |
| `05_主成分分析PCA.py` | PCA（sklearn） | 降维、方差解释率、碎石图、载荷分析 | **2022C 降维**、综合评价指标构建、多指标压缩 |
| `06_因子分析.py` | Factor Analysis + varimax | KMO/Bartlett、因子旋转、载荷、因子得分 | 潜在维度发现、问卷/多指标综合评价体系 |
| `07_趋势检验MK.py` | Mann-Kendall、Sen 斜率、UF-UB 突变 | 时间序列趋势检验 + 突变点检测（纯手写） | 时间序列趋势/转折分析（气象、水文、环境、经济） |
| `08_Kendall与秩相关.py` | Pearson/Spearman/Kendall 三者对比 + 手写 τ | 三种相关系数并排算、显著性 p、选用建议、秩散点图 | 小样本/有序/有异常值数据的相关性判断与选型 |
| `09_FPGrowth关联规则.py` | FP-Growth（退回手写 Apriori） | 频繁项集 + 关联规则（支持度/置信度/提升度 lift） | **2023C 品类共现/搭配补货**、购物篮分析、货架陈列、捆绑定价 |
| `10_贝叶斯回归MCMC.py` | 贝叶斯回归 + Metropolis-Hastings | 参数**后验分布**与可信区间（不只点估计），后验预测带区间 | **价格弹性等需带不确定性的参数估计**、小样本、敏感性分析加分项 |

> `04` 侧重相关**矩阵**与偏相关；`08` 是两变量相关的**选型专题**——把 Pearson/Spearman/Kendall
> 三者并排对比并给"该用哪个"的判断，含手写 Kendall τ 帮助理解原理。

## 各文件核心参数与使用条件

### 01 描述性统计与分布检验
- **核心函数**：`describe_stats`、`normality_tests`、`fit_best_distribution`、`qq_plot`
- **使用条件**：Shapiro 适合小样本（3≤n≤5000）；K-S 用样本均值方差作参照；D'Agostino 需 n≥20。
- **判读**：正态性检验 H0=服从正态，p>0.05 不拒绝（近似正态）；偏度≈0 对称，峰度≈0（费雪定义）近正态。

### 02 假设检验
- **核心函数**：`one_sample_ttest`、`two_sample_ttest`（自动 Levene 判方差齐性→Welch）、`paired_ttest`、`mann_whitney`、`wilcoxon_signed`、`chi2_independence`、`chi2_goodness`、`fisher_exact_test`
- **使用条件**：t 检验要求**近似正态**；独立双样本还需**方差齐性**（Levene）；卡方要求期望频数≥5，否则 2×2 用 Fisher。

### 03 方差分析 ANOVA
- **核心函数**：`levene_test`、`one_way_anova`、`one_way_anova_df`、`two_way_anova`、`tukey_posthoc`、`kruskal_wallis`
- **使用条件**：各组**正态**、**方差齐性**、观测独立；违背时用 Kruskal-Wallis。ANOVA 显著后须做 Tukey 事后比较确定差异组。statsmodels 公式要求列名为合法标识符。

### 04 相关分析
- **核心函数**：`pair_correlation`、`corr_matrix`、`corr_pvalue_matrix`、`partial_correlation`、`corr_heatmap`
- **使用条件**：Pearson 要求连续、近似正态、线性；Spearman/Kendall 为非参数（单调关系、稳健）。相关系数须配合 p 值判断显著性。

### 05 主成分分析 PCA
- **核心函数**：`standardize`、`run_pca`、`loading_matrix`、`scree_plot`、`plot_loadings`
- **使用条件**：**PCA 前必须标准化**（消除量纲）；变量间应有相关性。主成分选择：Kaiser 准则（特征值>1）或累计方差≥85%。

### 06 因子分析
- **核心函数**：`adequacy_test`（KMO+Bartlett）、`choose_n_factors`、`run_factor_analysis`（varimax）、`composite_score`、载荷/碎石图
- **使用条件**：**KMO>0.6** 且 **Bartlett p<0.05** 才适合；数据建议标准化。因子数常取特征值>1；varimax 旋转使载荷更易解释。

### 07 趋势检验 MK
- **核心函数**：`mk_trend_test`、`sens_slope`、`mk_mutation_test`、`plot_mutation`
- **使用条件**：**非参数，不要求正态**，对离群值稳健；要求数据近似独立（强自相关需预白化）。|Z|>1.96 时趋势显著（α=0.05）。突变检验取 UF/UB 曲线在置信区间内的交点为突变点。

### 09 FP-Growth 关联规则
- **核心函数**：`mine_rules(transactions, min_support, min_conf)`（装了 `mlxtend` 用 FP-Growth，否则自动退回手写 Apriori）。
- **输入**：`transactions = [['花叶类','辣椒类'], ...]` 每笔交易一个商品列表。
- **看什么**：**support**（共同出现频率）、**confidence**（A 出现时 B 也出现的比例）、**lift**（>1 表正相关，可作联合补货/搭配依据；=1 独立；<1 负相关）。
- **调参**：规则太多→调高 `min_support`/`min_conf`；挖不出→调低。

### 10 贝叶斯回归 MCMC
- **核心函数**：`metropolis(x, y, n_samples, burn, step)`、`summarize`、`predict`。
- **何时用**：需要参数的**不确定性**而非单点值时（价格弹性、需求系数），或小样本想给可信区间做敏感性分析（论文加分）。
- **调参**：看**接受率**——目标 0.2~0.5，过高说明 `step` 太小（走不动）、过低说明太大（老被拒）。`burn` 丢弃前段未收敛样本。先验 `beta_sd` 取大值=弱信息（让数据主导，别把系数往 0 拉）。
- **升级**：装了 `pymc` 可换用 NUTS 采样，文件末尾给了等价写法。

## 如何换成国赛附件数据

统计分析的数据入口很统一：**大多是从附件 DataFrame 里取一列或多列数值**。拿到附件先读进来：

```python
import pandas as pd
df = pd.read_csv('附件1.csv', encoding='gbk')   # 中文乱码就换 utf-8 / gb18030
```

各文件的数据入口写法：

| 文件 | 附件数据 → 分析输入 |
|------|--------------------|
| 01 描述统计/分布检验 | 取一列一维序列：`x = df['指标A'].dropna().values` |
| 02 假设检验 | **按分组列拆分**：`group1 = df[df['组别']=='A']['指标'].values`；配对取两列；卡方用 `pd.crosstab` 造列联表 |
| 03 ANOVA | 按因素列拆成多组；方差分析表/事后比较/双因素直接传长格式 `df`（一列数值 + 一/两列分类） |
| 04 相关分析 | 取多个数值列：`df = df[['指标1','指标2','指标3']].dropna()` 再求相关矩阵 |
| 05 PCA | 取多个数值列组成矩阵 `X = df[[列...]]`（`run_pca` 内部自动标准化） |
| 06 因子分析 | 同 PCA 取多列；先 `adequacy_test` 看 KMO>0.6、Bartlett 显著 |
| 07 MK 趋势检验 | 先按时间排序，取一维序列：`series = df.sort_values('年份')['观测值'].values` |
| 09 FP-Growth | 把订单/流水按单据号分组成列表：`transactions = df.groupby('订单号')['品类'].apply(list).tolist()` |
| 10 贝叶斯 MCMC | 取自变量与因变量两列：`x = df['价格'].values; y = df['销量'].values`（多元把 x 换成设计矩阵） |

要点：**检验/降维类 → `X = df[[列...]].values`；分组检验 → 按分组列筛行拆组；时间序列 → 取一维列并先排序**。每个 `.py` 的主程序里已在示例数据正上方标注了具体替换写法。完整读取/编码/选列/缺失值处理见 [`../01_数据预处理与可视化/00_CSV数据导入完全指南.py`](../01_数据预处理与可视化/00_CSV数据导入完全指南.py)。

## 参数检验 vs 非参数检验 如何选择

| 维度 | 参数检验（t 检验 / ANOVA / Pearson） | 非参数检验（Mann-Whitney / Wilcoxon / Kruskal / Spearman） |
|------|--------------------------------|--------------------------------------|
| 前提 | 数据近似**正态**，方差齐性 | **不要求正态**，基于秩 |
| 数据 | 连续、近似正态 | 偏态、有序、含离群值、小样本 |
| 功效 | 满足前提时功效高 | 稳健但功效略低 |
| 决策 | 先做正态性检验（文件 01）→ 正态且方差齐 → 参数；否则 → 非参数 | |

**对应关系**：独立 t 检验 ↔ Mann-Whitney U；配对 t 检验 ↔ Wilcoxon 符号秩；单因素 ANOVA ↔ Kruskal-Wallis；Pearson ↔ Spearman/Kendall。

## PCA vs 因子分析 区别

| 维度 | 主成分分析 PCA | 因子分析 FA |
|------|--------------|------------|
| 目标 | 最大化方差、**降维压缩** | 解释相关结构、**发现潜在因子** |
| 模型 | 主成分 = 原变量的线性组合 | 观测变量 = 公共因子线性组合 + 特殊因子(误差) |
| 方向 | 变量 → 成分（合成） | 因子 → 变量（潜在驱动） |
| 旋转 | 一般不旋转 | 常用 varimax 旋转以命名因子 |
| 适用 | 降维、综合评价、去共线性 | 潜在维度挖掘、量表结构分析 |
| 前提 | 标准化即可 | KMO>0.6、Bartlett 显著 |

一句话：**PCA 重在降维，FA 重在解释潜在结构**。

## 输入输出格式

- **输入**：一维 `np.ndarray`/`pd.Series`（单变量、时间序列）；多列 `pd.DataFrame`（每列一变量）；列联表 2D array（卡方）。
- **输出**：控制台打印统计量、p 值、α=0.05 中文结论；可视化图保存为 `NN_xxx_示例.png`；降维/得分返回 DataFrame。

## 依赖库

```
numpy, pandas, scipy, matplotlib
statsmodels        # 03 ANOVA 方差分析表、Tukey
scikit-learn       # 05 PCA、标准化
seaborn            # 可选，热力图（缺失时自动降级为 matplotlib）
mlxtend            # 可选，09 FP-Growth（缺失时自动退回手写 Apriori）
```

安装：`pip install numpy pandas scipy matplotlib statsmodels scikit-learn seaborn mlxtend`

> 注：06 因子分析的提取+旋转+因子得分改用成熟库 **statsmodels**（`multivariate.factor.Factor`，主轴法 + varimax），KMO/Bartlett 两项检验用标准公式；不再依赖 `factor_analyzer`——其 0.5.1 与 sklearn≥1.8 有 `force_all_finite` 形参冲突会崩且上游未修。

## 运行方式

```bash
python 01_描述性统计与分布检验.py    # 每个文件均可独立运行演示
```

> 注：Windows 控制台若中文乱码，设置 `set PYTHONIOENCODING=utf-8`（不影响脚本正确性，仅显示问题）。
> 中文绘图已配置 SimHei/Microsoft YaHei 字体。

## 建模流程建议

1. 拿到数据 → `01` 描述统计 + 正态性检验，判断分布。
2. 组间/因素差异 → 正态用 `02`/`03` 参数检验，否则用非参数替代。
3. 指标关联/特征筛选 → `04` 相关分析（含显著性）。
4. 变量过多/共线 → `05` PCA 降维（先标准化）；需解释潜在结构 → `06` 因子分析（先 KMO/Bartlett）。
5. 时间序列趋势/转折 → `07` MK 趋势与突变检验。
