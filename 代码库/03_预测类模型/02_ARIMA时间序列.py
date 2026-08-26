# -*- coding: utf-8 -*-
"""
02 ARIMA 时间序列预测 (ARIMA / auto_arima)
================================================================
功能：
    面向国赛 C 题的“单变量时间序列短期预测”（销量、价格、流量、趋势等）：
      1. ADF 单位根检验判断平稳性；
      2. 自动差分定阶 d（直到序列平稳）；
      3. 白噪声检验（Ljung-Box），判断是否值得建模；
      4. 网格搜索 (p,q) 按 AIC/BIC 定阶；若装了 pmdarima 则用 auto_arima 一步到位；
      5. 训练/测试集评估 + 向后预测 + 置信区间；
      6. 预测误差评估 RMSE / MAE / MAPE。

输入格式：
    - 一维时间序列（list / np.ndarray / pd.Series）。若为 Series，最好带时间索引。
    - 参数 test_size：留作测试的末尾点数；n_forecast：向后预测步数。

输出：
    - 平稳性/白噪声检验结论、最优 (p,d,q)、测试集误差、未来预测值。

依赖：numpy, pandas, statsmodels, (可选) pmdarima, (可选) matplotlib
    可选安装：pip install pmdarima
运行：python 02_ARIMA时间序列.py
"""

import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import warnings
import itertools
import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.stats.diagnostic import acorr_ljungbox

# pmdarima（auto_arima）为可选依赖，未安装时自动退回网格搜索
try:
    import pmdarima as pm
    _HAS_PMD = True
except Exception:
    _HAS_PMD = False

try:
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    _HAS_PLT = True
except Exception:
    _HAS_PLT = False


def forecast_metrics(y_true, y_pred):
    """时间序列预测误差指标：RMSE / MAE / MAPE(%)。"""
    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    err = y_true - y_pred
    rmse = float(np.sqrt(np.mean(err ** 2)))
    mae = float(np.mean(np.abs(err)))
    mask = y_true != 0
    mape = float(np.mean(np.abs(err[mask] / y_true[mask])) * 100) if mask.any() else np.nan
    return {'RMSE': rmse, 'MAE': mae, 'MAPE(%)': mape}


# ----------------------------------------------------------------------
# 1. 平稳性检验 + 自动差分定阶 d
# ----------------------------------------------------------------------
def adf_test(series, name='序列'):
    """ADF 单位根检验。p 值 < 0.05 → 拒绝存在单位根 → 序列平稳。"""
    series = pd.Series(series).dropna()
    stat, pvalue, _, _, crit, _ = adfuller(series)
    stable = pvalue < 0.05
    print("  ADF[%s]: 统计量=%.4f  p值=%.4g  →  %s"
          % (name, stat, pvalue, '平稳' if stable else '非平稳'))
    return stable


def find_diff_order(series, max_d=3):
    """自动寻找使序列平稳的最小差分阶数 d。"""
    print("-" * 50)
    print("平稳性检验 + 差分定阶")
    s = pd.Series(series).astype(float)
    for d in range(max_d + 1):
        diffed = s if d == 0 else s.diff(d).dropna()
        if adf_test(diffed, name='%d阶差分' % d):
            print("  → 选定差分阶数 d=%d" % d)
            return d
    print("  → 达到最大差分阶数仍未平稳，取 d=%d" % max_d)
    return max_d


def ljungbox_test(series, lags=10):
    """白噪声检验：p 值 < 0.05 表示非白噪声（含可建模信息）。"""
    res = acorr_ljungbox(pd.Series(series).dropna(), lags=[lags], return_df=True)
    p = float(res['lb_pvalue'].iloc[0])
    print("  Ljung-Box(lag=%d): p值=%.4g  →  %s"
          % (lags, p, '非白噪声(可建模)' if p < 0.05 else '接近白噪声(建模意义有限)'))
    return p < 0.05


# ----------------------------------------------------------------------
# 2. 定阶 (p, q)：网格搜索按 AIC 最小
# ----------------------------------------------------------------------
def grid_search_order(series, d, p_max=4, q_max=4):
    """网格搜索 (p,q)，返回 AIC 最小的 (p,d,q)。"""
    print("-" * 50)
    print("网格搜索定阶 (p,q)，按 AIC 最小")
    s = pd.Series(series).astype(float).reset_index(drop=True)
    best_aic, best_order = np.inf, (1, d, 0)
    for p, q in itertools.product(range(p_max + 1), range(q_max + 1)):
        if p == 0 and q == 0:
            continue
        try:
            model = ARIMA(s, order=(p, d, q)).fit()
            if model.aic < best_aic:
                best_aic, best_order = model.aic, (p, d, q)
        except Exception:
            continue
    print("  → 最优 order=%s  AIC=%.2f" % (str(best_order), best_aic))
    return best_order


# ----------------------------------------------------------------------
# 3. 训练 + 预测（含 auto_arima 分支）
# ----------------------------------------------------------------------
def arima_forecast(series, test_size=10, n_forecast=10, order=None, use_auto=True):
    """ARIMA 主流程：定阶 → 训练/测试评估 → 全量拟合 → 向后预测。

    参数:
        series: 一维时间序列。
        test_size: 末尾留作测试的点数。
        n_forecast: 训练完成后向后预测的步数。
        order: 手动指定 (p,d,q)；None 则自动定阶。
        use_auto: True 且已装 pmdarima 时用 auto_arima 定阶。
    返回:
        dict：order、测试集误差、未来预测值 forecast、置信区间。
    """
    s = pd.Series(series).astype(float).reset_index(drop=True)

    # ---- 定阶 ----
    if order is None:
        d = find_diff_order(s)
        ljungbox_test(s.diff(d).dropna() if d > 0 else s)
        if use_auto and _HAS_PMD:
            print("-" * 50)
            print("使用 pmdarima.auto_arima 自动定阶")
            auto = pm.auto_arima(s, d=d, seasonal=False, stepwise=True,
                                 suppress_warnings=True, error_action='ignore')
            order = auto.order
            print("  → auto_arima 选定 order=%s" % str(order))
        else:
            if use_auto and not _HAS_PMD:
                print("  (未安装 pmdarima，使用网格搜索定阶；可 pip install pmdarima)")
            order = grid_search_order(s, d)

    # ---- 训练/测试评估 ----
    print("-" * 50)
    print("训练/测试集评估  order=%s" % str(order))
    train, test = s.iloc[:-test_size], s.iloc[-test_size:]
    model = ARIMA(train, order=order).fit()
    pred_test = model.forecast(steps=test_size)
    metrics = forecast_metrics(test.values, pred_test.values)
    print("  测试集: RMSE=%.4f  MAE=%.4f  MAPE=%.2f%%"
          % (metrics['RMSE'], metrics['MAE'], metrics['MAPE(%)']))

    # ---- 全量拟合 + 向后预测 ----
    full_model = ARIMA(s, order=order).fit()
    fc_res = full_model.get_forecast(steps=n_forecast)
    forecast = fc_res.predicted_mean
    conf_int = fc_res.conf_int(alpha=0.05)
    print("-" * 50)
    print("未来 %d 步预测值：" % n_forecast)
    print("  ", np.round(np.asarray(forecast), 4))

    return {'order': order, 'metrics': metrics, 'pred_test': np.asarray(pred_test),
            'test': test.values, 'forecast': np.asarray(forecast),
            'conf_int': np.asarray(conf_int), 'full_series': s.values}


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
    #   result = arima_forecast(series, test_size=12, n_forecast=12, use_auto=True)
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    rng = np.random.RandomState(0)
    n = 120
    # 构造“趋势 + 季节波动 + 噪声”的示例序列（模拟销量/价格）
    t = np.arange(n)
    trend = 0.4 * t
    season = 5 * np.sin(2 * np.pi * t / 12)
    noise = rng.normal(0, 1.5, n)
    series = 20 + trend + season + noise

    print("########## ARIMA 时间序列预测演示 ##########")
    result = arima_forecast(series, test_size=12, n_forecast=12, use_auto=True)

    print("\n最优阶数：", result['order'])
    print("测试集误差：", {k: round(v, 4) for k, v in result['metrics'].items()})

    if _HAS_PLT:
        try:
            full = result['full_series']
            fc = result['forecast']
            ci = result['conf_int']
            plt.figure(figsize=(11, 5))
            plt.plot(range(n), full, 'b-', label='历史数据')
            fx = range(n, n + len(fc))
            plt.plot(fx, fc, 'r--', marker='o', ms=4, label='预测值')
            plt.fill_between(fx, ci[:, 0], ci[:, 1], color='r', alpha=0.2,
                             label='95%置信区间')
            plt.title('ARIMA%s 预测' % str(result['order']))
            plt.legend(); plt.grid(alpha=0.3); plt.tight_layout()
            plt.savefig('02_ARIMA预测示例.png', dpi=120)
            print("[图已保存] 02_ARIMA预测示例.png")
        except Exception as e:
            print("绘图跳过：", e)

    print("\n演示完成。把 series 换成自己的时间序列即可复用。")
