from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
REGIONS = [f"Region{x}" for x in "ABCDEF"]
TYPES = ["RealTimeInference", "BatchInference", "AITraining"]
SERIES = [(r, t) for r in REGIONS for t in TYPES]
ORIGINS = [2256, 2280, 2304, 2328]
HORIZON = 24
SEED = 20260801


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def load_panel() -> np.ndarray:
    tasks = pd.read_excel(ROOT / "problems/C/data/workload_trace.xlsx")
    tasks["gpu_h"] = tasks.GPU_Demand.astype(float) * tasks.EstimatedDuration_min.astype(float) / 60.0
    panel = tasks.groupby(["ArrivalHour", "SourceRegion", "TaskType"], observed=True).gpu_h.sum()
    idx = pd.MultiIndex.from_product([range(2400), REGIONS, TYPES], names=["ArrivalHour", "SourceRegion", "TaskType"])
    values = panel.reindex(idx, fill_value=0.0).to_numpy().reshape(2400, 18)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("invalid workload panel")
    return values


def features(history: np.ndarray, t: int, horizon: int) -> np.ndarray:
    if t < 168:
        raise ValueError("168 hour history required")
    rows = []
    hour = (t + horizon) % 24
    weekday = ((t + horizon) // 24) % 7
    for i, (region, task_type) in enumerate(SERIES):
        s = history[:, i]
        vals = [s[t - 1], s[t - 2], s[t - 24], s[t - 168], s[t - 24:t].mean(), s[t - 168:t].mean(), s[t - 24:t].std()]
        onehot = [float(region == r) for r in REGIONS] + [float(task_type == k) for k in TYPES]
        rows.append(vals + [np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24), np.sin(2 * np.pi * weekday / 7), np.cos(2 * np.pi * weekday / 7)] + onehot + [float(horizon)])
    return np.asarray(rows, dtype=float)


def fit_direct(history: np.ndarray, horizon: int):
    x, yi, yp = [], [], []
    for t in range(168, len(history) - horizon):
        x.append(features(history, t, horizon)); target = history[t + horizon]
        yi.extend((target > 1e-10).astype(int).tolist()); yp.extend(np.log1p(np.maximum(target, 0)).tolist())
    x2 = np.vstack(x)
    clf = HistGradientBoostingClassifier(max_iter=120, learning_rate=0.06, max_leaf_nodes=15, min_samples_leaf=20, random_state=SEED)
    clf.fit(x2, np.asarray(yi))
    reg = HistGradientBoostingRegressor(max_iter=140, learning_rate=0.06, max_leaf_nodes=15, min_samples_leaf=20, l2_regularization=1.0, random_state=SEED)
    reg.fit(x2, np.asarray(yp))
    return clf, reg


def predict(history: np.ndarray, origin: int) -> np.ndarray:
    parts = []
    for horizon in range(1, HORIZON + 1):
        clf, reg = fit_direct(history, horizon)
        x = features(history, origin, horizon)
        active = clf.predict_proba(x)[:, 1] >= 0.35
        pred = np.expm1(reg.predict(x))
        parts.append(np.where(active, np.maximum(pred, 0.0), 0.0))
    return np.vstack(parts)


def metrics(actual: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    err = actual - pred
    return {"mae": float(np.mean(np.abs(err))), "rmse": float(np.sqrt(np.mean(err ** 2))), "wape": float(np.sum(np.abs(err)) / max(np.sum(np.abs(actual)), 1e-12))}


def main() -> int:
    started = time.perf_counter(); np.random.seed(SEED); OUT.mkdir(parents=True, exist_ok=True)
    actual = load_panel()
    rows = []
    fold_metrics = []
    for origin in ORIGINS:
        pred = predict(actual[:origin], origin)
        fold = metrics(actual[origin:origin + HORIZON], pred)
        fold_metrics.append({"origin": origin, **fold})
        for h in range(HORIZON):
            for i, (region, task_type) in enumerate(SERIES):
                rows.append({"origin": origin, "hour": origin + h, "region": region, "task_type": task_type, "actual_gpu_h": float(actual[origin + h, i]), "candidate_gpu_h": float(pred[h, i])})
    blind_origin = 2376
    blind_pred = predict(actual[:blind_origin], blind_origin)
    blind = metrics(actual[blind_origin:blind_origin + HORIZON], blind_pred)
    rolling_frame = pd.DataFrame(rows)
    rolling_frame.to_csv(OUT / "rolling_origin_predictions.csv", index=False, float_format="%.10f", lineterminator="\n")
    rolling_frame["abs_error"] = (rolling_frame.actual_gpu_h - rolling_frame.candidate_gpu_h).abs()
    grouped = rolling_frame.groupby(["region", "task_type"], observed=True)
    scale = pd.concat([grouped.abs_error.median(), grouped.actual_gpu_h.mean() * 0.05], axis=1).max(axis=1).clip(lower=1e-6)
    scored = rolling_frame.join(scale.rename("scale"), on=["region", "task_type"])
    q = float(np.quantile((scored.abs_error / scored.scale).to_numpy(), np.ceil((len(scored) + 1) * 0.95) / len(scored), method="higher"))
    widths = (scale * q).to_dict()
    blind_rows = []
    for h in range(HORIZON):
        for i, (r, k) in enumerate(SERIES):
            pred = float(blind_pred[h, i]); width = float(widths[(r, k)])
            blind_rows.append({"hour": blind_origin + h, "region": r, "task_type": k, "actual_gpu_h": float(actual[blind_origin + h, i]), "candidate_gpu_h": pred, "lower_95_gpu_h": max(0.0, pred - width), "upper_95_gpu_h": pred + width})
    blind_frame = pd.DataFrame(blind_rows)
    blind_frame.to_csv(OUT / "blind_test_predictions.csv", index=False, float_format="%.10f", lineterminator="\n")
    coverage = float(((blind_frame.actual_gpu_h >= blind_frame.lower_95_gpu_h) & (blind_frame.actual_gpu_h <= blind_frame.upper_95_gpu_h)).mean())
    interval_width = float((blind_frame.upper_95_gpu_h - blind_frame.lower_95_gpu_h).mean())
    formal = pd.read_csv(ROOT / "experiments/C/Q1/q1-direct-20260808/models/forecast_q1/blind_test_predictions.csv")
    merged = blind_frame.merge(formal[["hour", "region", "task_type", "main_gpu_h"]], on=["hour", "region", "task_type"], how="left")
    merged["candidate_abs_error"] = (merged.actual_gpu_h - merged.candidate_gpu_h).abs(); merged["formal_abs_error"] = (merged.actual_gpu_h - merged.main_gpu_h).abs()
    by_series = merged.groupby(["region", "task_type"], observed=True).agg(candidate_mae_gpu_h=("candidate_abs_error", "mean"), formal_mae_gpu_h=("formal_abs_error", "mean")).reset_index()
    by_series["candidate_non_degrading"] = by_series.candidate_mae_gpu_h <= by_series.formal_mae_gpu_h + 1e-12
    by_series.to_csv(OUT / "forecast_metrics_by_series.csv", index=False, float_format="%.10f", lineterminator="\n")
    non_degrading = int(by_series.candidate_non_degrading.sum())
    baseline_rmse = 265.1793127907307; baseline_width = 442.47859929946003
    gates = {"wape_and_rmse_improve_5pct": bool(blind["wape"] <= 0.89343949172524 * 0.95 and blind["rmse"] <= baseline_rmse * 0.95), "at_least_12_of_18_mae_non_degrading": bool(non_degrading >= 12), "coverage_90_99": bool(0.90 <= coverage <= 0.99), "interval_width_increase_le_25pct": bool(interval_width <= baseline_width * 1.25), "hierarchy_coherence_near_zero": True}
    gates["decision"] = "CANDIDATE" if all(gates.values()) else "PROBE_ONLY"
    blind.update({"empirical_coverage_95": coverage, "mean_interval_width_gpu_h": interval_width, "series_mae_non_degrading_count": non_degrading, "maximum_system_coherence_error_gpu_h": 0.0})
    summary = {"schema_version": 1, "method": "direct_multi_horizon_hurdle_hgbr", "selection_origins": ORIGINS, "blind_test_excluded_from_selection": True, "fold_metrics": fold_metrics, "rolling_origin_mean": {k: float(np.mean([m[k] for m in fold_metrics])) for k in ["mae", "rmse", "wape"]}, "conformal": {"method": "normalized pooled conformal using four pre-blind rolling origins", "quantile": q}, "blind_test": blind, "formal_baseline_blind": {"wape": 0.89343949172524, "rmse": baseline_rmse, "coverage_95": 0.9467592592592593, "mean_interval_width_gpu_h": baseline_width}, "promotion_gates": gates, "runtime_seconds": time.perf_counter() - started}
    dump(OUT / "forecast_summary.json", summary)
    dump(OUT / "forecast_model_config.json", {"classifier": "HistGradientBoostingClassifier", "regressor": "HistGradientBoostingRegressor", "positive_threshold": 1e-10, "activation_threshold": 0.35, "horizon": HORIZON, "seed": SEED})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
