from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.io import savemat
from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.utils.figure_style import configure_matplotlib, palette  # noqa: E402


DEFAULT_SEED = 20260801
COLORS = palette()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_mat_header(path: Path) -> None:
    """Remove SciPy's wall-clock timestamp from the MATLAB v5 header."""
    description = b"MATLAB 5.0 MAT-file, Platform: math-modeling-workbench, Created deterministically"
    with path.open("r+b") as handle:
        handle.write(description.ljust(116, b" "))


def safe_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", value):
        raise ValueError("experiment-id may contain only letters, digits, dot, underscore, and hyphen")
    return value


def save_figure(fig: plt.Figure, stem: Path) -> list[Path]:
    paths = [stem.with_suffix(".pdf"), stem.with_suffix(".svg"), stem.with_suffix(".png")]
    fig.savefig(paths[0], bbox_inches="tight", metadata={"CreationDate": None, "ModDate": None})
    fig.savefig(paths[1], bbox_inches="tight", metadata={"Date": None})
    fig.savefig(paths[2], bbox_inches="tight", dpi=400, metadata={"Software": "math-modeling-workbench"})
    return paths


def run_regression(rng: np.random.Generator, results: Path, figures: Path) -> tuple[dict, list[Path]]:
    x = np.linspace(0.0, 10.0, 80)
    observed = 2.5 + 1.8 * x + rng.normal(0.0, 1.0, size=x.size)
    design = np.column_stack([np.ones_like(x), x])
    beta, *_ = np.linalg.lstsq(design, observed, rcond=None)
    predicted = design @ beta
    residual = observed - predicted
    rmse = float(np.sqrt(np.mean(residual**2)))
    ss_tot = float(np.sum((observed - observed.mean()) ** 2))
    r2 = float(1.0 - np.sum(residual**2) / ss_tot)
    csv_path = results / "regression_predictions.csv"
    pd.DataFrame({"x": x, "observed": observed, "predicted": predicted}).to_csv(csv_path, index=False)

    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.scatter(x, observed, s=22, alpha=0.75, marker="o", color=COLORS["auxiliary"], label="Observed")
    ax.plot(x, predicted, color=COLORS["primary"], linewidth=2.0, label="Least squares")
    ax.set(xlabel="Input (dimensionless)", ylabel="Response (dimensionless)", title="Regression fit and observations")
    ax.grid(alpha=0.22, linewidth=0.6)
    ax.legend(frameon=False)
    fig.tight_layout()
    paths = save_figure(fig, figures / "demo_regression")
    plt.close(fig)
    return {"intercept": float(beta[0]), "slope": float(beta[1]), "rmse": rmse, "r2": r2}, [csv_path, *paths]


def run_linear_program(results: Path, figures: Path) -> tuple[dict, list[Path]]:
    result = linprog(
        c=[-3.0, -5.0],
        A_ub=[[1.0, 2.0], [4.0, 2.0]],
        b_ub=[8.0, 16.0],
        bounds=[(0.0, None), (0.0, None)],
        method="highs",
    )
    if not result.success:
        raise RuntimeError(result.message)
    x_opt, y_opt = map(float, result.x)
    x_grid = np.linspace(0.0, 8.0, 300)
    y_1 = (8.0 - x_grid) / 2.0
    y_2 = (16.0 - 4.0 * x_grid) / 2.0
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.fill_between(x_grid, 0.0, np.maximum(0.0, np.minimum(y_1, y_2)), color=COLORS["primary"], alpha=0.20, label="Feasible region")
    ax.plot(x_grid, y_1, color=COLORS["primary"], linestyle="-", label="Constraint 1")
    ax.plot(x_grid, y_2, color=COLORS["improved"], linestyle="--", label="Constraint 2")
    ax.scatter([x_opt], [y_opt], color=COLORS["highlight"], marker="D", zorder=3, label="Optimum")
    ax.set(xlim=(0, 8), ylim=(0, 5), xlabel="Decision variable x", ylabel="Decision variable y", title="Linear-programming feasible region")
    ax.grid(alpha=0.22, linewidth=0.6)
    ax.legend(frameon=False)
    fig.tight_layout()
    paths = save_figure(fig, figures / "demo_linear_program")
    plt.close(fig)
    return {"x": x_opt, "y": y_opt, "objective": float(-result.fun), "solver": "scipy-highs"}, paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the reproducible modeling workbench demo.")
    parser.add_argument("--experiment-id", default="demo")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output-root", type=Path, default=ROOT / "experiments")
    args = parser.parse_args()

    experiment_id = safe_id(args.experiment_id)
    experiment_root = args.output_root.resolve() / experiment_id
    results = experiment_root / "results"
    figures = experiment_root / "figures"
    results.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    configure_matplotlib()
    matplotlib.rcParams["svg.hashsalt"] = f"math-modeling-{args.seed}"
    started = datetime.now(UTC)
    clock = time.perf_counter()
    rng = np.random.default_rng(args.seed)

    regression, regression_files = run_regression(rng, results, figures)
    linear_program, lp_files = run_linear_program(results, figures)
    mat_path = results / "experiment_data.mat"
    savemat(mat_path, {"seed": args.seed, "regression_metrics": np.array([regression["rmse"], regression["r2"]]), "lp_solution": np.array([linear_program["x"], linear_program["y"], linear_program["objective"]])})
    normalize_mat_header(mat_path)
    config_path = experiment_root / "config.yaml"
    config_path.write_text(f"experiment_id: {experiment_id}\nrandom_seed: {args.seed}\nrunner: src/modeling/run_demo.py\n", encoding="utf-8")

    files = [config_path, mat_path, *regression_files, *lp_files]
    artifacts = [
        {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in sorted(set(files))
    ]
    payload = {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "random_seed": args.seed,
        "methods": ["ordinary_least_squares", "linear_programming"],
        "metrics": {"regression": regression, "linear_program": linear_program},
        "artifacts": artifacts,
        "provenance": {
            "runner": "src/modeling/run_demo.py",
            "started_at_utc": started.isoformat(),
            "duration_seconds": round(time.perf_counter() - clock, 6),
            "numpy_version": np.__version__,
        },
    }
    result_path = results / "experiment_result.json"
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
