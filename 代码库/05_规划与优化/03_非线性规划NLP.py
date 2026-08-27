# -*- coding: utf-8 -*-
"""
03 非线性规划 NLP：多起点、可行性与局部最优边界
================================================

study-only 模板。核心原则：

- scipy.optimize.minimize 的 SLSQP/trust-constr 默认提供局部数值解，不自动证明全局最优。
- 多起点可以暴露初值敏感性、降低漏掉更好局部解的风险，但仍不是全局性证明。
- 无界变量不能为了随机起点悄悄假设 [-10, 10]；必须显式给 sampling_bounds 或 x0 列表。
- success 之后仍要回查 bounds/constraints；正式论文应报告求解状态、可行性和初值敏感性。
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

FEAS_TOL = 1e-7


def constraint_violation(x, bounds, constraints=None):
    x = np.asarray(x, dtype=float)
    values = [0.0]
    for value, (lo, hi) in zip(x, bounds):
        if lo is not None:
            values.append(max(0.0, float(lo) - float(value)))
        if hi is not None:
            values.append(max(0.0, float(value) - float(hi)))
    for cons in list(constraints or []):
        v = np.asarray(cons["fun"](x), dtype=float)
        if cons.get("type") == "ineq":
            values.append(float(np.max(np.maximum(-v, 0.0))))
        elif cons.get("type") == "eq":
            values.append(float(np.max(np.abs(v))))
        else:
            raise ValueError(f"未知约束类型: {cons.get('type')}")
    return float(max(values))


def _sampling_box(bounds, sampling_bounds=None):
    if sampling_bounds is not None:
        box = list(sampling_bounds)
        if len(box) != len(bounds):
            raise ValueError("sampling_bounds 与变量维度不一致")
    else:
        box = list(bounds)
    checked = []
    for i, (lo, hi) in enumerate(box):
        if lo is None or hi is None or not np.isfinite([lo, hi]).all() or hi <= lo:
            raise ValueError(
                f"变量 {i} 缺少有限的多起点采样范围；请显式提供 sampling_bounds，"
                "不要让模板擅自假设搜索域。"
            )
        checked.append((float(lo), float(hi)))
    return checked


def solve_nlp_multistart(fun, bounds, constraints=None, n_starts=30,
                         method="SLSQP", seed=42, sampling_bounds=None,
                         x0_list=None, feas_tol=FEAS_TOL):
    """运行多个局部求解起点，返回全部接受结果与最好局部候选。"""
    bounds = list(bounds)
    constraints = list(constraints or [])
    if n_starts < 1:
        raise ValueError("n_starts 必须 >= 1")

    starts = []
    if x0_list is not None:
        starts = [np.asarray(x0, dtype=float) for x0 in x0_list]
        if not starts:
            raise ValueError("x0_list 不能为空")
    else:
        box = _sampling_box(bounds, sampling_bounds)
        rng = np.random.default_rng(seed)
        for _ in range(n_starts):
            starts.append(np.array([rng.uniform(lo, hi) for lo, hi in box]))

    runs = []
    accepted = []
    for idx, x0 in enumerate(starts):
        if x0.shape != (len(bounds),):
            raise ValueError(f"起点 {idx} 维度不一致")
        res = minimize(fun, x0, method=method, bounds=bounds, constraints=constraints)
        violation = constraint_violation(res.x, bounds, constraints)
        ok = bool(res.success and np.isfinite(res.fun) and violation <= feas_tol)
        record = {
            "start_index": idx, "x0": np.asarray(x0), "success": bool(res.success),
            "accepted": ok, "fun": float(res.fun) if np.isfinite(res.fun) else None,
            "x": np.asarray(res.x), "constraint_violation": violation,
            "message": str(res.message),
        }
        runs.append(record)
        if ok:
            accepted.append(record)

    if not accepted:
        return {
            "accepted": False, "best": None, "runs": runs,
            "n_starts": len(starts), "n_accepted": 0,
            "claim_boundary": "未获得满足当前容差的可接受局部解",
        }

    best = min(accepted, key=lambda row: row["fun"])
    objective_values = np.array([row["fun"] for row in accepted], dtype=float)
    spread = {
        "min": float(objective_values.min()), "median": float(np.median(objective_values)),
        "max": float(objective_values.max()), "std": float(objective_values.std(ddof=0)),
    }
    return {
        "accepted": True, "best": best, "runs": runs,
        "n_starts": len(starts), "n_accepted": len(accepted),
        "objective_spread": spread,
        "claim_boundary": "多起点中最好的可行局部候选；无全局性证据时不得称全局最优",
    }


if __name__ == "__main__":
    print("########## 带约束 NLP ##########")

    def f(x):
        return (x[0] - 1) ** 2 + (x[1] - 2.5) ** 2

    cons = [
        {"type": "ineq", "fun": lambda x: x[0] - 2 * x[1] + 2},
        {"type": "ineq", "fun": lambda x: -x[0] - 2 * x[1] + 6},
        {"type": "ineq", "fun": lambda x: -x[0] + 2 * x[1] + 2},
    ]
    # 原模型只有非负下界，随机起点需要额外给有限 sampling_bounds；这只是搜索设置，
    # 不会被偷偷当成题面硬约束。
    result = solve_nlp_multistart(
        f, [(0, None), (0, None)], cons, n_starts=20,
        sampling_bounds=[(0, 5), (0, 5)], seed=42,
    )
    print("accepted=", result["accepted"], "n_accepted=", result["n_accepted"])
    if result["accepted"]:
        print("best x=", np.round(result["best"]["x"], 4))
        print("best f=", round(result["best"]["fun"], 6))
        print("objective spread=", result["objective_spread"])
        print("boundary=", result["claim_boundary"])

    print("\n########## 多峰函数：初值敏感性 ##########")

    def g(x):
        return x[0] * np.sin(x[0]) + 0.5 * x[0]

    result = solve_nlp_multistart(g, [(0, 20)], n_starts=50, seed=7)
    print("best=", result["best"] and {"x": result["best"]["x"], "fun": result["best"]["fun"]})
    print("spread=", result.get("objective_spread"))
    print("结论只应写：在这些起点和当前局部求解设置中找到的最好可行候选，而非全局最优。")
