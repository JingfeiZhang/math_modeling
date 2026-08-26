"""Project-owned hybrid-model contract skeleton."""

from __future__ import annotations

from typing import Any


def validate_hybrid_contract(contract: dict[str, Any]) -> list[str]:
    required = {"upstream_model", "downstream_model", "interface", "fallback", "ablation_plan", "seed"}
    return [f"missing {key}" for key in sorted(required - set(contract))]


def compare_hybrid_to_components(metrics: dict[str, float]) -> list[str]:
    required = {"hybrid", "component_a", "component_b"}
    return [f"missing {key}" for key in sorted(required - set(metrics))]
