"""Project-owned classification and clustering contract skeleton."""

from __future__ import annotations

from typing import Any, Sequence


def make_stratified_splits(labels: Sequence[Any], test_fraction: float = 0.2) -> dict[str, Any]:
    """Record a reproducible split plan; the project chooses the seed and grouping rule."""
    if not labels or not 0 < test_fraction < 1:
        raise ValueError("labels and a valid test_fraction are required")
    return {"method": "stratified", "test_fraction": test_fraction, "n": len(labels), "seed": None}


def evaluate_classifier(y_true: Sequence[Any], y_pred: Sequence[Any]) -> dict[str, float]:
    if len(y_true) != len(y_pred) or not y_true:
        raise ValueError("classification outputs must be non-empty and aligned")
    accuracy = sum(a == b for a, b in zip(y_true, y_pred)) / len(y_true)
    return {"accuracy": accuracy}


def validate_cluster_labels(labels: Sequence[int], expected_n: int) -> list[str]:
    issues: list[str] = []
    if len(labels) != expected_n:
        issues.append("cluster labels are not aligned with input rows")
    if len(set(labels)) < 2:
        issues.append("clustering must produce at least two groups for comparison")
    return issues


def validate_classification_receipt(receipt: dict[str, Any]) -> list[str]:
    required = {"split", "baseline", "metrics", "seed", "feature_schema"}
    return [f"missing {key}" for key in sorted(required - set(receipt))]
