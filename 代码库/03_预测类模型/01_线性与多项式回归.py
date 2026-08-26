# -*- coding: utf-8 -*-
"""
01 线性与多项式回归 (Linear / Polynomial / Ridge / Lasso Regression)
================================================================
功能：
    面向国赛 C 题的“连续值预测/关系拟合”问题，提供一站式回归模板：
      1. 一元线性回归（含 R²、显著性 t 检验、p 值，基于 statsmodels OLS）
      2. 多元线性回归（含各自变量系数显著性、整体 F 检验、VIF 共线性提示）
      3. 多项式回归（一元 n 次多项式拟合，附最优次数选择思路）
      4. 岭回归 Ridge（L2 正则，缓解共线性）
      5. Lasso 回归（L1 正则，自动做特征选择）
    每个模型均输出预测误差评估：RMSE / MAE / MAPE / R²。

输入格式：
    - 自变量 X：形如 (n_samples, n_features) 的二维数组或 DataFrame（一元时为单列）。
    - 因变量 y：长度为 n_samples 的一维数组/Series。
    - 若为“一元多项式拟合”，X 为一维序列即可。

输出：
    - 各模型的拟合系数、显著性检验结果、误差指标；
    - 若 matplotlib 可用，绘制拟合曲线/预测对比图（无显示环境自动跳过）。

依赖：numpy, pandas, scikit-learn, statsmodels, (可选) matplotlib
运行：python 01_线性与多项式回归.py
"""

import sys
# 兼容 Windows GBK 控制台：把标准输出切到 UTF-8，避免 R² 等字符报 UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import numpy as np
import pandas as pd

from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline

# statsmodels 用于输出显著性（t 检验、p 值、F 检验），是竞赛论文的加分项
import statsmodels.api as sm

# matplotlib 为可选依赖：无图形环境时自动降级为“只算不画”
try:
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['SimHei']   # 中文显示（Windows 黑体）
    plt.rcParams['axes.unicode_minus'] = False
    _HAS_PLT = True
except Exception:
    _HAS_PLT = False


# ----------------------------------------------------------------------
# 通用预测误差评估指标（RMSE / MAE / MAPE / R²）
# ----------------------------------------------------------------------
def regression_metrics(y_true, y_pred):
    """计算回归预测的常用误差指标。

    参数:
        y_true: 真实值序列
        y_pred: 预测值序列
    返回:
        dict，包含 RMSE、MAE、MAPE(%)、R2
    """
    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    err = y_true - y_pred
    rmse = float(np.sqrt(np.mean(err ** 2)))
    mae = float(np.mean(np.abs(err)))
    # MAPE 需排除真实值为 0 的点，避免除零
    mask = y_true != 0
    mape = float(np.mean(np.abs(err[mask] / y_true[mask])) * 100) if mask.any() else np.nan
    # R²（决定系数）
    ss_res = float(np.sum(err ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return {'RMSE': rmse, 'MAE': mae, 'MAPE(%)': mape, 'R2': r2}


def print_metrics(name, y_true, y_pred):
    """打印模型误差指标的辅助函数。"""
    m = regression_metrics(y_true, y_pred)
    print("[%s] RMSE=%.4f  MAE=%.4f  MAPE=%.2f%%  R2=%.4f"
          % (name, m['RMSE'], m['MAE'], m['MAPE(%)'], m['R2']))
    return m


# ----------------------------------------------------------------------
# 1. 一元 / 多元线性回归（statsmodels，带显著性检验）
# ----------------------------------------------------------------------
def ols_regression(X, y, feature_names=None):
    """基于 statsmodels 的最小二乘回归，输出完整统计信息。

    参数:
        X: (n, k) 自变量矩阵；一元时可传入一维数组。
        y: (n,)  因变量。
        feature_names: 自变量名称列表（可选，用于结果可读性）。
    返回:
        result: statsmodels 拟合结果对象（含 .summary(), .params, .pvalues）。
    """
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    y = np.asarray(y, dtype=float).ravel()

    if feature_names is None:
        feature_names = ['x%d' % (i + 1) for i in range(X.shape[1])]

    X_const = sm.add_constant(X)          # 增加截距项
    model = sm.OLS(y, X_const)
    result = model.fit()

    print("=" * 60)
    print("OLS 回归结果（系数 / t 检验 / p 值 / R²）")
    print("=" * 60)
    print("截距 const: 系数=%.4f  p=%.4g" % (result.params[0], result.pvalues[0]))
    for i, name in enumerate(feature_names):
        coef = result.params[i + 1]
        pval = result.pvalues[i + 1]
        sig = '显著' if pval < 0.05 else '不显著'
        print("  %-8s 系数=%.4f  p=%.4g  (%s, 显著性水平0.05)" % (name, coef, pval, sig))
    print("  R2=%.4f  调整R2=%.4f  F检验p值=%.4g"
          % (result.rsquared, result.rsquared_adj, result.f_pvalue))
    return result


def compute_vif(X, feature_names=None):
    """计算方差膨胀因子 VIF，检测多重共线性（VIF>10 视为严重共线）。"""
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    Xc = sm.add_constant(X)
    if feature_names is None:
        feature_names = ['x%d' % (i + 1) for i in range(X.shape[1])]
    print("-" * 40)
    print("VIF 共线性检验（>10 表示严重共线，建议改用岭回归/Lasso）")
    for i, name in enumerate(feature_names):
        vif = variance_inflation_factor(Xc, i + 1)
        print("  %-8s VIF=%.2f" % (name, vif))


# ----------------------------------------------------------------------
# 2. 多项式回归（一元 n 次）
# ----------------------------------------------------------------------
def polynomial_regression(x, y, degree=3):
    """一元多项式回归，返回拟合模型（sklearn Pipeline）与系数。

    参数:
        x: 一维自变量；y: 一维因变量；degree: 多项式最高次数。
    """
    x = np.asarray(x, dtype=float).reshape(-1, 1)
    y = np.asarray(y, dtype=float).ravel()
    model = make_pipeline(PolynomialFeatures(degree), LinearRegression())
    model.fit(x, y)
    y_pred = model.predict(x)
    coefs = model.named_steps['linearregression'].coef_
    intercept = model.named_steps['linearregression'].intercept_
    print("=" * 60)
    print("多项式回归 (degree=%d)" % degree)
    print("  截距=%.4f  各次项系数=%s" % (intercept, np.round(coefs, 4)))
    print_metrics("多项式回归", y, y_pred)
    return model


def select_best_degree(x, y, max_degree=6):
    """通过对比不同次数的调整R²/RMSE，给出建议的多项式次数。"""
    x = np.asarray(x, dtype=float).reshape(-1, 1)
    y = np.asarray(y, dtype=float).ravel()
    print("-" * 40)
    print("多项式次数选择（关注 RMSE 是否还在明显下降，避免过拟合）")
    best_deg, best_rmse = 1, np.inf
    for d in range(1, max_degree + 1):
        model = make_pipeline(PolynomialFeatures(d), LinearRegression())
        model.fit(x, y)
        m = regression_metrics(y, model.predict(x))
        print("  degree=%d  RMSE=%.4f  R2=%.4f" % (d, m['RMSE'], m['R2']))
        if m['RMSE'] < best_rmse:
            best_rmse, best_deg = m['RMSE'], d
    print("  训练集 RMSE 最小的次数=%d（实战建议配合交叉验证防过拟合）" % best_deg)
    return best_deg


# ----------------------------------------------------------------------
# 3. 岭回归 / Lasso（正则化，处理共线性 / 特征选择）
# ----------------------------------------------------------------------
def ridge_regression(X, y, alpha=1.0):
    """岭回归（L2 正则）。alpha 越大正则越强，系数越小。"""
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    y = np.asarray(y, dtype=float).ravel()
    model = Ridge(alpha=alpha)
    model.fit(X, y)
    y_pred = model.predict(X)
    print("=" * 60)
    print("岭回归 Ridge (alpha=%.3g)" % alpha)
    print("  系数=%s  截距=%.4f" % (np.round(model.coef_, 4), model.intercept_))
    print_metrics("Ridge", y, y_pred)
    return model


def lasso_regression(X, y, alpha=0.1):
    """Lasso 回归（L1 正则）。会把不重要特征的系数压缩为 0，实现特征选择。"""
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    y = np.asarray(y, dtype=float).ravel()
    model = Lasso(alpha=alpha, max_iter=10000)
    model.fit(X, y)
    y_pred = model.predict(X)
    nonzero = int(np.sum(model.coef_ != 0))
    print("=" * 60)
    print("Lasso 回归 (alpha=%.3g)" % alpha)
    print("  系数=%s  截距=%.4f  非零特征数=%d"
          % (np.round(model.coef_, 4), model.intercept_, nonzero))
    print_metrics("Lasso", y, y_pred)
    return model


# ----------------------------------------------------------------------
# 演示：自带示例数据
# ----------------------------------------------------------------------
if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   # 多元回归：多个自变量列 → 一个因变量列
    #   X_multi = df[['特征1', '特征2', '特征3']].values   # 自变量矩阵 (n_samples, k)
    #   y_multi = df['目标列'].values                      # 因变量 (n_samples,)
    #   names = ['特征1', '特征2', '特征3']
    #   res2 = ols_regression(X_multi, y_multi, feature_names=names)
    #   # 一元/多项式回归：单列自变量 x + 因变量 y
    #   x1 = df['自变量列'].values ; y1 = df['目标列'].values
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    rng = np.random.RandomState(42)
    n = 100

    print("\n########## 演示 1：一元线性回归 ##########")
    x1 = np.linspace(0, 10, n)
    y1 = 2.5 * x1 + 3 + rng.normal(0, 1.5, n)      # 真实关系 y=2.5x+3
    res1 = ols_regression(x1, y1, feature_names=['x'])
    print_metrics("一元线性", y1, res1.predict(sm.add_constant(x1.reshape(-1, 1))))

    print("\n########## 演示 2：多元线性回归 + 共线性检验 ##########")
    x_a = rng.uniform(0, 10, n)
    x_b = rng.uniform(0, 5, n)
    x_c = x_a * 0.9 + rng.normal(0, 0.3, n)        # 与 x_a 高度相关（制造共线性）
    X_multi = np.column_stack([x_a, x_b, x_c])
    y_multi = 1.5 * x_a + 3.0 * x_b + rng.normal(0, 1.0, n)
    names = ['特征A', '特征B', '特征C']
    res2 = ols_regression(X_multi, y_multi, feature_names=names)
    compute_vif(X_multi, feature_names=names)

    print("\n########## 演示 3：多项式回归 ##########")
    x3 = np.linspace(-3, 3, n)
    y3 = 0.5 * x3 ** 3 - 2 * x3 ** 2 + x3 + rng.normal(0, 2, n)
    select_best_degree(x3, y3, max_degree=6)
    poly_model = polynomial_regression(x3, y3, degree=3)

    print("\n########## 演示 4：岭回归 / Lasso（应对共线性）##########")
    ridge_regression(X_multi, y_multi, alpha=1.0)
    lasso_regression(X_multi, y_multi, alpha=0.1)

    # 可视化（可选）
    if _HAS_PLT:
        try:
            fig, axes = plt.subplots(1, 2, figsize=(13, 5))
            axes[0].scatter(x1, y1, s=15, alpha=0.6, label='样本')
            axes[0].plot(x1, res1.predict(sm.add_constant(x1.reshape(-1, 1))),
                         'r-', lw=2, label='线性拟合')
            axes[0].set_title('一元线性回归'); axes[0].legend(); axes[0].grid(alpha=0.3)

            xs = np.linspace(x3.min(), x3.max(), 200)
            axes[1].scatter(x3, y3, s=15, alpha=0.6, label='样本')
            axes[1].plot(xs, poly_model.predict(xs.reshape(-1, 1)),
                         'r-', lw=2, label='3次多项式拟合')
            axes[1].set_title('多项式回归'); axes[1].legend(); axes[1].grid(alpha=0.3)
            plt.tight_layout()
            plt.savefig('01_回归拟合示例.png', dpi=120)
            print("\n[图已保存] 01_回归拟合示例.png")
        except Exception as e:
            print("绘图跳过：", e)

    print("\n演示完成。把示例数据替换成自己的 X、y 即可复用。")
