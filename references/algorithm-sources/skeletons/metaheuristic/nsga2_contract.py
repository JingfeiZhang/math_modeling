"""Project-owned metaheuristic search contract.

The file specifies evidence and extension points only.  It is not an NSGA-II
implementation and must not be treated as one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence


@dataclass(frozen=True)
class SearchSpec:
    population_size: int
    generations: int
    seeds: tuple[int, ...]
    repair: str
    stop_rule: str

    def __post_init__(self) -> None:
        if self.population_size < 2 or self.generations < 1:
            raise ValueError("population_size must be >= 2 and generations must be positive")
        if len(self.seeds) < 3:
            raise ValueError("formal stochastic evidence requires at least three independent seeds")


def dominates(left: Sequence[float], right: Sequence[float], directions: Sequence[str]) -> bool:
    if not (len(left) == len(right) == len(directions)):
        raise ValueError("objective vectors and directions must have equal lengths")
    converted = [(a if direction == "min" else -a, b if direction == "min" else -b) for a, b, direction in zip(left, right, directions)]
    return all(a <= b for a, b in converted) and any(a < b for a, b in converted)


def select_non_dominated(points: Sequence[Sequence[float]], directions: Sequence[str]) -> list[int]:
    return [index for index, point in enumerate(points) if not any(index != other and dominates(candidate, point, directions) for other, candidate in enumerate(points))]


def run_search(*_args: Any, **_kwargs: Any) -> Any:
    """Project hook for a documented search implementation."""

    raise NotImplementedError("Implement the selected search in the project and record every seed and trace")


def validate_search_receipt(receipt: dict[str, Any]) -> list[str]:
    required = {"algorithm", "population_size", "generations", "seeds", "traces", "baseline", "feasible_rate", "stop_reason"}
    issues = [f"missing field: {field}" for field in sorted(required - set(receipt))]
    seeds = receipt.get("seeds", [])
    if isinstance(seeds, list) and len(seeds) < 3:
        issues.append("at least three independent seeds are required")
    if receipt.get("contest_evidence_eligible") is True:
        issues.append("metaheuristic scaffold cannot be contest evidence")
    return issues


__all__ = ["SearchSpec", "dominates", "select_non_dominated", "run_search", "validate_search_receipt"]
