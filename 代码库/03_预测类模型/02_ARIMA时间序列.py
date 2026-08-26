# -*- coding: utf-8 -*-
"""
ARIMA 时间序列预测（study-only reference）

Use when
    单变量、有时间顺序的序列，需要经典统计预测与区间。
Do not use when
    强多变量联动、复杂季节结构未建模、测试窗口被用于定阶或调参。
Quality contract
    先切训练/测试；只在训练窗口定 d/(p,q)；与 last-value baseline 比较；
    最终未来预测可在验证完成后用同一 order 对全量已观测数据重拟合。

正式比赛中应在当前项目 runner 重新实现并采用 rolling/out-of-time 验证。
"""

import itertools
import warnings

import numpy as np
import pandas as pd
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings("ignore")

try:
    import pmdarima as pm
    _HAS_PMD = True
except Exception:
    _HAS_PMD = False


def forecast_metrics(y_true, y_pred):
    """RMSE / MAE / MAPE；MAPE 忽略真实值为 0 的位置。"""
    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    err = y_true - y_pred
    mask = y_true != 0
    return {
        "RMSE": float(np.sqrt(np.mean(err ** 2))),
        "MAE": float(np.mean(np.abs(err))),
        "MAPE(%)": float(np.mean(np.abs(err[mask] / y_true[mask])) * 100)
        if mask.any() else np.nan,
    }


def difference_n(series, d):
    """真正的 d 阶逐次一阶差分，而不是 Series.diff(d)。"""
    out = pd.Series(series, dtype=float)
    for _ in range(d):
        out = out.diff().dropna()
    return out


def adf_test(series, name="序列"):
    s = pd.Series(series, dtype=float).dropna()
    if len(s) < 8:
        return False, np.nan
    stat, pvalue, *_ = adfuller(s)
    stable = bool(pvalue < 0.05)
    print(f"  ADF[{name}]: stat={stat:.4f}, p={pvalue:.4g} -> "
          f"{'平稳' if stable else '未判为平稳'}")
    return stable, float(pvalue)


def find_diff_order(train_series, max_d=3):
    """仅使用训练窗口寻找最小差分阶数。"""
    s = pd.Series(train_series, dtype=float)
    for d in range(max_d + 1):
        diffed = difference_n(s, d)
        stable, _ = adf_test(diffed, name=f"{d}阶差分")
        if stable:
            return d
    return max_d


def ljungbox_test(series, lags=10):
    s = pd.Series(series, dtype=float).dropna()
    use_lag = max(1, min(lags, len(s) // 5))
    res = acorr_ljungbox(s, lags=[use_lag], return_df=True)
    p = float(res["lb_pvalue"].iloc[0])
    print(f"  Ljung-Box(lag={use_lag}): p={p:.4g}")
    return p


def grid_search_order(train_series, d, p_max=4, q_max=4):
    """仅在训练窗口按 AIC 搜索 (p,d,q)。"""
    s = pd.Series(train_series, dtype=float).reset_index(drop=True)
    best_aic, best_order = np.inf, None
    for p, q in itertools.product(range(p_max + 1), range(q_max + 1)):
        if p == 0 and q == 0:
            continue
        try:
            fit = ARIMA(s, order=(p, d, q)).fit()
            if np.isfinite(fit.aic) and fit.aic < best_aic:
                best_aic, best_order = float(fit.aic), (p, d, q)
        except Exception:
            continue
    if best_order is None:
        raise RuntimeError("训练窗口内没有得到可用 ARIMA order")
    print(f"  training-only AIC -> order={best_order}, AIC={best_aic:.2f}")
    return best_order


def _choose_order(train, order=None, use_auto=True, p_max=4, q_max=4):
    if order is not None:
        return tuple(order)
    d = find_diff_order(train)
    diffed = difference_n(train, d)
    ljungbox_test(diffed)
    if use_auto and _HAS_PMD:
        auto = pm.auto_arima(
            train,
            d=d,
            seasonal=False,
            stepwise=True,
            suppress_warnings=True,
            error_action="ignore",
        )
        chosen = tuple(auto.order)
        print(f"  training-only auto_arima -> order={chosen}")
        return chosen
    if use_auto and not _HAS_PMD:
        print("  pmdarima 未安装：显式使用 training-only AIC 网格搜索")
    return grid_search_order(train, d, p_max=p_max, q_max=q_max)


def arima_forecast(
    series,
    test_size=10,
    n_forecast=10,
    order=None,
    use_auto=True,
    p_max=4,
    q_max=4,
):
    """
    训练窗口定阶 -> holdout 评估 -> 与 last-value baseline 比较 ->
    验证后使用同一 order 在全量已观测数据重拟合并预测未来。
    """
    s = pd.Series(series, dtype=float).dropna().reset_index(drop=True)
    if test_size <= 0 or test_size >= len(s) // 2:
        raise ValueError("test_size 必须 >0 且应小于序列长度的一半")
    if n_forecast <= 0:
        raise ValueError("n_forecast 必须 >0")

    train = s.iloc[:-test_size].copy()
    test = s.iloc[-test_size:].copy()

    # 关键：模型选择只看训练窗口
    chosen_order = _choose_order(
        train, order=order, use_auto=use_auto, p_max=p_max, q_max=q_max
    )

    fit_train = ARIMA(train, order=chosen_order).fit()
    pred_test = np.asarray(fit_train.forecast(steps=test_size), dtype=float)
    metrics = forecast_metrics(test.values, pred_test)

    naive_pred = np.repeat(float(train.iloc[-1]), test_size)
    baseline_metrics = forecast_metrics(test.values, naive_pred)

    print("=" * 64)
    print(f"ARIMA{chosen_order} holdout evaluation (order selected on train only)")
    print("  ARIMA  :", {k: round(v, 4) for k, v in metrics.items()})
    print("  LastVal:", {k: round(v, 4) for k, v in baseline_metrics.items()})

    # 验证完成后，固定同一 order 用全部已观测数据重拟合未来模型
    full_fit = ARIMA(s, order=chosen_order).fit()
    fc_res = full_fit.get_forecast(steps=n_forecast)
    forecast = np.asarray(fc_res.predicted_mean, dtype=float)
    conf_int = np.asarray(fc_res.conf_int(alpha=0.05), dtype=float)

    return {
        "method": "ARIMA",
        "status": "ok",
        "selection_scope": "train_only",
        "order": chosen_order,
        "metrics": metrics,
        "baseline_method": "last_value",
        "baseline_metrics": baseline_metrics,
        "test": test.values,
        "pred_test": pred_test,
        "forecast": forecast,
        "conf_int": conf_int,
        "full_series": s.values,
    }


if __name__ == "__main__":
    # 【Study-only example】示例数据只用于理解接口，不是比赛证据。
    rng = np.random.default_rng(0)
    n = 120
    t = np.arange(n)
    series = 20 + 0.4 * t + 5 * np.sin(2 * np.pi * t / 12) + rng.normal(0, 1.5, n)

    result = arima_forecast(series, test_size=12, n_forecast=12, use_auto=False)
    print("order =", result["order"])
    print("future =", np.round(result["forecast"], 3))

    print(
        "\n正式赛题不要只替换 series：应在当前项目中重新定义时间边界、"
        "baseline、指标、rolling/out-of-time 验证和结论范围。"
    )