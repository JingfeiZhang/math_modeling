# -*- coding: utf-8 -*-
"""
VAR 向量自回归（study-only reference）

Use when
    多个等间隔时间序列存在动态联动，需要联合预测。
Do not use when
    样本相对参数量过小、非平稳关系更适合协整/VECM、变量含义或时间对齐不清楚。

Academic boundaries
    - Granger 检验只表示“历史信息有助于预测”，不自动证明机制因果；
    - 定阶只使用训练窗口；
    - 对数变换和非负约束必须显式选择，不能默认改变变量语义；
    - 与 last-value multivariate baseline 比较；
    - 正式赛题建议使用 rolling/out-of-time 验证。
"""

import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.api import VAR
from statsmodels.tsa.stattools import adfuller, grangercausalitytests

warnings.filterwarnings("ignore")


def adf_test(series, name=""):
    s = pd.Series(series, dtype=float).dropna()
    if len(s) < 8:
        return False, np.nan
    stat, p = adfuller(s, autolag="AIC")[:2]
    stable = bool(p < 0.05)
    print(f"ADF[{name}]: stat={stat:.3f}, p={p:.4f}, stable_signal={stable}")
    return stable, float(p)


def difference_n(df, d):
    out = pd.DataFrame(df, dtype=float).copy()
    for _ in range(d):
        out = out.diff().dropna()
    return out


def make_stationary(df, max_diff=2):
    """逐次一阶差分，返回训练数据的平稳化版本与差分阶数。"""
    base = pd.DataFrame(df, dtype=float).copy()
    for d in range(max_diff + 1):
        cur = difference_n(base, d)
        flags = [adf_test(cur[c], c)[0] for c in cur.columns]
        if flags and all(flags):
            return cur, d
    raise RuntimeError(
        f"在 0..{max_diff} 阶逐次差分后仍有序列未判为平稳；"
        "不要继续机械差分，考虑趋势/季节项、协整/VECM或重新定义模型。"
    )


def select_order(df_stat, maxlags=10, force_p=None):
    """只在传入的训练平稳序列上选 lag order。"""
    if force_p is not None:
        p = int(force_p)
        if p < 1:
            raise ValueError("force_p 必须 >= 1")
        print(
            f"使用预先给定 p={p}；业务机制只能作为候选依据，"
            "仍需用样本外表现和残差诊断验证。"
        )
        return p

    n, k = df_stat.shape
    safe_max = min(int(maxlags), max(1, n // (k + 1) - 1))
    sel = VAR(df_stat).select_order(maxlags=safe_max)
    p = int(sel.aic) if sel.aic is not None and sel.aic > 0 else 1
    print(f"training-only lag selection: AIC={sel.aic}, BIC={sel.bic}, chosen={p}")
    return p


def granger_predictive_relation(df, maxlag, verbose=True):
    """
    两两 Granger predictive relation：X 的历史是否改善对 Y 的预测。
    该统计关系不是机制因果结论。
    """
    cols = list(df.columns)
    out = pd.DataFrame(np.nan, index=cols, columns=cols, dtype=float)
    for target in cols:
        for predictor in cols:
            if target == predictor:
                continue
            try:
                tests = grangercausalitytests(
                    df[[target, predictor]].dropna(),
                    maxlag=maxlag,
                    verbose=False,
                )
                pvals = [tests[i + 1][0]["ssr_ftest"][1] for i in range(maxlag)]
                out.loc[predictor, target] = float(np.min(pvals))
            except Exception:
                out.loc[predictor, target] = np.nan
    if verbose:
        print("Granger predictive relation p-values (row history -> column prediction):")
        print(out.round(4).to_string())
        print("注意：预测信息关系不自动等于机制因果。")
    return out


# 兼容旧调用名称，但语义在文档中明确为 predictive relation。
def granger_causality(df, maxlag, verbose=True):
    return granger_predictive_relation(df, maxlag=maxlag, verbose=verbose)


def _invert_differences(fc_diff, hist_level, d):
    """按真实逐阶差分历史正确还原 d 阶差分预测。"""
    fc = pd.DataFrame(fc_diff).copy()
    history_layers = [pd.DataFrame(hist_level, dtype=float).copy()]
    for _ in range(d):
        history_layers.append(history_layers[-1].diff().dropna())

    # d-th diff -> (d-1)-th diff -> ... -> level
    for k in range(d - 1, -1, -1):
        base = history_layers[k].iloc[-1].to_numpy(dtype=float)
        fc = fc.cumsum() + base
    return fc


def _to_model_scale(df, log_transform):
    work = pd.DataFrame(df, dtype=float).copy()
    if log_transform:
        if (work <= -1).any().any():
            raise ValueError("log1p 需要所有值 > -1；不要对含更小负值的变量强行变换")
        work = np.log1p(work)
    return work


def _from_model_scale(df, log_transform, nonnegative):
    out = np.expm1(df) if log_transform else pd.DataFrame(df).copy()
    if nonnegative:
        out = out.clip(lower=0)
    return out


def _metric_table(actual, predicted):
    rows = {}
    for c in actual.columns:
        a = actual[c].to_numpy(dtype=float)
        p = predicted[c].to_numpy(dtype=float)
        err = a - p
        mask = a != 0
        rows[c] = {
            "RMSE": float(np.sqrt(np.mean(err ** 2))),
            "MAE": float(np.mean(np.abs(err))),
            "MAPE(%)": float(np.mean(np.abs(err[mask] / a[mask])) * 100)
            if mask.any() else np.nan,
        }
    return rows


def fit_var_forecast(
    df,
    force_p=None,
    test_size=7,
    n_forecast=7,
    log_transform=False,
    nonnegative=False,
    maxlags=10,
    max_diff=2,
):
    """
    VAR 主流程：尾部 holdout -> 训练段变换/差分/定阶 -> 测试预测 -> baseline ->
    同一阶数在全部已观测数据重拟合未来模型。

    返回 (full_fitted_model, future_forecast) 保持旧接口兼容。
    详细评估同时挂在 fitted model 的 `_study_diagnostics` 属性上。
    """
    raw = pd.DataFrame(df).astype(float)
    if raw.isna().any().any():
        raise ValueError("VAR 模板不自动插补缺失值；请先在项目中定义缺失处理")
    if test_size <= 0 or test_size >= len(raw) // 2:
        raise ValueError("test_size 必须 >0 且应小于样本长度的一半")
    if n_forecast <= 0:
        raise ValueError("n_forecast 必须 >0")

    work = _to_model_scale(raw, log_transform)
    train = work.iloc[:-test_size].copy()
    test = work.iloc[-test_size:].copy()

    train_stat, d = make_stationary(train, max_diff=max_diff)
    p = select_order(train_stat, maxlags=maxlags, force_p=force_p)
    if len(train_stat) <= p:
        raise ValueError("平稳化后的训练样本不足以拟合所选 VAR 阶数")

    fitted = VAR(train_stat).fit(p)
    lag = fitted.k_ar
    fc_stat = pd.DataFrame(
        fitted.forecast(train_stat.to_numpy()[-lag:], steps=test_size),
        columns=raw.columns,
    )
    fc_train_scale = _invert_differences(fc_stat, train, d)
    predicted = _from_model_scale(fc_train_scale, log_transform, nonnegative)
    actual = _from_model_scale(test.reset_index(drop=True), log_transform, nonnegative)

    metrics = _metric_table(actual, predicted)

    # multivariate last-value baseline
    last_level = _from_model_scale(train.iloc[[-1]].reset_index(drop=True), log_transform, nonnegative)
    baseline = pd.DataFrame(
        np.repeat(last_level.to_numpy(), test_size, axis=0),
        columns=raw.columns,
    )
    baseline_metrics = _metric_table(actual, baseline)

    print("=" * 72)
    print(f"VAR({p}), d={d}, selection=train_only, log_transform={log_transform}")
    for c in raw.columns:
        print(f"  {c}: VAR={metrics[c]} | LastValue={baseline_metrics[c]}")

    if len(train_stat) > p * len(raw.columns) + 10:
        granger_predictive_relation(train_stat, maxlag=p)

    # 固定已验证的 p，用全量已观测数据重拟合；差分阶数重新从全量观测确定。
    full_stat, d_full = make_stationary(work, max_diff=max_diff)
    full_fit = VAR(full_stat).fit(p)
    fc_future_stat = pd.DataFrame(
        full_fit.forecast(full_stat.to_numpy()[-full_fit.k_ar:], steps=n_forecast),
        columns=raw.columns,
    )
    fc_future_scale = _invert_differences(fc_future_stat, work, d_full)
    future = _from_model_scale(fc_future_scale, log_transform, nonnegative)

    diagnostics = {
        "method": "VAR",
        "status": "ok",
        "selection_scope": "train_only",
        "order": p,
        "difference_order_train": d,
        "difference_order_full": d_full,
        "metrics": metrics,
        "baseline_method": "multivariate_last_value",
        "baseline_metrics": baseline_metrics,
        "log_transform": bool(log_transform),
        "nonnegative": bool(nonnegative),
    }
    setattr(full_fit, "_study_diagnostics", diagnostics)
    return full_fit, future


if __name__ == "__main__":
    # 【Study-only example】仅演示联合预测接口。
    rng = np.random.default_rng(42)
    n = 120
    a = np.zeros(n)
    b = np.zeros(n)
    c = np.zeros(n)
    a[:2], b[:2], c[:2] = [50, 52], [5, 5], [30, 31]
    for t in range(2, n):
        a[t] = 10 + 0.6 * a[t - 1] + 0.3 * c[t - 1] + rng.normal(0, 3)
        b[t] = 1 + 0.5 * b[t - 1] + 0.05 * a[t - 1] + rng.normal(0, 0.5)
        c[t] = 5 + 0.5 * c[t - 1] + 0.3 * a[t - 1] + rng.normal(0, 2)
    demo = pd.DataFrame({"series_a": a, "series_b": b, "series_c": c})

    model, future = fit_var_forecast(
        demo,
        force_p=None,
        test_size=12,
        n_forecast=7,
        log_transform=False,
        nonnegative=False,
    )
    print(future.round(3).to_string(index=False))
    print(
        "\n正式赛题必须结合变量语义决定是否允许负值/对数变换；"
        "Granger predictive relation 不写成机制因果。"
    )