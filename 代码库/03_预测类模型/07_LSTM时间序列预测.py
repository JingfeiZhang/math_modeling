# -*- coding: utf-8 -*-
"""
LSTM 时间序列预测（study-only reference）

Quality contract
    - 先按时间切训练/测试，再只用训练段拟合 scaler；
    - 默认不允许把缺失 TensorFlow 静默替换成 MLP；
    - holdout 结果明确为 one-step / observed-history evaluation；
    - 与 last-value baseline 比较；
    - 正式赛题应在当前项目中使用 rolling/out-of-time 验证。
"""

import os
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import MinMaxScaler

try:
    from tensorflow.keras.callbacks import EarlyStopping
    from tensorflow.keras.layers import Dense, Dropout, LSTM
    from tensorflow.keras.models import Sequential
    _HAS_TF = True
except Exception:
    _HAS_TF = False


def forecast_metrics(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    err = y_true - y_pred
    mask = y_true != 0
    return {
        "RMSE": float(np.sqrt(np.mean(err ** 2))),
        "MAE": float(np.mean(np.abs(err))),
        "MAPE(%)": float(np.mean(np.abs(err[mask] / y_true[mask])) * 100)
        if mask.any() else np.nan,
    }


def create_dataset(series_scaled, look_back=10):
    X, y = [], []
    for i in range(look_back, len(series_scaled)):
        X.append(series_scaled[i - look_back:i, 0])
        y.append(series_scaled[i, 0])
    return np.asarray(X), np.asarray(y)


def _build_lstm(look_back, units):
    model = Sequential([
        LSTM(units, activation="tanh", input_shape=(look_back, 1)),
        Dropout(0.1),
        Dense(1),
    ])
    model.compile(optimizer="adam", loss="mse")
    return model


def lstm_forecast(
    series,
    look_back=12,
    test_size=20,
    n_forecast=12,
    units=50,
    epochs=100,
    batch_size=16,
    fallback=None,
    random_state=0,
):
    """
    LSTM holdout 评估。

    fallback:
        None  -> TensorFlow 不可用时明确失败（默认，推荐）
        "mlp" -> 显式使用 MLPRegressor；返回 method 会标记为 MLP，不冒充 LSTM。
    """
    raw = np.asarray(series, dtype=float).reshape(-1, 1)
    n = len(raw)
    if look_back < 1:
        raise ValueError("look_back 必须 >= 1")
    if test_size <= 0 or test_size >= n - look_back:
        raise ValueError("test_size 不合法：训练段必须保留至少 look_back+1 个点")
    if n_forecast <= 0:
        raise ValueError("n_forecast 必须 > 0")

    train_end = n - test_size

    # 关键：scaler 只拟合训练段，避免测试窗口泄漏。
    scaler = MinMaxScaler()
    scaler.fit(raw[:train_end])
    scaled = scaler.transform(raw)

    X, y = create_dataset(scaled, look_back)
    split = train_end - look_back
    X_tr, X_te = X[:split], X[split:]
    y_tr, y_te = y[:split], y[split:]

    if _HAS_TF:
        method = "LSTM"
        model = _build_lstm(look_back, units)
        X_tr3 = X_tr.reshape(-1, look_back, 1)
        X_te3 = X_te.reshape(-1, look_back, 1)

        # validation_split 只来自训练样本；shuffle=False 保留时序顺序。
        callbacks = [
            EarlyStopping(
                monitor="val_loss",
                patience=15,
                restore_best_weights=True,
            )
        ]
        model.fit(
            X_tr3,
            y_tr,
            epochs=epochs,
            batch_size=batch_size,
            verbose=0,
            callbacks=callbacks,
            validation_split=0.2,
            shuffle=False,
        )
        pred_te_s = model.predict(X_te3, verbose=0).ravel()

        def predict_window(window):
            return float(
                model.predict(window.reshape(1, look_back, 1), verbose=0).ravel()[0]
            )
    else:
        if fallback != "mlp":
            raise RuntimeError(
                "TensorFlow/Keras 不可用，LSTM 未执行。"
                "如仅需显式比较 MLP，可传 fallback='mlp'；"
                "该结果会以 MLP 身份返回。"
            )
        method = "MLP"
        model = MLPRegressor(
            hidden_layer_sizes=(units, max(1, units // 2)),
            activation="tanh",
            max_iter=1500,
            early_stopping=True,
            random_state=random_state,
        )
        model.fit(X_tr, y_tr)
        pred_te_s = model.predict(X_te)

        def predict_window(window):
            return float(model.predict(window.reshape(1, -1)).ravel()[0])

    pred_te = scaler.inverse_transform(pred_te_s.reshape(-1, 1)).ravel()
    true_te = scaler.inverse_transform(y_te.reshape(-1, 1)).ravel()
    metrics = forecast_metrics(true_te, pred_te)

    # 同输出简单 baseline：每个测试时点用上一真实观测预测下一点。
    baseline_pred = raw[train_end - 1:n - 1, 0]
    baseline_metrics = forecast_metrics(raw[train_end:, 0], baseline_pred)

    # 未来递归演示。模型仍是 holdout 训练模型，不冒充“全量重训最终模型”。
    window = scaled[-look_back:, 0].copy()
    future_s = []
    for _ in range(n_forecast):
        nxt = predict_window(window)
        future_s.append(nxt)
        window = np.append(window[1:], nxt)
    future = scaler.inverse_transform(np.asarray(future_s).reshape(-1, 1)).ravel()

    print("=" * 64)
    print(f"requested=LSTM, executed={method}")
    print("  holdout :", {k: round(v, 4) for k, v in metrics.items()})
    print("  LastVal :", {k: round(v, 4) for k, v in baseline_metrics.items()})

    return {
        "requested_method": "LSTM",
        "method": method,
        "status": "ok" if method == "LSTM" else "fallback",
        "selection_scope": "train_only",
        "evaluation_mode": "one_step_with_observed_history",
        "metrics": metrics,
        "baseline_method": "last_value",
        "baseline_metrics": baseline_metrics,
        "true_test": true_te,
        "pred_test": pred_te,
        "forecast": future,
        "series": raw.ravel(),
        "test_size": test_size,
        "scaler_fit_end": train_end,
        "seed": random_state,
    }


if __name__ == "__main__":
    # 【Study-only example】不作为比赛证据。
    rng = np.random.default_rng(3)
    n = 300
    t = np.arange(n)
    series = (
        60
        + 0.15 * t
        + 12 * np.sin(2 * np.pi * t / 30)
        + 5 * np.sin(2 * np.pi * t / 7)
        + rng.normal(0, 1.5, n)
    )

    if _HAS_TF:
        res = lstm_forecast(
            series,
            look_back=20,
            test_size=30,
            n_forecast=15,
            units=50,
            epochs=80,
        )
        print("future =", np.round(res["forecast"], 3))
    else:
        print(
            "TensorFlow 不可用：本示例不会把 MLP 冒充 LSTM。"
            "如需研究 MLP fallback，请显式调用 fallback='mlp'。"
        )

    print(
        "正式赛题应在当前项目中重新设计 rolling/out-of-time 验证、"
        "baseline、预测窗口和最终全量重训策略。"
    )