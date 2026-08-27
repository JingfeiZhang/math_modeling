# -*- coding: utf-8 -*-
"""
07 熵权-TOPSIS：数据离散度权重 + 相对排序
========================================

study-only 模板。该组合不是“最稳妥、最客观”的默认答案；它只是：

    当前样本离散度 -> 数据驱动权重 -> TOPSIS 相对贴近度

因此结论依赖样本、指标变换和候选集合。正式使用必须至少比较 equal-weight TOPSIS，
并检查权重/删指标稳定性。若熵权与等权结论差异很大，应解释差异来源，而不是把
“数据算出的权重”自动视为正确。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

VALID_TYPES = {"max", "min", "mid", "range"}


def _validate_X(X):
    X = np.asarray(X, dtype=float)
    if X.ndim != 2 or X.shape[0] < 2 or X.shape[1] < 1 or not np.isfinite(X).all():
        raise ValueError("X 必须是至少 2x1 的有限二维矩阵")
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
        if best is None:
            raise ValueError("mid 指标需要目标值")
        dist = np.abs(col - float(best))
        span = float(np.max(dist))
        return np.ones_like(col) if span == 0 else 1 - dist / span
    if best is None or len(best) != 2:
        raise ValueError("range 指标需要 [lower, upper]")
    lower, upper = map(float, best)
    if lower > upper:
        raise ValueError("range 下界不能高于上界")
    dist = np.maximum(lower - col, 0) + np.maximum(col - upper, 0)
    span = float(np.max(dist))
    return np.ones_like(col) if span == 0 else 1 - dist / span


def positivize_matrix(X, indicator_types, best_values=None):
    X = _validate_X(X)
    if len(indicator_types) != X.shape[1]:
        raise ValueError("indicator_types 长度与指标数不一致")
    best_values = best_values or {}
    return np.column_stack([
        positivize(X[:, j], indicator_types[j], best_values.get(j))
        for j in range(X.shape[1])
    ])


def entropy_weight(Xp):
    """已正向化矩阵的熵权；常数列 divergence=0。"""
    Xp = _validate_X(Xp)
    n, m = Xp.shape
    mn, mx = Xp.min(axis=0), Xp.max(axis=0)
    span = mx - mn
    informative = span > 0
    Z = np.zeros_like(Xp)
    Z[:, informative] = (Xp[:, informative] - mn[informative]) / span[informative]

    P = np.zeros_like(Z)
    col_sum = Z.sum(axis=0)
    usable = informative & (col_sum > 0)
    P[:, usable] = Z[:, usable] / col_sum[usable]

    entropy = np.ones(m, dtype=float)
    if np.any(usable):
        Pu = P[:, usable]
        with np.errstate(divide="ignore", invalid="ignore"):
            terms = np.where(Pu > 0, Pu * np.log(Pu), 0.0)
        entropy[usable] = np.clip(-(1 / np.log(n)) * terms.sum(axis=0), 0, 1)
    divergence = np.maximum(1 - entropy, 0)
    divergence[~informative] = 0
    if divergence.sum() <= 1e-14:
        raise ValueError("所有指标在当前样本中均缺乏区分度，熵权不可识别")
    weights = divergence / divergence.sum()
    return {"weights": weights, "entropy": entropy, "divergence": divergence,
            "uninformative_columns": np.where(~informative)[0].tolist()}


def topsis_score(Xp, weights):
    Xp = _validate_X(Xp)
    w = np.asarray(weights, dtype=float).ravel()
    if len(w) != Xp.shape[1] or np.any(w < 0) or not np.isfinite(w).all() or w.sum() <= 0:
        raise ValueError("weights 非法")
    w = w / w.sum()
    norm = np.linalg.norm(Xp, axis=0)
    informative = norm > 0
    Z = np.zeros_like(Xp)
    Z[:, informative] = Xp[:, informative] / norm[informative]
    Zw = Z * w
    best, worst = Zw.max(axis=0), Zw.min(axis=0)
    d_best = np.linalg.norm(Zw - best, axis=1)
    d_worst = np.linalg.norm(Zw - worst, axis=1)
    denom = d_best + d_worst
    score = np.divide(d_worst, denom, out=np.full_like(d_worst, 0.5), where=denom > 0)
    rank = pd.Series(score).rank(ascending=False, method="min").astype(int).to_numpy()
    return {"score": score, "rank": rank, "weights": w}


def entropy_topsis(X, indicator_types, best_values=None):
    Xp = positivize_matrix(X, indicator_types, best_values)
    ew = entropy_weight(Xp)
    main = topsis_score(Xp, ew["weights"])
    equal = topsis_score(Xp, np.ones(Xp.shape[1]))
    return {
        "score": main["score"], "rank": main["rank"],
        "weights": ew["weights"], "entropy": ew["entropy"],
        "equal_weight_score": equal["score"], "equal_weight_rank": equal["rank"],
        "uninformative_columns": ew["uninformative_columns"],
        "baseline_max_rank_shift": int(np.max(np.abs(main["rank"] - equal["rank"]))),
        "claim_boundary": "熵权反映当前样本离散度；TOPSIS 分数是当前候选集与权重下的相对构造量",
        "positive_matrix": Xp,
    }


def sensitivity(result, relative_change=0.20):
    """对熵权逐项 ± 扰动，并做单指标删除。"""
    Xp = np.asarray(result["positive_matrix"], dtype=float)
    base_w = np.asarray(result["weights"], dtype=float)
    base_rank = np.asarray(result["rank"], dtype=int)
    rows = []

    def add(name, X_local, w_local):
        r = topsis_score(X_local, w_local)["rank"]
        rows.append({
            "scenario": name,
            "top1": int(np.argmin(r)),
            "max_rank_shift": int(np.max(np.abs(r - base_rank))),
            "rank": r.tolist(),
        })

    for j in range(len(base_w)):
        for factor in (1 - relative_change, 1 + relative_change):
            if factor > 0:
                w = base_w.copy(); w[j] *= factor
                add(f"weight_{j}_x{factor:.2f}", Xp, w)
    if Xp.shape[1] > 1:
        for j in range(Xp.shape[1]):
            keep = [k for k in range(Xp.shape[1]) if k != j]
            # 评估对象的 rank 长度不变，因此可直接比较。
            add(f"drop_indicator_{j}", Xp[:, keep], base_w[keep])

    base_top = int(np.argmin(base_rank))
    return {
        "scenarios": rows,
        "top1_stability_rate": float(np.mean([row["top1"] == base_top for row in rows])) if rows else 1.0,
        "worst_max_rank_shift": max((row["max_rank_shift"] for row in rows), default=0),
    }


if __name__ == "__main__":
    data = np.array([
        [6.8, 1.2, 8.5, 45, 3.9],
        [5.2, 0.9, 7.2, 52, 4.5],
        [7.9, 1.6, 9.1, 60, 3.2],
        [4.5, 0.8, 6.0, 48, 5.1],
        [6.1, 1.1, 8.0, 55, 4.0],
        [5.8, 1.4, 7.8, 42, 4.8],
    ])
    result = entropy_topsis(data, ["max", "min", "max", "mid", "min"], {3: 50})
    print("entropy weights:", np.round(result["weights"], 4))
    print("entropy rank:", result["rank"].tolist())
    print("equal-weight rank:", result["equal_weight_rank"].tolist())
    print("baseline max rank shift:", result["baseline_max_rank_shift"])
    print("sensitivity:", sensitivity(result))
    print("\n若熵权和等权结论明显不同，应解释是哪些指标离散度驱动了变化，而不是用‘客观赋权’结束论证。")
