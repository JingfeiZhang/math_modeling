# -*- coding: utf-8 -*-
"""
01 Grey-Markov：趋势模型 + 残差状态修正的可消融候选
==================================================

study-only 模板。组合模型不因“GM+Markov”名称就更高级。只有当 GM 在训练期暴露出
可重复的残差状态结构，且修正项在样本外稳定改善同输出 baseline 时才保留。

关键边界：
- GM 负责趋势候选；Markov 只建模 GM 残差状态，不是独立真值模型；
- 状态划分、转移矩阵只能在训练窗口估计；
- 某状态无历史转移时不能用数组 argmax 人为选第 0 状态；必须显式回退；
- n_states 若通过测试集反复试选，会发生模型选择泄漏；
- 正式证据至少比较 naive、GM、GM+Markov 三者。
"""

from __future__ import annotations

import numpy as np


def _validate_series(x, min_points=6):
    x = np.asarray(x, dtype=float).ravel()
    if len(x) < min_points or not np.isfinite(x).all() or np.any(x <= 0):
        raise ValueError(f"序列至少 {min_points} 个有限正值")
    return x


def gm11(x, n_predict=1):
    x = _validate_series(x, min_points=4)
    n = len(x)
    x1 = np.cumsum(x)
    z1 = 0.5 * (x1[:-1] + x1[1:])
    B = np.column_stack([-z1, np.ones(n - 1)])
    params, _, rank, singular = np.linalg.lstsq(B, x[1:], rcond=None)
    if rank < 2:
        raise ValueError("GM 参数矩阵秩不足")
    a, b = map(float, params)
    if abs(a) < 1e-10:
        raise ValueError("GM 发展系数过接近 0，时间响应不稳定")
    k = np.arange(n + int(n_predict), dtype=float)
    x1_hat = (x[0] - b / a) * np.exp(-a * k) + b / a
    x0_hat = np.empty_like(x1_hat)
    x0_hat[0] = x1_hat[0]
    x0_hat[1:] = np.diff(x1_hat)
    return {
        "a": a, "b": b, "fitted": x0_hat[:n], "predict": x0_hat[n:],
        "condition": float(singular[0] / singular[-1]) if singular[-1] > 0 else np.inf,
    }


def build_states(rel_residual, n_states=4):
    r = np.asarray(rel_residual, dtype=float).ravel()
    if not 2 <= n_states <= max(2, len(r) // 2):
        raise ValueError("n_states 相对样本量过大；每个状态至少应有合理支持")
    lo, hi = float(np.min(r)), float(np.max(r))
    if np.isclose(lo, hi):
        return {
            "edges": np.array([lo - 1e-12, hi + 1e-12]),
            "mids": np.array([0.0]),
            "states": np.zeros(len(r), dtype=int),
            "n_states": 1,
            "occupancy": np.array([len(r)]),
        }
    edges = np.linspace(lo - 1e-12, hi + 1e-12, n_states + 1)
    states = np.clip(np.digitize(r, edges[1:-1]), 0, n_states - 1)
    mids = 0.5 * (edges[:-1] + edges[1:])
    occupancy = np.bincount(states, minlength=n_states)
    return {"edges": edges, "mids": mids, "states": states,
            "n_states": n_states, "occupancy": occupancy}


def estimate_transition(states, n_states, empty_row_policy="global"):
    states = np.asarray(states, dtype=int).ravel()
    counts = np.zeros((n_states, n_states), dtype=float)
    for cur, nxt in zip(states[:-1], states[1:]):
        counts[cur, nxt] += 1
    support = counts.sum(axis=1)
    global_freq = np.bincount(states[1:], minlength=n_states).astype(float)
    global_prob = global_freq / global_freq.sum() if global_freq.sum() > 0 else np.ones(n_states) / n_states
    P = np.zeros_like(counts)
    fallback_rows = []
    for i in range(n_states):
        if support[i] > 0:
            P[i] = counts[i] / support[i]
        else:
            fallback_rows.append(i)
            if empty_row_policy == "global":
                P[i] = global_prob
            elif empty_row_policy == "identity":
                P[i, i] = 1.0
            elif empty_row_policy == "uniform":
                P[i] = 1.0 / n_states
            else:
                raise ValueError("empty_row_policy 必须为 global/identity/uniform")
    return {"P": P, "counts": counts, "support": support,
            "fallback_rows": fallback_rows, "empty_row_policy": empty_row_policy}


def grey_markov(x, n_predict=1, n_states=4, empty_row_policy="global"):
    x = _validate_series(x)
    gm = gm11(x, n_predict=n_predict)
    fitted = gm["fitted"]
    if np.any(np.abs(fitted) < 1e-12):
        raise ValueError("GM 拟合值接近 0，无法稳定定义相对残差状态")
    rel_residual = (x - fitted) / fitted
    state_model = build_states(rel_residual, n_states=n_states)
    transition = estimate_transition(state_model["states"], state_model["n_states"], empty_row_policy)

    # 用状态概率分布递推，采用“期望残差”修正，避免 argmax 在概率近似时造成跳变。
    p = np.zeros(state_model["n_states"], dtype=float)
    p[int(state_model["states"][-1])] = 1.0
    corrected = []
    expected_residual = []
    for gm_value in gm["predict"]:
        p = p @ transition["P"]
        correction = float(p @ state_model["mids"])
        expected_residual.append(correction)
        corrected.append(float(gm_value * (1.0 + correction)))

    return {
        "gm": gm,
        "rel_residual": rel_residual,
        "state_model": state_model,
        "transition": transition,
        "gm_predict": np.asarray(gm["predict"]),
        "corrected": np.asarray(corrected),
        "expected_residual": np.asarray(expected_residual),
        "claim_boundary": "Markov 修正来自训练残差状态的有限频数估计；低支持状态与状态划分会显著影响结果",
    }


def metrics(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    err = y_true - y_pred
    return {"RMSE": float(np.sqrt(np.mean(err ** 2))),
            "MAE": float(np.mean(np.abs(err))),
            "MAPE(%)": float(np.mean(np.abs(err / y_true)) * 100)}


def holdout_ablation(series, test_size=3, n_states=4, empty_row_policy="global"):
    series = _validate_series(series, min_points=max(8, test_size + 6))
    train, test = series[:-test_size], series[-test_size:]
    hybrid = grey_markov(train, n_predict=test_size, n_states=n_states,
                         empty_row_policy=empty_row_policy)
    naive = np.repeat(train[-1], test_size)
    comparison = {
        "naive": metrics(test, naive),
        "gm": metrics(test, hybrid["gm_predict"]),
        "gm_markov": metrics(test, hybrid["corrected"]),
    }
    improvement_vs_gm = comparison["gm"]["RMSE"] - comparison["gm_markov"]["RMSE"]
    return {
        "train": train, "test": test,
        "hybrid": hybrid,
        "comparison": comparison,
        "hybrid_rmse_improvement_vs_gm": float(improvement_vs_gm),
        "keep_hybrid_on_this_holdout": bool(improvement_vs_gm > 0),
        "claim_boundary": "一次 holdout 改善仍不足以证明组合稳定增益；条件允许时应做多个滚动窗口/起点的 ablation",
    }


if __name__ == "__main__":
    rng = np.random.default_rng(7)
    base = 50 * np.exp(0.05 * np.arange(20))
    data = base * (1 + rng.normal(0, 0.06, size=20))
    result = holdout_ablation(data, test_size=3, n_states=4)
    print("comparison:", result["comparison"])
    print("transition support:", result["hybrid"]["transition"]["support"])
    print("fallback rows:", result["hybrid"]["transition"]["fallback_rows"])
    print("\n组合只有在多个样本外窗口相对 GM/naive 都有稳定增益时才值得保留。")
