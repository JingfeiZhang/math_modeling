# -*- coding: utf-8 -*-
"""
04 指数平滑预测 (Exponential Smoothing / Holt / Holt-Winters)
================================================================
功能：
    面向国赛 C 题的“带趋势/季节性的时间序列短期预测”：
      1. 一次指数平滑 SES（无趋势无季节，适合平稳序列）；
      2. 二次指数平滑 Holt（含线性趋势）；
      3. 三次指数平滑 Holt-Winters（含趋势 + 季节性，加法/乘法可选）；
      4. 训练/测试评估 + 向后预测 + 预测误差 RMSE / MAE / MAPE。

    基于 statsmodels，同时给出一次平滑的纯 numpy 手写实现（便于论文推导展示）。

输入格式：
    - 一维时间序列（list / np.ndarray / pd.Series）。
    - 使用 Holt-Winters 时需指定 seasonal_periods（季节周期，如月度=12、周度=7）。

输出：
    - 各方法拟合参数、测试集误差、未来预测值。

依赖：numpy, pandas, statsmodels, (可选) matplotlib
运行：python 04_指数平滑.py
"""

import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import warnings
import numpy as np
import pandas as pd
warnings.filterwarnings('ignore')

from statsmodels.tsa.holtwinters import (SimpleExpSmoothing, Holt,
                                         ExponentialSmoothing)

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


# ----------------------------------------------------------------------
# 一次指数平滑：纯 numpy 手写实现（便于论文写公式推导）
# ----------------------------------------------------------------------
def ses_manual(series, alpha=0.3):
    """手写一次指数平滑：S_t = alpha*x_t + (1-alpha)*S_{t-1}。

    平滑系数 alpha 越大越贴近近期数据、越灵敏；越小越平滑。
    返回平滑序列（其最后一个值即为对下一期的预测）。
    """
    x = np.asarray(series, dtype=float)
    s = np.empty_like(x)
    s[0] = x[0]
    for t in range(1, len(x)):
        s[t] = alpha * x[t] + (1 - alpha) * s[t - 1]
    return s


# ----------------------------------------------------------------------
# 三种指数平滑（statsmodels），统一评估 + 预测
# ----------------------------------------------------------------------
def exp_smoothing_forecast(series, method='holt', test_size=12, n_forecast=12,
                           seasonal_periods=12, seasonal='add', trend='add'):
    """指数平滑预测主流程。

    参数:
        method: 'ses'（一次）| 'holt'（二次/趋势）| 'hw'（三次/Holt-Winters）
        test_size: 末尾留作测试的点数
        n_forecast: 向后预测步数
        seasonal_periods: 季节周期（method='hw' 时必填，如 12）
        seasonal: 'add' 加法季节 | 'mul' 乘法季节
        trend: 'add' 加法趋势 | 'mul' 乘法趋势
    返回:
        dict：测试集误差、未来预测值、拟合值。
    """
    s = pd.Series(np.asarray(series, dtype=float))
    train, test = s.iloc[:-test_size], s.iloc[-test_size:]

    if method == 'ses':
        name = '一次指数平滑 SES'
        fit_train = SimpleExpSmoothing(train).fit()
        fit_full = SimpleExpSmoothing(s).fit()
    elif method == 'holt':
        name = '二次指数平滑 Holt(趋势)'
        # Holt 默认加法趋势；trend='mul' 时用 exponential=True 表示指数(乘法)趋势
        exp_trend = (trend == 'mul')
        fit_train = Holt(train, exponential=exp_trend).fit()
        fit_full = Holt(s, exponential=exp_trend).fit()
    elif method == 'hw':
        name = '三次指数平滑 Holt-Winters(趋势+季节)'
        fit_train = ExponentialSmoothing(
            train, trend=trend, seasonal=seasonal,
            seasonal_periods=seasonal_periods).fit()
        fit_full = ExponentialSmoothing(
            s, trend=trend, seasonal=seasonal,
            seasonal_periods=seasonal_periods).fit()
    else:
        raise ValueError("method 需为 'ses' / 'holt' / 'hw'")

    pred_test = np.asarray(fit_train.forecast(test_size))
    metrics = forecast_metrics(test.values, pred_test)
    forecast = np.asarray(fit_full.forecast(n_forecast))

    print("=" * 60)
    print(name)
    # 打印已估计的平滑参数
    params = fit_full.params
    print("  平滑参数: alpha(水平)=%.3f  beta(趋势)=%s  gamma(季节)=%s"
          % (params.get('smoothing_level', float('nan')),
             _fmt(params.get('smoothing_trend')),
             _fmt(params.get('smoothing_seasonal'))))
    print("  测试集: RMSE=%.4f  MAE=%.4f  MAPE=%.2f%%"
          % (metrics['RMSE'], metrics['MAE'], metrics['MAPE(%)']))
    print("  未来 %d 步预测：" % n_forecast, np.round(forecast, 4))
    return {'method': method, 'metrics': metrics, 'forecast': forecast,
            'pred_test': pred_test, 'test': test.values,
            'fitted': np.asarray(fit_full.fittedvalues), 'series': s.values}


def _fmt(v):
    """格式化可能为 None/nan 的平滑参数。"""
    try:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return '—'
        return '%.3f' % v
    except Exception:
        return str(v)


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
    #   series = df['数值列'].values                      # 一维时间序列
    #   # 有季节性时用 method='hw'，并按周期设 seasonal_periods(月度=12/周度=7)
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    rng = np.random.RandomState(7)
    n = 96                                   # 8 年月度数据
    t = np.arange(n)
    trend = 0.5 * t                          # 线性上升趋势
    season = 10 * np.sin(2 * np.pi * t / 12) # 年周期季节性
    noise = rng.normal(0, 2, n)
    series = 50 + trend + season + noise

    print("########## 指数平滑预测演示 ##########")

    print("\n【手写一次平滑，展示公式】alpha=0.3 平滑序列末值=%.4f（即下一期预测）"
          % ses_manual(series, alpha=0.3)[-1])

    print("\n---- 一次指数平滑 SES（适合无趋势序列，此处仅作对比）----")
    r_ses = exp_smoothing_forecast(series, method='ses', test_size=12, n_forecast=12)

    print("\n---- 二次指数平滑 Holt（含趋势）----")
    r_holt = exp_smoothing_forecast(series, method='holt', test_size=12, n_forecast=12)

    print("\n---- 三次指数平滑 Holt-Winters（趋势+季节）----")
    r_hw = exp_smoothing_forecast(series, method='hw', test_size=12, n_forecast=12,
                                  seasonal_periods=12, seasonal='add', trend='add')

    print("\n三种方法测试集 RMSE 对比：SES=%.3f  Holt=%.3f  HW=%.3f  → 有季节性时 HW 最优"
          % (r_ses['metrics']['RMSE'], r_holt['metrics']['RMSE'], r_hw['metrics']['RMSE']))

    if _HAS_PLT:
        try:
            fc = r_hw['forecast']
            plt.figure(figsize=(11, 5))
            plt.plot(range(n), series, 'b-', label='历史数据')
            plt.plot(range(n), r_hw['fitted'], 'g--', alpha=0.7, label='HW拟合')
            plt.plot(range(n, n + len(fc)), fc, 'r--', marker='o', ms=4,
                     label='HW未来预测')
            plt.title('Holt-Winters 指数平滑预测')
            plt.legend(); plt.grid(alpha=0.3); plt.tight_layout()
            plt.savefig('04_指数平滑示例.png', dpi=120)
            print("[图已保存] 04_指数平滑示例.png")
        except Exception as e:
            print("绘图跳过：", e)

    print("\n演示完成。无趋势用SES，有趋势用Holt，有季节性用Holt-Winters。")
