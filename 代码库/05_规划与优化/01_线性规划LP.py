# -*- coding: utf-8 -*-
"""
01 线性规划 LP：状态、可行性与约束审计
====================================

study-only 模板。LP 的算法很成熟，比赛中更容易错的是变量/约束语义、单位、方向和
求解后没有逐项回查。只有 solver success + feasibility audit 都成立时才解释目标值。
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import linprog

FEAS_TOL = 1e-8


def _array_or_none(value, ndim, name):
    if value is None:
        return None
    arr = np.asarray(value, dtype=float)
    if arr.ndim != ndim or not np.isfinite(arr).all():
        raise ValueError(f"{name} 维度或数值非法")
    return arr


def _validate_problem(c, A_ub, b_ub, A_eq, b_eq, bounds):
    c = np.asarray(c, dtype=float).ravel()
    if len(c) == 0 or not np.isfinite(c).all():
        raise ValueError("c 必须为非空有限向量")
    n = len(c)
    A_ub = _array_or_none(A_ub, 2, "A_ub")
    b_ub = _array_or_none(b_ub, 1, "b_ub")
    A_eq = _array_or_none(A_eq, 2, "A_eq")
    b_eq = _array_or_none(b_eq, 1, "b_eq")
    if (A_ub is None) != (b_ub is None):
        raise ValueError("A_ub/b_ub 必须同时提供")
    if A_ub is not None and (A_ub.shape[1] != n or A_ub.shape[0] != len(b_ub)):
        raise ValueError("A_ub/b_ub 与变量维度不一致")
    if (A_eq is None) != (b_eq is None):
        raise ValueError("A_eq/b_eq 必须同时提供")
    if A_eq is not None and (A_eq.shape[1] != n or A_eq.shape[0] != len(b_eq)):
        raise ValueError("A_eq/b_eq 与变量维度不一致")
    if bounds is None:
        bounds = [(0, None)] * n
    if len(bounds) != n:
        raise ValueError("bounds 长度必须等于变量数")
    checked_bounds = []
    for i, pair in enumerate(bounds):
        if pair is None:
            pair = (None, None)
        if len(pair) != 2:
            raise ValueError(f"bounds[{i}] 必须为 (lower, upper)")
        lo, hi = pair
        if lo is not None and not np.isfinite(float(lo)):
            raise ValueError("有限下界请使用数值，无界用 None")
        if hi is not None and not np.isfinite(float(hi)):
            raise ValueError("有限上界请使用数值，无界用 None")
        if lo is not None and hi is not None and float(lo) > float(hi):
            raise ValueError(f"bounds[{i}] 下界大于上界")
        checked_bounds.append((lo, hi))
    return c, A_ub, b_ub, A_eq, b_eq, checked_bounds


def feasibility_audit(x, A_ub=None, b_ub=None, A_eq=None, b_eq=None,
                      bounds=None, tol=FEAS_TOL):
    x = np.asarray(x, dtype=float).ravel()
    violations = []
    if A_ub is not None:
        ub_residual = np.asarray(A_ub) @ x - np.asarray(b_ub)
        violations.extend(np.maximum(ub_residual, 0).tolist())
    else:
        ub_residual = np.array([])
    if A_eq is not None:
        eq_residual = np.asarray(A_eq) @ x - np.asarray(b_eq)
        violations.extend(np.abs(eq_residual).tolist())
    else:
        eq_residual = np.array([])
    bound_violations = []
    for value, (lo, hi) in zip(x, bounds or [(None, None)] * len(x)):
        v = 0.0
        if lo is not None:
            v = max(v, float(lo) - value)
        if hi is not None:
            v = max(v, value - float(hi))
        bound_violations.append(max(v, 0.0))
    violations.extend(bound_violations)
    max_violation = float(max([0.0, *violations]))
    return {
        "feasible": bool(max_violation <= tol),
        "max_violation": max_violation,
        "ineq_residual": ub_residual,
        "eq_residual": eq_residual,
        "bound_violations": np.asarray(bound_violations),
        "tol": tol,
    }


def solve_lp(c, A_ub=None, b_ub=None, A_eq=None, b_eq=None,
             bounds=None, maximize=False, method="highs", tol=FEAS_TOL):
    c, A_ub, b_ub, A_eq, b_eq, bounds = _validate_problem(
        c, A_ub, b_ub, A_eq, b_eq, bounds
    )
    c_solve = -c if maximize else c
    res = linprog(c_solve, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method=method)
    result = {
        "solver_success": bool(res.success),
        "accepted": False,
        "status": int(res.status),
        "message": str(res.message),
        "x": None,
        "objective": None,
        "feasibility": None,
        "maximize": bool(maximize),
        "method": method,
    }
    if not res.success or res.x is None or not np.isfinite(res.x).all():
        return result

    audit = feasibility_audit(res.x, A_ub, b_ub, A_eq, b_eq, bounds, tol)
    objective = float(c @ res.x)
    result.update({
        "accepted": bool(audit["feasible"]),
        "x": np.asarray(res.x),
        "objective": objective,
        "feasibility": audit,
        "nit": getattr(res, "nit", None),
        "claim_boundary": "目标值只对当前线性模型、变量域与约束集合成立；LP 最优性不能弥补建模语义错误",
    })

    # HiGHS 在可用时提供 slack/marginal 等诊断；仅作为敏感性线索，不自动解释成因果。
    if hasattr(res, "ineqlin"):
        result["inequality_slack"] = np.asarray(getattr(res.ineqlin, "residual", []))
        result["inequality_marginals"] = np.asarray(getattr(res.ineqlin, "marginals", []))
    if hasattr(res, "eqlin"):
        result["equality_residual"] = np.asarray(getattr(res.eqlin, "residual", []))
        result["equality_marginals"] = np.asarray(getattr(res.eqlin, "marginals", []))
    return result


if __name__ == "__main__":
    r = solve_lp(
        [40, 30],
        A_ub=[[1, 1], [2, 1]], b_ub=[40, 60],
        bounds=[(0, None), (0, None)], maximize=True,
    )
    print("生产计划:", {"accepted": r["accepted"], "x": r["x"],
                         "objective": r["objective"], "status": r["status"],
                         "max_violation": r["feasibility"] and r["feasibility"]["max_violation"]})

    r2 = solve_lp(
        [2, 3, 1], A_ub=[[-1, 0, -2]], b_ub=[-40],
        A_eq=[[1, 1, 1]], b_eq=[100], bounds=[(0, None)] * 3,
    )
    print("运输计划:", {"accepted": r2["accepted"], "x": r2["x"],
                         "objective": r2["objective"], "status": r2["status"]})
    print("\n正式使用应把每条题面约束映射到矩阵行，并在解后回查，而不是只看 status=0。")
