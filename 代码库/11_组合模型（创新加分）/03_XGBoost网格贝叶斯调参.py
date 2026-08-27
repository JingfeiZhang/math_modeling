# -*- coding: utf-8 -*-
"""
03 Gradient Boosting + 超参数搜索：测试集只评估一次
================================================

study-only 模板。GridSearchCV 与 RandomizedSearchCV 都是超参数搜索器；后者不是贝叶斯优化。
真正的贝叶斯优化需要独立的 surrogate/acquisition 机制或相应库。

核心实验边界：
1. 先切出最终 holdout/test；
2. 默认模型、网格搜索、随机搜索的选择全部只看 training 内 CV；
3. 根据预先规定的 CV 指标选定一个候选；
4. 只对这个最终候选读取一次 test；
5. 如果看过 test 后又换模型/搜索空间，test 已成为开发集，应另留最终评估集。

若没有 xgboost，本模板会明确改用 sklearn GradientBoostingRegressor；不会仍把结果称为 XGBoost。
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import (train_test_split, GridSearchCV,
                                     RandomizedSearchCV, KFold, cross_val_score)
from sklearn.metrics import mean_squared_error, r2_score

try:
    from xgboost import XGBRegressor
    HAS_XGBOOST = True
except Exception:
    HAS_XGBOOST = False


def make_base_model(engine="auto", seed=42):
    if engine == "auto":
        engine = "xgboost" if HAS_XGBOOST else "sklearn_gbdt"
    if engine == "xgboost":
        if not HAS_XGBOOST:
            raise RuntimeError("请求 xgboost，但当前环境未安装；请安装依赖或显式选择 sklearn_gbdt")
        model = XGBRegressor(objective="reg:squarederror", random_state=seed,
                             n_jobs=1, verbosity=0)
        grid = {
            "n_estimators": [100, 200, 300],
            "max_depth": [3, 4, 5],
            "learning_rate": [0.05, 0.1, 0.2],
            "subsample": [0.8, 1.0],
        }
    elif engine == "sklearn_gbdt":
        model = GradientBoostingRegressor(random_state=seed)
        grid = {
            "n_estimators": [100, 200, 300],
            "max_depth": [2, 3, 4],
            "learning_rate": [0.05, 0.1, 0.2],
            "subsample": [0.8, 1.0],
        }
    else:
        raise ValueError("engine 必须为 auto/xgboost/sklearn_gbdt")
    return model, grid, engine


def regression_metrics(model, X, y):
    pred = model.predict(X)
    return {
        "RMSE": float(np.sqrt(mean_squared_error(y, pred))),
        "R2": float(r2_score(y, pred)),
    }


def tune_on_training(X_train, y_train, engine="auto", seed=42,
                     cv_splits=5, randomized_iter=12):
    """只在训练数据内部比较 default / grid / randomized 三个开发方案。"""
    X_train = np.asarray(X_train, dtype=float)
    y_train = np.asarray(y_train, dtype=float).ravel()
    cv = KFold(n_splits=cv_splits, shuffle=True, random_state=seed)

    default_model, grid, engine_id = make_base_model(engine, seed)
    default_scores = cross_val_score(default_model, X_train, y_train, cv=cv,
                                     scoring="neg_root_mean_squared_error", n_jobs=1)
    candidates = [{
        "name": "default",
        "cv_rmse_mean": float(-default_scores.mean()),
        "cv_rmse_std": float(default_scores.std()),
        "estimator": default_model,
        "params": default_model.get_params(),
    }]

    grid_model, grid_space, _ = make_base_model(engine_id, seed)
    gs = GridSearchCV(grid_model, grid_space, cv=cv,
                      scoring="neg_root_mean_squared_error", n_jobs=1,
                      return_train_score=True)
    gs.fit(X_train, y_train)
    candidates.append({
        "name": "grid_search",
        "cv_rmse_mean": float(-gs.best_score_),
        "cv_rmse_std": float(gs.cv_results_["std_test_score"][gs.best_index_]),
        "estimator": gs.best_estimator_,
        "params": dict(gs.best_params_),
    })

    random_model, random_space, _ = make_base_model(engine_id, seed)
    rs = RandomizedSearchCV(random_model, random_space, n_iter=randomized_iter, cv=cv,
                            scoring="neg_root_mean_squared_error",
                            random_state=seed, n_jobs=1, return_train_score=True)
    rs.fit(X_train, y_train)
    candidates.append({
        "name": "random_search",
        "cv_rmse_mean": float(-rs.best_score_),
        "cv_rmse_std": float(rs.cv_results_["std_test_score"][rs.best_index_]),
        "estimator": rs.best_estimator_,
        "params": dict(rs.best_params_),
    })

    # 仅按 training-CV 选择；test 此时完全未读取。
    selected = min(candidates, key=lambda row: row["cv_rmse_mean"])
    selected["estimator"].fit(X_train, y_train)
    return {
        "engine": engine_id,
        "candidates": candidates,
        "selected_name": selected["name"],
        "selected_cv_rmse": selected["cv_rmse_mean"],
        "selected_estimator": selected["estimator"],
        "selection_rule": "minimum mean training-CV RMSE",
    }


def train_select_test(X, y, test_size=0.25, engine="auto", seed=42):
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).ravel()
    if X.ndim != 2 or len(X) != len(y) or not np.isfinite(X).all() or not np.isfinite(y).all():
        raise ValueError("X/y 非法")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed
    )
    development = tune_on_training(X_train, y_train, engine=engine, seed=seed)
    # 唯一一次 final holdout evaluation。
    test_metrics = regression_metrics(development["selected_estimator"], X_test, y_test)
    return {
        "engine": development["engine"],
        "selected_name": development["selected_name"],
        "selected_cv_rmse": development["selected_cv_rmse"],
        "candidates": [{k: v for k, v in row.items() if k != "estimator"}
                       for row in development["candidates"]],
        "test_metrics": test_metrics,
        "train_size": len(y_train), "test_size": len(y_test),
        "claim_boundary": "最终 test 只用于选定模型的一次评估；搜索范围本身若反复根据 test 修改，需要新的独立评估集或 nested CV",
    }


if __name__ == "__main__":
    rng = np.random.default_rng(42)
    X = rng.uniform(-2, 2, size=(400, 6))
    y = (3 * np.sin(X[:, 0]) + X[:, 1] ** 2 - 2 * X[:, 2] * X[:, 3]
         + 0.5 * X[:, 4] + rng.normal(0, 0.3, size=len(X)))
    result = train_select_test(X, y)
    print("engine:", result["engine"])
    print("training-CV candidates:")
    for row in result["candidates"]:
        print(" ", row["name"], "CV RMSE=", round(row["cv_rmse_mean"], 4))
    print("selected before test:", result["selected_name"])
    print("final test once:", result["test_metrics"])
    print("\nRandomizedSearchCV 是随机超参数搜索，不应在论文里改名为贝叶斯优化。")
