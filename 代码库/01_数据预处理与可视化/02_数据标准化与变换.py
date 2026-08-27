# -*- coding: utf-8 -*-
"""
02 数据尺度与变换：fit-on-train / apply-on-new-data
================================================

study-only 模板。预处理不是固定流水线，任何会从样本分布“学习参数”的步骤都属于模型
的一部分：scaler、变换参数、特征选择、插补统计量等必须只在允许的信息边界内拟合。

- 预测/分类：fit 只看训练折/训练窗口，再 transform 验证与测试；
- 纯描述/评价：若全部对象本来就是同时评价的全集，可在该评价集合上定义尺度，但要说明；
- 树模型通常不因量纲不同而需要标准化；
- Box-Cox/Yeo-Johnson 的目标是改善模型残差/关系或数值性质，不是为了“让数据看起来正态”。
"""

from __future__ import annotations

import numpy as np
from scipy import stats
from sklearn.preprocessing import MinMaxScaler, StandardScaler, RobustScaler


def _matrix(X):
    X = np.asarray(X, dtype=float)
    if X.ndim != 2 or len(X) == 0 or not np.isfinite(X).all():
        raise ValueError("X 必须为非空有限二维矩阵")
    return X


def fit_scaler(X_train, method="standard"):
    X_train = _matrix(X_train)
    if method == "standard":
        scaler = StandardScaler()
    elif method == "minmax":
        scaler = MinMaxScaler()
    elif method == "robust":
        scaler = RobustScaler()
    else:
        raise ValueError("method 必须为 standard/minmax/robust")
    scaler.fit(X_train)
    return scaler


def transform_scaler(scaler, X):
    X = _matrix(X)
    out = scaler.transform(X)
    if not np.isfinite(out).all():
        raise ValueError("scaler transform 产生非有限值")
    return out


def fit_transform_split(X_train, X_other=None, method="standard"):
    """显式展示正确边界：只在 train 拟合；X_other 可以是 validation/test。"""
    scaler = fit_scaler(X_train, method)
    result = {"scaler": scaler, "train": transform_scaler(scaler, X_train), "other": None}
    if X_other is not None:
        result["other"] = transform_scaler(scaler, X_other)
    return result


def min_max_scale(X):
    """仅作单集合探索/评价便利函数；预测任务请用 fit_transform_split。"""
    X = _matrix(X)
    return fit_transform_split(X, method="minmax")["train"]


def z_score_scale(X):
    """仅作单集合探索便利函数；预测任务请用 fit_transform_split。"""
    X = _matrix(X)
    return fit_transform_split(X, method="standard")["train"]


def vector_normalize(X):
    """逐列 L2 归一化；零范数列保持 0 并应在后续记录为无区分指标。"""
    X = _matrix(X)
    norm = np.linalg.norm(X, axis=0)
    out = np.zeros_like(X)
    informative = norm > 0
    out[:, informative] = X[:, informative] / norm[informative]
    return out


def to_max(x):
    x = np.asarray(x, dtype=float)
    if not np.isfinite(x).all():
        raise ValueError("指标含 NaN/Inf")
    return np.max(x) - x


def to_middle(x, best):
    """中间型指标必须由题意/业务显式给 best，不能默默用样本中位数定义最优。"""
    x = np.asarray(x, dtype=float)
    if not np.isfinite(x).all() or not np.isfinite(float(best)):
        raise ValueError("x/best 必须有限")
    d = np.abs(x - float(best))
    span = float(np.max(d))
    return np.ones_like(x) if span == 0 else 1 - d / span


def to_interval(x, lower, upper):
    x = np.asarray(x, dtype=float)
    lower, upper = float(lower), float(upper)
    if not np.isfinite(x).all() or not np.isfinite([lower, upper]).all() or lower > upper:
        raise ValueError("区间或数据非法")
    d = np.maximum(lower - x, 0) + np.maximum(x - upper, 0)
    span = float(np.max(d))
    return np.ones_like(x) if span == 0 else 1 - d / span


def log_transform(x, shift=0.0):
    x = np.asarray(x, dtype=float)
    shifted = x + float(shift)
    if not np.isfinite(shifted).all() or np.any(shifted <= 0):
        raise ValueError("log 变换要求 x+shift>0；shift 必须由变量定义支持，不能只为运行而任意添加")
    return np.log(shifted)


def fit_boxcox(x_train):
    """只用训练参考样本选择 λ。"""
    x = np.asarray(x_train, dtype=float).ravel()
    if len(x) < 2 or not np.isfinite(x).all() or np.any(x <= 0):
        raise ValueError("Box-Cox 拟合要求至少两个有限正值")
    transformed, lmbda = stats.boxcox(x)
    return {"lambda": float(lmbda), "train": transformed}


def apply_boxcox(x, lmbda):
    x = np.asarray(x, dtype=float)
    if not np.isfinite(x).all() or np.any(x <= 0):
        raise ValueError("Box-Cox 应用要求正值")
    return stats.boxcox(x, lmbda=float(lmbda))


def boxcox_transform(x):
    """单集合探索兼容函数；预测任务应使用 fit_boxcox(train)+apply_boxcox(test)。"""
    fit = fit_boxcox(x)
    return fit["train"], fit["lambda"]


if __name__ == "__main__":
    X = np.array([[100, 0.2], [200, 0.5], [150, 0.8], [300, 0.1]], dtype=float)
    split = fit_transform_split(X[:3], X[3:], method="standard")
    print("train scaled:\n", np.round(split["train"], 3))
    print("held-out transformed with train parameters:\n", np.round(split["other"], 3))

    train_positive = np.array([1.0, 1.5, 2.0, 4.0, 8.0])
    test_positive = np.array([10.0, 12.0])
    bc = fit_boxcox(train_positive)
    print("Box-Cox lambda from train =", bc["lambda"])
    print("test transformed =", apply_boxcox(test_positive, bc["lambda"]))
    print("\n任何 scaler/变换参数如果看过 test，再报告 test 性能，就已经发生数据泄漏。")
