# -*- coding: utf-8 -*-
"""
Random Forest / XGBoost 回归（study-only reference）

用于多特征监督回归。模型选择应依据数据结构和样本外证据。
若数据具有时间/主体结构，不能默认随机切分。

注意：feature importance 表示模型内部的预测贡献线索，不是因果效应。
XGBoost 缺失时默认明确失败；如显式传 fallback="gbdt"，结果会以 GBDT 身份返回。
"""

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.model_selection import KFold, TimeSeriesSplit, cross_val_score, train_test_split

try:
    from xgboost import XGBRegressor
    _HAS_XGB = True
except Exception:
    _HAS_XGB = False


def regression_metrics(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    err = y_true - y_pred
    mask = y_true != 0
    ss_res = float(np.sum(err ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    return {
        "RMSE": float(np.sqrt(np.mean(err ** 2))),
        "MAE": float(np.mean(np.abs(err))),
        "MAPE(%)": float(np.mean(np.abs(err[mask] / y_true[mask])) * 100)
        if mask.any() else np.nan,
        "R2": 1 - ss_res / ss_tot if ss_tot > 0 else np.nan,
    }


def _split(X, y, test_size, ordered):
    if ordered:
        n_test = int(np.ceil(len(y) * test_size)) if 0 < test_size < 1 else int(test_size)
        if n_test <= 0 or n_test >= len(y):
            raise ValueError("ordered split 的 test_size 不合法")
        cut = len(y) - n_test
        return X[:cut], X[cut:], y[:cut], y[cut:]
    return train_test_split(X, y, test_size=test_size, random_state=0)


def _evaluate(name, model, X_tr, X_te, y_tr, y_te, ordered=False):
    """holdout 为主证据；CV 只在训练数据内部完成，不读取 holdout。"""
    model.fit(X_tr, y_tr)
    pred = model.predict(X_te)
    metrics = regression_metrics(y_te, pred)

    if ordered:
        splitter = TimeSeriesSplit(n_splits=5)
    else:
        splitter = KFold(5, shuffle=True, random_state=0)

    cv_scores = cross_val_score(model, X_tr, y_tr, cv=splitter, scoring="r2")
    metrics["CV_R2_mean_train_only"] = float(np.mean(cv_scores))
    metrics["CV_R2_std_train_only"] = float(np.std(cv_scores))
    metrics["method"] = name
    metrics["split_mode"] = "ordered" if ordered else "iid_random"

    print("=" * 64)
    print(name)
    print("  holdout:", {k: round(v, 4) for k, v in metrics.items()
                         if isinstance(v, (float, np.floating))})
    return model, metrics


def _predictive_importance(importances, feature_names, n_features):
    """输出 predictive importance 排序；禁止解释为因果效应。"""
    if feature_names is None:
        feature_names = [f"特征{i + 1}" for i in range(n_features)]
    order = np.argsort(importances)[::-1]
    print("  模型内 predictive importance（非因果）：")
    for rank, idx in enumerate(order, 1):
        print(f"    {rank}. {feature_names[idx]:<12} {importances[idx]:.4f}")
    return [(feature_names[i], float(importances[i])) for i in order]


def random_forest_regression(
    X,
    y,
    feature_names=None,
    test_size=0.25,
    n_estimators=200,
    max_depth=None,
    ordered=False,
):
    """随机森林回归。ordered=True 时使用尾部 holdout + TimeSeriesSplit。"""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).ravel()
    X_tr, X_te, y_tr, y_te = _split(X, y, test_size, ordered)
    model = RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=0,
        n_jobs=-1,
    )
    model, metrics = _evaluate(
        "RandomForestRegressor", model, X_tr, X_te, y_tr, y_te, ordered=ordered
    )
    metrics["predictive_importance"] = _predictive_importance(
        model.feature_importances_, feature_names, X.shape[1]
    )
    return model, metrics


def xgboost_regression(
    X,
    y,
    feature_names=None,
    test_size=0.25,
    n_estimators=300,
    max_depth=5,
    learning_rate=0.1,
    ordered=False,
    fallback=None,
):
    """
    XGBoost 回归。

    fallback:
        None   -> xgboost 不可用时明确失败；
        "gbdt" -> 显式运行 GradientBoostingRegressor，并以 GBDT 身份返回。
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).ravel()
    X_tr, X_te, y_tr, y_te = _split(X, y, test_size, ordered)

    if _HAS_XGB:
        name = "XGBoost"
        model = XGBRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=0,
            n_jobs=-1,
        )
    else:
        if fallback != "gbdt":
            raise RuntimeError(
                "xgboost 不可用，XGBoost 未执行。"
                "如需显式比较 GBDT，可传 fallback='gbdt'。"
            )
        name = "GradientBoostingRegressor"
        model = GradientBoostingRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=0,
        )

    model, metrics = _evaluate(
        name, model, X_tr, X_te, y_tr, y_te, ordered=ordered
    )
    metrics["requested_method"] = "XGBoost"
    metrics["status"] = "ok" if name == "XGBoost" else "fallback"
    metrics["predictive_importance"] = _predictive_importance(
        model.feature_importances_, feature_names, X.shape[1]
    )
    return model, metrics


def make_lag_features(series, n_lags=3):
    """把有序单变量序列转成监督学习 lag features；切分仍需保持时间方向。"""
    s = np.asarray(series, dtype=float).ravel()
    if n_lags < 1 or n_lags >= len(s):
        raise ValueError("n_lags 不合法")
    X, y = [], []
    for i in range(n_lags, len(s)):
        X.append(s[i - n_lags:i])
        y.append(s[i])
    return np.asarray(X), np.asarray(y)


if __name__ == "__main__":
    # 【Study-only example】不作为比赛证据。
    rng = np.random.default_rng(42)
    n = 400
    x1 = rng.uniform(0, 10, n)
    x2 = rng.uniform(0, 5, n)
    x3 = rng.uniform(0, 1, n)
    x4 = rng.normal(0, 1, n)
    y = 3 * x1 + 2 * np.sin(x2) + 8 * x3 ** 2 + rng.normal(0, 1.0, n)
    X = np.column_stack([x1, x2, x3, x4])
    names = ["x1", "x2", "x3", "noise"]

    _, rf = random_forest_regression(X, y, feature_names=names)
    print("RF R2 =", round(rf["R2"], 4))

    if _HAS_XGB:
        _, xgb = xgboost_regression(X, y, feature_names=names)
        print("XGB R2 =", round(xgb["R2"], 4))
    else:
        print("xgboost 未安装：不静默改用 GBDT。")

    print(
        "正式赛题应先建立同输出 baseline，并按 iid/time/group/spatial "
        "结构选择切分；predictive importance 不写成因果。"
    )