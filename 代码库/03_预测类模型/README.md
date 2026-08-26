# 03 预测类模型

> 面向国赛 C 题的**预测类**算法模板库。C 题几乎必考“用历史数据预测未来/拟合变量关系”：
> 销量、价格、需求、产量、趋势外推等。本目录 7 个 `.py` 均**独立可运行**，
> 自带示例数据、全中文注释、`__main__` 演示，并统一输出预测误差 **RMSE / MAE / MAPE(/R²)**，
> 比赛时把示例数据换成自己的数据即可。

## 文件总览

| 文件 | 算法 | 功能简介 |
|------|------|----------|
| `01_线性与多项式回归.py` | 线性/多元/多项式/Ridge/Lasso 回归 | 变量关系拟合与预测，含 R²、系数显著性(t/p)、F 检验、VIF 共线性、正则化 |
| `02_ARIMA时间序列.py` | ARIMA / auto_arima | 单变量时序短期预测：ADF 平稳性、差分定阶、白噪声检验、AIC 定阶、置信区间 |
| `03_灰色预测GM11.py` | 灰色 GM(1,1) | **小样本**（4~15 点）单调趋势预测：级比检验、后验差检验、精度分级 |
| `04_指数平滑.py` | SES / Holt / Holt-Winters | 带趋势/季节的时序预测，三档平滑，自动对比选优 |
| `05_随机森林与XGBoost预测.py` | 随机森林 / XGBoost(退回 GBDT) | **多特征**数值预测 + **特征重要性**（呼应 2025C 数据挖掘类） |
| `06_BP神经网络预测.py` | BP 神经网络 (MLPRegressor) | 中小样本非线性映射预测，轻依赖(无需 tensorflow) |
| `07_LSTM时间序列预测.py` | LSTM (Keras，退回 MLP 滑窗) | 长序列/强非线性时序预测，滑动窗口 + 递归多步 |
| `08_VAR向量自回归.py` | VAR 向量自回归 + Granger 因果 | **多序列联合预测**：销量↔损耗↔价格互相影响时一起建模；ADF平稳化、业务/AIC定阶、Granger因果、对数变换保非负 |
| `09_Prophet风格STL分解回归.py` | STL 分解 + 外生变量回归 | **带外生变量(如价格)的可解释预测**：趋势/季节/回归三成分可加分解，Windows零编译替代 Prophet，输出预测区间 |

## 各文件核心参数与调参建议

### 01 线性与多项式回归
- **核心接口**：`ols_regression`(带显著性)、`polynomial_regression(degree)`、`ridge_regression(alpha)`、`lasso_regression(alpha)`、`compute_vif`。
- **调参**：多项式 `degree` 从低到高试，看 RMSE 是否还明显下降，别一味加次数（过拟合）；`select_best_degree` 辅助选。Ridge/Lasso 的 `alpha` 越大正则越强：**VIF>10（共线性严重）用 Ridge**，**想自动筛特征用 Lasso**（把无用特征系数压 0）。
- **看什么**：p 值 < 0.05 说明该自变量显著；R²/调整 R² 越接近 1 拟合越好。

### 02 ARIMA 时间序列
- **核心接口**：`arima_forecast(series, test_size, n_forecast, order, use_auto)`。
- **定阶 (p,d,q)**：`d` 由 `find_diff_order` 自动差分定（ADF 检验平稳为止，通常 0~2）；`p,q` 由网格搜索按 AIC 最小定，装了 `pmdarima` 则用 `auto_arima` 一步到位。想手动可传 `order=(p,d,q)`。
- **前提**：序列需**非白噪声**（Ljung-Box p<0.05 才值得建模）。适合**平稳或差分后平稳、无强季节性**的中短期预测；有季节性用 SARIMA 或转 04。

### 03 灰色预测 GM(1,1)
- **核心接口**：`gm11_predict(x, n_predict, auto_shift)`。
- **适用**：数据点**很少（4~15）**、近似指数增长/单调、贫信息。这是 GM 的独门场景，其它模型样本不够时它顶上。
- **检验**：先过**级比检验**（越界会自动平移变换）；建完看**后验差比 C**（≤0.35 好）和**小误差概率 P**（≥0.95 好）判精度等级。数据波动大/有季节性**不要用**。

### 04 指数平滑
- **核心接口**：`exp_smoothing_forecast(series, method, seasonal_periods, ...)`，`method ∈ {'ses','holt','hw'}`。
- **选型**：无趋势无季节→**SES**；有趋势无季节→**Holt**；有趋势且有季节→**Holt-Winters**（必填 `seasonal_periods`，如月度=12、周度=7；季节波动随幅度变大用 `seasonal='mul'`）。
- **调参**：平滑系数 alpha/beta/gamma 默认由 statsmodels 自动优化，一般不用手调。

### 08 VAR 向量自回归
- **核心接口**：`fit_var_forecast(df, force_p, test_size, n_forecast, log_transform)`，辅以 `adf_test`、`make_stationary`、`select_order`、`granger_causality`。
- **何时用**：多条序列**互相影响**（销量、损耗、销售次数、价格彼此拉扯）且想**一起预测**、还想看谁是因谁是果时。单序列用 02 ARIMA 即可。
- **定阶**：`force_p` 可按**业务逻辑**直接指定（如蔬菜 2 天保质期 → 2 阶，比纯 AIC 更有说服力）；不填则自动 AIC。
- **三个坑**：① 预测**可能出负**——模板默认 `log_transform=True` 对 ln(1+y) 建模，还原自动非负；② 序列**必须平稳**，`make_stationary` 自动差分并记录阶数用于还原；③ 参数量 ≈ k²p，**变量别贪多**（样本少时 3~4 条为宜）。

### 09 Prophet 风格 STL 分解回归
- **核心接口**：`stl_regression_forecast(y, period, exog, future_exog, n_forecast)`。
- **何时用**：想要 Prophet 的**可解释分解**（趋势+季节+外生回归）但装不上 Prophet（Windows 常编译失败）；尤其适合**用价格解释并预测销量**——传 `exog=价格`、`future_exog=未来价格`，输出里直接给出价格的边际效应系数。
- **产出**：预测均值 + 95% 区间（基于残差 σ）；`period` 为季节周期（日频周季节=7）。
- **升级**：环境若装了 `prophet`，文件末尾注释给了等价调用，可无缝替换。

### 05 随机森林与 XGBoost
- **核心接口**：`random_forest_regression`、`xgboost_regression`，均输出特征重要性；`make_lag_features` 把时序转监督学习。
- **随机森林**：`n_estimators`(树数, 100~500, 越多越稳越慢)、`max_depth`(深度, 样本少设 5~15 防过拟合, None 不限)。少调参、抗过拟合，**首选基线**。
- **XGBoost**：`n_estimators`(轮数)、`learning_rate`(学习率, 0.01~0.1)、`max_depth`(3~8)。**lr 小 + 轮数多**通常更稳更准；精度常高于随机森林。未装 xgboost 自动退回 sklearn GBDT。
- **加分点**：特征重要性图直接回答“哪些因素影响最大”，是 C 题论文常用图。

### 06 BP 神经网络
- **核心接口**：`bp_regression(X, y, hidden_layer_sizes, activation, learning_rate_init, alpha, max_iter)`。
- **调参**：`hidden_layer_sizes` 如 `(64,32)` 两层，层数/神经元越多拟合力越强但小样本易过拟合；`learning_rate_init`(0.001~0.01)过大不收敛、过小慢；`alpha`(L2 正则)增大缓解过拟合；`activation` 用 `relu`/`tanh`。
- **必做**：输入**标准化**（模板内已用 Pipeline 处理）。适合中小样本非线性映射，轻依赖免装 tensorflow。

### 07 LSTM 时间序列
- **核心接口**：`lstm_forecast(series, look_back, test_size, n_forecast, units, epochs, batch_size)`。
- **调参**：`look_back`（时间窗口，用多少历史点预测下一点，5~30，越长可捕捉越长依赖但需更多数据）；`units`（LSTM 单元数 32~128）；`epochs`/`batch_size`（训练轮数/批大小）。**必做归一化到 [0,1]**（模板内已做）。
- **依赖**：需 `pip install tensorflow`（CPU 版即可）。**未装则自动退回 MLP 滑窗**等价演示，保证可跑。数据量小（<100）时 LSTM 易过拟合，建议用 ARIMA/指数平滑。

## 适用 C 题场景与选型速查

| 数据情况 | 推荐方法 | 对应文件 |
|----------|----------|----------|
| 变量间关系拟合、有自变量 | 回归（线性/多项式/正则） | 01 |
| 单变量时序、样本适中、想要置信区间 | ARIMA | 02 |
| **样本极少(4~15)**、单调趋势 | **灰色 GM(1,1)** | 03 |
| 单变量时序、有明显趋势/季节 | 指数平滑 Holt-Winters | 04 |
| **多特征**驱动、要解释影响因素 | **随机森林/XGBoost** | 05 |
| 多特征强非线性、中小样本 | BP 神经网络 | 06 |
| 长序列、强非线性、数据充足 | LSTM | 07 |

**小样本 vs 大样本**：样本 <15 用灰色预测(03)；十几到几百用 ARIMA/指数平滑/回归/随机森林；上千且非线性强再上 BP/LSTM（神经网络吃数据，小样本反而不如树模型和统计方法）。

**短期 vs 长期**：短期（未来几步）ARIMA/指数平滑/LSTM 都行且更准；长期外推优先趋势明确的回归/灰色/Holt，纯 ARIMA 长期会退化为均值。

**比赛策略**：先跑随机森林(05)或 ARIMA(02)拿基线，再针对数据特性换更合适的方法，多模型对比 RMSE/MAPE 择优，论文里同时给误差表和预测图。

## 如何换成国赛附件数据

每个 `.py` 的 `if __name__ == '__main__':` 里都有一段【示例数据】，正上方已加 `👉` 注释块教你替换。通用三步：

1. **注释掉**示例数据整段，取消注释 `👉` 块里的 `pd.read_csv(...)` 那几行。
2. **改文件名与列名**：把 `附件1.csv`、`特征1/目标列/数值列` 换成附件里的真实名称（读入乱码就把 `encoding='gbk'` 换成 `utf-8` 或 `gb18030`）。
3. 直接运行，看控制台的 RMSE / MAE / MAPE 与预测图。

- **回归类(01,05,06)**：`X = df[['特征1','特征2']].values`，`y = df['目标列'].values`。
- **时间序列类(02,03,04,07)**：附件通常**一列日期、一列数值**。务必先 `df['日期列']=pd.to_datetime(df['日期列'])` 解析日期、再 `df.sort_values('日期列')` **按时间排序**，然后取 `series = df['数值列'].values` 一维序列。**顺序错了预测就没意义**。

更完整的读取技巧（多编码尝试、日期解析、缺失值、多附件合并）见 `01_数据预处理与可视化/00_CSV数据导入完全指南.py`。

## 输入输出格式

- **回归类(01,05,06)**：输入特征矩阵 `X` 形如 `(n_samples, n_features)` + 目标 `y` 一维；输出模型、误差指标、（05）特征重要性。
- **时序类(02,03,04,07)**：输入一维时间序列（list/ndarray/Series）；输出未来预测值、测试集误差、（02）置信区间。
- 所有文件统一返回/打印 **RMSE、MAE、MAPE(%)**（回归类另含 R²），可直接抄进论文。
- 若装有 matplotlib，各文件会把预测/拟合图保存为同名 `.png`（无图形环境自动跳过，不影响计算）。

## 依赖库

```bash
# 必需（一般 Anaconda 自带）
pip install numpy pandas scipy scikit-learn statsmodels matplotlib
# 可选（按需，模板均已做“未装自动退回”处理）
pip install pmdarima      # 02 auto_arima 自动定阶
pip install xgboost       # 05 XGBoost（未装退回 GBDT）
pip install tensorflow    # 07 LSTM（未装退回 MLP 滑窗）
```

- Python 3.7+。中文绘图统一设 `plt.rcParams['font.sans-serif']=['SimHei']`。
- Windows 控制台若为 GBK，模板已在文件顶部 `sys.stdout.reconfigure(encoding='utf-8')`，避免 R² 等字符报错。

## 素材来源

在 `好用代码/Mathematical-modeling-model` 的回归分析、ARIMA、灰色预测、Prophet、LSTM、BP、XGBoost、机器学习回归、时间序列分解等素材基础上，重写为标准化、自带示例数据、可直接运行的竞赛模板。
