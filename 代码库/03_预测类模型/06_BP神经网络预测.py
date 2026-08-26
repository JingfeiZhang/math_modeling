# -*- coding: utf-8 -*-
"""
06 BP 神经网络回归预测 (BP Neural Network / MLPRegressor)
================================================================
功能：
    面向国赛 C 题的“非线性多因素预测”，用多层感知机(MLP)实现经典 BP 神经网络：
      1. 数据标准化（神经网络对量纲敏感，必做）；
      2. MLPRegressor 训练（反向传播 BP 算法，sklearn 实现，无重型依赖）；
      3. 训练/测试评估 + 预测误差 RMSE / MAE / MAPE / R²；
      4. 演示两类用法：多特征回归、时间序列滞后特征预测。

    选用 sklearn 的 MLPRegressor 而非 tensorflow：安装轻、竞赛机器都有、
    对中小样本足够用。需要更深网络/LSTM 时见 07_LSTM时间序列预测.py。

输入格式：
    - 特征矩阵 X：(n_samples, n_features)，数值型。
    - 目标 y：(n_samples,) 连续值。

输出：
    - 网络结构、迭代收敛情况、测试集误差指标。

依赖：numpy, pandas, scikit-learn, (可选) matplotlib
运行：python 06_BP神经网络预测.py
"""

import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import warnings
import numpy as np
warnings.filterwarnings('ignore')

from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline

try:
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    _HAS_PLT = True
except Exception:
    _HAS_PLT = False


def regression_metrics(y_true, y_pred):
    """回归预测误差：RMSE / MAE / MAPE(%) / R²。"""
    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    err = y_true - y_pred
    rmse = float(np.sqrt(np.mean(err ** 2)))
    mae = float(np.mean(np.abs(err)))
    mask = y_true != 0
    mape = float(np.mean(np.abs(err[mask] / y_true[mask])) * 100) if mask.any() else np.nan
    ss_res = float(np.sum(err ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return {'RMSE': rmse, 'MAE': mae, 'MAPE(%)': mape, 'R2': r2}


# ----------------------------------------------------------------------
# BP 神经网络回归
# ----------------------------------------------------------------------
def bp_regression(X, y, hidden_layer_sizes=(64, 32), activation='relu',
                  max_iter=1000, learning_rate_init=0.01, test_size=0.25,
                  alpha=1e-4):
    """BP 神经网络（MLP）回归。

    关键参数：
        hidden_layer_sizes: 隐藏层结构，如 (64,32) 表示两层。层数/神经元
                            越多拟合能力越强，但小样本易过拟合。
        activation: 激活函数，'relu'(默认)/'tanh'/'logistic'。
        learning_rate_init: 初始学习率，过大不收敛、过小收敛慢。
        alpha: L2 正则强度，增大可缓解过拟合。
        max_iter: 最大迭代轮数。

    说明：内部用 Pipeline 先标准化再训练；预测时自动反标准化输入。
    """
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    y = np.asarray(y, dtype=float).ravel()

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=test_size, random_state=0)

    # 标准化 + MLP。目标 y 也做标准化更稳，这里对 y 单独缩放。
    y_scaler = StandardScaler()
    y_tr_s = y_scaler.fit_transform(y_tr.reshape(-1, 1)).ravel()

    model = make_pipeline(
        StandardScaler(),
        MLPRegressor(hidden_layer_sizes=hidden_layer_sizes, activation=activation,
                     solver='adam', alpha=alpha, learning_rate_init=learning_rate_init,
                     max_iter=max_iter, early_stopping=True, n_iter_no_change=20,
                     random_state=0)
    )
    model.fit(X_tr, y_tr_s)

    # 预测并反标准化
    pred_te = y_scaler.inverse_transform(model.predict(X_te).reshape(-1, 1)).ravel()
    m = regression_metrics(y_te, pred_te)

    mlp = model.named_steps['mlpregressor']
    print("=" * 60)
    print("BP 神经网络回归 (MLPRegressor)")
    print("  网络结构: 输入%d → 隐藏%s → 输出1   激活=%s"
          % (X.shape[1], str(hidden_layer_sizes), activation))
    print("  实际迭代轮数=%d   最终训练损失=%.5f" % (mlp.n_iter_, mlp.loss_))
    print("  测试集: RMSE=%.4f  MAE=%.4f  MAPE=%.2f%%  R2=%.4f"
          % (m['RMSE'], m['MAE'], m['MAPE(%)'], m['R2']))
    return {'model': model, 'y_scaler': y_scaler, 'metrics': m,
            'y_test': y_te, 'pred_test': pred_te}


def make_lag_features(series, n_lags=5):
    """时间序列转监督学习：前 n_lags 个点 → 当前点。"""
    s = np.asarray(series, dtype=float)
    X, y = [], []
    for i in range(n_lags, len(s)):
        X.append(s[i - n_lags:i])
        y.append(s[i])
    return np.array(X), np.array(y)


# ----------------------------------------------------------------------
# 演示
# ----------------------------------------------------------------------
if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   # 多特征非线性回归：多个特征列 → 一个目标列
    #   X = df[['特征1', '特征2', '特征3']].values   # 特征矩阵 (n_samples, n_features)
    #   y = df['目标列'].values                      # 目标 (n_samples,) 连续值
    #   r1 = bp_regression(X, y, hidden_layer_sizes=(64, 32))
    #   # (时序数据可用 make_lag_features(ts, n_lags) 转滞后特征再预测)
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    rng = np.random.RandomState(1)
    n = 500

    print("########## 演示 1：BP 神经网络多特征非线性回归 ##########")
    x1 = rng.uniform(-3, 3, n)
    x2 = rng.uniform(-3, 3, n)
    x3 = rng.uniform(0, 2, n)
    # 强非线性目标，考验网络拟合能力
    y = np.sin(x1) * 3 + x2 ** 2 * 0.5 + np.exp(x3) + rng.normal(0, 0.3, n)
    X = np.column_stack([x1, x2, x3])
    r1 = bp_regression(X, y, hidden_layer_sizes=(64, 32),
                       max_iter=1500, learning_rate_init=0.01)

    print("\n########## 演示 2：BP 网络做时间序列预测 ##########")
    t = np.arange(200)
    ts = 30 + 0.2 * t + 8 * np.sin(2 * np.pi * t / 24) + rng.normal(0, 1, 200)
    Xl, yl = make_lag_features(ts, n_lags=8)
    r2 = bp_regression(Xl, yl, hidden_layer_sizes=(50, 20),
                       max_iter=2000, learning_rate_init=0.005, test_size=0.2)

    if _HAS_PLT:
        try:
            plt.figure(figsize=(10, 5))
            idx = np.argsort(r1['y_test'])
            plt.plot(r1['y_test'][idx], 'b-', label='真实值(排序)')
            plt.plot(r1['pred_test'][idx], 'r.', alpha=0.6, label='BP预测值')
            plt.title('BP 神经网络预测 (测试集, R2=%.3f)' % r1['metrics']['R2'])
            plt.legend(); plt.grid(alpha=0.3); plt.tight_layout()
            plt.savefig('06_BP神经网络示例.png', dpi=120)
            print("[图已保存] 06_BP神经网络示例.png")
        except Exception as e:
            print("绘图跳过：", e)

    print("\n演示完成。BP网络适合中小样本非线性映射；务必先标准化，注意防过拟合。")
