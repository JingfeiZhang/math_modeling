# -*- coding: utf-8 -*-
"""
01 ODE 机理模型：数值求解、参数标定与可辨识性诊断
=================================================

study-only 模板。机理模型的可信度不来自“拟合曲线很贴”，而来自：

    机制/量纲 -> 初值边界 -> 参数来源 -> 数值求解 -> 标定 -> 可辨识性
    -> 数值敏感性 -> 观测验证 -> 外推边界

关键边界：
- 通用参数默认不应被偷偷限制为非负；参数 bounds 必须由模型语义决定；
- 优化器收敛只说明数值优化停止，不证明参数是真实机制参数；
- 高 R² 不等于机制正确，也不保证外推可靠；
- 多组参数若产生近似相同拟合，应报告参数不稳定/弱可辨识；
- 数值容差改变主结论时，应先解决求解器问题再讨论模型结论。
"""

from __future__ import annotations

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares


def _validate_time(t):
    t = np.asarray(t, dtype=float).ravel()
    if len(t) < 2 or not np.isfinite(t).all():
        raise ValueError("时间网格至少含两个有限点")
    if np.any(np.diff(t) <= 0):
        raise ValueError("时间必须严格递增；重复/乱序时间应在建模前处理")
    return t


def simulate_ode(rhs, t_eval, y0, params, method="RK45", rtol=1e-8, atol=1e-10):
    t = _validate_time(t_eval)
    y0 = np.asarray(y0, dtype=float).ravel()
    params = np.asarray(params, dtype=float).ravel()
    if len(y0) == 0 or not np.isfinite(y0).all() or not np.isfinite(params).all():
        raise ValueError("y0/params 必须为有限数")
    sol = solve_ivp(rhs, (float(t[0]), float(t[-1])), y0, t_eval=t,
                    args=tuple(params), method=method, rtol=rtol, atol=atol)
    accepted = bool(sol.success and sol.y.shape[1] == len(t) and np.isfinite(sol.y).all())
    return {
        "accepted": accepted, "t": t, "y": sol.y if accepted else None,
        "message": str(sol.message), "nfev": int(sol.nfev),
        "method": method, "rtol": rtol, "atol": atol,
    }


def logistic_rhs(t, y, r, K):
    N = y[0]
    if K <= 0:
        return [np.nan]
    return [r * N * (1.0 - N / K)]


def solve_logistic(t_eval, N0, r, K, rtol=1e-8, atol=1e-10):
    if not np.isfinite([N0, r, K]).all() or N0 < 0 or K <= 0:
        raise ValueError("Logistic 要求 N0>=0、K>0 且参数有限")
    result = simulate_ode(logistic_rhs, t_eval, [N0], [r, K], rtol=rtol, atol=atol)
    if not result["accepted"]:
        raise RuntimeError(f"Logistic 数值求解失败: {result['message']}")
    return result["y"][0]


def _jacobian_diagnostics(jac, parameter_count):
    J = np.asarray(jac, dtype=float)
    if J.ndim != 2 or J.size == 0 or not np.isfinite(J).all():
        return {"jacobian_rank": None, "jacobian_condition": None, "weak_identifiability_signal": True}
    singular = np.linalg.svd(J, compute_uv=False)
    if len(singular) == 0:
        return {"jacobian_rank": 0, "jacobian_condition": np.inf, "weak_identifiability_signal": True}
    tol = np.finfo(float).eps * max(J.shape) * singular[0]
    rank = int(np.sum(singular > tol))
    cond = float(singular[0] / singular[-1]) if singular[-1] > tol else np.inf
    return {
        "jacobian_rank": rank,
        "jacobian_condition": cond,
        "weak_identifiability_signal": bool(rank < parameter_count or not np.isfinite(cond) or cond > 1e8),
    }


def fit_ode_params(rhs, t_data, y_data, p0, y0=None, bounds=None,
                   observed_state=0, method="RK45", rtol=1e-8, atol=1e-10,
                   max_nfev=None):
    """用最小二乘标定一个被观测状态；bounds=None 表示不额外限制参数符号。"""
    t = _validate_time(t_data)
    y_obs = np.asarray(y_data, dtype=float).ravel()
    if len(y_obs) != len(t) or not np.isfinite(y_obs).all():
        raise ValueError("y_data 必须与时间等长且有限")
    p0 = np.asarray(p0, dtype=float).ravel()
    if len(p0) == 0 or not np.isfinite(p0).all():
        raise ValueError("p0 必须为非空有限向量")
    if y0 is None:
        if observed_state != 0:
            raise ValueError("observed_state!=0 时必须显式给出完整 y0")
        y0 = [y_obs[0]]
    y0 = np.asarray(y0, dtype=float).ravel()
    if not 0 <= observed_state < len(y0):
        raise ValueError("observed_state 超出状态维度")

    if bounds is None:
        lower = np.full(len(p0), -np.inf)
        upper = np.full(len(p0), np.inf)
    else:
        lower = np.broadcast_to(np.asarray(bounds[0], dtype=float), p0.shape).copy()
        upper = np.broadcast_to(np.asarray(bounds[1], dtype=float), p0.shape).copy()
        if np.any(lower >= upper):
            raise ValueError("参数 bounds 必须满足 lower < upper")

    scale = max(float(np.std(y_obs)), float(np.max(np.abs(y_obs))), 1.0)
    penalty = np.full_like(y_obs, 1e3 * scale)

    def simulate(params):
        try:
            out = simulate_ode(rhs, t, y0, params, method=method, rtol=rtol, atol=atol)
        except (ValueError, FloatingPointError, OverflowError):
            return None
        if not out["accepted"] or observed_state >= out["y"].shape[0]:
            return None
        pred = out["y"][observed_state]
        return pred if np.isfinite(pred).all() else None

    def residual(params):
        pred = simulate(params)
        return penalty if pred is None else pred - y_obs

    opt = least_squares(residual, p0, bounds=(lower, upper), method="trf", max_nfev=max_nfev)
    y_fit = simulate(opt.x)
    accepted = bool(opt.success and y_fit is not None)
    if not accepted:
        return {
            "accepted": False, "optimizer_success": bool(opt.success),
            "message": str(opt.message), "params": np.asarray(opt.x),
            "claim_boundary": "数值标定未形成可接受求解结果",
        }

    residuals = y_fit - y_obs
    sse = float(np.sum(residuals ** 2))
    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    ss_tot = float(np.sum((y_obs - np.mean(y_obs)) ** 2))
    r2 = float(1 - sse / ss_tot) if ss_tot > 0 else np.nan
    ident = _jacobian_diagnostics(opt.jac, len(p0))
    return {
        "accepted": True,
        "optimizer_success": bool(opt.success),
        "message": str(opt.message),
        "params": np.asarray(opt.x),
        "y_fit": y_fit,
        "residuals": residuals,
        "SSE": sse, "RMSE": rmse, "R2": r2,
        "y0": y0, "observed_state": int(observed_state),
        "nfev": int(opt.nfev),
        **ident,
        "claim_boundary": "参数是当前模型、初值、数据和损失下的标定结果；高拟合度不证明机制唯一或外推可靠",
    }


def fit_ode_multistart(rhs, t_data, y_data, starts, y0=None, bounds=None, **kwargs):
    """多初值参数标定，用参数/损失分散度暴露局部极值或弱可辨识。"""
    runs = [fit_ode_params(rhs, t_data, y_data, p0, y0=y0, bounds=bounds, **kwargs)
            for p0 in starts]
    accepted = [r for r in runs if r.get("accepted")]
    if not accepted:
        return {"accepted": False, "runs": runs}
    best = min(accepted, key=lambda r: r["SSE"])
    params = np.vstack([r["params"] for r in accepted])
    return {
        "accepted": True,
        "best": best,
        "runs": runs,
        "parameter_min": params.min(axis=0),
        "parameter_max": params.max(axis=0),
        "parameter_std": params.std(axis=0),
        "sse_min": float(min(r["SSE"] for r in accepted)),
        "sse_max": float(max(r["SSE"] for r in accepted)),
        "claim_boundary": "多初值一致只能增强数值稳定性证据，不能单独证明结构可辨识或参数具有真实机制含义",
    }


def numerical_tolerance_check(rhs, t_eval, y0, params, base=(1e-7, 1e-9), tighter=(1e-10, 1e-12)):
    """比较两组容差下的状态轨迹差异。"""
    a = simulate_ode(rhs, t_eval, y0, params, rtol=base[0], atol=base[1])
    b = simulate_ode(rhs, t_eval, y0, params, rtol=tighter[0], atol=tighter[1])
    if not a["accepted"] or not b["accepted"]:
        return {"accepted": False, "base": a, "tighter": b}
    diff = np.abs(a["y"] - b["y"])
    scale = np.maximum(np.abs(b["y"]), 1.0)
    return {
        "accepted": True,
        "max_abs_difference": float(np.max(diff)),
        "max_relative_difference": float(np.max(diff / scale)),
        "base_nfev": a["nfev"], "tighter_nfev": b["nfev"],
    }


if __name__ == "__main__":
    rng = np.random.default_rng(42)
    r_true, K_true, N0 = 0.55, 1000.0, 50.0
    t = np.arange(0, 15, dtype=float)
    clean = solve_logistic(t, N0, r_true, K_true)
    observed = clean * (1 + rng.normal(0, 0.04, len(t)))

    starts = [[0.2, 800], [0.5, 1200], [1.0, 1600]]
    fit = fit_ode_multistart(
        logistic_rhs, t, observed, starts, y0=[observed[0]],
        bounds=([0.0, max(observed)], [5.0, 10 * max(observed)]),
    )
    print("multistart accepted:", fit["accepted"])
    if fit["accepted"]:
        best = fit["best"]
        print("best params:", np.round(best["params"], 4))
        print("RMSE/R2:", best["RMSE"], best["R2"])
        print("Jacobian condition:", best["jacobian_condition"])
        print("parameter range:", fit["parameter_min"], fit["parameter_max"])
        print("tolerance check:", numerical_tolerance_check(logistic_rhs, t, [observed[0]], best["params"]))
    print("\n只有在机制、参数来源、可辨识性和数值检查都成立后，才讨论外推。")
