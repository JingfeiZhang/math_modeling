"""Project-owned preprocessing contract.

This module is an interface and audit scaffold.  It deliberately contains no
implementation copied from an external source and does not load project data.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def build_data_quality_report(
    frame: Any,
    *,
    required_columns: Sequence[str],
    units: Mapping[str, str],
    time_column: str | None = None,
) -> dict[str, Any]:
    """Return a project-owned, read-only data-quality summary.

    The caller supplies the DataFrame-like object and field contract.  The
    function intentionally reports structure only; imputation, filtering and
    outlier policy must be implemented and reviewed by the current project.
    """

    columns = [str(column) for column in getattr(frame, "columns", ())]
    missing_columns = [column for column in required_columns if column not in columns]
    return {
        "row_count": _safe_length(frame),
        "column_count": len(columns),
        "columns": columns,
        "missing_required_columns": missing_columns,
        "units_missing": sorted(set(required_columns) - set(units)),
        "time_column": time_column,
        "time_column_present": time_column is None or time_column in columns,
        "transformations": [],
        "contest_evidence_eligible": False,
    }


def apply_project_transformations(frame: Any, transformations: Sequence[Mapping[str, Any]]) -> Any:
    """Apply only transformations defined in the current project's contract.

    Replace this explicit stop with project code after each transformation has
    an input/output field, rule, unit, rationale and hash in the run receipt.
    """

    if transformations:
        raise NotImplementedError(
            "Implement transformations in the current project; this scaffold does not copy external code."
        )
    return frame


def validate_transform_receipt(receipt: Mapping[str, Any]) -> list[str]:
    """Validate the minimum audit fields for a preprocessing run."""

    required = {"input_hash", "output_hash", "transformations", "unit_check", "row_count_before", "row_count_after"}
    issues = [f"missing field: {field}" for field in sorted(required - set(receipt))]
    if receipt.get("contest_evidence_eligible") is True:
        issues.append("preprocessing scaffold cannot be contest evidence")
    return issues


def _safe_length(frame: Any) -> int | None:
    try:
        return int(len(frame))
    except (TypeError, ValueError):
        return None


__all__ = ["apply_project_transformations", "build_data_quality_report", "validate_transform_receipt"]
