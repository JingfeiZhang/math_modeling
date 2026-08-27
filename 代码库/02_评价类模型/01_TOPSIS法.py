# -*- coding: utf-8 -*-
"""
01 TOPSIS：构造性综合评分与排名稳定性
===================================

study-only 模板。TOPSIS 的相对贴近度是由指标方向、正向化、归一化、权重和当前
候选集合共同构造的比较量，不具有天然的绝对物理意义。

正式使用至少同时检查：
- 指标方向 / 目标值 / 区间是否由题面或业务定义支持；
- equal-weight 或简单业务规则 baseline；
- 权重扰动后的 top-k / 排名稳定性；
- 删除高度重复或单个指标后的排名稳定性；
- 极端样本是否显著移动正负理想点。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

VALID_TYPES = {"max", "min", "mid", "range"}


def _validate_matrix(X):
    X = np.asarray(X, dtype=float)
    if X.ndim != 2 or X.shape[0] < 2 or X.shape[1] < 1:
        raise ValueError("X 必须是至少 2 个对象、1 个指标的二维矩阵")
    if not np.isfinite(X).all():
        raise ValueError("X 含 NaN/Inf；缺失值处理必须在评价模型之前明确完成")
    return X


def positivize(col, kind, best=None):
    col = np.asarray(col, dtype=float)
    if kind not in VALID_TYPES:
        raise ValueError(f"未知指标类型: {kind}")
    if kind == "max":
        return col.copy()
    if kind == "min":
        return np.max(col) - col
    if kind == "mid":
        if best is None or not np.isfinite(float(best)):
            raise ValueError("mid 指标必须给出有限 best 目标值")
        distance = np.abs(col - float(best))
        span = float(np.max(distance))
        return np.ones_like(col) if span == 0 else 1 - distance / span
    if best is None or len(best) != 2:
        raise ValueError("range 指标必须给出 [lower, upper]")
    lower, upper = map(float, best)
    if not np.isfinite([lower, upper]).all() or lower > upper:
        raise ValueError("range 的 lower/upper 非法")
    distance = np.maximum(lower - col, 0) + np.maximum(col - upper, 0)
    span = float(np.max(distance))
    return np.ones_like(col) if span == 0 else 1 - distance / span


def positivize_matrix(X, indicator_types, best_values=None):
    X = _validate_matrix(X)
    if len(indicator_types) != X.shape[1]:
        raise ValueError("indicator_types 长度必须等于指标数")
    best_values = best_values or {}
    out = np.empty_like(X, dtype=float)
    for j, kind in enumerate(indicator_types):
        out[:, j] = positivize(X[:, j], kind, best_values.get(j))
    return out


def _validate_weights(weights, m):
    if weights is None:
        return np.ones(m, dtype=float) / m
    w = np.asarray(weights, dtype=float).ravel()
    if len(w) != m or not np.isfinite(w).all() or np.any(w < 0) or w.sum() <= 0:
        raise ValueError("weights 必须为与指标数一致的非负有限向量，且总和>0")
    return w / w.sum()


def topsis_from_positive(Xp, weights=None):
    """对已正向化矩阵评分，返回 score/rank 及诊断。"""
    Xp = _validate_matrix(Xp)
    w = _validate_weights(weights, Xp.shape[1])
    norm = np.linalg.norm(Xp, axis=0)
    informative = norm > 0
    Z = np.zeros_like(Xp, dtype=float)
    Z[:, informative] = Xp[:, informative] / norm[informative]
    Zw = Z * w
    ideal_best = Zw.max(axis=0)
    ideal_worst = Zw.min(axis=0)
    d_best = np.linalg.norm(Zw - ideal_best, axis=1)
    d_worst = np.linalg.norm(Zw - ideal_worst, axis=1)
    denom = d_best + d_worst
    score = np.divide(d_worst, denom, out=np.full_like(d_worst, 0.5), where=denom > 0)
    rank = pd.Series(score).rank(ascending=False, method="min").astype(int).to_numpy()
    return {
        "score": score, "rank": rank, "weights": w,
        "ideal_best": ideal_best, "ideal_worst": ideal_worst,
        "uninformative_columns": np.where(~informative)[0].tolist(),
        "degenerate_objects": np.where(denom <= 0)[0].tolist(),
        "claim_boundary": "相对贴近度是当前候选集、变换和权重下的构造性比较分数，不是绝对效用或因果效果",
    }


def topsis(X, indicator_types, best_values=None, weights=None, return_details=False):
    """保持简洁 API；return_details=True 时返回完整诊断。"""
    Xp = positivize_matrix(X, indicator_types, best_values)
    result = topsis_from_positive(Xp, weights)
    if return_details:
        result["positive_matrix"] = Xp
        return result
    return result["score"], result["rank"]


def rank_stability(X, indicator_types, best_values=None, weights=None,
                   perturbation=0.2, include_equal_weight=True):
    """确定性敏感性：逐个权重 ± perturbation，并做 leave-one-indicator-out。"""
    Xp = positivize_matrix(X, indicator_types, best_values)
    m = Xp.shape[1]
    base = topsis_from_positive(Xp, weights)
    base_rank = base["rank"]
    base_w = base["weights"]
    scenarios = []

    def record(name, result):
        rank = result["rank"]
        scenarios.append({
            "scenario": name,
            "top1": int(np.argmin(rank)),
            "max_rank_shift": int(np.max(np.abs(rank - base_rank))),
            "mean_rank_shift": float(np.mean(np.abs(rank - base_rank))),
            "rank": rank.tolist(),
        })

    if include_equal_weight:
        record("equal_weight", topsis_from_positive(Xp, None))

    for j in range(m):
        for factor in (1 - perturbation, 1 + perturbation):
            if factor < 0:
                continue
            w = base_w.copy()
            w[j] *= factor
            record(f"weight_{j}_x{factor:.3f}", topsis_from_positive(Xp, w))

    if m > 1:
        for j in range(m):
            keep = [k for k in range(m) if k != j]
            record(f"drop_indicator_{j}", topsis_from_positive(Xp[:, keep], base_w[keep]))

    top1_values = [row["top1"] for row in scenarios]
    return {
        "base_rank": base_rank.tolist(),
        "base_top1": int(np.argmin(base_rank)),
        "scenarios": scenarios,
        "top1_stability_rate": float(np.mean(np.asarray(top1_values) == np.argmin(base_rank))) if scenarios else 1.0,
        "worst_max_rank_shift": max((row["max_rank_shift"] for row in scenarios), default=0),
    }


if __name__ == "__main__":
    data = np.array([
        [1200, 0.55, 300, 80],
        [900, 0.30, 450, 90],
        [1500, 0.70, 200, 75],
        [1100, 0.40, 380, 88],
    ], dtype=float)
    objects = ["企业A", "企业B", "企业C", "企业D"]
    types = ["max", "min", "max", "mid"]
    best_values = {3: 85}
    weights = [0.35, 0.20, 0.30, 0.15]

    result = topsis(data, types, best_values, weights, return_details=True)
    print(pd.DataFrame({"对象": objects, "score": result["score"], "rank": result["rank"]})
          .sort_values("rank").round(4).to_string(index=False))
    print("\n稳定性:", rank_stability(data, types, best_values, weights))
    print("\n论文中应写‘在当前指标体系与权重下排名靠前’，而不是把综合分解释成绝对客观真值。")
