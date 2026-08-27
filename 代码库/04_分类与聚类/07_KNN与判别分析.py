# -*- coding: utf-8 -*-
"""
07 KNN / LDA / QDA：折内预处理与公平比较
=====================================

study-only 模板。KNN 的尺度参数必须在每个 CV 训练折内部估计；不能先对整个训练集
StandardScaler.fit 后再 cross-validation。LDA/QDA 的假设与误差结构也应单独检查，
而不是因为某次 holdout Accuracy 更高就宣布普遍更优。
"""

from __future__ import annotations

import numpy as np
from sklearn.neighbors import KNeighborsClassifier
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis, QuadraticDiscriminantAnalysis
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, precision_score,
                             recall_score, f1_score, confusion_matrix)


def evaluate(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    avg = "binary" if len(np.unique(y_true)) == 2 else "macro"
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, average=avg, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, average=avg, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, average=avg, zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }


def knn_pipeline(k):
    return Pipeline([
        ("scale", StandardScaler()),
        ("knn", KNeighborsClassifier(n_neighbors=int(k))),
    ])


def choose_k(X_train, y_train, k_values=None, scoring="balanced_accuracy", cv_splits=5):
    X_train = np.asarray(X_train, dtype=float)
    y_train = np.asarray(y_train)
    k_values = list(range(1, 21)) if k_values is None else [int(k) for k in k_values]
    cv = StratifiedKFold(n_splits=cv_splits, shuffle=True, random_state=42)
    rows = []
    for k in k_values:
        if k < 1:
            continue
        scores = cross_val_score(knn_pipeline(k), X_train, y_train, cv=cv, scoring=scoring)
        rows.append({"k": k, "cv_mean": float(scores.mean()), "cv_std": float(scores.std())})
    if not rows:
        raise ValueError("没有可评估的 k")
    best = max(rows, key=lambda row: row["cv_mean"])
    return {"best_k": best["k"], "scoring": scoring, "cv": rows}


def run_all(X, y, test_size=0.3, seed=42, scoring="balanced_accuracy"):
    X = np.asarray(X, dtype=float)
    y = np.asarray(y)
    if X.ndim != 2 or len(X) != len(y) or not np.isfinite(X).all():
        raise ValueError("X/y 非法")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y
    )

    k_search = choose_k(X_train, y_train, scoring=scoring)
    models = {
        f"KNN(k={k_search['best_k']})": knn_pipeline(k_search["best_k"]),
        "LDA": Pipeline([("scale", StandardScaler()), ("lda", LinearDiscriminantAnalysis())]),
        "QDA": Pipeline([("scale", StandardScaler()), ("qda", QuadraticDiscriminantAnalysis())]),
    }
    results = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        results[name] = {"model": model, "metrics": evaluate(y_test, pred)}

    print("【holdout comparison】")
    for name, row in results.items():
        print(name, {k: round(v, 4) for k, v in row["metrics"].items() if isinstance(v, float)})
    print("KNN CV:", k_search)
    return {
        "models": results,
        "knn_search": k_search,
        "train_size": len(y_train), "test_size": len(y_test),
        "claim_boundary": "当前随机 holdout 仅适用于近似 i.i.d. 数据；若存在时间/主体/空间结构，应替换 split，并重新调参",
    }


def exploratory_lda_projection(X, y, n_components=2):
    """全数据 LDA 投影仅用于 exploratory visualization，不是样本外分类证据。"""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y)
    max_components = min(X.shape[1], len(np.unique(y)) - 1)
    n = min(int(n_components), max_components)
    if n < 1:
        raise ValueError("类别数不足")
    pipe = Pipeline([
        ("scale", StandardScaler()),
        ("lda", LinearDiscriminantAnalysis(n_components=n)),
    ])
    Z = pipe.fit_transform(X, y)
    return {"projection": Z, "model": pipe,
            "claim_boundary": "监督投影使用了全部标签，只用于展示已知类别结构，不证明样本外可分性"}


if __name__ == "__main__":
    from sklearn.datasets import load_wine
    wine = load_wine()
    result = run_all(wine.data, wine.target)
    print("\nKNN 的 scaler 已进入 Pipeline，因此 k 的每个 CV 折都不读取验证折的均值/方差。")
