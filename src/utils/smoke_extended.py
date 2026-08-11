from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path


IMPORTS = [
    "ortools", "pulp", "cvxpy", "pyomo", "highspy", "cv2", "fitz", "pdfplumber",
    "rapidocr_onnxruntime", "schemdraw", "SALib", "deap", "simpy", "pyswarms", "pypdf",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-python", choices=("3.12", "3.13"))
    args = parser.parse_args()
    checks: list[dict] = []
    for name in IMPORTS:
        try:
            module = importlib.import_module(name)
            checks.append({"name": name, "passed": True, "version": getattr(module, "__version__", None)})
        except Exception as exc:
            checks.append({"name": name, "passed": False, "error": f"{type(exc).__name__}: {exc}"})

    try:
        import cvxpy as cp

        x = cp.Variable(nonneg=True)
        problem = cp.Problem(cp.Minimize((x - 2) ** 2), [x <= 3])
        problem.solve()
        ok = problem.status in {"optimal", "optimal_inaccurate"} and abs(float(x.value) - 2.0) < 1e-4
        checks.append({"name": "cvxpy-solver", "passed": ok, "status": problem.status})
    except Exception as exc:
        checks.append({"name": "cvxpy-solver", "passed": False, "error": f"{type(exc).__name__}: {exc}"})

    try:
        from ortools.linear_solver import pywraplp

        solver = pywraplp.Solver.CreateSolver("GLOP")
        assert solver is not None
        value = solver.NumVar(0, 4, "value")
        solver.Maximize(value)
        status = solver.Solve()
        ok = status == pywraplp.Solver.OPTIMAL and abs(value.solution_value() - 4.0) < 1e-9
        checks.append({"name": "ortools-solver", "passed": ok, "status": int(status)})
    except Exception as exc:
        checks.append({"name": "ortools-solver", "passed": False, "error": f"{type(exc).__name__}: {exc}"})

    observed_python = f"{sys.version_info.major}.{sys.version_info.minor}"
    python_ok = observed_python in {"3.12", "3.13"}
    if args.expected_python:
        python_ok = observed_python == args.expected_python
    payload = {
        "schema_version": 1,
        "python": sys.version.split()[0],
        "expected_python": args.expected_python,
        "python_compatible": python_ok,
        "user_site_disabled": bool(sys.flags.no_user_site),
        "checks": checks,
        "status": "PASS" if all(item["passed"] for item in checks) and python_ok and sys.flags.no_user_site else "FAIL",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
