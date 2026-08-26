"""Project-owned multi-criteria ranking contract."""

from __future__ import annotations

from typing import Sequence


def normalize_matrix(values: Sequence[Sequence[float]], directions: Sequence[str]) -> list[list[float]]:
    """Min-max normalize columns using explicitly declared indicator directions."""

    if not values or any(len(row) != len(directions) for row in values):
        raise ValueError("values must be non-empty and match directions")
    columns = list(zip(*values))
    normalized: list[list[float]] = [[0.0] * len(directions) for _ in values]
    for column_index, (column, direction) in enumerate(zip(columns, directions)):
        low, high = min(column), max(column)
        scale = high - low
        for row_index, value in enumerate(column):
            score = 1.0 if scale == 0 else (value - low) / scale
            normalized[row_index][column_index] = score if direction == "max" else 1.0 - score
    return normalized


def rank_with_weights(values: Sequence[Sequence[float]], directions: Sequence[str], weights: Sequence[float]) -> list[tuple[int, float]]:
    """Return a transparent weighted ranking after direction-aware scaling."""

    if len(directions) != len(weights) or any(weight < 0 for weight in weights) or sum(weights) <= 0:
        raise ValueError("directions and non-negative weights must be valid")
    normalized = normalize_matrix(values, directions)
    total = float(sum(weights))
    scores = [(index, sum(value * weight for value, weight in zip(row, weights)) / total) for index, row in enumerate(normalized)]
    return sorted(scores, key=lambda item: (-item[1], item[0]))


def validate_ranking_receipt(receipt: dict[str, object]) -> list[str]:
    required = {"indicator_directions", "units", "weights", "baseline", "sensitivity", "ranking_hash"}
    issues = [f"missing field: {field}" for field in sorted(required - set(receipt))]
    if receipt.get("contest_evidence_eligible") is True:
        issues.append("ranking scaffold cannot be contest evidence")
    return issues


__all__ = ["normalize_matrix", "rank_with_weights", "validate_ranking_receipt"]
