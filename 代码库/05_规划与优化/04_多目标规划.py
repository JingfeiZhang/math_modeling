# -*- coding: utf-8 -*-
"""
04 多目标规划：偏好方案、ε-constraint 与非支配近似
===================================================

study-only 模板。核心边界：

1. 一个固定权重解只是“给定偏好下的折中方案”，不是 Pareto 前沿。
2. 求解器 success 不等于数学上可接受；每个候选都必须回查 bounds / constraints。
3. ε 扫描得到的是有限采样候选；还需去除不可行点和被支配点，之后最多称为
   “在当前扫描范围与求解设置下的 non-dominated / Pareto approximation”。
4. SLSQP 是局部数值求解器。非凸问题若无全局性证据，不声称全局 Pareto 最优。
5. 多目标归一化必须来自有意义的尺度/范围，不能因某个理想值接近 0 就失真。
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

FEAS_TOL = 1e-7


def _as_constraints(constraints):
    return list(constraints or [])


def constraint_violation(x, bounds, constraints=None):
    """返回最大违反量；0 表示在给定容差前满足当前可检查约束。"""
    x = np.asarray(x, dtype=float)
    violations = [0.0]
    for value, bound in zip(x, bounds):
        lo, hi = bound
        if lo is not None:
            violations.append(max(0.0, float(lo) - float(value)))
        if hi is not None:
            violations.append(max(0.0, float(value) - float(hi)))
    for cons in _as_constraints(constraints):
        value = np.asarray(cons["fun"](x), dtype=float)
        if cons.get("type") == "eq":
            violations.append(float(np.max(np.abs(value))))
        elif cons.get("type") == "ineq":
            violations.append(float(np.max(np.maximum(-value, 0.0))))
        else:
            raise ValueError(f"未知约束类型: {cons.get('type')}")
    return float(max(violations))


def _annotate_result(res, bounds, constraints, tol=FEAS_TOL):
    violation = constraint_violation(res.x, bounds, constraints)
    res.constraint_violation = violation
    res.feasible = bool(violation <= tol)
    res.accepted = bool(res.success and res.feasible and np.isfinite(res.fun))
    return res


def weighted_sum(objs, weights, bounds, x0, constraints=None, normalize_scale=None):
    """给定权重下的单个偏好方案，不等同于完整 Pareto 搜索。"""
    k = len(objs)
    w = np.asarray(weights, dtype=float)
    if w.shape != (k,) or np.any(w < 0) or not np.isfinite(w).all() or w.sum() <= 0:
        raise ValueError("weights 必须为与目标数一致的非负有限向量，且总和>0")
    w = w / w.sum()

    if normalize_scale is None:
        scale = np.ones(k)
    else:
        scale = np.asarray(normalize_scale, dtype=float)
        if scale.shape != (k,) or np.any(~np.isfinite(scale)) or np.any(scale <= 0):
            raise ValueError("normalize_scale 必须为每个目标给出正的有限尺度")

    def combined(x):
        values = np.array([f(x) for f in objs], dtype=float)
        return float(np.sum(w * values / scale))

    cons = _as_constraints(constraints)
    res = minimize(combined, x0, method="SLSQP", bounds=bounds, constraints=cons)
    return _annotate_result(res, bounds, cons)


def epsilon_constraint(objs, main_idx, eps, bounds, x0, constraints=None):
    """优化一个主目标，其余目标用 f_j(x)<=eps[j] 约束。"""
    if not 0 <= main_idx < len(objs):
        raise ValueError("main_idx 越界")
    if main_idx in eps:
        raise ValueError("主目标不应同时出现在 eps 约束中")
    for j in eps:
        if not 0 <= j < len(objs):
            raise ValueError(f"eps 目标索引越界: {j}")

    cons = _as_constraints(constraints)
    for j, e in eps.items():
        cons.append({"type": "ineq", "fun": lambda x, jj=j, ee=float(e): ee - objs[jj](x)})
    res = minimize(objs[main_idx], x0, method="SLSQP", bounds=bounds, constraints=cons)
    return _annotate_result(res, bounds, cons)


def ideal_point(objs, bounds, x0, constraints=None, weights=None, p=2, normalize_scale=None):
    """构造理想点并寻找距离最小的偏好方案；仍是标量化局部求解。"""
    k = len(objs)
    cons = _as_constraints(constraints)
    w = np.ones(k) if weights is None else np.asarray(weights, dtype=float)
    if w.shape != (k,) or np.any(w < 0) or w.sum() <= 0:
        raise ValueError("weights 非法")
    w = w / w.sum()

    single = []
    ideal = []
    for f in objs:
        r = minimize(f, x0, method="SLSQP", bounds=bounds, constraints=cons)
        r = _annotate_result(r, bounds, cons)
        single.append(r)
        ideal.append(float(r.fun) if r.accepted else np.nan)
    ideal = np.asarray(ideal, dtype=float)
    if not np.isfinite(ideal).all():
        return {"accepted": False, "reason": "至少一个单目标理想点求解失败", "single_objective": single}

    if normalize_scale is None:
        # 仅作数值尺度，避免理想点为 0 时除零；正式问题应优先传入有业务意义的尺度。
        scale = np.maximum(np.abs(ideal), 1.0)
    else:
        scale = np.asarray(normalize_scale, dtype=float)
        if scale.shape != (k,) or np.any(scale <= 0) or np.any(~np.isfinite(scale)):
            raise ValueError("normalize_scale 非法")

    def distance(x):
        values = np.array([f(x) for f in objs], dtype=float)
        diff = w * (values - ideal) / scale
        if np.isinf(p):
            return float(np.max(np.abs(diff)))
        return float(np.sum(np.abs(diff) ** p) ** (1.0 / p))

    r = minimize(distance, x0, method="SLSQP", bounds=bounds, constraints=cons)
    r = _annotate_result(r, bounds, cons)
    values = np.array([f(r.x) for f in objs], dtype=float)
    return {
        "accepted": bool(r.accepted), "ideal": ideal, "x": np.asarray(r.x),
        "f": values, "result": r, "single_objective": single,
    }


def nondominated_mask(objective_values, atol=1e-10):
    """最小化目标下的非支配筛选。objective_values: (n_solutions, n_objectives)."""
    values = np.asarray(objective_values, dtype=float)
    if values.ndim != 2:
        raise ValueError("objective_values 必须是二维数组")
    keep = np.ones(len(values), dtype=bool)
    for i in range(len(values)):
        if not keep[i]:
            continue
        # j dominates i iff j 所有目标不差，且至少一个严格更好。
        no_worse = np.all(values <= values[i] + atol, axis=1)
        strictly_better = np.any(values < values[i] - atol, axis=1)
        dominated_by_other = no_worse & strictly_better
        dominated_by_other[i] = False
        if dominated_by_other.any():
            keep[i] = False
    return keep


def epsilon_sweep(objs, main_idx, eps_grid, bounds, x0, constraints=None, tol=FEAS_TOL):
    """扫描多个 ε 设定，返回可行候选和其中的非支配子集。"""
    candidates = []
    current_x0 = np.asarray(x0, dtype=float)
    for eps in eps_grid:
        res = epsilon_constraint(objs, main_idx, eps, bounds, current_x0, constraints)
        row = {
            "eps": dict(eps), "success": bool(res.success), "feasible": bool(res.feasible),
            "accepted": bool(res.accepted), "message": str(res.message),
            "constraint_violation": float(res.constraint_violation),
        }
        if res.accepted:
            row["x"] = np.asarray(res.x, dtype=float)
            row["objectives"] = np.array([f(res.x) for f in objs], dtype=float)
            current_x0 = np.asarray(res.x, dtype=float)
        candidates.append(row)

    accepted = [row for row in candidates if row["accepted"]]
    if accepted:
        mask = nondominated_mask(np.vstack([row["objectives"] for row in accepted]))
        nondominated = [row for row, keep in zip(accepted, mask) if keep]
    else:
        nondominated = []
    return {"candidates": candidates, "nondominated": nondominated, "tol": tol}


def _print_solution(label, res, objs):
    print(label)
    print(f"  success={res.success}, feasible={res.feasible}, violation={res.constraint_violation:.3g}")
    if res.accepted:
        print("  x =", np.round(res.x, 4))
        print("  objectives =", np.round([f(res.x) for f in objs], 4))
    else:
        print("  未接受该候选；message =", res.message)


if __name__ == "__main__":
    # 双目标示例：均转成“最小化”口径。
    def f_cost(x):
        return x[0] ** 2 + x[1] ** 2

    def f_neg_profit(x):
        return -(2 * x[0] + x[1])

    objs = [f_cost, f_neg_profit]
    bounds = [(0, 5), (0, 5)]
    x0 = [1.0, 1.0]
    cons = [{"type": "ineq", "fun": lambda x: 5 - x[0] - x[1]}]

    r_weight = weighted_sum(objs, [0.5, 0.5], bounds, x0, cons, normalize_scale=[25, 15])
    _print_solution("【固定权重偏好方案】", r_weight, objs)
    print("  解释边界：这只是给定权重/尺度下的单个方案。")

    r_eps = epsilon_constraint(objs, 0, {1: -8.0}, bounds, x0, cons)
    _print_solution("\n【ε-constraint 单个候选】", r_eps, objs)

    r_ideal = ideal_point(objs, bounds, x0, cons, weights=[1, 1], p=2, normalize_scale=[25, 15])
    print("\n【理想点偏好方案】 accepted=", r_ideal["accepted"])
    if r_ideal["accepted"]:
        print("  ideal =", np.round(r_ideal["ideal"], 4))
        print("  x =", np.round(r_ideal["x"], 4))
        print("  objectives =", np.round(r_ideal["f"], 4))

    grid = [{1: -target} for target in [2, 4, 6, 8, 10]]
    sweep = epsilon_sweep(objs, 0, grid, bounds, x0, cons)
    print("\n【有限 ε 扫描得到的 non-dominated 样本】")
    for row in sweep["nondominated"]:
        cost, neg_profit = row["objectives"]
        print(f"  eps={row['eps']} -> cost={cost:.4f}, profit={-neg_profit:.4f}, violation={row['constraint_violation']:.2g}")
    print("  这些点只是当前 ε 网格和局部求解设置下的 Pareto approximation；")
    print("  不能由有限扫描自动声称得到完整或全局 Pareto 前沿。")
