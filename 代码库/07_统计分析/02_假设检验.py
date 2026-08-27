# -*- coding: utf-8 -*-
"""
02 假设检验：效应量、区间与检验证据
=====================================

本文件是 study-only 统计模板。推荐报告顺序：

    效应方向/大小 -> 置信区间 -> p 值 -> 设计与假设边界

关键原则：
- 独立两组均值比较默认使用 Welch t，不再“先 Levene、再按 p 值切换 t 检验”。
- 参数/非参数方法由研究问题、量表、分布形态、异常值、样本量和估计目标共同决定，
  不使用“正态性检验 p<0.05 -> 全部改非参数”的机械流程。
- Mann-Whitney U 不是一般意义上的“中位数检验”；分布形状不同时应谨慎解释。
- p<0.05 不等于效果大、实际意义强或存在因果；p>=0.05 也不证明两组相同。
- 大量并行检验需要预先定义主比较或控制 FWER/FDR。
"""

from __future__ import annotations

import math
import numpy as np
from scipy import stats

ALPHA = 0.05


def _clean_1d(data):
    x = np.asarray(data, dtype=float).ravel()
    return x[np.isfinite(x)]


def _evidence_text(p, alpha=ALPHA):
    if not np.isfinite(p):
        return "p 值不可用"
    if p < alpha:
        return f"在 α={alpha:.2f} 下有反对 H0 的统计证据"
    return f"在 α={alpha:.2f} 下未发现足够证据拒绝 H0"


def _mean_ci(x, alpha=ALPHA):
    x = _clean_1d(x)
    n = len(x)
    if n < 2:
        return float("nan"), float("nan")
    mean = float(np.mean(x))
    se = float(stats.sem(x))
    q = stats.t.ppf(1 - alpha / 2, n - 1)
    return mean - q * se, mean + q * se


def _cohen_d_one_sample(x, popmean):
    x = _clean_1d(x)
    sd = np.std(x, ddof=1)
    return float((np.mean(x) - popmean) / sd) if sd > 0 else float("nan")


def _hedges_g_independent(a, b):
    """近似 Hedges g；仅是标准化组间差异，不是因果效应。"""
    a, b = _clean_1d(a), _clean_1d(b)
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return float("nan")
    s1, s2 = np.var(a, ddof=1), np.var(b, ddof=1)
    pooled = math.sqrt(((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2))
    if pooled == 0:
        return float("nan")
    d = (np.mean(a) - np.mean(b)) / pooled
    correction = 1 - 3 / (4 * (n1 + n2) - 9)
    return float(correction * d)


def _welch_diff_ci(a, b, alpha=ALPHA):
    """Welch-Satterthwaite 区间，目标为 mean(a)-mean(b)。"""
    a, b = _clean_1d(a), _clean_1d(b)
    n1, n2 = len(a), len(b)
    m1, m2 = np.mean(a), np.mean(b)
    v1, v2 = np.var(a, ddof=1), np.var(b, ddof=1)
    se2 = v1 / n1 + v2 / n2
    if se2 <= 0:
        return float(m1 - m2), (float("nan"), float("nan")), float("nan")
    df = se2 ** 2 / ((v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1))
    q = stats.t.ppf(1 - alpha / 2, df)
    diff = float(m1 - m2)
    se = math.sqrt(se2)
    return diff, (diff - q * se, diff + q * se), float(df)


def one_sample_ttest(data, popmean, alpha=ALPHA):
    x = _clean_1d(data)
    t, p = stats.ttest_1samp(x, popmean)
    ci = _mean_ci(x, alpha)
    d = _cohen_d_one_sample(x, popmean)
    result = {
        "test": "one_sample_t", "n": len(x), "mean": float(np.mean(x)),
        "reference": float(popmean), "mean_ci": tuple(map(float, ci)),
        "cohen_d": d, "stat": float(t), "p": float(p), "alpha": alpha,
    }
    print("【单样本 t】")
    print(f"  mean={result['mean']:.4f}, {100*(1-alpha):.0f}% CI=[{ci[0]:.4f}, {ci[1]:.4f}]")
    print(f"  相对参考值 {popmean:.4f} 的 Cohen d={d:.4f}")
    print(f"  t={t:.4f}, p={p:.4g}; {_evidence_text(p, alpha)}")
    return result


def two_sample_ttest(a, b, alpha=ALPHA):
    """独立两组均值比较，默认 Welch t，并返回原始差、区间和 Hedges g。"""
    a, b = _clean_1d(a), _clean_1d(b)
    t, p = stats.ttest_ind(a, b, equal_var=False)
    diff, ci, df = _welch_diff_ci(a, b, alpha)
    g = _hedges_g_independent(a, b)
    result = {
        "test": "welch_t", "n_a": len(a), "n_b": len(b),
        "mean_a": float(np.mean(a)), "mean_b": float(np.mean(b)),
        "mean_difference_a_minus_b": diff, "difference_ci": tuple(map(float, ci)),
        "hedges_g": g, "df": df, "stat": float(t), "p": float(p), "alpha": alpha,
    }
    print("【独立双样本 Welch t】")
    print(f"  A mean={np.mean(a):.4f} (n={len(a)}), B mean={np.mean(b):.4f} (n={len(b)})")
    print(f"  A-B={diff:.4f}, {100*(1-alpha):.0f}% CI=[{ci[0]:.4f}, {ci[1]:.4f}], Hedges g={g:.4f}")
    print(f"  t={t:.4f}, df≈{df:.2f}, p={p:.4g}; {_evidence_text(p, alpha)}")
    return result


def paired_ttest(x, y, alpha=ALPHA):
    x, y = _clean_1d(x), _clean_1d(y)
    if len(x) != len(y):
        raise ValueError("配对样本必须等长，且缺失值应按配对共同删除。")
    diff = x - y
    t, p = stats.ttest_rel(x, y)
    ci = _mean_ci(diff, alpha)
    sd = np.std(diff, ddof=1)
    dz = float(np.mean(diff) / sd) if sd > 0 else float("nan")
    result = {
        "test": "paired_t", "n_pairs": len(diff),
        "mean_difference": float(np.mean(diff)), "difference_ci": tuple(map(float, ci)),
        "cohen_dz": dz, "stat": float(t), "p": float(p), "alpha": alpha,
    }
    print("【配对 t】")
    print(f"  配对差均值={np.mean(diff):.4f}, {100*(1-alpha):.0f}% CI=[{ci[0]:.4f}, {ci[1]:.4f}], dz={dz:.4f}")
    print(f"  t={t:.4f}, p={p:.4g}; {_evidence_text(p, alpha)}")
    return result


def mann_whitney(a, b, alpha=ALPHA):
    a, b = _clean_1d(a), _clean_1d(b)
    u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    rank_biserial = float(2 * u / (len(a) * len(b)) - 1)
    result = {
        "test": "mann_whitney_u", "n_a": len(a), "n_b": len(b),
        "median_a": float(np.median(a)), "median_b": float(np.median(b)),
        "rank_biserial": rank_biserial, "stat": float(u), "p": float(p), "alpha": alpha,
    }
    print("【Mann-Whitney U】")
    print(f"  median(A)={np.median(a):.4f}, median(B)={np.median(b):.4f}, rank-biserial={rank_biserial:.4f}")
    print(f"  U={u:.4f}, p={p:.4g}; {_evidence_text(p, alpha)}")
    print("  注意：若两组分布形状不同，不应把该检验简单解释为‘中位数检验’。")
    return result


def wilcoxon_signed(x, y, alpha=ALPHA):
    x, y = _clean_1d(x), _clean_1d(y)
    if len(x) != len(y):
        raise ValueError("配对样本必须等长，且缺失值应按配对共同删除。")
    diff = x - y
    w, p = stats.wilcoxon(diff)
    result = {
        "test": "wilcoxon_signed_rank", "n_pairs": len(diff),
        "median_difference": float(np.median(diff)), "stat": float(w),
        "p": float(p), "alpha": alpha,
    }
    print("【Wilcoxon 符号秩】")
    print(f"  配对差中位数={np.median(diff):.4f}, W={w:.4f}, p={p:.4g}; {_evidence_text(p, alpha)}")
    return result


def chi2_independence(table, alpha=ALPHA):
    table = np.asarray(table)
    correction = table.shape == (2, 2)
    chi2, p, dof, expected = stats.chi2_contingency(table, correction=correction)
    n = table.sum()
    phi2 = chi2 / n if n > 0 else float("nan")
    k = min(table.shape[0] - 1, table.shape[1] - 1)
    cramers_v = math.sqrt(phi2 / k) if k > 0 and np.isfinite(phi2) else float("nan")
    result = {
        "test": "chi2_independence", "chi2": float(chi2), "p": float(p),
        "dof": int(dof), "cramers_v": float(cramers_v),
        "expected_min": float(np.min(expected)),
        "expected_lt5_fraction": float(np.mean(expected < 5)), "alpha": alpha,
    }
    print("【卡方独立性】")
    print(f"  chi2={chi2:.4f}, dof={dof}, p={p:.4g}, Cramer's V={cramers_v:.4f}")
    print(f"  {_evidence_text(p, alpha)}")
    if (expected < 5).any():
        print("  警告：存在较小期望频数；2x2 可考虑 Fisher，较大表需检查卡方近似是否可靠。")
    return result


def chi2_goodness(observed, expected=None, alpha=ALPHA):
    observed = np.asarray(observed, dtype=float)
    chi2, p = stats.chisquare(observed, expected)
    result = {"test": "chi2_goodness", "chi2": float(chi2), "p": float(p), "alpha": alpha}
    print("【卡方拟合优度】")
    print(f"  chi2={chi2:.4f}, p={p:.4g}; {_evidence_text(p, alpha)}")
    return result


def fisher_exact_test(table, alpha=ALPHA):
    table = np.asarray(table)
    odds, p = stats.fisher_exact(table, alternative="two-sided")
    result = {"test": "fisher_exact", "odds_ratio": float(odds), "p": float(p), "alpha": alpha}
    print("【Fisher 精确检验】")
    print(f"  OR={odds:.4f}, p={p:.4g}; {_evidence_text(p, alpha)}")
    print("  OR 是关联强度，不因检验显著而自动具有因果解释。")
    return result


if __name__ == "__main__":
    rng = np.random.default_rng(0)

    print("\n########## 均值比较：先看效应和区间 ##########")
    weights = rng.normal(102, 5, 30)
    one_sample_ttest(weights, popmean=100)

    group_a = rng.normal(50, 6, 40)
    group_b = rng.normal(54, 9, 35)
    two_sample_ttest(group_a, group_b)

    before = rng.normal(70, 8, 25)
    after = before + rng.normal(3, 4, 25)
    paired_ttest(after, before)

    print("\n########## 秩检验：解释范围与设计匹配 ##########")
    skew_a = rng.exponential(5, 30)
    skew_b = rng.exponential(7, 30)
    mann_whitney(skew_a, skew_b)
    wilcoxon_signed(after, before)

    print("\n########## 分类变量关联 ##########")
    contingency = np.array([[30, 20], [15, 35]])
    chi2_independence(contingency)
    fisher_exact_test(contingency)

    print("\n注意：正式分析应先定义主要比较；大量变量逐个检验时需控制多重比较。")
