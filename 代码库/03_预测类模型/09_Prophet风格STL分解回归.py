# -*- coding: utf-8 -*-
"""
Prophet 风格：STL 分解 + 外生变量回归（可加式趋势/季节/回归）
================================================================
功能：
    复现 Facebook Prophet 的核心思想——把序列拆成
        y(t) = 趋势 g(t) + 季节 s(t) + 外生回归 β·x(t) + 残差
    但只用 statsmodels + numpy，Windows 上零编译、必跑（Prophet 常装不上）。
    适合“带价格等外生变量的销量预测”（如 2023C 用价格解释销量）。
    若环境已装 prophet，末尾注释给出等价调用，可直接替换升级。

做法：
    1) STL 稳健分解出 趋势 + 周期季节（自动扣除）
    2) 对 (趋势+残差) 用 线性回归 拟合 时间 + 外生变量
    3) 预测时：趋势用回归外推、季节用历史同相位复用、外生用给定的未来值
    支持返回近似预测区间（基于残差标准差 ±1.96σ）。

输入：
    y            : pd.Series，DatetimeIndex 或等间隔数值索引
    period       : 季节周期（周数据日频=7）
    exog         : 训练期外生变量 DataFrame（可 None）
    future_exog  : 未来期外生变量 DataFrame（与预测步数等长；无则自动持平/线性延展）

输出：预测均值 + 上下界 DataFrame；打印各成分贡献与拟合优度

依赖：numpy, pandas, statsmodels（STL、OLS）
运行：PYTHONIOENCODING=utf-8 python 09_Prophet风格STL分解回归.py
================================================================
"""
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL
import statsmodels.api as sm

try:
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
    plt.rcParams['axes.unicode_minus'] = False
    _HAS_PLT = True
except Exception:
    _HAS_PLT = False


def stl_regression_forecast(y, period=7, exog=None, future_exog=None,
                            n_forecast=7, seasonal_deg=1):
    """STL 分解 + 趋势/外生回归预测。返回含 预测/下界/上界 的 DataFrame。"""
    y = pd.Series(np.asarray(y, dtype=float))
    n = len(y)

    # 1) STL 稳健分解
    stl = STL(y.values, period=period, robust=True).fit()
    trend = stl.trend
    seasonal = stl.seasonal
    resid = stl.resid
    deseason = y.values - seasonal          # 去季节后的序列 = 趋势 + 残差

    # 2) 用 时间 t + 外生变量 拟合去季节序列
    t = np.arange(n)
    X_cols = [t]
    names = ['t']
    if exog is not None:
        exog = pd.DataFrame(exog).reset_index(drop=True)
        for c in exog.columns:
            X_cols.append(exog[c].values.astype(float))
            names.append(str(c))
    X = np.column_stack(X_cols)
    X = sm.add_constant(X)
    ols = sm.OLS(deseason, X).fit()
    print(f"[拟合] 去季节回归 R²={ols.rsquared:.4f}, 调整R²={ols.rsquared_adj:.4f}")
    coef = dict(zip(['const'] + names, ols.params))
    print("  系数：", {k: round(v, 4) for k, v in coef.items()})
    if exog is not None:
        for c in exog.columns:
            print(f"  -> 外生变量[{c}] 边际效应 = {coef[str(c)]:+.4f}（每单位变化对去季节销量的影响）")

    # 3) 构造未来外生变量
    if exog is not None:
        if future_exog is None:                       # 未给则用末值持平
            future_exog = pd.DataFrame(
                np.tile(exog.iloc[-1].values, (n_forecast, 1)), columns=exog.columns)
            print("  [提示] 未提供 future_exog，默认外生变量持平于最后一期")
        future_exog = pd.DataFrame(future_exog).reset_index(drop=True)

    # 4) 外推：趋势由回归给出，季节按周期复用历史同相位
    tf = np.arange(n, n + n_forecast)
    Xf_cols = [tf]
    if exog is not None:
        for c in exog.columns:
            Xf_cols.append(future_exog[c].values.astype(float))
    Xf = sm.add_constant(np.column_stack(Xf_cols), has_constant='add')
    trend_resid_pred = ols.predict(Xf)
    season_future = np.array([seasonal[(n + i) % period - period] for i in range(n_forecast)])
    # 更稳妥：用最后一个完整周期的季节形状
    last_cycle = seasonal[-period:]
    season_future = np.array([last_cycle[i % period] for i in range(n_forecast)])

    yhat = trend_resid_pred + season_future
    sigma = np.std(resid, ddof=1)
    out = pd.DataFrame({
        '预测': yhat,
        '下界95': yhat - 1.96 * sigma,
        '上界95': yhat + 1.96 * sigma,
    })
    out = out.clip(lower=0)          # 销量非负兜底
    print(f"\n[未来 {n_forecast} 步预测]（残差σ={sigma:.3f}）")
    print(out.round(3).to_string())
    return out, stl, ols


if __name__ == '__main__':
    # 演示：150 天销量 = 趋势 + 周季节 + 价格负向影响 + 噪声
    rng = np.random.default_rng(0)
    n = 150
    t = np.arange(n)
    price = 6 + 1.5 * np.sin(t / 20) + rng.normal(0, 0.3, n)   # 波动的价格
    trend = 40 + 0.15 * t
    season = 8 * np.sin(2 * np.pi * t / 7)
    y = trend + season - 4.0 * (price - price.mean()) + rng.normal(0, 3, n)
    y = np.clip(y, 0, None)

    exog = pd.DataFrame({'价格': price})
    # 未来一周价格：假设促销降价到 5.5
    future_price = pd.DataFrame({'价格': np.full(7, 5.5)})

    print("=" * 60)
    print("Prophet 风格 STL 分解 + 价格外生回归 演示")
    print("=" * 60)
    out, stl, ols = stl_regression_forecast(
        pd.Series(y), period=7, exog=exog, future_exog=future_price, n_forecast=7)

    if _HAS_PLT:
        try:
            fig, axes = plt.subplots(4, 1, figsize=(11, 9), sharex=False)
            axes[0].plot(y, color='steelblue'); axes[0].set_title('原始销量')
            axes[1].plot(stl.trend, color='darkorange'); axes[1].set_title('STL 趋势')
            axes[2].plot(stl.seasonal, color='green'); axes[2].set_title('STL 周季节')
            axes[3].plot(range(n, n + 7), out['预测'], 'r--o', ms=4, label='预测')
            axes[3].fill_between(range(n, n + 7), out['下界95'], out['上界95'],
                                 alpha=0.2, color='red', label='95%区间')
            axes[3].set_title('未来一周预测'); axes[3].legend()
            for ax in axes:
                ax.grid(alpha=0.3)
            plt.tight_layout()
            plt.savefig('Prophet风格_分解预测.png', dpi=120, bbox_inches='tight')
            print("\n[图] 已保存 Prophet风格_分解预测.png")
        except Exception as e:
            print(f"绘图跳过: {e}")

    # ===== 若已安装真正的 Prophet，可直接替换为： =====
    # from prophet import Prophet
    # dfp = pd.DataFrame({'ds': pd.date_range('2023-01-01', periods=n), 'y': y, '价格': price})
    # m = Prophet(weekly_seasonality=True); m.add_regressor('价格'); m.fit(dfp)
    # future = m.make_future_dataframe(periods=7); future['价格'] = ...; m.predict(future)
