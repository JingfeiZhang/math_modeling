"""Project-owned statistical inference and experiment contract skeleton."""

from __future__ import annotations

from typing import Any, Sequence


def summarize_groups(groups: dict[str, Sequence[float]]) -> dict[str, dict[str, float | int]]:
    result: dict[str, dict[str, float | int]] = {}
    for name, values in groups.items():
        if not values:
            raise ValueError(f"empty group: {name}")
        mean = sum(values) / len(values)
        result[name] = {"n": len(values), "mean": mean, "min": min(values), "max": max(values)}
    return result


def choose_test_design(*, independent: bool, normality_supported: bool, equal_variance_supported: bool) -> str:
    if independent and normality_supported and equal_variance_supported:
        return "parametric_between_group"
    if independent:
        return "robust_or_nonparametric_between_group"
    return "paired_or_blocked_design"


def validate_inference_receipt(receipt: dict[str, Any]) -> list[str]:
    required = {"hypothesis", "alpha", "test", "effect_size", "assumption_checks", "multiple_comparison_rule"}
    return [f"missing {key}" for key in sorted(required - set(receipt))]
