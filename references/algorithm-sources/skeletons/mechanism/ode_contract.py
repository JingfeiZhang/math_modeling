"""Project-owned ODE and mechanistic calibration contract skeleton."""

from __future__ import annotations

from typing import Any, Callable, Sequence


def validate_ode_contract(contract: dict[str, Any]) -> list[str]:
    required = {"state_variables", "parameters", "initial_conditions", "boundary_conditions", "units", "rhs"}
    return [f"missing {key}" for key in sorted(required - set(contract))]


def check_conservation(before: float, after: float, tolerance: float) -> bool:
    if tolerance < 0:
        raise ValueError("tolerance must be non-negative")
    return abs(after - before) <= tolerance


def fit_mechanism(*_args: Any, rhs: Callable[..., Sequence[float]] | None = None, **_kwargs: Any) -> Any:
    if rhs is None:
        raise ValueError("project RHS and solver must be supplied")
    raise NotImplementedError("Implement the project-specific integrator and parameter fit")


def validate_mechanism_receipt(receipt: dict[str, Any]) -> list[str]:
    required = {"solver", "tolerance", "initial_state", "boundary_checks", "conservation_checks", "parameter_units"}
    return [f"missing {key}" for key in sorted(required - set(receipt))]
