"""Project-owned forecasting and time-split contract."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import mean
from typing import Any


@dataclass(frozen=True)
class ForecastSpec:
    target: str
    horizon: int
    metric: str
    unit: str
    training_window: int | None = None
    interval_level: float | None = None


def make_time_splits(n_observations: int, *, horizon: int, windows: int = 3, min_train: int | None = None) -> list[tuple[range, range]]:
    """Create expanding-window, forward-only validation splits."""

    if n_observations < 1 or horizon < 1 or windows < 1:
        raise ValueError("n_observations, horizon and windows must be positive")
    min_train = min_train or horizon
    last_train_end = n_observations - horizon
    first_train_end = max(min_train, last_train_end - (windows - 1) * horizon)
    splits: list[tuple[range, range]] = []
    for train_end in range(first_train_end, last_train_end + 1, horizon):
        test_end = min(train_end + horizon, n_observations)
        splits.append((range(0, train_end), range(train_end, test_end)))
    return splits[-windows:]


def evaluate_point_forecast(actual: list[float], predicted: list[float]) -> dict[str, float]:
    """Compute transparent point metrics for one time-ordered window."""

    if len(actual) != len(predicted) or not actual:
        raise ValueError("actual and predicted must be non-empty and equally sized")
    errors = [float(a) - float(p) for a, p in zip(actual, predicted)]
    return {
        "mae": mean(abs(error) for error in errors),
        "rmse": sqrt(mean(error * error for error in errors)),
    }


def fit_and_forecast(*_args: Any, **_kwargs: Any) -> Any:
    """Project hook for a model implementation; no external implementation is used."""

    raise NotImplementedError("Implement and hash the project model before running a formal forecast")


def validate_forecast_receipt(receipt: dict[str, Any]) -> list[str]:
    required = {"target", "horizon", "metric", "unit", "splits", "baseline", "model_hash"}
    issues = [f"missing field: {field}" for field in sorted(required - set(receipt))]
    if receipt.get("contest_evidence_eligible") is True:
        issues.append("forecast scaffold cannot be contest evidence")
    return issues


__all__ = ["ForecastSpec", "evaluate_point_forecast", "fit_and_forecast", "make_time_splits", "validate_forecast_receipt"]
