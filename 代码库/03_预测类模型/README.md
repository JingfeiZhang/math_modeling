# 03 预测与时间序列

> 本目录用于学习预测候选方法。模型选择必须由**预测对象、决策时点可获得信息、时间结构、样本规模和样本外验证**决定，而不是按算法复杂度或单次 RMSE 排名。

## 文件地图

| 文件 | 方法族 | 主要用途 |
|---|---|---|
| `01_线性与多项式回归.py` | 线性/正则/低阶非线性回归 | 有明确协变量的关系预测 |
| `02_ARIMA时间序列.py` | ARIMA | 单变量序列的经典统计预测 |
| `03_灰色预测GM11.py` | GM(1,1) | 极小样本、近单调趋势的候选 |
| `04_指数平滑.py` | SES/Holt/Holt-Winters | 水平、趋势、季节结构 |
| `05_随机森林与XGBoost预测.py` | 树集成 | 多特征非线性关系 |
| `06_BP神经网络预测.py` | MLP | 非线性映射候选 |
| `07_LSTM时间序列预测.py` | LSTM | 数据充足时的序列候选 |
| `08_VAR向量自回归.py` | VAR | 多变量联合动态 |
| `09_Prophet风格STL分解回归.py` | STL + 回归 | 趋势/季节/外生变量分解 |

## 默认模型梯子

```text
persistence / seasonal naive
→ 简单回归、ETS、ARIMA
→ dynamic regression / STL / regularized model
→ tree boosting 等结构化非线性模型
→ 只有数据与验证支持时才考虑神经网络
```

随机森林不是通用 baseline；ARIMA 也不是所有时间序列的默认主模型。

## 预测前必须固定

- 预测对象和单位；
- 预测 horizon / step；
- 决策时点可用特征；
- 时间切分方式；
- 题面主指标和分母；
- 是否需要点预测、区间或分位数。

## 验证优先级

1. rolling / expanding window 或明确的 out-of-time holdout；
2. 与 seasonal naive 等同输出 baseline 比较；
3. 峰值、节假日、极端区间等 failure group；
4. residual bias；
5. 需要区间时检查 coverage 与 width。

定阶、特征选择、标准化和调参都只能在训练窗口内完成。

## 常见误区

- 随机 K 折评估有时间顺序的数据；
- 用完整序列选择 ARIMA 阶数后再报告“测试集”；
- MAPE 在接近零时仍作为唯一指标；
- 特征重要性直接解释为因果；
- 小样本为了“高级”使用 LSTM；
- 未安装某依赖时静默换成语义不同模型并仍沿用原名称。

## 升级触发器

只有出现稳定的结构性残差、非线性、外生驱动或多变量动态，而且更复杂模型在多个时间窗口稳定改善时才保留升级。

## 论文证据

优先：题面主指标表、observed-vs-predicted、prediction interval、error-by-group、residual/calibration。不要把 6 条模型预测曲线叠在一张主图里。

## 回退规则

复杂模型若只在单一窗口略好、波动更大或难以解释，优先保留简单模型并诚实报告不确定性。
