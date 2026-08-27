# -*- coding: utf-8 -*-
"""
02 系统动力学 SIR：存量守恒、有效再生数与数值诊断
================================================

study-only 模板。SIR 是机制示例，不应直接把 β、γ 或 β/γ 的估计解释成普遍规律。
正式使用需要说明封闭人口、均匀混合、参数是否随时间变化、观测机制等假设。

本实现显式检查：
- 初始存量/参数合法性；
- S+I+R 守恒；
- 状态非负；
- 数值求解状态；
- 基本再生数 R0=β/γ 与初始有效再生数 Re(0)=R0*S0/N 的区别。
"""

from __future__ import annotations

import numpy as np
from scipy.integrate import solve_ivp


def sir_rhs(t, y, beta, gamma):
    S, I, R = y
    N = S + I + R
    if N <= 0:
        return [np.nan, np.nan, np.nan]
    infection = beta * S * I / N
    removal = gamma * I
    return [-infection, infection - removal, removal]


def simulate_sir(S0, I0, R0_initial, beta, gamma, t, rtol=1e-8, atol=1e-10):
    t = np.asarray(t, dtype=float).ravel()
    initial = np.asarray([S0, I0, R0_initial], dtype=float)
    if len(t) < 2 or not np.isfinite(t).all() or np.any(np.diff(t) <= 0):
        raise ValueError("t 必须为严格递增的有限时间网格")
    if not np.isfinite(initial).all() or np.any(initial < 0) or initial.sum() <= 0:
        raise ValueError("S0/I0/R0 必须非负且总量>0")
    if not np.isfinite([beta, gamma]).all() or beta < 0 or gamma <= 0:
        raise ValueError("要求 beta>=0、gamma>0 且有限")

    N0 = float(initial.sum())
    sol = solve_ivp(sir_rhs, (float(t[0]), float(t[-1])), initial, t_eval=t,
                    args=(float(beta), float(gamma)), method="RK45",
                    rtol=rtol, atol=atol)
    if not sol.success or sol.y.shape != (3, len(t)) or not np.isfinite(sol.y).all():
        return {"accepted": False, "message": str(sol.message)}

    S, I, R = sol.y
    total = S + I + R
    conservation_error = float(np.max(np.abs(total - N0)))
    min_state = float(np.min(sol.y))
    state_tol = max(1e-8 * N0, 1e-9)
    feasible = bool(min_state >= -state_tol and conservation_error <= 1e-6 * max(N0, 1.0))

    basic_R0 = float(beta / gamma)
    effective_R = basic_R0 * S / N0
    initial_Re = float(effective_R[0])
    peak_idx = int(np.argmax(I))
    peak_I = float(I[peak_idx])
    peak_t = float(t[peak_idx])

    return {
        "accepted": bool(feasible),
        "solver_success": True,
        "message": str(sol.message),
        "S": S, "I": I, "R": R,
        "N0": N0,
        "basic_R0": basic_R0,
        "effective_R": effective_R,
        "initial_Re": initial_Re,
        "initial_growth_expected": bool(initial_Re > 1),
        "peak_I": peak_I, "peak_t": peak_t,
        "cumulative_new_removals": float(R[-1] - R0_initial),
        "conservation_error": conservation_error,
        "min_state": min_state,
        "nfev": int(sol.nfev),
        "rtol": rtol, "atol": atol,
        "claim_boundary": "R0/Re 和轨迹只在当前封闭、均匀混合、常参数 SIR 假设下解释；参数变化或观测偏差会改变结论",
    }


def scenario_compare(initial, scenarios, t):
    """比较明确命名的参数场景；不把任意 ±20% 自动包装成正式敏感性。"""
    rows = []
    for name, beta, gamma in scenarios:
        result = simulate_sir(*initial, beta, gamma, t)
        rows.append({
            "scenario": name,
            "accepted": result.get("accepted", False),
            "basic_R0": result.get("basic_R0"),
            "initial_Re": result.get("initial_Re"),
            "peak_I": result.get("peak_I"),
            "peak_t": result.get("peak_t"),
            "conservation_error": result.get("conservation_error"),
        })
    return rows


if __name__ == "__main__":
    N = 10000
    I0, R_init = 5, 0
    S0 = N - I0 - R_init
    beta, gamma = 0.35, 0.10
    t = np.linspace(0, 160, 161)

    result = simulate_sir(S0, I0, R_init, beta, gamma, t)
    print("accepted:", result["accepted"])
    print("basic R0 =", round(result["basic_R0"], 3))
    print("initial Re =", round(result["initial_Re"], 3),
          "-> 初期感染者期望增长" if result["initial_growth_expected"] else "-> 初期感染者不期望增长")
    print("peak I / time =", round(result["peak_I"]), result["peak_t"])
    print("conservation error =", result["conservation_error"])

    print("\n场景比较:")
    for row in scenario_compare((S0, I0, R_init), [
        ("baseline", 0.35, 0.10),
        ("higher-contact scenario", 0.50, 0.10),
        ("faster-removal scenario", 0.35, 0.15),
    ], t):
        print(row)

    print("\n注意：β/γ>1 不是脱离初始易感比例的无条件‘爆发判据’；本模型初期增长看 Re(0)。")
