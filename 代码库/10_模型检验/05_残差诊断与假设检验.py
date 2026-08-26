# -*- coding: utf-8 -*-
"""
残差诊断与假设检查（study-only reference）

本模板不输出“模型通过/未通过”的总分。统计检验只能提供针对某项假设的证据，
不能证明模型整体正确、稳健或具有因果效力。是否需要某项诊断取决于当前模型的
推断目标、数据结构和失败风险。
"""

import numpy as np
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.stattools import durbin_watson

ALPHA = 0.05


def _pvalue_status(p, null_name):
    if not np.isfinite(p):
        return "not_available"
    if p < ALPHA:
        return f"evidence_against_{null_name}"
    return f"insufficient_evidence_against_{null_name}"


def test_normality(resid):
    """
    Shapiro-Wilk: H0 为样本来自正态分布。
    p>=alpha 只能解释为“没有足够证据拒绝 H0”，不能写成“证明正态”。
    """
    resid = np.asarray(resid, dtype=float).ravel()
    if resid.size < 3:
        raise ValueError("Shapiro-Wilk 至少需要 3 个残差")
    sample = (
        resid
        if resid.size <= 5000
        else np.random.default_rng(0).choice(resid, 5000, replace=False)
    )
    stat, p = stats.shapiro(sample)
    status = _pvalue_status(float(p), "normality")
    print(f"Shapiro-Wilk: W={stat:.4f}, p={p:.4g}, status={status}")
    return {
        "name": "normality",
        "stat": float(stat),
        "p": float(p),
        "status": status,
        "interpretation": (
            "存在反对正态假设的证据；若推断依赖正态性，考虑稳健/Bootstrap/变换。"
            if p < ALPHA
            else "未发现足够证据拒绝正态假设；这不等于证明残差正态。"
        ),
    }


def test_homoscedasticity_levene(resid, y_pred, n_groups=3):
    """
    按预测值分组的 Levene 探针。分组方式本身是诊断设计的一部分，
    不应把 p>=alpha 写成“同方差已证明”。
    """
    resid = np.asarray(resid, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    if len(resid) != len(y_pred):
        raise ValueError("resid 与 y_pred 长度必须一致")
    if n_groups < 2 or len(resid) < n_groups * 2:
        raise ValueError("样本量不足以进行当前分组 Levene 诊断")
    order = np.argsort(y_pred)
    groups = np.array_split(resid[order], n_groups)
    stat, p = stats.levene(*groups)
    status = _pvalue_status(float(p), "equal_variance")
    print(f"Levene: W={stat:.4f}, p={p:.4g}, status={status}")
    return {
        "name": "equal_variance",
        "stat": float(stat),
        "p": float(p),
        "status": status,
        "interpretation": (
            "存在组间方差差异信号；考虑稳健标准误、WLS、变换或重新建模。"
            if p < ALPHA
            else "当前分组下未发现足够证据拒绝等方差；仍应结合残差图判断。"
        ),
    }


def test_independence_dw(resid):
    """
    Durbin-Watson 是自相关诊断量，不是“独立性通过证书”。
    1.5~2.5 仅作为粗略筛查区间。
    """
    resid = np.asarray(resid, dtype=float).ravel()
    dw = float(durbin_watson(resid))
    if dw < 1.5:
        status = "possible_positive_autocorrelation"
    elif dw > 2.5:
        status = "possible_negative_autocorrelation"
    else:
        status = "no_obvious_first_order_signal"
    print(f"Durbin-Watson: DW={dw:.4f}, status={status}")
    return {
        "name": "first_order_autocorrelation",
        "stat": dw,
        "p": np.nan,
        "status": status,
        "interpretation": (
            "DW 只用于初步筛查；时序/面板数据应结合残差 ACF、Ljung-Box、"
            "分组结构或相应模型诊断。"
        ),
    }


def test_heteroscedasticity_bp(resid, X):
    """Breusch-Pagan: H0 为误差方差不随给定解释变量系统变化。"""
    resid = np.asarray(resid, dtype=float).ravel()
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    if len(resid) != len(X):
        raise ValueError("resid 与 X 行数必须一致")
    Xc = sm.add_constant(X)
    lm_stat, lm_p, f_stat, f_p = het_breuschpagan(resid, Xc)
    status = _pvalue_status(float(lm_p), "homoscedasticity")
    print(f"Breusch-Pagan: LM={lm_stat:.4f}, p={lm_p:.4g}, status={status}")
    return {
        "name": "heteroscedasticity",
        "stat": float(lm_stat),
        "p": float(lm_p),
        "f_stat": float(f_stat),
        "f_p": float(f_p),
        "status": status,
        "interpretation": (
            "存在异方差信号；检查模型形式并考虑稳健标准误/WLS/变换。"
            if lm_p < ALPHA
            else "未发现足够证据拒绝同方差；不代表模型其他假设成立。"
        ),
    }


def diagnose_residuals(
    y_true=None,
    y_pred=None,
    residuals=None,
    X=None,
    run_normality=True,
    run_levene=True,
    run_dw=True,
    run_bp=True,
):
    """
    按需要执行残差诊断。调用方应根据模型目标选择测试，而不是机械全跑。

    返回 diagnostics 列表，不生成“总通过率”。
    """
    if residuals is None:
        if y_true is None or y_pred is None:
            raise ValueError("请提供 (y_true, y_pred) 或 residuals")
        y_true = np.asarray(y_true, dtype=float).ravel()
        y_pred = np.asarray(y_pred, dtype=float).ravel()
        if len(y_true) != len(y_pred):
            raise ValueError("y_true 与 y_pred 长度必须一致")
        residuals = y_true - y_pred
    else:
        residuals = np.asarray(residuals, dtype=float).ravel()
        if y_pred is not None:
            y_pred = np.asarray(y_pred, dtype=float).ravel()

    diagnostics = []

    if run_normality:
        diagnostics.append(test_normality(residuals))

    if run_levene:
        if y_pred is None:
            print("Levene: skipped（未提供 y_pred，无法按预测水平分组）")
        else:
            diagnostics.append(test_homoscedasticity_levene(residuals, y_pred))

    if run_dw:
        diagnostics.append(test_independence_dw(residuals))

    if run_bp:
        if X is None:
            print("Breusch-Pagan: skipped（未提供 X）")
        else:
            diagnostics.append(test_heteroscedasticity_bp(residuals, X))

    print("-" * 64)
    print("诊断摘要（不是模型总分）：")
    for item in diagnostics:
        print(f"  {item['name']}: {item['status']}")
        print(f"    {item['interpretation']}")

    print(
        "结论边界：以上结果只说明特定残差风险是否被观察到；"
        "模型是否可信还需结合样本外表现、baseline、数据生成结构和任务专项验证。"
    )
    return diagnostics


if __name__ == "__main__":
    # 【Study-only example】
    rng = np.random.default_rng(42)
    n = 150
    X = rng.uniform(0, 10, (n, 2))
    y = X @ np.array([2.0, -1.0]) + 5
    pred = y + rng.normal(0, 1.0, n)

    diagnose_residuals(y_true=y, y_pred=pred, X=X)

    print(
        "\n正式赛题不要把‘p>=0.05’写成模型通过。"
        "先说明当前模型最可能违反哪项假设，再选择对应诊断。"
    )