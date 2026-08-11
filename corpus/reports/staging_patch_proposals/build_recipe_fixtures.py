from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


RECIPES: list[dict[str, Any]] = [
    {
        "recipe_id": "solar-tilt-sensitivity",
        "pair": "cumcm-2012-b149",
        "kind": "solar_tilt_sensitivity",
        "title": "Solar tilt sensitivity",
        "input": {"latitude_deg": 40.1, "tilt_points": 91, "days": [15, 46, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349], "baseline_tilt_deg": 30.0},
    },
    {
        "recipe_id": "traffic-capacity-ga",
        "pair": "cumcm-2013-a056",
        "kind": "traffic_capacity_ga",
        "title": "Traffic capacity optimization",
        "input": {"population": 80, "generations": 60},
    },
    {
        "recipe_id": "cellular-traffic",
        "pair": "cumcm-2013-a117",
        "kind": "cellular_traffic",
        "title": "Cellular traffic simulation",
        "input": {"road_cells": 180, "steps": 180, "density": 0.22, "vmax": 5, "slow_probability": 0.18},
    },
    {
        "recipe_id": "fragment-row-matching",
        "pair": "cumcm-2013-b201",
        "kind": "fragment_greedy",
        "title": "Fragment edge matching",
        "input": {"strips": 10, "height": 48},
    },
    {
        "recipe_id": "fragment-global-matching",
        "pair": "cumcm-2013-b254",
        "kind": "fragment_dp",
        "title": "Global fragment path optimization",
        "input": {"strips": 8},
    },
    {
        "recipe_id": "normal-uncertainty-monte-carlo",
        "pair": "cumcm-2014-a012",
        "kind": "normal_uncertainty_mc",
        "title": "Uncertainty propagation",
        "input": {"samples": 6000, "x1_mean": 5.0, "x1_sd": 0.7, "x2_mean": 2.0, "x2_sd": 0.35},
    },
    {
        "recipe_id": "lunar-descent-control",
        "pair": "cumcm-2014-a305",
        "kind": "lunar_descent_control",
        "title": "Powered descent feedback control",
        "input": {"altitude": 1200.0, "velocity": -28.0, "dt": 0.1, "gravity": 1.62, "max_steps": 3000},
    },
    {
        "recipe_id": "trajectory-angle-scan",
        "pair": "cumcm-2014-a377",
        "kind": "trajectory_angle_scan",
        "title": "Trajectory angle sensitivity",
        "input": {"min_angle_deg": 5.0, "max_angle_deg": 80.0, "points": 151, "speed": 82.0, "gravity": 9.81, "target_range": 620.0},
    },
    {
        "recipe_id": "ode-parameter-sensitivity",
        "pair": "cumcm-2014-a499",
        "kind": "ode_parameter_sensitivity",
        "title": "ODE parameter sensitivity",
        "input": {"r_min": 0.08, "r_max": 0.42, "points": 80, "carrying": 100.0, "y0": 4.0, "dt": 0.02, "horizon": 16.0},
    },
    {
        "recipe_id": "folding-table-geometry",
        "pair": "cumcm-2014-b009",
        "kind": "folding_geometry",
        "title": "Folding table feasible design",
        "input": {"target_height": 0.72, "height_tolerance": 0.025, "max_footprint": 0.82, "slats": 18},
    },
    {
        "recipe_id": "folding-table-shape-scan",
        "pair": "cumcm-2014-b261",
        "kind": "shape_scan",
        "title": "Tabletop shape trade-off",
        "input": {"min_sides": 4, "max_sides": 14, "target_area": 1.0},
    },
    {
        "recipe_id": "storage-slot-sizing",
        "pair": "cumcm-2014-d026",
        "kind": "storage_slot_sizing",
        "title": "Storage slot standardization",
        "input": {
            "samples": 240,
            "width_mean_mm": 38.0,
            "width_sd_mm": 12.0,
            "height_mean_mm": 61.0,
            "height_sd_mm": 21.0,
            "clearance_mm": 2.0,
            "standard_widths_mm": [17, 19, 23, 27, 30, 34, 37, 40, 43, 46, 49, 58, 70],
            "standard_heights_mm": [35, 41, 47, 53, 59, 65, 71, 77, 83, 89, 95, 113, 127, 150],
            "cabinet_area_mm2": 3000000,
            "max_daily_count": 20
        },
    },
]


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair-evidence", type=Path, required=True)
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    evidence = json.loads(args.pair_evidence.read_text(encoding="utf-8"))
    pairs = {item["candidate_id"]: item for item in evidence["pairs"]}
    if len(RECIPES) != 12 or len({item["recipe_id"] for item in RECIPES}) != 12:
        raise ValueError("recipe catalog must contain 12 unique fixtures")

    created = []
    for index, item in enumerate(RECIPES):
        pair = pairs.get(item["pair"])
        if not pair or pair["trusted_pair"] is not True:
            raise ValueError(f"recipe source is not a trusted paper-code pair: {item['pair']}")
        recipe_root = args.output / item["recipe_id"]
        recipe_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.runner, recipe_root / "run.py")
        source_pair = {
            "candidate_id": pair["candidate_id"],
            "relationship": pair["relationship"],
            "repository": pair["paper"]["repository"],
            "commit": pair["paper"]["commit"],
            "paper": {
                "path": pair["paper"]["path"],
                "blob_sha": pair["paper"]["blob_sha"],
                "sha256": pair["paper"]["sha256"],
            },
            "code": [
                {
                    "path": code["source"]["path"],
                    "blob_sha": code["source"]["blob_sha"],
                    "sha256": code["source"]["sha256"],
                    "execution_status": code["execution_status"],
                }
                for code in pair["code"]
            ],
        }
        recipe = {
            "schema_version": 1,
            "recipe_id": item["recipe_id"],
            "kind": item["kind"],
            "title": item["title"],
            "seed": 20260801 + index,
            "source_pair": source_pair,
            "scope": "controlled synthetic fixture for reusable method testing",
            "not_a_reproduction": True,
            "upstream_code_execution": "forbidden",
        }
        write_json(recipe_root / "recipe.json", recipe)
        write_json(recipe_root / "input.json", item["input"])
        created.append(str(recipe_root))

    print(json.dumps({"created": len(created), "directories": created}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
