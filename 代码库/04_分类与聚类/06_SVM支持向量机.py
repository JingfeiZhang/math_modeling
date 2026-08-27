# -*- coding: utf-8 -*-
"""
06 SVM：折内预处理、可配置调参与分类证据
=====================================

study-only 模板。SVM 对尺度敏感，但 scaler 必须放在 CV Pipeline 内；先对整个训练集
fit scaler 再 GridSearchCV，会让各验证折的信息进入预处理参数，形成隐蔽泄漏。

模型选择应由样本规模、边界结构、误判代价和验证结果决定；RBF 不是“绝大多数问题的
默认最优核”。Accuracy 也不是类别不平衡任务的默认调参指标。
"""

from __future__ import annotations

import numpy as np
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, precision_score,
                             recall_score, f1_score, confusion_matrix)


def classification_metrics(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    average = "binary" if len(np.unique(y_true)) == 2 else "macro"
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, average=average, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, average=average, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, average=average, zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
        "average": average,
    }


def build_svm_pipeline(C=1.0, kernel="rbf", gamma="scale", class_weight=None):
    return Pipeline([
        ("scale", StandardScaler()),
        ("svc", SVC(C=C, kernel=kernel, gamma=gamma, class_weight=class_weight)),
    ])


def grid_search_svm(X_train, y_train, scoring="balanced_accuracy", cv_splits=5,
                    class_weight=None, n_jobs=1):
    """scaler 在每个 CV 训练子折内部拟合。"""
    pipe = build_svm_pipeline(class_weight=class_weight)
    param_grid = [
        {"svc__kernel": ["linear"], "svc__C": [0.1, 1, 10, 100]},
        {"svc__kernel": ["rbf"], "svc__C": [0.1, 1, 10, 100],
         "svc__gamma": ["scale", 0.01, 0.1, 1]},
    ]
    cv = StratifiedKFold(n_splits=cv_splits, shuffle=True, random_state=42)
    grid = GridSearchCV(pipe, param_grid, cv=cv, scoring=scoring,
                        n_jobs=n_jobs, return_train_score=True)
    grid.fit(X_train, y_train)
    return {
        "model": grid.best_estimator_,
        "best_params": dict(grid.best_params_),
        "best_cv_score": float(grid.best_score_),
        "scoring": scoring,
        "cv_splits": cv_splits,
        "cv_results": grid.cv_results_,
    }


def run_svm(X, y, test_size=0.3, do_grid=True, scoring="balanced_accuracy",
            class_weight=None, seed=42):
    X = np.asarray(X, dtype=float)
    y = np.asarray(y)
    if X.ndim != 2 or len(X) != len(y) or not np.isfinite(X).all():
        raise ValueError("X/y 形状或数值非法")
    if len(np.unique(y)) < 2:
        raise ValueError("至少需要两个类别")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y
    )
    if do_grid:
        search = grid_search_svm(X_train, y_train, scoring=scoring,
                                 class_weight=class_weight)
        model = search["model"]
    else:
        model = build_svm_pipeline(class_weight=class_weight)
        model.fit(X_train, y_train)
        search = None

    pred = model.predict(X_test)
    metrics = classification_metrics(y_test, pred)
    svc = model.named_steps["svc"]
    result = {
        "model": model,
        "search": search,
        "metrics": metrics,
        "train_size": len(y_train),
        "test_size": len(y_test),
        "support_vectors_per_class": svc.n_support_.tolist(),
        "claim_boundary": "性能来自当前 holdout/CV 结构；若数据按时间、主体或空间相关，应改用对应 split，随机分层并不代表真实部署能力",
    }
    print("【SVM holdout】")
    if search:
        print("  CV scoring:", search["scoring"], "best:", search["best_cv_score"])
        print("  params:", search["best_params"])
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
    return result


if __name__ == "__main__":
    from sklearn.datasets import load_wine
    data = load_wine()
    result = run_svm(data.data, data.target, scoring="balanced_accuracy")
    print("\n关键点：scaler 在 Pipeline 里，因此 GridSearchCV 每折只用该折训练数据估计均值/方差。")
