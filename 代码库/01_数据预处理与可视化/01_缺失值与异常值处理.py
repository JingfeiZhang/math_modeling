# -*- coding: utf-8 -*-
"""
01 缺失与异常：诊断优先、处理参数显式、异常默认不删除
====================================================

study-only 模板。缺失和极端值首先是数据生成机制问题，不是“脏数据”的同义词。

原则：
- 先报告缺失/异常的比例、位置和业务含义，再决定处理；
- 预测任务中，均值/中位数/众数等填充值只能由训练折/训练窗口估计；
- 时间序列 bfill 和双向插值会使用未来信息，只有在任务信息边界允许时才能使用；
- IQR/3σ/LOF 只是异常候选检测，不自动证明记录错误；
- 真实极端天气、事故、峰值需求等可能正是题目要研究的现象，不能为了模型好看删除；
- 删除样本必须记录规则、原因和处理前后样本量。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.neighbors import LocalOutlierFactor


def detect_missing(df):
    df = pd.DataFrame(df)
    count = df.isna().sum()
    return pd.DataFrame({"missing_count": count, "missing_rate": df.isna().mean()})


def fit_stat_imputer(df_reference, cols=None, method="median"):
    """在 reference（预测任务通常是 train）上拟合填充值。"""
    df = pd.DataFrame(df_reference)
    cols = list(cols) if cols is not None else list(df.columns)
    values = {}
    for c in cols:
        s = df[c]
        if method == "mean":
            value = s.mean()
        elif method == "median":
            value = s.median()
        elif method == "mode":
            mode = s.mode(dropna=True)
            value = mode.iloc[0] if len(mode) else np.nan
        else:
            raise ValueError("method 必须为 mean/median/mode")
        if pd.isna(value):
            raise ValueError(f"列 {c!r} 在 reference 中无法估计填充值")
        values[c] = value
    return {"method": method, "values": values, "reference_rows": len(df)}


def apply_stat_imputer(df, fitted):
    out = pd.DataFrame(df).copy()
    for c, value in fitted["values"].items():
        if c not in out:
            raise ValueError(f"待处理数据缺少列 {c!r}")
        out[c] = out[c].fillna(value)
    return out


def fill_stat(df, cols=None, method="median"):
    """单集合探索兼容函数；预测实验请显式 fit_stat_imputer(train) 后 apply。"""
    fitted = fit_stat_imputer(df, cols, method)
    return apply_stat_imputer(df, fitted)


def fill_time_directional(df, method="ffill", cols=None):
    """方向性时间填补。ffill 只用过去；bfill 会用未来，调用者必须确认任务允许。"""
    out = pd.DataFrame(df).copy()
    cols = list(cols) if cols is not None else list(out.columns)
    if method not in {"ffill", "bfill"}:
        raise ValueError("method 只能为 ffill/bfill")
    for c in cols:
        out[c] = out[c].ffill() if method == "ffill" else out[c].bfill()
    return out


def interpolate_time(df, cols=None, method="linear", allow_future_information=False,
                     fill_edges=False, order=None):
    """双侧插值默认被视为会读取未来邻点；必须显式 opt-in。"""
    if not allow_future_information:
        raise ValueError(
            "插值通常会使用缺失点之后的观测；若任务信息边界允许，请显式设置 allow_future_information=True；"
            "在线/滚动预测优先使用因果填补或在每个训练窗口内单独拟合。"
        )
    out = pd.DataFrame(df).copy()
    cols = list(cols) if cols is not None else list(out.columns)
    for c in cols:
        kwargs = {"method": method}
        if method == "polynomial":
            if order is None:
                raise ValueError("polynomial 插值需要 order")
            kwargs["order"] = order
        out[c] = out[c].interpolate(**kwargs)
        if fill_edges:
            # 明确 opt-in；bfill 对开头缺失使用未来信息。
            out[c] = out[c].bfill().ffill()
    return out


def detect_outlier_3sigma(series, n_sigma=3.0):
    s = pd.Series(series, dtype=float)
    if n_sigma <= 0:
        raise ValueError("n_sigma 必须>0")
    mean, std = s.mean(), s.std(ddof=1)
    if not np.isfinite(std) or std == 0:
        return pd.Series(False, index=s.index), (float(mean), float(mean))
    lower, upper = mean - n_sigma * std, mean + n_sigma * std
    return (s < lower) | (s > upper), (float(lower), float(upper))


def fit_iqr_bounds(df_reference, cols=None, k=1.5):
    if k < 0:
        raise ValueError("k 必须>=0")
    df = pd.DataFrame(df_reference)
    cols = list(cols) if cols is not None else list(df.columns)
    bounds = {}
    for c in cols:
        s = pd.to_numeric(df[c], errors="coerce")
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        bounds[c] = (float(q1 - k * iqr), float(q3 + k * iqr))
    return {"k": float(k), "bounds": bounds, "reference_rows": len(df)}


def flag_iqr(df, fitted_bounds):
    df = pd.DataFrame(df)
    per_column = pd.DataFrame(False, index=df.index, columns=list(fitted_bounds["bounds"]))
    for c, (lower, upper) in fitted_bounds["bounds"].items():
        s = pd.to_numeric(df[c], errors="coerce")
        per_column[c] = (s < lower) | (s > upper)
    return {"any_flag": per_column.any(axis=1), "per_column": per_column}


def detect_outlier_iqr(series, k=1.5):
    df = pd.DataFrame({"x": series})
    fitted = fit_iqr_bounds(df, ["x"], k)
    flags = flag_iqr(df, fitted)["any_flag"]
    return flags, fitted["bounds"]["x"]


def detect_outlier_lof(df, n_neighbors=20, contamination="auto", scale_sensitive=True):
    X = np.asarray(pd.DataFrame(df), dtype=float)
    if X.ndim != 2 or len(X) < 3 or not np.isfinite(X).all():
        raise ValueError("LOF 输入必须为至少 3 行的有限数值矩阵")
    if not 1 <= n_neighbors < len(X):
        raise ValueError("n_neighbors 必须在 [1, n_samples-1]")
    if scale_sensitive:
        # 只提示语义，不在此处擅自标准化；正式流程应由训练数据拟合 scaler。
        scale_ratio = np.nanmax(np.std(X, axis=0)) / max(np.nanmin(np.std(X, axis=0)[np.std(X, axis=0) > 0], initial=1.0), 1e-12)
    else:
        scale_ratio = None
    lof = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=contamination)
    labels = lof.fit_predict(X)
    return {
        "flag": pd.Series(labels == -1, index=pd.DataFrame(df).index),
        "negative_outlier_factor": lof.negative_outlier_factor_.copy(),
        "scale_ratio_diagnostic": scale_ratio,
        "claim_boundary": "LOF 标记表示相对局部密度异常，不证明记录错误，也不应自动删除",
    }


def remove_flagged(df, flag, reason):
    """删除必须显式写 reason，防止‘检测到异常 -> 自动删除’。"""
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("删除异常候选必须记录明确原因，例如已核实的测量/录入错误")
    df = pd.DataFrame(df)
    flag = pd.Series(flag, index=df.index).astype(bool)
    return {
        "data": df.loc[~flag].copy(),
        "removed_rows": int(flag.sum()),
        "original_rows": int(len(df)),
        "reason": reason.strip(),
    }


if __name__ == "__main__":
    train = pd.DataFrame({"x": [1.0, 2.0, np.nan, 4.0, 100.0], "y": [2, 3, 4, 5, 6]})
    test = pd.DataFrame({"x": [np.nan, 10.0], "y": [7, 8]})
    imp = fit_stat_imputer(train, ["x"], method="median")
    print("imputer from train:", imp)
    print("test after train-fitted imputation:\n", apply_stat_imputer(test, imp))

    iqr = fit_iqr_bounds(train.fillna({"x": imp["values"]["x"]}), ["x"])
    flags = flag_iqr(train.fillna({"x": imp["values"]["x"]}), iqr)
    print("IQR candidate flags:", flags["any_flag"].tolist())
    print("\n异常检测首先产生‘待核验候选’，而不是自动删除命令。")
