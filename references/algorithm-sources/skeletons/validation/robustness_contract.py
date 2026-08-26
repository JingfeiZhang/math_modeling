"""Project-owned validation, sensitivity and robustness contract."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Any, Sequence


@dataclass(frozen=True)
class ValidationSpec:
    split_strategy: str
    metric: str
    unit: str
    perturbations: tuple[str, ...] = ()
    seeds: tuple[int, ...] = ()


def summarize_runs(values: Sequence[float]) -> dict[str, float | int]:
    """Summarize repeated runs without assigning a statistical claim."""

    if not values:
        raise ValueError("values must be non-empty")
    numeric = [float(value) for value in values]
    return {"n": len(numeric), "mean": mean(numeric), "std_population": pstdev(numeric), "min": min(numeric), "max": max(numeric)}


def compare_models(model_metrics: dict[str, Sequence[float]]) -> dict[str, dict[str, float | int]]:
    """Return per-model run summaries; interpretation belongs to the project."""

    return {name: summarize_runs(values) for name, values in model_metrics.items()}


def run_robustness_probe(*_args: Any, **_kwargs: Any) -> Any:
    """Project hook for sensitivity or robustness experiments."""

    raise NotImplementedError("Define perturbations and validation splits in the current project")


def validate_robustness_receipt(receipt: dict[str, Any]) -> list[str]:
    required = {"split_strategy", "metric", "unit", "baseline", "runs", "perturbations", "failure_conditions"}
    issues = [f"missing field: {field}" for field in sorted(required - set(receipt))]
    if receipt.get("contest_evidence_eligible") is True:
        issues.append("validation scaffold cannot be contest evidence")
    return issues


__all__ = ["ValidationSpec", "compare_models", "run_robustness_probe", "summarize_runs", "validate_robustness_receipt"]
