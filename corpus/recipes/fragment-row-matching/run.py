from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import sys
import time
from itertools import product
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def style(recipe_id: str) -> None:
    plt.rcParams.update(
        {
            "axes.grid": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 120,
            "font.size": 9,
            "savefig.bbox": "tight",
            "svg.hashsalt": recipe_id,
        }
    )


def save_figure(fig: plt.Figure) -> list[Path]:
    outputs = []
    for extension, metadata in (
        ("png", {"Software": "math-modeling-recipe"}),
        ("svg", {"Date": None}),
        ("pdf", {"CreationDate": None, "ModDate": None}),
    ):
        path = ROOT / f"figure.{extension}"
        fig.savefig(path, dpi=400 if extension == "png" else None, metadata=metadata)
        outputs.append(path)
    plt.close(fig)
    return outputs


def solar(cfg: dict[str, Any], rng: np.random.Generator) -> tuple[dict[str, Any], np.ndarray, np.ndarray, str, str]:
    del rng
    latitude = math.radians(float(cfg["latitude_deg"]))
    tilts = np.linspace(0.0, 90.0, int(cfg["tilt_points"]))
    days = np.asarray(cfg["days"], dtype=float)
    declination = np.deg2rad(23.45 * np.sin(2 * np.pi * (284 + days) / 365.0))
    energy = []
    for tilt in np.deg2rad(tilts):
        incidence = np.cos(latitude - tilt - declination)
        energy.append(float(np.clip(incidence, 0, None).mean()))
    values = np.asarray(energy)
    best = int(np.argmax(values))
    baseline = int(np.argmin(np.abs(tilts - float(cfg["baseline_tilt_deg"]))))
    metrics = {
        "best_tilt_deg": float(tilts[best]),
        "normalized_energy": float(values[best]),
        "baseline_energy": float(values[baseline]),
        "relative_gain": float(values[best] / values[baseline] - 1.0),
    }
    return metrics, tilts, values, "Tilt (deg)", "Normalized annual irradiance"


def traffic_ga(cfg: dict[str, Any], rng: np.random.Generator) -> tuple[dict[str, Any], np.ndarray, np.ndarray, str, str]:
    pop_size, generations = int(cfg["population"]), int(cfg["generations"])
    population = np.column_stack((rng.uniform(25, 75, pop_size), rng.uniform(0.8, 2.8, pop_size)))

    def objective(values: np.ndarray) -> np.ndarray:
        speed_ms = values[:, 0] / 3.6
        capacity = 3600.0 / (5.0 / speed_ms + values[:, 1])
        penalty = 0.18 * np.maximum(values[:, 0] - 60.0, 0.0) ** 2
        return capacity - penalty

    history = []
    for _ in range(generations):
        score = objective(population)
        order = np.argsort(score)[::-1]
        elite = population[order[: max(2, pop_size // 4)]]
        children = elite[rng.integers(0, len(elite), pop_size)].copy()
        children += rng.normal([0, 0], [2.0, 0.08], children.shape)
        children[:, 0] = np.clip(children[:, 0], 25, 75)
        children[:, 1] = np.clip(children[:, 1], 0.8, 2.8)
        population = children
        history.append(float(score[order[0]]))
    score = objective(population)
    best = int(np.argmax(score))
    baseline = np.asarray([[50.0, 1.8]])
    metrics = {
        "best_speed_kmh": float(population[best, 0]),
        "best_headway_s": float(population[best, 1]),
        "optimized_score": float(score[best]),
        "baseline_score": float(objective(baseline)[0]),
    }
    x = np.arange(1, generations + 1)
    return metrics, x, np.asarray(history), "Generation", "Best capacity score"


def traffic_ca(cfg: dict[str, Any], rng: np.random.Generator) -> tuple[dict[str, Any], np.ndarray, np.ndarray, str, str]:
    length, steps = int(cfg["road_cells"]), int(cfg["steps"])
    cars = max(2, int(round(length * float(cfg["density"]))))
    positions = np.linspace(0, length - 1, cars, dtype=int)
    speeds = np.zeros(cars, dtype=int)
    vmax, slow = int(cfg["vmax"]), float(cfg["slow_probability"])
    mean_speed, flow = [], 0
    for _ in range(steps):
        gaps = (np.roll(positions, -1) - positions - 1) % length
        speeds = np.minimum(np.minimum(speeds + 1, vmax), gaps)
        mask = (rng.random(cars) < slow) & (speeds > 0)
        speeds[mask] -= 1
        flow += int(np.sum(positions + speeds >= length))
        positions = (positions + speeds) % length
        order = np.argsort(positions)
        positions, speeds = positions[order], speeds[order]
        mean_speed.append(float(speeds.mean()))
    baseline_flow = steps * cars * vmax / length
    metrics = {
        "simulated_flow_vehicles": int(flow),
        "mean_speed_cells_per_step": float(np.mean(mean_speed)),
        "free_flow_baseline": float(baseline_flow),
    }
    return metrics, np.arange(steps), np.asarray(mean_speed), "Step", "Mean speed (cells/step)"


def fragment_greedy(cfg: dict[str, Any], rng: np.random.Generator) -> tuple[dict[str, Any], np.ndarray, np.ndarray, str, str]:
    strips, height = int(cfg["strips"]), int(cfg["height"])
    x = np.linspace(0, 4 * np.pi, strips * 8)
    base = np.vstack([np.sin(x + phase) + 0.15 * np.cos(3 * x - phase) for phase in np.linspace(0, 1.5, height)])
    pieces = np.stack(np.split(base, strips, axis=1))
    permutation = rng.permutation(strips)
    shuffled = pieces[permutation]
    cost = np.full((strips, strips), np.inf)
    for i, j in product(range(strips), repeat=2):
        if i != j:
            cost[i, j] = float(np.mean((shuffled[i, :, -1] - shuffled[j, :, 0]) ** 2))
    start = int(np.argmin([np.min(cost[:, i]) for i in range(strips)]))
    path, remaining = [start], set(range(strips)) - {start}
    while remaining:
        nxt = min(remaining, key=lambda item: cost[path[-1], item])
        path.append(nxt)
        remaining.remove(nxt)
    order = permutation[path]
    accuracy = float(np.mean(np.diff(order) == 1))
    baseline = float(np.mean(np.diff(permutation) == 1))
    metrics = {"adjacency_accuracy": accuracy, "shuffled_baseline": baseline, "recovered_order": order.tolist()}
    return metrics, np.arange(strips), order, "Recovered position", "Original strip index"


def fragment_dp(cfg: dict[str, Any], rng: np.random.Generator) -> tuple[dict[str, Any], np.ndarray, np.ndarray, str, str]:
    strips = int(cfg["strips"])
    anchors = np.cumsum(rng.normal(0, 0.8, (strips + 1, 12)), axis=0)
    permutation = rng.permutation(strips)
    left, right = anchors[permutation], anchors[permutation + 1]
    cost = np.full((strips, strips), np.inf)
    for i, j in product(range(strips), repeat=2):
        if i != j:
            cost[i, j] = float(np.mean((right[i] - left[j]) ** 2))
    state: dict[tuple[int, int], tuple[float, tuple[int, ...]]] = {(1 << j, j): (0.0, (j,)) for j in range(strips)}
    for size in range(1, strips):
        for (mask, last), (score, path) in list(state.items()):
            if mask.bit_count() != size:
                continue
            for nxt in range(strips):
                if mask & (1 << nxt):
                    continue
                key = (mask | (1 << nxt), nxt)
                candidate = (score + cost[last, nxt], path + (nxt,))
                if key not in state or candidate[0] < state[key][0]:
                    state[key] = candidate
    full = (1 << strips) - 1
    score, path = min((value for (mask, _), value in state.items() if mask == full), key=lambda item: item[0])
    recovered = permutation[list(path)]
    accuracy = float(np.mean(np.diff(recovered) == 1))
    metrics = {"optimal_path_cost": float(score), "adjacency_accuracy": accuracy, "recovered_order": recovered.tolist()}
    return metrics, np.arange(strips), recovered, "Recovered position", "Original strip index"


def normal_mc(cfg: dict[str, Any], rng: np.random.Generator) -> tuple[dict[str, Any], np.ndarray, np.ndarray, str, str]:
    samples = int(cfg["samples"])
    x1 = rng.normal(float(cfg["x1_mean"]), float(cfg["x1_sd"]), samples)
    x2 = rng.normal(float(cfg["x2_mean"]), float(cfg["x2_sd"]), samples)
    response = 2.0 * x1 - 0.5 * x2**2 + 0.15 * x1 * x2
    q025, q975 = np.quantile(response, [0.025, 0.975])
    metrics = {
        "mean": float(response.mean()),
        "std": float(response.std(ddof=1)),
        "q025": float(q025),
        "q975": float(q975),
        "baseline_at_means": float(2 * cfg["x1_mean"] - 0.5 * cfg["x2_mean"] ** 2 + 0.15 * cfg["x1_mean"] * cfg["x2_mean"]),
    }
    hist, edges = np.histogram(response, bins=40, density=True)
    return metrics, (edges[:-1] + edges[1:]) / 2, hist, "Response", "Density"


def lunar_descent(cfg: dict[str, Any], rng: np.random.Generator) -> tuple[dict[str, Any], np.ndarray, np.ndarray, str, str]:
    del rng
    dt, gravity = float(cfg["dt"]), float(cfg["gravity"])
    altitude, velocity, fuel = float(cfg["altitude"]), float(cfg["velocity"]), 0.0
    track = []
    for step in range(int(cfg["max_steps"])):
        target_v = -max(2.0, 0.03 * altitude)
        thrust = float(np.clip(gravity + 0.35 * (target_v - velocity), 0.0, 2.2 * gravity))
        velocity += (thrust - gravity) * dt
        altitude += velocity * dt
        fuel += thrust * dt
        track.append((step * dt, max(altitude, 0.0), velocity))
        if altitude <= 0:
            break
    array = np.asarray(track)
    metrics = {
        "touchdown_speed_mps": float(abs(velocity)),
        "fuel_proxy": float(fuel),
        "duration_s": float(array[-1, 0]),
        "constant_thrust_baseline_speed_mps": float(abs(cfg["velocity"] - 0.1 * gravity * array[-1, 0])),
    }
    return metrics, array[:, 0], array[:, 1], "Time (s)", "Altitude (m)"


def trajectory_scan(cfg: dict[str, Any], rng: np.random.Generator) -> tuple[dict[str, Any], np.ndarray, np.ndarray, str, str]:
    del rng
    angles = np.linspace(float(cfg["min_angle_deg"]), float(cfg["max_angle_deg"]), int(cfg["points"]))
    speed, gravity, target = float(cfg["speed"]), float(cfg["gravity"]), float(cfg["target_range"])
    ranges = speed**2 * np.sin(2 * np.deg2rad(angles)) / gravity
    error = np.abs(ranges - target)
    best = int(np.argmin(error))
    baseline = int(np.argmin(np.abs(angles - 45.0)))
    metrics = {
        "best_angle_deg": float(angles[best]),
        "range_m": float(ranges[best]),
        "absolute_error_m": float(error[best]),
        "baseline_error_m": float(error[baseline]),
    }
    return metrics, angles, error, "Launch angle (deg)", "Target error (m)"


def ode_sensitivity(cfg: dict[str, Any], rng: np.random.Generator) -> tuple[dict[str, Any], np.ndarray, np.ndarray, str, str]:
    del rng
    rates = np.linspace(float(cfg["r_min"]), float(cfg["r_max"]), int(cfg["points"]))
    carrying, y0, dt, horizon = float(cfg["carrying"]), float(cfg["y0"]), float(cfg["dt"]), float(cfg["horizon"])
    finals = []
    for rate in rates:
        y = y0
        for _ in range(round(horizon / dt)):
            def f(value: float) -> float:
                return rate * value * (1 - value / carrying)
            k1 = f(y)
            k2 = f(y + dt * k1 / 2)
            k3 = f(y + dt * k2 / 2)
            k4 = f(y + dt * k3)
            y += dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6
        finals.append(y)
    values = np.asarray(finals)
    gradient = np.gradient(values, rates)
    metrics = {"max_final_state": float(values.max()), "max_sensitivity": float(np.max(np.abs(gradient))), "baseline_final_state": float(values[len(values) // 2])}
    return metrics, rates, values, "Growth rate", "Final state"


def folding_geometry(cfg: dict[str, Any], rng: np.random.Generator) -> tuple[dict[str, Any], np.ndarray, np.ndarray, str, str]:
    del rng
    lengths = np.linspace(0.7, 1.3, 80)
    angles = np.deg2rad(np.linspace(25, 75, 80))
    points, objectives = [], []
    for length, angle in product(lengths, angles):
        height = length * math.sin(angle)
        footprint = length * math.cos(angle)
        if abs(height - float(cfg["target_height"])) <= float(cfg["height_tolerance"]) and footprint <= float(cfg["max_footprint"]):
            material = float(cfg["slats"]) * length
            points.append((math.degrees(angle), footprint))
            objectives.append(material)
    values = np.asarray(objectives)
    best = int(np.argmin(values))
    point_array = np.asarray(points)
    metrics = {"best_angle_deg": float(point_array[best, 0]), "best_footprint_m": float(point_array[best, 1]), "material_proxy": float(values[best]), "feasible_count": int(len(values))}
    return metrics, point_array[:, 0], values, "Fold angle (deg)", "Material proxy"


def shape_scan(cfg: dict[str, Any], rng: np.random.Generator) -> tuple[dict[str, Any], np.ndarray, np.ndarray, str, str]:
    del rng
    sides = np.arange(int(cfg["min_sides"]), int(cfg["max_sides"]) + 1)
    area = float(cfg["target_area"])
    radius = np.sqrt(2 * area / (sides * np.sin(2 * np.pi / sides)))
    perimeter = 2 * sides * radius * np.sin(np.pi / sides)
    stability = np.cos(np.pi / sides)
    score = perimeter / stability
    best = int(np.argmin(score))
    metrics = {"best_side_count": int(sides[best]), "score": float(score[best]), "square_baseline_score": float(score[np.where(sides == 4)[0][0]])}
    return metrics, sides, score, "Polygon sides", "Material/stability score"


def storage_slot_sizing(cfg: dict[str, Any], rng: np.random.Generator) -> tuple[dict[str, Any], np.ndarray, np.ndarray, str, str]:
    samples = int(cfg["samples"])
    width = np.clip(rng.normal(cfg["width_mean_mm"], cfg["width_sd_mm"], samples), 8, None) + cfg["clearance_mm"]
    height = np.clip(rng.normal(cfg["height_mean_mm"], cfg["height_sd_mm"], samples), 12, None) + cfg["clearance_mm"]
    standard_w = np.asarray(cfg["standard_widths_mm"], dtype=float)
    standard_h = np.asarray(cfg["standard_heights_mm"], dtype=float)
    assigned_w = standard_w[np.minimum(np.searchsorted(standard_w, width), len(standard_w) - 1)]
    assigned_h = standard_h[np.minimum(np.searchsorted(standard_h, height), len(standard_h) - 1)]
    area = assigned_w * assigned_h
    cabinet_area = float(cfg["cabinet_area_mm2"])
    demand = rng.integers(1, int(cfg["max_daily_count"]) + 1, samples)
    total_area = float(np.sum(area * demand))
    cabinets = int(math.ceil(total_area / cabinet_area))
    raw_area = width * height
    metrics = {
        "required_cabinets": cabinets,
        "standardized_area_mm2": total_area,
        "packing_overhead_ratio": float(np.sum(area * demand) / np.sum(raw_area * demand) - 1),
        "single_cabinet_baseline_capacity_mm2": cabinet_area,
    }
    order = np.argsort(area)
    return metrics, np.arange(samples), area[order], "Sorted medicine type", "Assigned slot area (mm^2)"


RUNNERS = {
    "solar_tilt_sensitivity": solar,
    "traffic_capacity_ga": traffic_ga,
    "cellular_traffic": traffic_ca,
    "fragment_greedy": fragment_greedy,
    "fragment_dp": fragment_dp,
    "normal_uncertainty_mc": normal_mc,
    "lunar_descent_control": lunar_descent,
    "trajectory_angle_scan": trajectory_scan,
    "ode_parameter_sensitivity": ode_sensitivity,
    "folding_geometry": folding_geometry,
    "shape_scan": shape_scan,
    "storage_slot_sizing": storage_slot_sizing,
}


def main() -> int:
    started = time.perf_counter()
    recipe = json.loads((ROOT / "recipe.json").read_text(encoding="utf-8"))
    inputs = json.loads((ROOT / "input.json").read_text(encoding="utf-8"))
    recipe_id = str(recipe["recipe_id"])
    seed = int(recipe["seed"])
    rng = np.random.default_rng(seed)
    style(recipe_id)
    metrics, x, y, xlabel, ylabel = RUNNERS[str(recipe["kind"])](inputs, rng)

    result_path = ROOT / "results.json"
    result_path.write_text(json.dumps({"recipe_id": recipe_id, "metrics": metrics}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    csv_path = ROOT / "series.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["x", "y"])
        writer.writerows(zip(np.asarray(x).tolist(), np.asarray(y).tolist()))

    fig, ax = plt.subplots(figsize=(6.8, 4.2), constrained_layout=True)
    kind = str(recipe["kind"])
    if kind == "folding_geometry":
        ax.scatter(x, y, color="#0072B2", s=13, alpha=0.58, edgecolors="none")
    elif kind in {"fragment_greedy", "fragment_dp", "shape_scan"}:
        ax.plot(x, y, color="#0072B2", linewidth=1.5, marker="o", markersize=4)
    elif kind == "normal_uncertainty_mc":
        ax.fill_between(x, y, color="#56B4E9", alpha=0.35)
        ax.plot(x, y, color="#0072B2", linewidth=1.6)
    else:
        ax.plot(x, y, color="#0072B2", linewidth=1.8)
    ax.set(xlabel=xlabel, ylabel=ylabel, title=recipe["title"])
    figure_paths = save_figure(fig)

    source_paths = [ROOT / "run.py", ROOT / "recipe.json", ROOT / "input.json"]
    output_paths = [result_path, csv_path, *figure_paths]
    report = {
        "schema_version": 1,
        "recipe_id": recipe_id,
        "status": "success",
        "relationship": "modernization_fixture_not_numerical_reproduction",
        "source_pair": recipe["source_pair"],
        "command": f"{sys.executable} run.py",
        "seed": seed,
        "working_directory": str(ROOT),
        "isolation": {"writes_within_recipe_directory": True, "upstream_code_executed": False},
        "environment": {
            "python": platform.python_version(),
            "executable": sys.executable,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "matplotlib": matplotlib.__version__,
        },
        "inputs": [{"path": path.name, "sha256": sha256(path), "bytes": path.stat().st_size} for path in source_paths],
        "outputs": [{"path": path.name, "sha256": sha256(path), "bytes": path.stat().st_size} for path in output_paths],
        "metrics": metrics,
        "runtime_ms": round((time.perf_counter() - started) * 1000, 3),
    }
    (ROOT / "run_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"recipe_id": recipe_id, "status": "success", "metrics": metrics}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
