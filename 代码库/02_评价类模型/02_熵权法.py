# -*- coding: utf-8 -*-
"""
02 熵权法：基于样本离散度的数据驱动权重
======================================

study-only 模板。熵权法根据当前样本中各指标的离散程度分配权重；它常被称作“客观赋权”，
但更准确的表述是 **data-dispersion-based weighting**：权重不需要人工逐项指定，
却仍依赖样本范围、指标变换、异常值和归一化方式，因此不等于“真实重要性”。

重要边界：
- 离散度大只表示在当前样本中区分度更高，不表示业务上更重要；
- 常数指标没有区分信息，应得到差异系数 0，而不是因为 0/0 处理错误得到高权重；
- 若所有指标都没有区分信息，熵权无法识别权重，应显式失败或改用题意支持的权重；
- 正式排序必须与 equal-weight / 简单业务 baseline 和权重稳定性一起看。
"""

from __future__ import annotations

import numpy as np

VALID_TYPES = {"max", "min", "mid", "range"}


def _validate_X(X):
    X = np.asarray(X, dtype=float)
    if X.ndim != 2 or X.shape[0] < 2 or X.shape[1] < 1:
        raise ValueError("X 必须至少包含 2 个对象和 1 个指标")
    if not np.isfinite(X).all():
        raise ValueError("X 含 NaN/Inf；缺失处理必须在赋权前明确完成")
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
            raise ValueError("mid 指标需要目标值 best")
        distance = np.abs(col - float(best))
        span = float(np.max(distance))
        return np.ones_like(col) if span == 0 else 1 - distance / span
    if best is None or len(best) != 2:
        raise ValueError("range 指标需要 [lower, upper]")
    lower, upper = map(float, best)
    if lower > upper:
        raise ValueError("range 下界不能大于上界")
    distance = np.maximum(lower - col, 0) + np.maximum(col - upper, 0)
    span = float(np.max(distance))
    return np.ones_like(col) if span == 0 else 1 - distance / span


def min_max_scale(X):
    X = _validate_X(X)
    mn = X.min(axis=0)
    mx = X.max(axis=0)
    span = mx - mn
    informative = span > 0
    Z = np.zeros_like(X, dtype=float)
    Z[:, informative] = (X[:, informative] - mn[informative]) / span[informative]
    return Z, informative


def entropy_weight(X, indicator_types=None, best_values=None, do_positivize=True,
                   return_details=False):
    """返回熵权；常数/无区分指标差异系数强制为 0。"""
    X = _validate_X(X)
    n, m = X.shape
    best_values = best_values or {}

    if do_positivize:
        if indicator_types is not None:
            if len(indicator_types) != m:
                raise ValueError("indicator_types 长度必须等于指标数")
            Xp = np.empty_like(X)
            for j, kind in enumerate(indicator_types):
                Xp[:, j] = positivize(X[:, j], kind, best_values.get(j))
        else:
            Xp = X.copy()
        Z, informative = min_max_scale(Xp)
    else:
        if np.any(X < 0):
            raise ValueError("do_positivize=False 时输入必须是已处理的非负矩阵")
        Z = X.copy()
        informative = np.ptp(Z, axis=0) > 0

    P = np.zeros_like(Z, dtype=float)
    col_sum = Z.sum(axis=0)
    usable = informative & (col_sum > 0)
    P[:, usable] = Z[:, usable] / col_sum[usable]

    k = 1.0 / np.log(n)
    e = np.ones(m, dtype=float)  # 无区分列定义为最大熵 -> d=0
    if np.any(usable):
        Pu = P[:, usable]
        with np.errstate(divide="ignore", invalid="ignore"):
            terms = np.where(Pu > 0, Pu * np.log(Pu), 0.0)
        e[usable] = -k * np.sum(terms, axis=0)
        e[usable] = np.clip(e[usable], 0.0, 1.0)

    d = np.maximum(1.0 - e, 0.0)
    d[~informative] = 0.0
    if d.sum() <= 1e-14:
        raise ValueError("当前样本中的指标均无足够区分信息，熵权无法识别权重；请复核指标或改用有依据的权重方案")
    w = d / d.sum()

    details = {
        "weights": w,
        "entropy": e,
        "divergence": d,
        "informative": informative,
        "uninformative_columns": np.where(~informative)[0].tolist(),
        "normalized_matrix": Z,
        "claim_boundary": "权重反映当前样本离散度，不等于指标的客观真实重要性",
    }
    if return_details:
        return details
    return w, e


if __name__ == "__main__":
    data = np.array([
        [3200, 4.5, 38, 55, 1.0],
        [2800, 3.2, 42, 48, 1.0],
        [4100, 5.8, 30, 72, 1.0],
        [3600, 4.0, 45, 50, 1.0],
        [2500, 6.2, 35, 65, 1.0],
    ], dtype=float)
    types = ["max", "min", "max", "min", "max"]
    result = entropy_weight(data, types, return_details=True)
    print("weights =", np.round(result["weights"], 4))
    print("entropy =", np.round(result["entropy"], 4))
    print("uninformative columns =", result["uninformative_columns"])
    print("注意：最后一列为常数，应得到 0 权重，而不是被误认为高信息指标。")
