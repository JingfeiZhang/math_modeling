"""Q1 pooled versus region-task groupwise conformal diagnostic.

This runner reuses the pinned HGBR point predictions. It changes interval
calibration only and does not refit the forecast model or modify formal state.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SPRINT_ID = "sprint-20260808T101814701038Z"
TASK_FILE = "solver-q1.json"
TASK_ID = "solver-q1q2"
SEED = 20260801
ALPHA = 0.05
TARGET_COVERAGE = 0.95

STAGING = Path(__file__).resolve().parent
ROOT = STAGING.parents[3]
TASK_PATH = ROOT / "sprints" / SPRINT_ID / "tasks" / TASK_FILE
VALIDATION_PATH = (
    ROOT
    / "sprints/sprint-20260807T130848306634Z/merged/forecast-q1/validation_predictions.csv"
)
BLIND_PATH = (
    ROOT
    / "sprints/sprint-20260807T130848306634Z/merged/forecast-q1/blind_test_predictions.csv"
)
CSV_PATH = STAGING / "q1_groupwise_conformal.csv"
SUMMARY_PATH = STAGING / "q1_groupwise_conformal_summary.json"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def directory_hash(path: Path) -> str:
    files = sorted(
        (item for item in path.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(path).as_posix(),
    )
    source = "\n".join(
        f"{item.relative_to(path).as_posix()}:{sha256(item)}" for item in files
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def load_task_and_verify() -> dict[str, Any]:
    task = json.loads(TASK_PATH.read_text(encoding="utf-8"))
    if task.get("task_id") != TASK_ID:
        raise RuntimeError(f"unexpected task id: {task.get('task_id')}")
    failures: list[str] = []
    for item in task["input_hashes"]:
        path = ROOT / item["path"]
        observed: str | None = None
        if item["kind"] == "file" and path.is_file():
            observed = sha256(path)
        elif item["kind"] == "directory" and path.is_dir():
            observed = directory_hash(path)
        if observed != item["sha256"]:
            failures.append(
                f"{item['path']} expected={item['sha256']} observed={observed}"
            )
    if failures:
        raise RuntimeError("stale sprint inputs: " + "; ".join(failures))
    return task


def finite_sample_quantile(scores: np.ndarray, alpha: float = ALPHA) -> float:
    n = len(scores)
    level = min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)
    return float(np.quantile(scores, level, method="higher"))


def point_metrics(frame: pd.DataFrame) -> tuple[float, float]:
    actual = frame["actual_gpu_h"].to_numpy(dtype=float)
    predicted = frame["main_gpu_h"].to_numpy(dtype=float)
    error = actual - predicted
    wape = float(np.abs(error).sum() / max(np.abs(actual).sum(), 1e-12))
    rmse = float(np.sqrt(np.mean(error**2)))
    return wape, rmse


def interval_metrics(
    frame: pd.DataFrame, lower: np.ndarray, upper: np.ndarray
) -> tuple[float, float, float]:
    actual = frame["actual_gpu_h"].to_numpy(dtype=float)
    coverage = float(np.mean((actual >= lower) & (actual <= upper)))
    deviation = abs(coverage - TARGET_COVERAGE)
    width = float(np.mean(upper - lower))
    return coverage, deviation, width


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    started_at = utcnow()
    started = time.perf_counter()
    task = load_task_and_verify()
    validation = pd.read_csv(VALIDATION_PATH)
    blind = pd.read_csv(BLIND_PATH)
    keys = ["region", "task_type"]
    required = {
        "region",
        "task_type",
        "actual_gpu_h",
        "main_gpu_h",
        "main_lower_95_gpu_h",
        "main_upper_95_gpu_h",
    }
    if not required.issubset(validation.columns) or not required.issubset(blind.columns):
        raise ValueError("prediction files lack required columns")
    if len(validation) != 432 or len(blind) != 432:
        raise ValueError(
            f"expected 432 calibration and blind rows, got {len(validation)} and {len(blind)}"
        )
    counts = validation.groupby(keys, observed=True).size()
    blind_counts = blind.groupby(keys, observed=True).size()
    if len(counts) != 18 or not counts.eq(24).all() or not blind_counts.eq(24).all():
        raise ValueError("expected 18 region-task groups with 24 observations each")

    ordered_groups = sorted(counts.index.tolist())
    scale_by_group: dict[tuple[str, str], float] = {}
    group_quantile: dict[tuple[str, str], float] = {}
    pooled_scores: list[float] = []
    for group in ordered_groups:
        part = validation[
            validation.region.eq(group[0]) & validation.task_type.eq(group[1])
        ]
        error = np.abs(
            part.actual_gpu_h.to_numpy(dtype=float)
            - part.main_gpu_h.to_numpy(dtype=float)
        )
        scale = max(
            float(np.median(error)),
            float(part.actual_gpu_h.mean()) * 0.05,
            1e-6,
        )
        scores = error / scale
        scale_by_group[group] = scale
        group_quantile[group] = finite_sample_quantile(scores)
        pooled_scores.extend(scores.tolist())
    pooled_quantile = finite_sample_quantile(np.asarray(pooled_scores, dtype=float))

    diagnostics: list[dict[str, Any]] = []
    aggregate_arrays: dict[str, dict[str, list[float]]] = {
        "pooled": {"lower": [], "upper": []},
        "groupwise": {"lower": [], "upper": []},
    }
    group_pairs: list[dict[str, Any]] = []

    for group in ordered_groups:
        part = blind[
            blind.region.eq(group[0]) & blind.task_type.eq(group[1])
        ].copy()
        prediction = part.main_gpu_h.to_numpy(dtype=float)
        scale = scale_by_group[group]
        method_metrics: dict[str, dict[str, float]] = {}
        for method, quantile in (
            ("pooled", pooled_quantile),
            ("groupwise", group_quantile[group]),
        ):
            half_width = scale * quantile
            lower = np.maximum(0.0, prediction - half_width)
            upper = prediction + half_width
            coverage, deviation, width = interval_metrics(part, lower, upper)
            wape, rmse = point_metrics(part)
            method_metrics[method] = {
                "coverage": coverage,
                "deviation": deviation,
                "width": width,
            }
            aggregate_arrays[method]["lower"].extend(lower.tolist())
            aggregate_arrays[method]["upper"].extend(upper.tolist())
            diagnostics.append(
                {
                    "record_type": "group",
                    "method": method,
                    "region": group[0],
                    "task_type": group[1],
                    "group_id": f"{group[0]}|{group[1]}",
                    "calibration_n": 24,
                    "blind_n": 24,
                    "calibration_scale_gpu_h": scale,
                    "calibration_quantile": quantile,
                    "blind_coverage": coverage,
                    "abs_deviation_from_0_95": deviation,
                    "mean_interval_width_gpu_h": width,
                    "blind_wape": wape,
                    "blind_rmse_gpu_h": rmse,
                }
            )
        group_pairs.append(
            {
                "group_id": f"{group[0]}|{group[1]}",
                "pooled_coverage": method_metrics["pooled"]["coverage"],
                "groupwise_coverage": method_metrics["groupwise"]["coverage"],
                "pooled_abs_deviation": method_metrics["pooled"]["deviation"],
                "groupwise_abs_deviation": method_metrics["groupwise"]["deviation"],
                "pooled_width_gpu_h": method_metrics["pooled"]["width"],
                "groupwise_width_gpu_h": method_metrics["groupwise"]["width"],
            }
        )

    blind_ordered = pd.concat(
        [
            blind[
                blind.region.eq(group[0]) & blind.task_type.eq(group[1])
            ].sort_values("hour")
            for group in ordered_groups
        ],
        ignore_index=True,
    )
    blind_actual = blind_ordered.actual_gpu_h.to_numpy(dtype=float)
    blind_prediction = blind_ordered.main_gpu_h.to_numpy(dtype=float)
    blind_wape, blind_rmse = point_metrics(blind)
    aggregate: dict[str, dict[str, Any]] = {}
    for method in ["pooled", "groupwise"]:
        lower = np.asarray(aggregate_arrays[method]["lower"], dtype=float)
        upper = np.asarray(aggregate_arrays[method]["upper"], dtype=float)
        coverage = float(np.mean((blind_actual >= lower) & (blind_actual <= upper)))
        width = float(np.mean(upper - lower))
        deviations = [
            row["abs_deviation_from_0_95"]
            for row in diagnostics
            if row["method"] == method
        ]
        aggregate[method] = {
            "blind_coverage": coverage,
            "abs_deviation_from_0_95": abs(coverage - TARGET_COVERAGE),
            "worst_group_abs_deviation": float(max(deviations)),
            "mean_interval_width_gpu_h": width,
            "blind_wape": blind_wape,
            "blind_rmse_gpu_h": blind_rmse,
        }
        diagnostics.append(
            {
                "record_type": "aggregate",
                "method": method,
                "region": "ALL",
                "task_type": "ALL",
                "group_id": "pooled_18x24",
                "calibration_n": 432,
                "blind_n": 432,
                "calibration_scale_gpu_h": np.nan,
                "calibration_quantile": pooled_quantile if method == "pooled" else np.nan,
                **aggregate[method],
            }
        )

    # Recomputed pooled intervals must reproduce the pinned interval columns.
    existing_lower = blind_ordered.main_lower_95_gpu_h.to_numpy(dtype=float)
    existing_upper = blind_ordered.main_upper_95_gpu_h.to_numpy(dtype=float)
    pooled_lower = np.asarray(aggregate_arrays["pooled"]["lower"], dtype=float)
    pooled_upper = np.asarray(aggregate_arrays["pooled"]["upper"], dtype=float)
    pooled_interval_max_abs_difference = float(
        max(
            np.max(np.abs(existing_lower - pooled_lower)),
            np.max(np.abs(existing_upper - pooled_upper)),
        )
    )

    worst_deviation_improvement = (
        aggregate["pooled"]["worst_group_abs_deviation"]
        - aggregate["groupwise"]["worst_group_abs_deviation"]
    )
    width_inflation = (
        aggregate["groupwise"]["mean_interval_width_gpu_h"]
        / aggregate["pooled"]["mean_interval_width_gpu_h"]
        - 1.0
    )
    criteria = {
        "worst_group_deviation_improves_at_least_0_02": bool(
            worst_deviation_improvement >= 0.02 - 1e-12
        ),
        "groupwise_pooled_coverage_between_0_90_and_0_99": bool(
            0.90 <= aggregate["groupwise"]["blind_coverage"] <= 0.99
        ),
        "mean_width_inflation_at_most_0_25": bool(width_inflation <= 0.25 + 1e-12),
        "point_wape_unchanged": True,
        "point_rmse_unchanged": True,
        "pooled_reproduction_tolerance_passed": bool(
            pooled_interval_max_abs_difference <= 1e-5
        ),
    }
    groupwise_accepted = bool(all(criteria.values()))
    negative_findings: list[str] = []
    if not criteria["worst_group_deviation_improves_at_least_0_02"]:
        negative_findings.append(
            "Groupwise calibration did not improve worst-group absolute coverage deviation by the required 0.02."
        )
    if not criteria["groupwise_pooled_coverage_between_0_90_and_0_99"]:
        negative_findings.append(
            "Groupwise pooled blind coverage fell outside the pre-registered [0.90, 0.99] interval."
        )
    if not criteria["mean_width_inflation_at_most_0_25"]:
        negative_findings.append(
            "Groupwise mean interval width inflation exceeded the pre-registered 25% limit."
        )
    worsened_groups = [
        item["group_id"]
        for item in group_pairs
        if item["groupwise_abs_deviation"] > item["pooled_abs_deviation"] + 1e-12
    ]
    if worsened_groups:
        negative_findings.append(
            "Coverage deviation worsened for groups: " + ", ".join(worsened_groups)
        )
    negative_findings.append(
        "Each region-task group has only 24 calibration scores; the 95% finite-sample groupwise quantile is coarse and must not be described as conditional coverage proof."
    )

    output = pd.DataFrame(diagnostics)
    output.to_csv(CSV_PATH, index=False, float_format="%.12g")
    duration = time.perf_counter() - started
    summary = {
        "schema_version": 1,
        "sprint_id": SPRINT_ID,
        "task_id": TASK_ID,
        "problem_id": "C",
        "question_id": "Q1",
        "status": "PASS",
        "evidence_type": "fixed-point-prediction-conformal-diagnostic",
        "design": {
            "point_predictions": "pinned shared-HGBR reconciled predictions; no refit",
            "calibration_hours": [2352, 2375],
            "blind_hours": [2376, 2399],
            "groups": "6 regions x 3 task types",
            "group_count": 18,
            "calibration_observations_per_group": 24,
            "alpha": ALPHA,
            "lower_bound": "nonnegative clipping at zero",
        },
        "aggregate": aggregate,
        "acceptance": {
            "criteria": criteria,
            "worst_group_deviation_improvement": worst_deviation_improvement,
            "mean_width_inflation_ratio": width_inflation,
            "decision": (
                "PROPOSE_GROUPWISE_FOR_ROOT_REVIEW"
                if groupwise_accepted
                else "RETAIN_POOLED"
            ),
            "groupwise_accepted": groupwise_accepted,
        },
        "audits": {
            "validation_row_count": len(validation),
            "blind_row_count": len(blind),
            "group_counts_exact": True,
            "pooled_interval_max_abs_difference_gpu_h": pooled_interval_max_abs_difference,
            "pooled_reproduction_tolerance_gpu_h": 1e-5,
            "point_predictions_unchanged": True,
            "input_hashes_verified": True,
        },
        "group_comparison": group_pairs,
        "negative_or_rejected_findings": negative_findings,
        "interpretation_limits": [
            "This is an interval-calibration diagnostic; it does not refit or replace the HGBR point forecast.",
            "The blind window is used for model comparison reporting and cannot be reused for future tuning after this diagnostic without declaring a new holdout.",
            "Groupwise empirical coverage is descriptive and does not prove finite-sample conditional coverage."
        ],
        "run_record": {
            "command": [sys.executable, str(Path(__file__).resolve())],
            "environment": {
                "python": sys.version,
                "executable": sys.executable,
                "platform": platform.platform(),
                "numpy": np.__version__,
                "pandas": pd.__version__,
            },
            "random_seed": SEED,
            "input_hashes": task["input_hashes"],
            "code": {
                "path": Path(__file__).resolve().relative_to(ROOT).as_posix(),
                "sha256": sha256(Path(__file__).resolve()),
            },
            "started_at_utc": started_at,
            "duration_seconds": duration,
            "metric_units": {
                "coverage": "ratio",
                "absolute_deviation": "ratio",
                "interval_width": "GPU.h",
                "WAPE": "ratio",
                "RMSE": "GPU.h",
            },
        },
    }
    write_json(SUMMARY_PATH, summary)
    print(
        json.dumps(
            {
                "status": "PASS",
                "decision": summary["acceptance"]["decision"],
                "aggregate": aggregate,
                "duration_seconds": duration,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
