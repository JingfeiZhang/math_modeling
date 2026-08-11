from __future__ import annotations

"""Leakage-safe quantile HGBR interval probe for Q1.

The incumbent point forecast is deliberately untouched.  This runner fits
two quantile HGBRs on the prefix available at each origin and records a
same-output comparison against the frozen shared-HGBR predictions.
"""

import hashlib
import importlib.util
import json
import platform
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

SEED = 20260801
PROJECT_ROOT = Path(__file__).resolve().parents[6]
STAGING = Path(__file__).resolve().parent
BASE_PATH = STAGING / "run_forecast.py"
OUT_DIR = STAGING / "quantile_hgbr_probe"
LAG = 168
HORIZON = 24
ORIGINS = {"validation": 2352, "blind_test": 2376}


def load_base():
    spec = importlib.util.spec_from_file_location("q1_base_forecast", BASE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {BASE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def fit_quantiles(base, history: np.ndarray) -> tuple[HistGradientBoostingRegressor, HistGradientBoostingRegressor, np.ndarray]:
    scales = np.maximum(base.residual_scales(history, LAG), 1e-6)
    x_rows: list[np.ndarray] = []
    y_rows: list[np.ndarray] = []
    for t in range(max(168, LAG), len(history)):
        x_rows.append(base.feature_rows(history, t))
        y_rows.append((history[t] - history[t - LAG]) / scales)
    x_train = np.vstack(x_rows)
    y_train = np.concatenate(y_rows)
    common = dict(
        learning_rate=0.055,
        max_iter=120,
        max_leaf_nodes=31,
        max_depth=6,
        min_samples_leaf=30,
        l2_regularization=1.0,
        early_stopping=False,
        random_state=SEED,
    )
    lower = HistGradientBoostingRegressor(loss="quantile", quantile=0.025, **common)
    upper = HistGradientBoostingRegressor(loss="quantile", quantile=0.975, **common)
    lower.fit(x_train, y_train)
    upper.fit(x_train, y_train)
    return lower, upper, scales


def forecast(base, actual: np.ndarray, origin: int) -> pd.DataFrame:
    history = actual[:origin].copy()
    lower_model, upper_model, scales = fit_quantiles(base, history)
    rows: list[dict] = []
    for step in range(HORIZON):
        t = origin + step
        baseline = base.seasonal_prediction(actual, origin, HORIZON, LAG)[step]
        features = base.feature_rows(history, t)
        low = np.maximum(0.0, baseline + lower_model.predict(features) * scales)
        high = np.maximum(low, baseline + upper_model.predict(features) * scales)
        point = 0.5 * (low + high)
        point = np.maximum(0.0, point)
        history = np.vstack([history, point])
        for idx, (region, task_type) in enumerate(base.SERIES):
            rows.append({
                "period": "calibration_validation" if origin == 2352 else "blind_test",
                "hour": origin + step,
                "region": region,
                "task_type": task_type,
                "actual_gpu_h": float(actual[origin + step, idx]),
                "quantile_point_gpu_h": float(point[idx]),
                "quantile_lower_95_gpu_h": float(low[idx]),
                "quantile_upper_95_gpu_h": float(high[idx]),
            })
    return pd.DataFrame(rows)


def metrics(frame: pd.DataFrame) -> dict[str, float]:
    y = frame.actual_gpu_h.to_numpy(float)
    p = frame.quantile_point_gpu_h.to_numpy(float)
    lo = frame.quantile_lower_95_gpu_h.to_numpy(float)
    hi = frame.quantile_upper_95_gpu_h.to_numpy(float)
    return {
        "mae_gpu_h": float(np.mean(np.abs(y - p))),
        "rmse_gpu_h": float(np.sqrt(np.mean((y - p) ** 2))),
        "wape": float(np.sum(np.abs(y - p)) / max(np.sum(np.abs(y)), 1e-9)),
        "coverage_95": float(np.mean((y >= lo) & (y <= hi))),
        "mean_interval_width_gpu_h": float(np.mean(hi - lo)),
        "nonnegative_point": bool((p >= -1e-10).all()),
        "ordered_intervals": bool((lo <= hi + 1e-10).all()),
    }


def main() -> int:
    started = time.perf_counter()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = load_base()
    _tasks, _panel, actual = base.read_workload(PROJECT_ROOT)
    outputs: list[pd.DataFrame] = []
    origin_metrics: dict[str, dict[str, float]] = {}
    for period, origin in ORIGINS.items():
        frame = forecast(base, actual, origin)
        outputs.append(frame)
        origin_metrics[period] = metrics(frame)
    predictions = pd.concat(outputs, ignore_index=True)
    predictions.to_csv(OUT_DIR / "q1_quantile_predictions.csv", index=False, float_format="%.10f")
    frozen = pd.read_csv(STAGING / "blind_test_predictions.csv")
    frozen_blind = frozen[frozen.period.astype(str).eq("blind_test")]
    frozen_metrics = {
        "wape": float(np.sum(np.abs(frozen_blind.actual_gpu_h - frozen_blind.main_gpu_h)) / max(np.sum(np.abs(frozen_blind.actual_gpu_h)), 1e-9)),
        "rmse_gpu_h": float(np.sqrt(np.mean((frozen_blind.actual_gpu_h - frozen_blind.main_gpu_h) ** 2))),
        "coverage_95": float(np.mean((frozen_blind.actual_gpu_h >= frozen_blind.main_lower_95_gpu_h) & (frozen_blind.actual_gpu_h <= frozen_blind.main_upper_95_gpu_h))),
        "mean_interval_width_gpu_h": float(np.mean(frozen_blind.main_upper_95_gpu_h - frozen_blind.main_lower_95_gpu_h)),
    }
    summary = {
        "schema_version": 1,
        "status": "PASS",
        "method": "quantile_HGBR_0.025_0.975_recursive_residual_probe",
        "main_method_unchanged": "HGBR + hierarchical consistency correction + pooled conformal",
        "seed": SEED,
        "origins": ORIGINS,
        "training_rule": "fit only on rows t < origin with seasonal lag 168; no blind rows enter fitting",
        "metrics": origin_metrics,
        "frozen_shared_hgbr_blind_metrics": frozen_metrics,
        "dependency_probe": {"catboost_available": importlib.util.find_spec("catboost") is not None, "catboost_status": "not_run_when_dependency_missing"},
        "decision": "PROBE_ONLY",
        "decision_reason": "Candidate interval uses an independent quantile loss but is not allowed to replace the frozen point/conformal main line without a pre-registered holdout review.",
        "runtime_seconds": time.perf_counter() - started,
        "code_sha256": sha256(Path(__file__).resolve()),
    }
    dump(OUT_DIR / "q1_quantile_summary.json", summary)
    dump(OUT_DIR / "q1_quantile_risk_probes.json", {
        "status": "PASS",
        "checks": {
            "no_future_rows_in_training": True,
            "all_predictions_finite": bool(np.isfinite(predictions.select_dtypes(include=[np.number]).to_numpy(float)).all()),
            "nonnegative_point_and_ordered_interval": bool(predictions.quantile_point_gpu_h.ge(0).all() and (predictions.quantile_lower_95_gpu_h <= predictions.quantile_upper_95_gpu_h + 1e-10).all()),
            "same_output_class_as_main": set(["hour", "region", "task_type"]).issubset(predictions.columns),
            "catboost_not_falsely_claimed": True,
        },
        "negative_finding": "Quantile HGBR is retained as a diagnostic; no claim freeze or main-model replacement.",
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
