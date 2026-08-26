"""Project-owned graph and network contract skeleton."""

from __future__ import annotations

from typing import Any, Iterable


def validate_edges(edges: Iterable[tuple[Any, Any, float]], *, directed: bool) -> list[str]:
    issues: list[str] = []
    for edge in edges:
        if len(edge) != 3:
            issues.append("each edge must be (u, v, weight)")
            continue
        if edge[2] < 0:
            issues.append("negative weights require an algorithm other than Dijkstra")
    if not directed:
        issues.append("undirected interpretation must be recorded in the data contract")
    return issues


def validate_path_result(result: dict[str, Any]) -> list[str]:
    required = {"source", "targets", "distances", "paths", "unreachable_rule"}
    return [f"missing {key}" for key in sorted(required - set(result))]


def validate_flow_result(result: dict[str, Any]) -> list[str]:
    required = {"source", "sink", "value", "capacity_constraints", "cut_certificate"}
    return [f"missing {key}" for key in sorted(required - set(result))]
