# -*- coding: utf-8 -*-
"""
STL 分解 + 外生变量回归（study-only reference）

结构：y(t) = trend/regression(t, x_t) + seasonal(t) + residual。

Academic boundaries
    - 先做尾部 holdout，再在验证后用全量已观测数据重拟合未来模型；
    - 外生变量系数是条件预测关联，不自动是因果“边际效应”；
    - 未来存在外生变量时必须显式提供 future_exog，不静默假设末值持平；
    - 近似区间基于残差尺度，只是简单不确定性参考，正式使用应检查覆盖率；
    - 与 seasonal-naive baseline 比较。
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.seasonal import STL


@dataclass
class STLRegressionFit:
    stl: object
    ols: object
    period: int
    seasonal_cycle: np.ndarray
    exog_columns: list[str]
    n_train: int
    residual_sigma: float


def forecast_metrics(y_true, y_pred):
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


def _validate_exog(exog, n, name):
    if exog is None:
        return None
    frame = pd.DataFrame(exog).reset_index(drop=True)
    if len(frame) != n:
        raise ValueError(f"{name} 行数必须与对应 y 长度一致")
    if frame.isna().any().any():
        raise ValueError(f"{name} 含缺失；模板不自动插补")
    return frame.astype(float)


def _fit_model(y_train, period, exog_train=None):
    y_train = pd.Series(np.asarray(y_train, dtype=float)).reset_index(drop=True)
    if period < 2:
        raise ValueError("period 必须 >= 2")
    if len(y_train) < max(3 * period, 20):
        raise ValueError("训练样本过少，无法可靠进行当前 STL 分解；请简化模型")

    exog_train = _validate_exog(exog_train, len(y_train), "exog_train")

    stl = STL(y_train.to_numpy(), period=period, robust=True).fit()
    deseason = y_train.to_numpy() - stl.seasonal
    t = np.arange(len(y_train), dtype=float)

    columns = [t]
    names = ["t"]
    exog_columns: list[str] = []
    if exog_train is not None:
        exog_columns = [str(c) for c in exog_train.columns]
        for c in exog_train.columns:
            columns.append(exog_train[c].to_numpy(dtype=float))
            names.append(str(c))

    X = sm.add_constant(np.column_stack(columns), has_constant="add")
    ols = sm.OLS(deseason, X).fit()
    seasonal_cycle = np.asarray(stl.seasonal[-period:], dtype=float)
    sigma = float(np.std(stl.resid, ddof=1))

    print(f"STL-regression train R2={ols.rsquared:.4f}, adj.R2={ols.rsquared_adj:.4f}")
    coef = dict(zip(["const", *names], ols.params))
    for c in exog_columns:
        print(
            f"  {c}: conditional predictive coefficient={coef[c]:+.4f} "
            "(非因果效应结论)"
        )

    return STLRegressionFit(
        stl=stl,
        ols=ols,
        period=period,
        seasonal_cycle=seasonal_cycle,
        exog_columns=exog_columns,
        n_train=len(y_train),
        residual_sigma=sigma,
    )


def _predict(fit: STLRegressionFit, n_steps, future_exog=None):
    if n_steps <= 0:
        raise ValueError("n_steps 必须 > 0")

    if fit.exog_columns:
        if future_exog is None:
            raise ValueError(
                "模型使用了外生变量，必须显式提供对应未来期 exog；"
                "模板不会假设未来外生变量自动持平。"
            )
        future_exog = pd.DataFrame(future_exog).reset_index(drop=True)
        missing = [c for c in fit.exog_columns if c not in future_exog.columns]
        if missing:
            raise ValueError(f"future_exog 缺少列: {missing}")
        future_exog = future_exog[fit.exog_columns].astype(float)
        if len(future_exog) != n_steps:
            raise ValueError("future_exog 行数必须等于预测步数")
    elif future_exog is not None:
        raise ValueError("训练模型没有使用外生变量，不应额外传 future_exog")

    t_future = np.arange(fit.n_train, fit.n_train + n_steps, dtype=float)
    columns = [t_future]
    if fit.exog_columns:
        for c in fit.exog_columns:
            columns.append(future_exog[c].to_numpy(dtype=float))

    Xf = sm.add_constant(np.column_stack(columns), has_constant="add")
    deseason_pred = np.asarray(fit.ols.predict(Xf), dtype=float)
    seasonal_pred = np.asarray(
        [fit.seasonal_cycle[i % fit.period] for i in range(n_steps)],
        dtype=float,
    )
    yhat = deseason_pred + seasonal_pred
    return yhat


def stl_regression_forecast(
    y,
    period=7,
    exog=None,
    future_exog=None,
    n_forecast=7,
    test_size=None,
):
    """
    training-only fit -> tail holdout evaluation -> seasonal-naive baseline ->
    full observed-data refit -> future forecast。

    保持旧返回接口：return (future_dataframe, full_stl, full_ols)。
    详细诊断写入 `full_ols._study_diagnostics`。
    """
    y = pd.Series(np.asarray(y, dtype=float)).reset_index(drop=True)
    if y.isna().any():
        raise ValueError("y 含缺失；模板不自动插补")
    exog = _validate_exog(exog, len(y), "exog")

    if test_size is None:
        test_size = period
    test_size = int(test_size)
    if test_size <= 0 or test_size >= len(y) // 2:
        raise ValueError("test_size 必须 >0 且应小于样本长度的一半")

    split = len(y) - test_size
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    exog_train = exog.iloc[:split] if exog is not None else None
    exog_test = exog.iloc[split:] if exog is not None else None

    train_fit = _fit_model(y_train, period=period, exog_train=exog_train)
    pred_test = _predict(train_fit, test_size, future_exog=exog_test)
    metrics = forecast_metrics(y_test.to_numpy(), pred_test)

    # seasonal naive baseline：仅复用训练期最后一个周期。
    last_cycle = y_train.to_numpy()[-period:]
    baseline_pred = np.asarray([last_cycle[i % period] for i in range(test_size)])
    baseline_metrics = forecast_metrics(y_test.to_numpy(), baseline_pred)

    print("=" * 72)
    print("Tail holdout evaluation")
    print("  STL-regression:", {k: round(v, 4) for k, v in metrics.items()})
    print("  Seasonal-naive:", {k: round(v, 4) for k, v in baseline_metrics.items()})

    # 只有在完成 holdout 之后，才对全部已观测数据重拟合未来模型。
    full_fit = _fit_model(y, period=period, exog_train=exog)
    future_pred = _predict(full_fit, n_forecast, future_exog=future_exog)

    sigma = full_fit.residual_sigma
    out = pd.DataFrame(
        {
            "prediction": future_pred,
            "lower_approx_95": future_pred - 1.96 * sigma,
            "upper_approx_95": future_pred + 1.96 * sigma,
        }
    )

    diagnostics = {
        "method": "STL_regression",
        "status": "ok",
        "selection_scope": "train_only_holdout",
        "metrics": metrics,
        "baseline_method": "seasonal_naive",
        "baseline_metrics": baseline_metrics,
        "test_size": test_size,
        "period": period,
        "interval_method": "residual_normal_approximation_not_calibrated",
        "coefficient_boundary": "predictive_association_not_causal",
    }
    setattr(full_fit.ols, "_study_diagnostics", diagnostics)

    print(
        "区间说明：±1.96*residual_sigma 是近似参考，不等于已校准 prediction interval；"
        "正式论文应在滚动/样本外窗口检查 coverage 与 width。"
    )
    return out, full_fit.stl, full_fit.ols


if __name__ == "__main__":
    # 【Study-only example】不作为比赛证据。
    rng = np.random.default_rng(0)
    n = 150
    t = np.arange(n)
    price = 6 + 1.5 * np.sin(t / 20) + rng.normal(0, 0.3, n)
    y = (
        40
        + 0.15 * t
        + 8 * np.sin(2 * np.pi * t / 7)
        - 4.0 * (price - price.mean())
        + rng.normal(0, 3, n)
    )
    exog = pd.DataFrame({"price": price})
    future_exog = pd.DataFrame({"price": np.full(7, 5.5)})

    out, _, ols = stl_regression_forecast(
        y,
        period=7,
        exog=exog,
        future_exog=future_exog,
        n_forecast=7,
        test_size=14,
    )
    print(out.round(3).to_string(index=False))
    print(
        "\n正式赛题中，未来外生变量必须来自题面、已知计划或独立预测/场景；"
        "OLS 系数不自动解释为价格变化的因果效应。"
    )