"""Project-owned optimization and multi-objective evidence contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence


@dataclass(frozen=True)
class ObjectiveSpec:
    name: str
    direction: str
    unit: str

    def __post_init__(self) -> None:
        if self.direction not in {"min", "max"}:
            raise ValueError("direction must be 'min' or 'max'")


@dataclass(frozen=True)
class OptimizationSpec:
    objectives: tuple[ObjectiveSpec, ...]
    decision_variables: tuple[str, ...]
    fixed_inputs: tuple[str, ...]
    constraints: tuple[str, ...]
    search_mode: str = "exact"


def dominates(left: Sequence[float], right: Sequence[float], directions: Sequence[str]) -> bool:
    """Return whether ``left`` is no worse in every objective and better in one."""

    if not (len(left) == len(right) == len(directions)):
        raise ValueError("objective vectors and directions must have equal lengths")
    converted = [(a if direction == "min" else -a, b if direction == "min" else -b) for a, b, direction in zip(left, right, directions)]
    return all(a <= b for a, b in converted) and any(a < b for a, b in converted)


def non_dominated(points: Sequence[Sequence[float]], directions: Sequence[str]) -> list[int]:
    """Return indices of non-dominated objective rows."""

    return [index for index, point in enumerate(points) if not any(index != other and dominates(other_point, point, directions) for other, other_point in enumerate(points))]


def solve_project_model(*_args: Any, **_kwargs: Any) -> Any:
    """Project hook for a solver selected after baseline and constraint checks."""

    raise NotImplementedError("Implement the current project's solver; this scaffold does not ship an external solver")


def validate_optimization_receipt(receipt: dict[str, Any]) -> list[str]:
    required = {"search_mode", "objectives", "constraints", "baseline", "solver_status", "feasible", "solution_hash"}
    issues = [f"missing field: {field}" for field in sorted(required - set(receipt))]
    if receipt.get("search_mode") in {"random", "heuristic", "hybrid"} and not receipt.get("seed_set"):
        issues.append("random or heuristic search requires a seed_set")
    if receipt.get("contest_evidence_eligible") is True:
        issues.append("optimization scaffold cannot be contest evidence")
    return issues


__all__ = ["ObjectiveSpec", "OptimizationSpec", "dominates", "non_dominated", "solve_project_model", "validate_optimization_receipt"]
