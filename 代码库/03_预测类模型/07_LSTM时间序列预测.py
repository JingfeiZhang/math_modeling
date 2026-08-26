# -*- coding: utf-8 -*-
"""
07 LSTM 时间序列预测 (Long Short-Term Memory)
================================================================
功能：
    面向国赛 C 题的“长序列、强非线性时间序列预测”（长期依赖、多步预测）：
      1. 滑动时间窗口构造样本（用过去 look_back 个时刻预测下一时刻）；
      2. 数据归一化（LSTM 对量纲极敏感，必做 MinMax 到 [0,1]）；
      3. 搭建 LSTM 网络（Keras）训练；
      4. 训练/测试评估 + 向后多步递归预测 + 误差 RMSE / MAE / MAPE。

    重型依赖说明：LSTM 需要 TensorFlow/Keras。竞赛机器可能未装，
    安装命令：pip install tensorflow          （CPU 版即可，约几百 MB）
    若未安装 tensorflow，本脚本自动退回“sklearn MLP 滑窗预测”作为等价演示，
    保证文件可直接运行；正式使用 LSTM 时请安装 tensorflow 后走 LSTM 分支。

输入格式：
    - 一维时间序列（list / np.ndarray）。
    - look_back：时间窗口长度（用多少历史点预测下一点，常见 5~30）。

输出：
    - 训练收敛信息、测试集误差、向后多步预测结果。

依赖：numpy, scikit-learn, (可选/推荐) tensorflow, (可选) matplotlib
运行：python 07_LSTM时间序列预测.py
"""

import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import os
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')   # 屏蔽 TF 冗余日志

import warnings
import numpy as np
warnings.filterwarnings('ignore')

from sklearn.preprocessing import MinMaxScaler

# TensorFlow/Keras 为可选重型依赖
try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.callbacks import EarlyStopping
    _HAS_TF = True
except Exception:
    _HAS_TF = False

# 未装 TF 时的退路
from sklearn.neural_network import MLPRegressor

try:
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    _HAS_PLT = True
except Exception:
    _HAS_PLT = False


def forecast_metrics(y_true, y_pred):
    """预测误差指标：RMSE / MAE / MAPE(%)。"""
    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    err = y_true - y_pred
    rmse = float(np.sqrt(np.mean(err ** 2)))
    mae = float(np.mean(np.abs(err)))
    mask = y_true != 0
    mape = float(np.mean(np.abs(err[mask] / y_true[mask])) * 100) if mask.any() else np.nan
    return {'RMSE': rmse, 'MAE': mae, 'MAPE(%)': mape}


def create_dataset(series_scaled, look_back=10):
    """滑动窗口构造监督样本：X=[t-look_back, ..., t-1] → y=t。"""
    X, y = [], []
    for i in range(look_back, len(series_scaled)):
        X.append(series_scaled[i - look_back:i, 0])
        y.append(series_scaled[i, 0])
    return np.array(X), np.array(y)


# ----------------------------------------------------------------------
# LSTM 主流程
# ----------------------------------------------------------------------
def lstm_forecast(series, look_back=12, test_size=20, n_forecast=12,
                  units=50, epochs=100, batch_size=16):
    """LSTM 时间序列预测（未装 tensorflow 时自动退回 MLP 滑窗）。

    关键参数：
        look_back: 时间窗口长度（越长可捕捉越长依赖，但需更多数据）。
        units: LSTM 隐藏单元数（32~128 常用）。
        epochs / batch_size: 训练轮数 / 批大小。
        test_size: 末尾留作测试的点数；n_forecast: 向后递归预测步数。
    """
    series = np.asarray(series, dtype=float).reshape(-1, 1)

    # 归一化到 [0,1]（用全序列拟合 scaler；严谨做法可只用训练段拟合）
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(series)

    X, y = create_dataset(scaled, look_back)
    split = len(X) - test_size
    X_tr, X_te = X[:split], X[split:]
    y_tr, y_te = y[:split], y[split:]

    if _HAS_TF:
        engine = 'LSTM (TensorFlow/Keras)'
        # LSTM 需要 3D 输入：(样本数, 时间步, 特征数)
        X_tr3 = X_tr.reshape(X_tr.shape[0], look_back, 1)
        X_te3 = X_te.reshape(X_te.shape[0], look_back, 1)
        model = Sequential([
            LSTM(units, activation='tanh', input_shape=(look_back, 1)),
            Dropout(0.1),
            Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse')
        es = EarlyStopping(monitor='loss', patience=15, restore_best_weights=True)
        model.fit(X_tr3, y_tr, epochs=epochs, batch_size=batch_size,
                  verbose=0, callbacks=[es])
        pred_te_s = model.predict(X_te3, verbose=0).ravel()

        def _predict_window(window):        # window: (look_back,)
            return float(model.predict(window.reshape(1, look_back, 1),
                                       verbose=0).ravel()[0])
    else:
        engine = 'MLP 滑窗 (未装 tensorflow 的退路, 结构等价演示)'
        model = MLPRegressor(hidden_layer_sizes=(units, units // 2),
                             activation='tanh', max_iter=1500,
                             early_stopping=True, random_state=0)
        model.fit(X_tr, y_tr)
        pred_te_s = model.predict(X_te)

        def _predict_window(window):
            return float(model.predict(window.reshape(1, -1)).ravel()[0])

    # 反归一化，计算测试集误差
    pred_te = scaler.inverse_transform(pred_te_s.reshape(-1, 1)).ravel()
    true_te = scaler.inverse_transform(y_te.reshape(-1, 1)).ravel()
    m = forecast_metrics(true_te, pred_te)

    # 向后递归多步预测：每预测一步，把预测值滚入窗口
    window = scaled[-look_back:, 0].copy()
    future_s = []
    for _ in range(n_forecast):
        nxt = _predict_window(window)
        future_s.append(nxt)
        window = np.append(window[1:], nxt)
    future = scaler.inverse_transform(np.array(future_s).reshape(-1, 1)).ravel()

    print("=" * 60)
    print("时间序列预测引擎：%s" % engine)
    print("  时间窗口 look_back=%d   隐藏单元=%d" % (look_back, units))
    print("  测试集: RMSE=%.4f  MAE=%.4f  MAPE=%.2f%%"
          % (m['RMSE'], m['MAE'], m['MAPE(%)']))
    print("  未来 %d 步预测：" % n_forecast, np.round(future, 4))
    if not _HAS_TF:
        print("  提示：正式使用 LSTM 请先 pip install tensorflow")

    return {'engine': engine, 'metrics': m, 'true_test': true_te,
            'pred_test': pred_te, 'forecast': future, 'series': series.ravel(),
            'test_size': test_size}


# ----------------------------------------------------------------------
# 演示
# ----------------------------------------------------------------------
if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   # 附件通常一列日期、一列数值。务必按时间排序后取出一维序列：
    #   df['日期列'] = pd.to_datetime(df['日期列'])       # 解析日期
    #   df = df.sort_values('日期列')                     # 【务必按时间排序】
    #   series = df['数值列'].values                      # 一维时间序列(内部会自动归一化)
    #   res = lstm_forecast(series, look_back=20, test_size=30, n_forecast=15)
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    rng = np.random.RandomState(3)
    n = 300
    t = np.arange(n)
    # 构造带趋势 + 双周期 + 噪声的长序列（考验长期依赖建模）
    series = (60 + 0.15 * t
              + 12 * np.sin(2 * np.pi * t / 30)
              + 5 * np.sin(2 * np.pi * t / 7)
              + rng.normal(0, 1.5, n))

    print("########## LSTM 时间序列预测演示 ##########")
    res = lstm_forecast(series, look_back=20, test_size=30, n_forecast=15,
                        units=50, epochs=80, batch_size=16)

    if _HAS_PLT:
        try:
            full = res['series']
            ts = res['test_size']
            plt.figure(figsize=(12, 5))
            plt.plot(range(n), full, 'b-', alpha=0.7, label='历史数据')
            # 测试段预测对齐
            test_x = range(n - ts, n)
            plt.plot(test_x, res['pred_test'], 'g--', label='测试集预测')
            fc = res['forecast']
            plt.plot(range(n, n + len(fc)), fc, 'r--', marker='o', ms=4,
                     label='未来预测')
            plt.title('LSTM 时间序列预测 (%s)' % res['engine'])
            plt.legend(); plt.grid(alpha=0.3); plt.tight_layout()
            plt.savefig('07_LSTM预测示例.png', dpi=120)
            print("[图已保存] 07_LSTM预测示例.png")
        except Exception as e:
            print("绘图跳过：", e)

    print("\n演示完成。长序列/强非线性优先 LSTM(需 tensorflow)；数据少则用 ARIMA/指数平滑。")
