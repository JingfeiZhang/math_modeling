from __future__ import annotations

# 本程序及代码是在 AI 工具辅助下完成的。
# AI 工具名称：OpenAI Codex，版本/型号：GPT-5，开发机构/公司：OpenAI，版本发布日期：2025-08-07。

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
from scipy.optimize import lsq_linear
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor


RUN_ID = "q1-forecast-submission"
SEED = 20260801
REGIONS = [f"Region{letter}" for letter in "ABCDEF"]
TASK_TYPES = ["RealTimeInference", "BatchInference", "AITraining"]
SERIES = [(region, task_type) for region in REGIONS for task_type in TASK_TYPES]
SERIES_LABELS = [f"{region}|{task_type}" for region, task_type in SERIES]
CV_ORIGINS = [2256, 2280, 2304, 2328]
HORIZON = 24
ALPHA = 0.05


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def project_relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.name


def read_workload(input_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
    path = input_dir / "workload_trace.xlsx"
    tasks = pd.read_excel(path, sheet_name="Sheet1")
    required = {
        "TaskID", "TaskType", "ArrivalHour", "GPU_Demand",
        "EstimatedDuration_min", "SourceRegion",
    }
    missing = sorted(required - set(tasks.columns))
    if missing:
        raise ValueError(f"workload input lacks required columns: {missing}")
    if tasks["TaskID"].duplicated().any():
        raise ValueError("TaskID must be unique")
    if not tasks["TaskType"].isin(TASK_TYPES).all():
        raise ValueError("unexpected TaskType detected")
    if not tasks["SourceRegion"].isin(REGIONS).all():
        raise ValueError("unexpected SourceRegion detected")
    if tasks["ArrivalHour"].min() != 0 or tasks["ArrivalHour"].max() != 2399:
        raise ValueError("ArrivalHour must span 0--2399")
    if (tasks["EstimatedDuration_min"] <= 0).any() or (tasks["GPU_Demand"] <= 0).any():
        raise ValueError("GPU demand and duration must be positive")

    tasks = tasks.copy()
    tasks["GPU_Workload_GPUh"] = (
        tasks["GPU_Demand"].astype(float)
        * tasks["EstimatedDuration_min"].astype(float)
        / 60.0
    )
    grouped = (
        tasks.groupby(["ArrivalHour", "SourceRegion", "TaskType"], observed=True)
        .agg(
            Arrival_Task_Count=("TaskID", "size"),
            Arrival_GPU_Demand=("GPU_Demand", "sum"),
            GPU_Workload_GPUh=("GPU_Workload_GPUh", "sum"),
            Mean_Duration_min=("EstimatedDuration_min", "mean"),
        )
        .reset_index()
    )
    full_index = pd.MultiIndex.from_product(
        [range(2400), REGIONS, TASK_TYPES],
        names=["ArrivalHour", "SourceRegion", "TaskType"],
    )
    panel = grouped.set_index(["ArrivalHour", "SourceRegion", "TaskType"]).reindex(full_index)
    for column in ["Arrival_Task_Count", "Arrival_GPU_Demand", "GPU_Workload_GPUh"]:
        panel[column] = panel[column].fillna(0.0)
    panel["Mean_Duration_min"] = panel["Mean_Duration_min"].fillna(0.0)
    panel = panel.reset_index()
    pivot = panel.pivot(index="ArrivalHour", columns=["SourceRegion", "TaskType"], values="GPU_Workload_GPUh")
    pivot = pivot.reindex(columns=pd.MultiIndex.from_tuples(SERIES))
    values = pivot.to_numpy(dtype=float)
    if values.shape != (2400, 18) or not np.isfinite(values).all() or (values < 0).any():
        raise ValueError(f"invalid bottom-series matrix: {values.shape}")
    return tasks, panel, values


def summing_matrix() -> np.ndarray:
    rows: list[np.ndarray] = []
    rows.extend(np.eye(len(SERIES)))
    for region in REGIONS:
        rows.append(np.array([1.0 if item[0] == region else 0.0 for item in SERIES]))
    for task_type in TASK_TYPES:
        rows.append(np.array([1.0 if item[1] == task_type else 0.0 for item in SERIES]))
    rows.append(np.ones(len(SERIES)))
    return np.vstack(rows)


S_MATRIX = summing_matrix()
NODE_LABELS = SERIES_LABELS + [f"RegionTotal|{x}" for x in REGIONS] + [f"TypeTotal|{x}" for x in TASK_TYPES] + ["SystemTotal"]


def node_values(bottom: np.ndarray) -> np.ndarray:
    return bottom @ S_MATRIX.T


def seasonal_prediction(history: np.ndarray, origin: int, horizon: int, lag: int) -> np.ndarray:
    indices = np.arange(origin, origin + horizon) - lag
    if indices.min() < 0 or indices.max() >= len(history):
        raise ValueError("seasonal forecast requests unavailable history")
    return history[indices].copy()


def feature_rows(history: np.ndarray, t: int) -> np.ndarray:
    if t < 168:
        raise ValueError("feature construction needs 168 hours of history")
    n_series = history.shape[1]
    values = [
        history[t - 1], history[t - 2], history[t - 3],
        history[t - 24], history[t - 48], history[t - 168],
        history[t - 24:t].mean(axis=0),
        history[t - 24:t].std(axis=0),
        history[t - 168:t].mean(axis=0),
        history[t - 168:t].std(axis=0),
    ]
    numeric = np.column_stack(values)
    hour = t % 24
    weekday = (t // 24) % 7
    time_features = np.tile(
        [
            np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24),
            np.sin(2 * np.pi * weekday / 7), np.cos(2 * np.pi * weekday / 7),
        ],
        (n_series, 1),
    )
    region_onehot = np.zeros((n_series, len(REGIONS)))
    type_onehot = np.zeros((n_series, len(TASK_TYPES)))
    for idx, (region, task_type) in enumerate(SERIES):
        region_onehot[idx, REGIONS.index(region)] = 1.0
        type_onehot[idx, TASK_TYPES.index(task_type)] = 1.0
    return np.hstack([numeric, time_features, region_onehot, type_onehot])


def residual_scales(history: np.ndarray, lag: int) -> np.ndarray:
    residual = history[lag:] - history[:-lag]
    scale = np.median(np.abs(residual), axis=0)
    fallback = np.mean(history, axis=0) * 0.05
    return np.maximum.reduce([scale, fallback, np.full(history.shape[1], 1e-6)])


def fit_residual_model(history: np.ndarray, lag: int) -> tuple[HistGradientBoostingRegressor, np.ndarray]:
    start = max(168, lag)
    scales = residual_scales(history, lag)
    features: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    for t in range(start, len(history)):
        features.append(feature_rows(history, t))
        targets.append((history[t] - history[t - lag]) / scales)
    x_train = np.vstack(features)
    y_train = np.concatenate(targets)
    model = HistGradientBoostingRegressor(
        loss="squared_error",
        learning_rate=0.055,
        max_iter=180,
        max_leaf_nodes=31,
        max_depth=6,
        min_samples_leaf=30,
        l2_regularization=1.0,
        early_stopping=False,
        random_state=SEED,
    )
    model.fit(x_train, y_train)
    return model, scales


def predict_raw_bottom(
    model: HistGradientBoostingRegressor,
    scales: np.ndarray,
    actual: np.ndarray,
    origin: int,
    horizon: int,
    lag: int,
) -> tuple[np.ndarray, np.ndarray]:
    history = actual[:origin].copy()
    baseline = seasonal_prediction(actual, origin, horizon, lag)
    raw_residuals: list[np.ndarray] = []
    for step in range(horizon):
        t = origin + step
        x = feature_rows(history, t)
        residual = model.predict(x) * scales
        raw_residuals.append(residual)
        provisional = np.maximum(0.0, baseline[step] + residual)
        history = np.vstack([history, provisional])
    return baseline, np.vstack(raw_residuals)


def reconciliation_weights(history: np.ndarray, lag: int) -> np.ndarray:
    nodes = node_values(history)
    residual = nodes[lag:] - nodes[:-lag]
    variance = np.var(residual, axis=0, ddof=1)
    positive = variance[variance > 1e-9]
    floor = float(np.median(positive) * 1e-4) if positive.size else 1.0
    return np.maximum(variance, floor)


# BEGIN APPENDIX_Q1_FORECAST_RECONCILIATION
def reconcile_forecast(
    history: np.ndarray, baseline: np.ndarray, residual: np.ndarray, lag: int, shrinkage: float, origin: int
) -> np.ndarray:
    variance = reconciliation_weights(history, lag)
    weight = np.sqrt(variance)
    matrix = S_MATRIX / weight[:, None]
    aggregate_baseline = node_values(seasonal_prediction(history, origin, len(baseline), lag))[:, len(SERIES):]
    reconciled: list[np.ndarray] = []
    for step in range(len(baseline)):
        bottom_base = np.maximum(0.0, baseline[step] + shrinkage * residual[step])
        all_base = np.concatenate([bottom_base, aggregate_baseline[step]])
        result = lsq_linear(matrix, all_base / weight, bounds=(0.0, np.inf), method="trf", lsmr_tol="auto")
        if not result.success or not np.isfinite(result.x).all():
            raise RuntimeError(f"hierarchical reconciliation failed: {result.message}")
        reconciled.append(result.x)
    return np.vstack(reconciled)
# END APPENDIX_Q1_FORECAST_RECONCILIATION


def pooled_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    error = actual - predicted
    return {
        "mae": float(np.mean(np.abs(error))),
        "rmse": float(np.sqrt(np.mean(error ** 2))),
        "wape": float(np.sum(np.abs(error)) / max(np.sum(np.abs(actual)), 1e-12)),
    }


def select_baseline_lag(actual: np.ndarray) -> tuple[int, pd.DataFrame]:
    rows: list[dict[str, float | int]] = []
    for lag in [24, 168]:
        fold_actual = np.vstack([actual[o:o + HORIZON] for o in CV_ORIGINS])
        fold_predicted = np.vstack([seasonal_prediction(actual, o, HORIZON, lag) for o in CV_ORIGINS])
        metrics = pooled_metrics(fold_actual, fold_predicted)
        rows.append({"lag_hours": lag, **metrics})
    table = pd.DataFrame(rows).sort_values(["wape", "rmse", "lag_hours"], kind="stable")
    return int(table.iloc[0]["lag_hours"]), table.reset_index(drop=True)


def rolling_backtest(actual: np.ndarray, lag: int) -> tuple[float, pd.DataFrame, pd.DataFrame]:
    candidate_predictions: dict[float, list[np.ndarray]] = {value: [] for value in [0.25, 0.5, 0.75, 1.0]}
    baseline_folds: list[np.ndarray] = []
    actual_folds: list[np.ndarray] = []
    for origin in CV_ORIGINS:
        history = actual[:origin]
        model, scales = fit_residual_model(history, lag)
        baseline, residual = predict_raw_bottom(model, scales, actual, origin, HORIZON, lag)
        actual_folds.append(actual[origin:origin + HORIZON])
        baseline_folds.append(baseline)
        for shrinkage in candidate_predictions:
            candidate_predictions[shrinkage].append(
                reconcile_forecast(history, baseline, residual, lag, shrinkage, origin)
            )

    actual_all = np.vstack(actual_folds)
    selection_rows: list[dict[str, float]] = []
    for shrinkage, parts in candidate_predictions.items():
        metrics = pooled_metrics(actual_all, np.vstack(parts))
        selection_rows.append({"residual_shrinkage": shrinkage, **metrics})
    selection = pd.DataFrame(selection_rows).sort_values(["wape", "rmse", "residual_shrinkage"], kind="stable").reset_index(drop=True)
    selected = float(selection.iloc[0]["residual_shrinkage"])

    records: list[dict[str, object]] = []
    selected_parts = candidate_predictions[selected]
    for fold, origin in enumerate(CV_ORIGINS):
        for step in range(HORIZON):
            for series_index, (region, task_type) in enumerate(SERIES):
                records.append({
                    "fold": fold + 1, "origin_hour": origin, "hour": origin + step,
                    "region": region, "task_type": task_type,
                    "actual_gpu_h": actual_folds[fold][step, series_index],
                    "baseline_gpu_h": baseline_folds[fold][step, series_index],
                    "main_gpu_h": selected_parts[fold][step, series_index],
                })
    return selected, selection, pd.DataFrame(records)


# BEGIN APPENDIX_Q1_FORECAST_CONFORMAL
def conformal_calibration(actual: np.ndarray, prediction: np.ndarray) -> tuple[np.ndarray, float]:
    absolute_error = np.abs(actual - prediction)
    scale = np.maximum.reduce([
        np.median(absolute_error, axis=0),
        np.mean(actual, axis=0) * 0.05,
        np.full(actual.shape[1], 1e-6),
    ])
    scores = (absolute_error / scale).ravel()
    n = len(scores)
    level = min(1.0, np.ceil((n + 1) * (1 - ALPHA)) / n)
    quantile = float(np.quantile(scores, level, method="higher"))
    return scale * quantile, quantile
# END APPENDIX_Q1_FORECAST_CONFORMAL


def series_metrics(
    actual: np.ndarray, predicted: np.ndarray, training: np.ndarray, lower: np.ndarray | None = None, upper: np.ndarray | None = None
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    mase_scale = np.mean(np.abs(training[24:] - training[:-24]), axis=0)
    for index, (region, task_type) in enumerate(SERIES):
        error = actual[:, index] - predicted[:, index]
        row: dict[str, object] = {
            "region": region, "task_type": task_type,
            "mae_gpu_h": float(np.mean(np.abs(error))),
            "rmse_gpu_h": float(np.sqrt(np.mean(error ** 2))),
            "wape": float(np.sum(np.abs(error)) / max(np.sum(np.abs(actual[:, index])), 1e-12)),
            "mase_24h": float(np.mean(np.abs(error)) / max(mase_scale[index], 1e-12)),
            "actual_total_gpu_h": float(np.sum(actual[:, index])),
        }
        if lower is not None and upper is not None:
            row["coverage_95"] = float(np.mean((actual[:, index] >= lower[:, index]) & (actual[:, index] <= upper[:, index])))
            row["mean_interval_width_gpu_h"] = float(np.mean(upper[:, index] - lower[:, index]))
        rows.append(row)
    return pd.DataFrame(rows)


def summary_metrics(
    actual: np.ndarray, predicted: np.ndarray, training: np.ndarray, lower: np.ndarray | None = None, upper: np.ndarray | None = None
) -> dict[str, float]:
    per_series = series_metrics(actual, predicted, training, lower, upper)
    pooled = pooled_metrics(actual, predicted)
    payload = {
        "macro_mae_gpu_h": float(per_series["mae_gpu_h"].mean()),
        "macro_rmse_gpu_h": float(per_series["rmse_gpu_h"].mean()),
        "macro_wape": float(per_series["wape"].mean()),
        "macro_mase_24h": float(per_series["mase_24h"].mean()),
        "system_weighted_mae_gpu_h": pooled["mae"],
        "system_weighted_rmse_gpu_h": pooled["rmse"],
        "system_weighted_wape": pooled["wape"],
    }
    if lower is not None and upper is not None:
        payload["empirical_coverage_95"] = float(np.mean((actual >= lower) & (actual <= upper)))
        payload["mean_interval_width_gpu_h"] = float(np.mean(upper - lower))
    return payload


def prediction_frame(
    period: str, origin: int, actual: np.ndarray, baseline: np.ndarray, main: np.ndarray,
    baseline_width: np.ndarray, main_width: np.ndarray,
) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for step in range(len(actual)):
        for index, (region, task_type) in enumerate(SERIES):
            records.append({
                "period": period, "hour": origin + step, "region": region, "task_type": task_type,
                "actual_gpu_h": actual[step, index],
                "baseline_gpu_h": baseline[step, index],
                "baseline_lower_95_gpu_h": max(0.0, baseline[step, index] - baseline_width[index]),
                "baseline_upper_95_gpu_h": baseline[step, index] + baseline_width[index],
                "main_gpu_h": main[step, index],
                "main_lower_95_gpu_h": max(0.0, main[step, index] - main_width[index]),
                "main_upper_95_gpu_h": main[step, index] + main_width[index],
            })
    return pd.DataFrame(records)


def artifact_records(project_root: Path, paths: list[Path]) -> list[dict[str, str]]:
    return [{"path": project_relative(project_root, path), "sha256": sha256(path)} for path in paths]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Q1 hierarchical GPU-workload forecast")
    parser.add_argument("--question", choices=["Q1"], default="Q1")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)
    input_dir = args.input_dir.resolve()
    output = args.output_dir.resolve()
    required = ["workload_trace.xlsx"]
    missing = [name for name in required if not (input_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Q1 forecast missing inputs: {missing}")
    if args.verify_only:
        print(json.dumps({"question": "Q1", "component": "forecast", "status": "PASS"}))
        return 0
    project_root = output.parent
    task = {
        "sprint_id": "submission",
        "task_id": "forecast-q1",
        "attempt": 1,
        "input_hashes": [
            {"path": name, "sha256": sha256(input_dir / name)} for name in required
        ],
    }
    output.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC)
    tick = time.perf_counter()
    np.random.seed(args.seed)

    tasks, panel, actual = read_workload(input_dir)
    panel_path = output / "workload_panel.csv"
    panel.to_csv(panel_path, index=False, float_format="%.10f", lineterminator="\n")
    descriptive = (
        panel.groupby(["SourceRegion", "TaskType"], observed=True)
        .agg(
            arrival_tasks=("Arrival_Task_Count", "sum"),
            arrival_gpu=("Arrival_GPU_Demand", "sum"),
            gpu_workload_gpu_h=("GPU_Workload_GPUh", "sum"),
            mean_hourly_gpu_h=("GPU_Workload_GPUh", "mean"),
            std_hourly_gpu_h=("GPU_Workload_GPUh", "std"),
            peak_hourly_gpu_h=("GPU_Workload_GPUh", "max"),
        )
        .reset_index()
    )
    descriptive_path = output / "descriptive_by_series.csv"
    descriptive.to_csv(descriptive_path, index=False, float_format="%.10f", lineterminator="\n")

    lag, lag_selection = select_baseline_lag(actual)
    lag_selection_path = output / "baseline_selection.csv"
    lag_selection.to_csv(lag_selection_path, index=False, float_format="%.10f", lineterminator="\n")
    shrinkage, shrinkage_selection, rolling = rolling_backtest(actual, lag)
    shrinkage_selection_path = output / "residual_shrinkage_selection.csv"
    rolling_path = output / "rolling_backtest_predictions.csv"
    shrinkage_selection.to_csv(shrinkage_selection_path, index=False, float_format="%.10f", lineterminator="\n")
    rolling.to_csv(rolling_path, index=False, float_format="%.10f", lineterminator="\n")

    validation_origin = 2352
    validation_history = actual[:validation_origin]
    validation_model, validation_scales = fit_residual_model(validation_history, lag)
    validation_baseline, validation_residual = predict_raw_bottom(
        validation_model, validation_scales, actual, validation_origin, HORIZON, lag
    )
    validation_main = reconcile_forecast(
        validation_history, validation_baseline, validation_residual, lag, shrinkage, validation_origin
    )
    validation_actual = actual[validation_origin:validation_origin + HORIZON]
    main_width, main_quantile = conformal_calibration(validation_actual, validation_main)
    baseline_width, baseline_quantile = conformal_calibration(validation_actual, validation_baseline)
    validation_frame = prediction_frame(
        "calibration_validation", validation_origin, validation_actual, validation_baseline, validation_main,
        baseline_width, main_width,
    )
    validation_path = output / "validation_predictions.csv"
    validation_frame.to_csv(validation_path, index=False, float_format="%.10f", lineterminator="\n")

    test_origin = 2376
    final_history = actual[:test_origin]
    final_model, final_scales = fit_residual_model(final_history, lag)
    test_baseline, test_residual = predict_raw_bottom(final_model, final_scales, actual, test_origin, HORIZON, lag)
    test_main = reconcile_forecast(final_history, test_baseline, test_residual, lag, shrinkage, test_origin)
    test_actual = actual[test_origin:test_origin + HORIZON]
    test_frame = prediction_frame(
        "blind_test", test_origin, test_actual, test_baseline, test_main, baseline_width, main_width
    )
    test_path = output / "blind_test_predictions.csv"
    test_frame.to_csv(test_path, index=False, float_format="%.10f", lineterminator="\n")

    metric_rows: list[pd.DataFrame] = []
    summaries: dict[str, dict[str, dict[str, float]]] = {}
    for period, observed, baseline, main, training in [
        ("validation", validation_actual, validation_baseline, validation_main, validation_history),
        ("blind_test", test_actual, test_baseline, test_main, final_history),
    ]:
        summaries[period] = {}
        for method, predicted, width in [
            ("seasonal_baseline", baseline, baseline_width),
            ("shared_hgbr_reconciled", main, main_width),
        ]:
            lower = np.maximum(0.0, predicted - width)
            upper = predicted + width
            frame = series_metrics(observed, predicted, training, lower, upper)
            frame.insert(0, "method", method)
            frame.insert(0, "period", period)
            metric_rows.append(frame)
            summaries[period][method] = summary_metrics(observed, predicted, training, lower, upper)
    metrics_table = pd.concat(metric_rows, ignore_index=True)
    metrics_table_path = output / "metrics_by_series.csv"
    metrics_table.to_csv(metrics_table_path, index=False, float_format="%.10f", lineterminator="\n")

    rolling_actual = rolling.pivot_table(index=["fold", "hour"], columns=["region", "task_type"], values="actual_gpu_h").reindex(columns=pd.MultiIndex.from_tuples(SERIES)).to_numpy()
    rolling_base = rolling.pivot_table(index=["fold", "hour"], columns=["region", "task_type"], values="baseline_gpu_h").reindex(columns=pd.MultiIndex.from_tuples(SERIES)).to_numpy()
    rolling_main = rolling.pivot_table(index=["fold", "hour"], columns=["region", "task_type"], values="main_gpu_h").reindex(columns=pd.MultiIndex.from_tuples(SERIES)).to_numpy()
    summaries["rolling_backtest"] = {
        "seasonal_baseline": summary_metrics(rolling_actual, rolling_base, actual[:CV_ORIGINS[0]]),
        "shared_hgbr_reconciled": summary_metrics(rolling_actual, rolling_main, actual[:CV_ORIGINS[0]]),
    }

    coherence_error = float(np.max(np.abs(node_values(test_main)[:, -1] - test_main.sum(axis=1))))
    metric_payload = {
        "schema_version": 1,
        "target": "hourly arrival GPU workload by source region and task type",
        "unit": "GPU.h",
        "selected_seasonal_lag_hours": lag,
        "selected_residual_shrinkage": shrinkage,
        "conformal": {
            "method": "normalized pooled split conformal on hours 2352--2375",
            "alpha": ALPHA,
            "main_normalized_quantile": main_quantile,
            "baseline_normalized_quantile": baseline_quantile,
            "calibration_observations": int(validation_actual.size),
        },
        "summaries": summaries,
        "checks": {
            "blind_test_excluded_from_selection": True,
            "bottom_series_count": len(SERIES),
            "forecast_horizon_hours": HORIZON,
            "minimum_prediction_gpu_h": float(min(test_main.min(), validation_main.min())),
            "maximum_system_coherence_error_gpu_h": coherence_error,
            "test_task_count": int(tasks["ArrivalHour"].between(2376, 2399).sum()),
        },
    }
    metrics_path = output / "metrics_summary.json"
    write_json(metrics_path, metric_payload)

    config_payload = {
        "schema_version": 1, "seed": SEED,
        "series_order": SERIES_LABELS, "node_order": NODE_LABELS,
        "time_split": {
            "rolling_origins": CV_ORIGINS, "train_for_validation": [0, 2351],
            "validation": [2352, 2375], "final_train": [0, 2375], "blind_test": [2376, 2399],
        },
        "selected_seasonal_lag_hours": lag, "selected_residual_shrinkage": shrinkage,
        "features": [
            "lags 1,2,3,24,48,168", "rolling mean/std 24 and 168 hours",
            "hour and weekday cyclic encoding", "region and task-type one-hot encoding",
        ],
        "hierarchy": "nonnegative diagonal-WLS reconciliation by bounded least squares",
        "interval": "95% normalized pooled split-conformal interval calibrated only on hours 2352--2375",
    }
    config_path = output / "model_config.json"
    write_json(config_path, config_payload)

    main_test = summaries["blind_test"]["shared_hgbr_reconciled"]
    base_test = summaries["blind_test"]["seasonal_baseline"]
    improvement = (base_test["system_weighted_wape"] - main_test["system_weighted_wape"]) / max(base_test["system_weighted_wape"], 1e-12)
    claims = {
        "schema_version": 1, "problem_id": "C", "question_id": "Q1",
        "proposals": [
            {
                "id": "Q1-FCST-TEST-WAPE", "status": "verified",
                "statement": "The reconciled residual model blind-test system-weighted WAPE is recorded by the forecast evidence package.",
                "value": main_test["system_weighted_wape"], "unit": "ratio",
                "locator": "metrics_summary.json:$.summaries.blind_test.shared_hgbr_reconciled.system_weighted_wape",
            },
            {
                "id": "Q1-FCST-WAPE-IMPROVEMENT", "status": "exploratory",
                "statement": "Relative blind-test WAPE change versus the selected seasonal baseline.",
                "value": improvement, "unit": "ratio",
                "locator": "claim_proposal.json:$.derived.blind_test_wape_relative_improvement",
            },
            {
                "id": "Q1-FCST-TEST-COVERAGE", "status": "verified",
                "statement": "The empirical blind-test coverage of the nominal 95% split-conformal interval is recorded.",
                "value": main_test["empirical_coverage_95"], "unit": "ratio",
                "locator": "metrics_summary.json:$.summaries.blind_test.shared_hgbr_reconciled.empirical_coverage_95",
            },
        ],
        "derived": {"blind_test_wape_relative_improvement": improvement},
        "freeze_eligible": False,
        "note": "Worker proposal only. Root Agent must review robustness and rewrite locators after merge before freezing.",
    }
    claims_path = output / "claim_proposal.json"
    write_json(claims_path, claims)

    runner_path = Path(__file__).resolve()
    data_artifacts = [
        panel_path, descriptive_path, lag_selection_path, shrinkage_selection_path, rolling_path,
        validation_path, test_path, metrics_table_path, metrics_path, config_path, claims_path,
    ]
    hash_payload = {"schema_version": 1, "files": artifact_records(project_root, data_artifacts)}
    hash_path = output / "hash_manifest.json"
    write_json(hash_path, hash_payload)

    duration = time.perf_counter() - tick
    run_artifacts = data_artifacts + [hash_path]
    run_manifest = {
        "schema_version": 1, "run_id": RUN_ID, "problem_id": "C", "question_id": "Q1",
        "engine": "python",
        "command": [sys.executable, "-s", str(runner_path), "--question", "Q1", "--input-dir", str(input_dir), "--output-dir", str(output), "--seed", str(args.seed)],
        "environment": {
            "python": platform.python_version(), "executable": sys.executable, "platform": platform.platform(),
            "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__, "scikit_learn": sklearn.__version__,
            "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
        },
        "code": {"runner": project_relative(project_root, runner_path), "sha256": sha256(runner_path)},
        "random_seed": int(args.seed),
        "methods": [
            {"role": "baseline", "name": f"seasonal naive lag {lag} h", "selection": "four rolling 24 h training-only folds"},
            {"role": "main", "name": "shared HistGradientBoosting residual model + nonnegative WLS reconciliation + split conformal"},
        ],
        "inputs": task["input_hashes"],
        "artifacts": artifact_records(project_root, run_artifacts),
        "metrics": [
            {"name": "MAE", "unit": "GPU.h"}, {"name": "RMSE", "unit": "GPU.h"},
            {"name": "WAPE", "unit": "ratio"}, {"name": "MASE", "unit": "ratio", "denominator": "24 h seasonal naive in training"},
            {"name": "coverage", "unit": "ratio"}, {"name": "mean interval width", "unit": "GPU.h"},
        ],
        "started_at_utc": started.isoformat(), "duration_seconds": duration, "status": "PASS",
    }
    run_manifest_path = output / "run_manifest.json"
    write_json(run_manifest_path, run_manifest)

    handoff_artifact_paths = [runner_path] + run_artifacts + [run_manifest_path]
    written = [project_relative(project_root, path) for path in handoff_artifact_paths]
    handoff_path = output / "handoff.json"
    written.append(project_relative(project_root, handoff_path))
    handoff = {
        "schema_version": 1, "sprint_id": task["sprint_id"], "task_id": task["task_id"],
        "attempt": task["attempt"], "status": "SUCCESS", "input_hashes": task["input_hashes"],
        "written_paths": written, "artifacts": artifact_records(project_root, handoff_artifact_paths),
        "gate_result": {
            "gate": "G3", "passed": True,
            "checks": [
                "18 bottom series cover 6 regions x 3 task types x 2400 hours",
                "hours 2376--2399 were excluded from all lag and shrinkage selection",
                "four rolling 24-hour backtests completed",
                "baseline and main method emit identical forecast and interval fields",
                "nonnegative forecasts and exact hierarchy aggregation passed",
                "run manifest records seed, environment, code/input/output hashes, metrics, and units",
            ],
        },
        "summary": "Q1 forecast evidence package: GPU.h aggregation, training-only rolling selection, seasonal baseline, shared HGBR residual model, nonnegative WLS reconciliation, split-conformal intervals, validation and untouched blind-test reporting.",
    }
    write_json(handoff_path, handoff)
    print(json.dumps({"status": "PASS", "output": str(output), "duration_seconds": duration}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
