# -*- coding: utf-8 -*-
"""
04 相关分析：关联强度、区间与多重比较
=====================================

study-only 模板。相关分析用于描述 association，不自动识别因果。

- Pearson 描述线性关系；系数本身不要求变量“正态”，但经典小样本 p 值/区间的
  推断条件更强，应结合散点、异常值、独立性和研究设计判断。
- Spearman 描述单调秩关系；Kendall tau 适合秩关系、ties 和较小样本。
- 偏相关是在给定协变量线性调整后的剩余关联，不等于“控制了混杂所以得到因果效应”。
- 对很多变量同时做相关检验时，原始 p 值会累积假阳性，正式分析应预先定义主要关系
  或使用 FDR/FWER 控制。
- 不使用固定 |r| 阈值自动贴“强/弱”标签；相关大小必须结合领域尺度和实际意义解释。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

try:
    import matplotlib.pyplot as plt
    _HAS_PLT = True
except Exception:
    _HAS_PLT = False

ALPHA = 0.05


def _paired_clean(x, y):
    xy = np.column_stack([np.asarray(x, dtype=float), np.asarray(y, dtype=float)])
    xy = xy[np.isfinite(xy).all(axis=1)]
    if len(xy) < 3:
        raise ValueError("有效配对观测不足。")
    return xy[:, 0], xy[:, 1]


def _pearson_fisher_ci(r, n, alpha=ALPHA):
    """Fisher-z 近似区间；|r|=1 或 n<=3 时不可用。"""
    if n <= 3 or not np.isfinite(r) or abs(r) >= 1:
        return float("nan"), float("nan")
    z = np.arctanh(r)
    se = 1 / np.sqrt(n - 3)
    q = stats.norm.ppf(1 - alpha / 2)
    lo, hi = z - q * se, z + q * se
    return float(np.tanh(lo)), float(np.tanh(hi))


def pair_correlation(x, y, method="pearson", alpha=ALPHA):
    x, y = _paired_clean(x, y)
    if method == "pearson":
        r, p = stats.pearsonr(x, y)
        ci = _pearson_fisher_ci(float(r), len(x), alpha)
    elif method == "spearman":
        r, p = stats.spearmanr(x, y)
        ci = (float("nan"), float("nan"))
    elif method == "kendall":
        r, p = stats.kendalltau(x, y)
        ci = (float("nan"), float("nan"))
    else:
        raise ValueError("method 必须为 pearson/spearman/kendall")

    result = {
        "method": method, "n": len(x), "coefficient": float(r), "p": float(p),
        "alpha": alpha, "approx_ci": ci,
    }
    print(f"【{method} association】 coefficient={r:.4f}, n={len(x)}, p={p:.4g}")
    if method == "pearson" and np.isfinite(ci[0]):
        print(f"  {100*(1-alpha):.0f}% Fisher-z CI=[{ci[0]:.4f}, {ci[1]:.4f}]")
    if p < alpha:
        print("  在当前检验设定下有反对‘零关联’原假设的统计证据。")
    else:
        print("  当前样本未提供足够证据拒绝‘零关联’原假设；这不证明两变量独立。")
    print("  相关系数描述关联，不自动具有因果解释。")
    return result


def corr_matrix(df, method="pearson"):
    numeric = pd.DataFrame(df).apply(pd.to_numeric, errors="coerce")
    corr = numeric.corr(method=method)
    print(f"【{method} 相关系数矩阵】")
    print(corr.round(4))
    return corr


def _bh_adjust(p_values):
    """Benjamini-Hochberg FDR adjusted p-values，保持原顺序。"""
    p = np.asarray(p_values, dtype=float)
    m = len(p)
    order = np.argsort(p)
    ranked = p[order]
    adjusted = ranked * m / np.arange(1, m + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    adjusted = np.clip(adjusted, 0, 1)
    out = np.empty_like(adjusted)
    out[order] = adjusted
    return out


def corr_pvalue_matrix(df, method="pearson", alpha=ALPHA, adjust="fdr_bh"):
    """计算两两相关及 p 值；默认同时返回 BH-FDR 调整后的 q 值矩阵。"""
    numeric = pd.DataFrame(df).apply(pd.to_numeric, errors="coerce")
    cols = list(numeric.columns)
    n = len(cols)
    corr = np.eye(n)
    pval = np.full((n, n), np.nan)
    pairs = []
    raw_p = []
    func = {"pearson": stats.pearsonr, "spearman": stats.spearmanr,
            "kendall": stats.kendalltau}[method]

    for i in range(n):
        for j in range(i + 1, n):
            pair = numeric[[cols[i], cols[j]]].dropna()
            if len(pair) < 3:
                continue
            r, p = func(pair.iloc[:, 0], pair.iloc[:, 1])
            corr[i, j] = corr[j, i] = float(r)
            pval[i, j] = pval[j, i] = float(p)
            pairs.append((i, j))
            raw_p.append(float(p))

    qval = np.full((n, n), np.nan)
    if adjust == "fdr_bh" and raw_p:
        q = _bh_adjust(raw_p)
        for (i, j), value in zip(pairs, q):
            qval[i, j] = qval[j, i] = value
    elif adjust not in {None, "none"}:
        raise ValueError("adjust 目前支持 'fdr_bh' / 'none' / None")

    corr_df = pd.DataFrame(corr, index=cols, columns=cols)
    pval_df = pd.DataFrame(pval, index=cols, columns=cols)
    qval_df = pd.DataFrame(qval, index=cols, columns=cols)

    print(f"【{method} 两两关联】")
    for i, j in pairs:
        extra = f", q_BH={qval[i,j]:.4g}" if np.isfinite(qval[i, j]) else ""
        print(f"  {cols[i]} -- {cols[j]}: r/tau={corr[i,j]:.4f}, p={pval[i,j]:.4g}{extra}")
    print("  多重比较下优先结合调整后的 q 值、效应大小与事先研究问题解释。")
    return corr_df, pval_df, qval_df


def partial_correlation(df, x, y, covar, alpha=ALPHA):
    """线性残差法偏相关；结果仍是条件关联，不是自动的因果效应。"""
    covar = [covar] if isinstance(covar, str) else list(covar)
    data = pd.DataFrame(df)[[x, y, *covar]].dropna()
    if len(data) <= len(covar) + 3:
        raise ValueError("有效样本相对协变量数量过少。")
    z = np.column_stack([np.ones(len(data)), data[covar].to_numpy(dtype=float)])

    def residual(v):
        beta, *_ = np.linalg.lstsq(z, v, rcond=None)
        return v - z @ beta

    rx = residual(data[x].to_numpy(dtype=float))
    ry = residual(data[y].to_numpy(dtype=float))
    r, p = stats.pearsonr(rx, ry)
    print(f"【偏相关】给定 {covar} 的线性调整后，{x} 与 {y}: r={r:.4f}, p={p:.4g}")
    print("  该结果是模型条件下的剩余关联；协变量选择、函数形式和未观测混杂仍限制解释。")
    return {"coefficient": float(r), "p": float(p), "n": len(data), "covariates": covar, "alpha": alpha}


def corr_heatmap(corr, title="相关系数热力图", ax=None):
    """最小热力图；正式论文是否需要该图由 reader question 决定。"""
    if not _HAS_PLT:
        raise RuntimeError("matplotlib 不可用")
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(corr.values, vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.index)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right")
    ax.set_yticklabels(corr.index)
    for i in range(len(corr.index)):
        for j in range(len(corr.columns)):
            ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center", fontsize=8)
    plt.colorbar(im, ax=ax, shrink=0.8)
    ax.set_title(title)
    return ax


if __name__ == "__main__":
    rng = np.random.default_rng(2)
    n = 100
    x1 = rng.normal(0, 1, n)
    x2 = 0.8 * x1 + rng.normal(0, 0.6, n)
    x3 = -0.5 * x1 + rng.normal(0, 1, n)
    x4 = rng.normal(0, 1, n)
    df = pd.DataFrame({"指标1": x1, "指标2": x2, "指标3": x3, "指标4": x4})

    pair_correlation(df["指标1"], df["指标2"], method="pearson")
    corr, pval, qval = corr_pvalue_matrix(df, method="pearson", adjust="fdr_bh")
    partial_correlation(df, "指标2", "指标3", covar="指标1")

    if _HAS_PLT:
        ax = corr_heatmap(corr, "Pearson association")
        ax.figure.tight_layout()
        ax.figure.savefig("04_相关分析_示例.png", dpi=150, bbox_inches="tight")
        plt.close(ax.figure)
