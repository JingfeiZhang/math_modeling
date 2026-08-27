# -*- coding: utf-8 -*-
"""
03 GM(1,1)：小样本趋势候选与样本外验证
====================================

study-only 模板。GM(1,1) 只应作为“小样本、近指数/平滑趋势”下的候选模型。
传统级比、后验差比 C、小误差概率 P 都是模型内部/样本内诊断，不能替代未来留出验证。

关键边界：
- 序列需为有限正值、按时间排序；
- 级比可容区间是经典适用性启发，不是模型正确性的证明；
- 不再自动平移“修复”级比不通过：平移会改变建模问题，应由调用者显式决定并说明；
- 参数用 least-squares 求解，避免显式正规方程求逆/求解的数值不稳定；
- 必须与 last-value / simple trend 等同输出 baseline 比较；
- 样本内“精度等级”仅保留为 legacy diagnostic，不称预测精度证明。
"""

from __future__ import annotations

import numpy as np


def _validate_series(x, min_points=4):
    x = np.asarray(x, dtype=float).ravel()
    if len(x) < min_points or not np.isfinite(x).all():
        raise ValueError(f"GM(1,1) 至少需要 {min_points} 个有限点")
    if np.any(x <= 0):
        raise ValueError("本模板的 GM(1,1) 要求正序列；不要静默平移非正数据")
    return x


def forecast_metrics(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    if len(y_true) != len(y_pred):
        raise ValueError("y_true/y_pred 必须等长")
    err = y_true - y_pred
    return {
        "RMSE": float(np.sqrt(np.mean(err ** 2))),
        "MAE": float(np.mean(np.abs(err))),
        "MAPE(%)": float(np.mean(np.abs(err / y_true)) * 100),
    }


def level_ratio_diagnostic(x):
    x = _validate_series(x)
    n = len(x)
    lower, upper = np.exp(-2.0 / (n + 1)), np.exp(2.0 / (n + 1))
    ratios = x[:-1] / x[1:]
    return {
        "ratios": ratios,
        "interval": (float(lower), float(upper)),
        "inside_all": bool(np.all((ratios > lower) & (ratios < upper))),
        "claim_boundary": "经典级比可容区间只是 GM(1,1) 的适用性诊断之一，不证明样本外预测有效",
    }


def level_ratio_test(x):
    """兼容旧接口。"""
    d = level_ratio_diagnostic(x)
    return d["inside_all"], d["ratios"], d["interval"]


def shift_transform(x, c):
    """仅在调用者有明确理由时使用；不提供自动 c。"""
    x = np.asarray(x, dtype=float).ravel()
    c = float(c)
    shifted = x + c
    if not np.isfinite(shifted).all() or np.any(shifted <= 0):
        raise ValueError("平移后仍需保证正值")
    return shifted, c


def _legacy_posterior_diagnostic(x, fitted):
    residual = x - fitted
    s1 = float(np.std(x, ddof=0))
    s2 = float(np.std(residual, ddof=0))
    C = float(s2 / s1) if s1 > 0 else np.inf
    P = float(np.mean(np.abs(residual - np.mean(residual)) < 0.6745 * s1)) if s1 > 0 else 0.0
    if C <= 0.35 and P >= 0.95:
        grade = "legacy-level-1"
    elif C <= 0.50 and P >= 0.80:
        grade = "legacy-level-2"
    elif C <= 0.65 and P >= 0.70:
        grade = "legacy-level-3"
    else:
        grade = "legacy-level-4"
    return {"C": C, "P": P, "legacy_grade": grade,
            "claim_boundary": "C/P/grade 为传统样本内诊断，不等于未来预测精度等级"}


def gm11(x, n_predict=3):
    x = _validate_series(x)
    if n_predict < 1:
        raise ValueError("n_predict 必须>=1")
    n = len(x)
    x1 = np.cumsum(x)
    z1 = 0.5 * (x1[:-1] + x1[1:])
    B = np.column_stack([-z1, np.ones(n - 1)])
    Y = x[1:]
    params, residuals, rank, singular = np.linalg.lstsq(B, Y, rcond=None)
    a, b = map(float, params)
    if rank < 2:
        raise ValueError("GM(1,1) 参数矩阵秩不足，无法稳定识别 a/b")
    if abs(a) < 1e-10:
        raise ValueError("发展系数 a 过接近 0，本时间响应公式数值不稳定；考虑更简单趋势模型")

    k = np.arange(n + n_predict, dtype=float)
    x1_hat = (x[0] - b / a) * np.exp(-a * k) + b / a
    x0_hat = np.empty_like(x1_hat)
    x0_hat[0] = x1_hat[0]
    x0_hat[1:] = np.diff(x1_hat)
    fitted = x0_hat[:n]
    predict = x0_hat[n:]
    diagnostic = _legacy_posterior_diagnostic(x, fitted)
    return {
        "a": a, "b": b,
        "fitted": fitted, "predict": predict,
        "parameter_rank": int(rank),
        "design_condition": float(singular[0] / singular[-1]) if singular[-1] > 0 else np.inf,
        **diagnostic,
        "claim_boundary": "GM(1,1) 为当前小样本趋势的候选近似；正式预测结论必须来自时间留出/滚动验证和 baseline 比较",
    }


def naive_last_value(train, horizon):
    train = _validate_series(train)
    return np.repeat(train[-1], int(horizon))


def evaluate_holdout(series, test_size=2, allow_shift=False, shift_c=None):
    series = _validate_series(series, min_points=max(5, test_size + 4))
    if not 1 <= test_size < len(series) - 3:
        raise ValueError("test_size 过大或过小")
    train, test = series[:-test_size], series[-test_size:]
    diag = level_ratio_diagnostic(train)
    shift = 0.0
    train_used = train
    if not diag["inside_all"] and allow_shift:
        if shift_c is None:
            raise ValueError("allow_shift=True 时必须显式提供 shift_c 及其建模理由")
        train_used, shift = shift_transform(train, shift_c)

    model = gm11(train_used, n_predict=test_size)
    pred = model["predict"] - shift
    baseline = naive_last_value(train, test_size)
    return {
        "train": train, "test": test,
        "level_ratio": diag,
        "shift_c": shift,
        "model": model,
        "prediction": pred,
        "metrics": forecast_metrics(test, pred),
        "baseline_prediction": baseline,
        "baseline_metrics": forecast_metrics(test, baseline),
    }


def gm11_predict(x, n_predict=3, auto_shift=False, shift_c=None):
    """兼容主接口；auto_shift 已废弃为显式 shift_c 语义。"""
    x = _validate_series(x)
    diag = level_ratio_diagnostic(x)
    if auto_shift and shift_c is None:
        raise ValueError("不再支持自动选择平移量；请显式提供 shift_c 并说明理由")
    shift = 0.0
    used = x
    if shift_c is not None:
        used, shift = shift_transform(x, shift_c)
    result = gm11(used, n_predict=n_predict)
    result["fitted"] = result["fitted"] - shift
    result["predict"] = result["predict"] - shift
    result["shift_c"] = shift
    result["level_ratio"] = diag
    return result


if __name__ == "__main__":
    data = np.array([2.874, 3.278, 3.337, 3.390, 3.679, 3.996, 4.351, 4.702])
    evaluation = evaluate_holdout(data, test_size=2)
    print("GM holdout:", evaluation["metrics"])
    print("last-value baseline:", evaluation["baseline_metrics"])
    print("legacy in-sample diagnostic:",
          {k: evaluation["model"][k] for k in ["C", "P", "legacy_grade"]})
    print("\n只有样本外表现稳定优于简单 baseline 时，GM(1,1) 才有进入主模型的证据。")
