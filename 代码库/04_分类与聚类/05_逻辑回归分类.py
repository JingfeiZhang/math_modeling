# -*- coding: utf-8 -*-
"""
05 逻辑回归分类：baseline、阈值与概率质量
=====================================

study-only 模板。逻辑回归适合作为可解释分类 baseline，但高质量分类不能只报告
Accuracy，也不能默认 0.5 阈值适合所有题目。

本模板强调：
- stratified holdout；
- StandardScaler 与模型放入 Pipeline，防止未来扩展 CV 时预处理泄漏；
- 二分类显式 positive_label 与 threshold；
- Accuracy + balanced accuracy + Precision/Recall/F1 + ROC-AUC + PR-AUC；
- 概率进入决策时报告 Brier score，并把 calibration 作为后续验证；
- 系数解释为标准化特征对应的 log-odds association，不自动写成因果效应。
"""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, precision_score,
                             recall_score, f1_score, confusion_matrix, roc_auc_score,
                             average_precision_score, brier_score_loss)


def _binary_metrics(y_true, proba_pos, positive_label, threshold):
    y_true = np.asarray(y_true)
    y_bin = (y_true == positive_label).astype(int)
    pred_bin = (np.asarray(proba_pos) >= threshold).astype(int)
    return {
        "accuracy": float(accuracy_score(y_bin, pred_bin)),
        "balanced_accuracy": float(balanced_accuracy_score(y_bin, pred_bin)),
        "precision": float(precision_score(y_bin, pred_bin, zero_division=0)),
        "recall": float(recall_score(y_bin, pred_bin, zero_division=0)),
        "f1": float(f1_score(y_bin, pred_bin, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_bin, proba_pos)),
        "pr_auc": float(average_precision_score(y_bin, proba_pos)),
        "brier": float(brier_score_loss(y_bin, proba_pos)),
        "confusion_matrix": confusion_matrix(y_bin, pred_bin).tolist(),
        "threshold": float(threshold),
        "positive_label": positive_label.item() if hasattr(positive_label, "item") else positive_label,
        "prevalence": float(y_bin.mean()),
    }


def _multiclass_metrics(y_true, y_pred, proba, classes):
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "roc_auc_ovr_macro": float(roc_auc_score(y_true, proba, labels=classes, multi_class="ovr", average="macro")),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=classes).tolist(),
    }


def run_logistic(X, y, C=1.0, test_size=0.3, seed=42,
                 class_weight=None, positive_label=None, threshold=0.5):
    X = np.asarray(X, dtype=float)
    y = np.asarray(y)
    if X.ndim != 2 or len(X) != len(y) or not np.isfinite(X).all():
        raise ValueError("X/y 形状或数值非法")
    classes = np.unique(y)
    if len(classes) < 2:
        raise ValueError("分类至少需要两个类别")

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y
    )
    model = Pipeline([
        ("scale", StandardScaler()),
        ("logit", LogisticRegression(C=C, max_iter=2000, class_weight=class_weight)),
    ])
    model.fit(X_tr, y_tr)
    proba = model.predict_proba(X_te)
    fitted_classes = model.named_steps["logit"].classes_

    if len(fitted_classes) == 2:
        pos = fitted_classes[1] if positive_label is None else positive_label
        matches = np.where(fitted_classes == pos)[0]
        if len(matches) != 1:
            raise ValueError(f"positive_label={pos!r} 不在训练类别 {fitted_classes.tolist()} 中")
        pos_idx = int(matches[0])
        metrics = _binary_metrics(y_te, proba[:, pos_idx], pos, threshold)
        y_pred = np.where(proba[:, pos_idx] >= threshold, pos,
                          fitted_classes[1 - pos_idx])
    else:
        y_pred = fitted_classes[np.argmax(proba, axis=1)]
        metrics = _multiclass_metrics(y_te, y_pred, proba, fitted_classes)

    scaler = model.named_steps["scale"]
    clf = model.named_steps["logit"]
    result = {
        "model": model,
        "classes": fitted_classes.tolist(),
        "metrics": metrics,
        "test_size": int(len(y_te)),
        "train_size": int(len(y_tr)),
        "coefficients_on_standardized_features": clf.coef_.copy(),
        "feature_scale": scaler.scale_.copy(),
        "claim_boundary": "系数描述给定模型与协变量集合下的 log-odds association；分类性能来自当前 holdout，不自动代表其他时间/群体/场景",
    }

    print("【逻辑回归 holdout】")
    for key, value in metrics.items():
        if isinstance(value, (float, int)):
            print(f"  {key}: {value:.4f}" if isinstance(value, float) else f"  {key}: {value}")
    if len(fitted_classes) == 2:
        print("  阈值必须由误判代价/决策用途决定；0.5 只是默认候选，不是自然真值。")
        print("  若概率用于资源配置/风险决策，应进一步做 calibration curve / calibration-in-the-large。")
    print("  系数在标准化特征尺度上解释，且不是因果系数。")
    return result


def threshold_sweep(result, X_test, y_test, positive_label, thresholds=None):
    """辅助比较阈值；正式选择阈值应基于题面误判代价，不能只最大化 F1。"""
    thresholds = np.linspace(0.1, 0.9, 17) if thresholds is None else np.asarray(thresholds, dtype=float)
    model = result["model"]
    classes = np.asarray(result["classes"])
    idx = np.where(classes == positive_label)[0]
    if len(idx) != 1:
        raise ValueError("positive_label 不唯一或不存在")
    proba = model.predict_proba(X_test)[:, int(idx[0])]
    rows = []
    for threshold in thresholds:
        row = _binary_metrics(y_test, proba, positive_label, float(threshold))
        rows.append(row)
    return rows


if __name__ == "__main__":
    from sklearn.datasets import load_breast_cancer, load_iris

    print("########## 二分类 ##########")
    data = load_breast_cancer()
    binary = run_logistic(data.data, data.target, positive_label=1, threshold=0.5)

    print("\n########## 多分类 ##########")
    iris = load_iris()
    multi = run_logistic(iris.data, iris.target)

    print("\n正式竞赛若有时间/主体/空间结构，应把随机 holdout 换成 time/group/spatial split。")
