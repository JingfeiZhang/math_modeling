# -*- coding: utf-8 -*-
"""
03 AHP：主观判断权重、一致性诊断与敏感性
=======================================

study-only 模板。AHP 适用于确实需要表达专家/决策者成对偏好的场景。

关键边界：
- CR 只检查判断矩阵的内部一致性，不证明偏好“客观正确”；
- 1--9 标度和成对判断本身是主观输入，应说明来源；
- 默认使用主特征向量法；把算术/几何/特征值三种权重简单平均没有普遍的
  “更稳健”理论保证，因此不作为默认方法；
- 若关键判断轻微变化就改变推荐方案，应把这种不稳定性写进结论。
"""

from __future__ import annotations

import warnings
import numpy as np

# 常用 Saaty RI 近似表，索引为矩阵阶数 n；不同文献/模拟表可能略有差异。
RI_TABLE = {
    1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12,
    6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49,
    11: 1.51, 12: 1.48, 13: 1.56, 14: 1.57, 15: 1.59,
}


def validate_judgment_matrix(A, reciprocal_tol=1e-6):
    A = np.asarray(A, dtype=float)
    if A.ndim != 2 or A.shape[0] != A.shape[1]:
        raise ValueError("判断矩阵必须是方阵")
    if not np.isfinite(A).all() or np.any(A <= 0):
        raise ValueError("AHP 判断矩阵必须为正的有限数")
    if not np.allclose(np.diag(A), 1.0, atol=reciprocal_tol, rtol=0):
        raise ValueError("判断矩阵主对角线应为 1")
    reciprocal_error = np.max(np.abs(A * A.T - 1.0))
    if reciprocal_error > reciprocal_tol:
        raise ValueError(f"判断矩阵不是正互反矩阵；最大互反误差={reciprocal_error:.3g}")
    return A


def _weight_vector(A, method="eigen"):
    A = validate_judgment_matrix(A)
    n = len(A)
    if method == "arithmetic":
        w = np.mean(A / A.sum(axis=0), axis=1)
    elif method == "geometric":
        log_gm = np.mean(np.log(A), axis=1)
        w = np.exp(log_gm - np.max(log_gm))
    elif method == "eigen":
        eigvals, eigvecs = np.linalg.eig(A)
        idx = int(np.argmax(eigvals.real))
        vec = eigvecs[:, idx].real
        if np.sum(vec) < 0:
            vec = -vec
        w = np.abs(vec)
    elif method == "comprehensive":
        warnings.warn(
            "comprehensive 仅为历史兼容：简单平均三种近似权重没有普遍稳健性保证；"
            "正式分析优先 eigen/geometric，并用判断扰动检查敏感性。",
            RuntimeWarning,
        )
        ws = [_weight_vector(A, m)[0] for m in ("arithmetic", "geometric", "eigen")]
        w = np.mean(ws, axis=0)
    else:
        raise ValueError("method 必须为 arithmetic/geometric/eigen/comprehensive")
    w = np.asarray(w, dtype=float)
    if not np.isfinite(w).all() or np.any(w < 0) or w.sum() <= 0:
        raise ValueError("权重计算失败")
    return w / w.sum(), n


def consistency(A, threshold=0.10):
    """返回 λmax、CI、CR 与诊断状态。CR 是内部一致性指标，不是有效性证明。"""
    A = validate_judgment_matrix(A)
    n = len(A)
    eigvals = np.linalg.eigvals(A)
    lambda_max = float(np.max(eigvals.real))
    if n <= 2:
        ci, cr = 0.0, 0.0
    elif n not in RI_TABLE:
        ci, cr = float((lambda_max - n) / (n - 1)), None
    else:
        ci = float((lambda_max - n) / (n - 1))
        ri = RI_TABLE[n]
        cr = float(ci / ri) if ri > 0 else 0.0
    status = "CONSISTENT_ENOUGH" if cr is not None and cr < threshold else (
        "RI_UNAVAILABLE" if cr is None else "REVIEW_JUDGMENTS"
    )
    return {"lambda_max": lambda_max, "CI": ci, "CR": cr, "threshold": threshold, "status": status}


def cal_weights(A, algorithm="eigen", consistency_threshold=0.10):
    w, _ = _weight_vector(A, algorithm)
    diag = consistency(A, consistency_threshold)
    return {"weights": w, "method": algorithm, **diag,
            "claim_boundary": "权重反映当前成对判断输入；一致性比率不证明偏好客观正确"}


def ahp(criteria, alternatives=None, algorithm="eigen", consistency_threshold=0.10,
        allow_inconsistent=False):
    """AHP 主流程，返回结构化结果；不一致时默认停止综合排序。"""
    crit = cal_weights(criteria, algorithm, consistency_threshold)
    accepted_criteria = crit["status"] == "CONSISTENT_ENOUGH"
    result = {
        "criteria": crit,
        "accepted": accepted_criteria or allow_inconsistent,
        "scores": None,
        "rank": None,
        "alternative_layers": [],
    }
    if not result["accepted"]:
        result["reason"] = "准则层判断一致性不足；先复核成对判断，不应直接输出推荐方案"
        return result
    if alternatives is None:
        return result
    if len(alternatives) != len(crit["weights"]):
        raise ValueError("方案层判断矩阵数量必须等于准则数")

    local_weights = []
    all_layers_ok = True
    for i, matrix in enumerate(alternatives):
        layer = cal_weights(matrix, algorithm, consistency_threshold)
        layer["criterion_index"] = i
        result["alternative_layers"].append(layer)
        local_weights.append(layer["weights"])
        all_layers_ok &= layer["status"] == "CONSISTENT_ENOUGH"

    if not all_layers_ok and not allow_inconsistent:
        result["accepted"] = False
        result["reason"] = "至少一个方案层判断一致性不足；复核后再综合排序"
        return result

    W = np.asarray(local_weights, dtype=float)
    if len({len(row) for row in W}) != 1:
        raise ValueError("各方案层矩阵必须对应相同方案集合")
    scores = crit["weights"] @ W
    rank = (-scores).argsort().argsort() + 1
    result.update({
        "accepted": True,
        "scores": scores,
        "rank": rank,
        "claim_boundary": "排名仅表示当前判断矩阵、标度与层次结构下的综合偏好，不是绝对客观最优",
    })
    return result


def judgment_sensitivity(A, method="eigen", relative_change=0.10, consistency_threshold=0.10):
    """逐个上三角判断做 ±relative_change 的互反扰动，观察权重与首位准则变化。"""
    A = validate_judgment_matrix(A)
    base = cal_weights(A, method, consistency_threshold)
    base_w = base["weights"]
    scenarios = []
    n = len(A)
    for i in range(n):
        for j in range(i + 1, n):
            for factor in (1 - relative_change, 1 + relative_change):
                if factor <= 0:
                    continue
                B = A.copy()
                B[i, j] *= factor
                B[j, i] = 1.0 / B[i, j]
                res = cal_weights(B, method, consistency_threshold)
                scenarios.append({
                    "pair": (i, j), "factor": factor,
                    "top_criterion": int(np.argmax(res["weights"])),
                    "max_abs_weight_shift": float(np.max(np.abs(res["weights"] - base_w))),
                    "CR": res["CR"], "status": res["status"],
                })
    top = int(np.argmax(base_w))
    return {
        "base_weights": base_w,
        "base_top_criterion": top,
        "scenarios": scenarios,
        "top_stability_rate": float(np.mean([r["top_criterion"] == top for r in scenarios])) if scenarios else 1.0,
        "worst_weight_shift": max((r["max_abs_weight_shift"] for r in scenarios), default=0.0),
    }


if __name__ == "__main__":
    criteria = np.array([
        [1,   2,   7,   5,   5],
        [1/2, 1,   4,   3,   3],
        [1/7, 1/4, 1,   1/2, 1/3],
        [1/5, 1/3, 2,   1,   1],
        [1/5, 1/3, 3,   1,   1],
    ], dtype=float)

    b = [
        np.array([[1, 1/3, 1/8], [3, 1, 1/3], [8, 3, 1]], dtype=float),
        np.array([[1, 2, 5], [1/2, 1, 2], [1/5, 1/2, 1]], dtype=float),
        np.array([[1, 1, 3], [1, 1, 3], [1/3, 1/3, 1]], dtype=float),
        np.array([[1, 3, 4], [1/3, 1, 1], [1/4, 1, 1]], dtype=float),
        np.array([[1, 4, 1/2], [1/4, 1, 1/4], [2, 4, 1]], dtype=float),
    ]

    result = ahp(criteria, b)
    print("AHP result:", {k: v for k, v in result.items() if k not in {"criteria", "alternative_layers"}})
    print("criteria diagnostics:", result["criteria"])
    print("judgment sensitivity:", judgment_sensitivity(criteria))
    print("\n论文应说明判断来源，并把 CR 写成一致性诊断；不要把 CR<0.1 写成权重客观有效的证明。")
