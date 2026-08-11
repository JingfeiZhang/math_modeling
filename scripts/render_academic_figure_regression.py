"""Render six deterministic single-figure recipes for publication QA."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
RECIPE_ROOT = ROOT / "templates" / "figures" / "python"
DEFAULT_OUTPUT = ROOT / "output" / "_verification" / "academic-figure-regression"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8", float_format="%.10g", lineterminator="\n")


def fixtures(seed: int) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    x = np.arange(48, dtype=float)
    truth = 520 + 38 * np.sin(2 * np.pi * (x - 5) / 24) + 0.7 * x
    observed = truth + rng.normal(0, 7, len(x))
    predicted = truth + 2.2 * np.sin(2 * np.pi * x / 36)
    baseline = 512 + 32 * np.sin(2 * np.pi * (x - 3) / 24) + 0.45 * x
    prediction = pd.DataFrame({
        "x": x, "observed": observed, "predicted": predicted,
        "lower": predicted - 16, "upper": predicted + 16, "baseline": baseline,
    })

    calibration_rows = []
    for series, is_baseline, bias in (("主模型", False, 0.015), ("季节基线", True, 0.105)):
        for value in np.linspace(460, 610, 8):
            calibration_rows.append({
                "series": series, "predicted_mean": value,
                "observed_mean": value * (1 - bias) + 7.5 + rng.normal(0, 2.0),
                "ci95_half": 5.0 + 0.012 * abs(value - 535), "is_baseline": is_baseline,
            })
    calibration = pd.DataFrame(calibration_rows)

    comparison = pd.DataFrame({
        "model": ["线性基线", "随机森林", "支持向量回归", "梯度提升", "集成主模型"],
        "estimate": [0.785, 0.842, 0.826, 0.866, 0.891],
        "lower": [0.756, 0.819, 0.801, 0.846, 0.874],
        "upper": [0.813, 0.864, 0.849, 0.884, 0.907],
        "is_baseline": [True, False, False, False, False],
        "is_primary": [False, False, False, False, True],
    })

    cost = rng.uniform(0.20, 0.95, 180)
    risk = 0.95 - 0.62 * cost + rng.normal(0, 0.075, len(cost))
    service = 0.72 + 0.25 * cost - 0.10 * risk + rng.normal(0, 0.025, len(cost))
    feasible = service >= 0.84
    pareto = np.zeros(len(cost), dtype=bool)
    for index in np.flatnonzero(feasible):
        dominated = np.any(feasible & (cost <= cost[index]) & (risk <= risk[index]) & ((cost < cost[index]) | (risk < risk[index])))
        pareto[index] = not dominated
    frontier = np.flatnonzero(pareto)
    ideal_cost, ideal_risk = cost[frontier].min(), risk[frontier].min()
    score = ((cost[frontier] - ideal_cost) / max(np.ptp(cost[frontier]), 1e-9)) ** 2
    score += ((risk[frontier] - ideal_risk) / max(np.ptp(risk[frontier]), 1e-9)) ** 2
    recommended = np.arange(len(cost)) == frontier[int(np.argmin(score))]
    pareto_frame = pd.DataFrame({
        "objective_x": cost, "objective_y": risk, "is_feasible": feasible,
        "is_pareto": pareto, "is_recommended": recommended,
        "baseline_x": np.full(len(cost), 0.82), "baseline_y": np.full(len(cost), 0.55),
    })

    scenarios = ["需求下降", "名义情景", "成本上升", "供应中断", "复合冲击"]
    metrics = ["成本", "缺口", "排放", "延误", "风险"]
    matrix = np.array([
        [-0.10, -0.08, -0.04, -0.06, -0.05], [-0.02, 0.00, 0.01, 0.00, 0.01],
        [0.12, 0.05, 0.03, 0.08, 0.07], [0.07, 0.18, 0.06, 0.22, 0.16],
        [0.21, 0.28, 0.14, 0.31, 0.27],
    ])
    robustness = pd.DataFrame([
        {"scenario": scenario, "metric": metric, "value": 1 + matrix[i, j], "baseline": 1.0}
        for i, scenario in enumerate(scenarios) for j, metric in enumerate(metrics)
    ])

    edges = [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D"), ("C", "E"),
             ("D", "F"), ("E", "F"), ("E", "G"), ("F", "H"), ("G", "H")]
    network = pd.DataFrame([
        {"source": source, "target": target, "flow": 18 + 5 * i + (i % 3) * 4, "baseline_flow": 22 + 4 * i}
        for i, (source, target) in enumerate(edges)
    ])
    return {
        "prediction": prediction, "calibration": calibration, "model-comparison": comparison,
        "pareto": pareto_frame, "robustness": robustness, "network": network,
    }


RECIPES = {
    "prediction": ("plot_prediction_interval.py", ["--x-label", "测试时段", "--x-unit", "小时", "--y-label", "系统负荷", "--y-unit", "MW"]),
    "calibration": ("plot_calibration.py", ["--response-label", "系统负荷", "--response-unit", "MW"]),
    "model-comparison": ("plot_model_comparison.py", ["--metric-label", "交叉验证 R²", "--metric-unit", "无量纲"]),
    "pareto": ("plot_pareto_frontier.py", ["--x-label", "综合成本指数", "--x-unit", "无量纲", "--y-label", "运行风险指数", "--y-unit", "无量纲"]),
    "robustness": ("plot_robustness_matrix.py", ["--value-label", "相对变化", "--value-unit", "比例"]),
    "network": ("plot_network_flow.py", ["--flow-unit", "单位/小时", "--layout-seed", "20260807"]),
}


def svg_text_count(path: Path) -> int:
    root = ET.parse(path).getroot()
    return sum(1 for node in root.iter() if str(node.tag).split("}")[-1] in {"text", "tspan"})


def render(output_root: Path, seed: int) -> dict:
    output_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, frame in fixtures(seed).items():
        folder = output_root / name
        folder.mkdir(parents=True, exist_ok=True)
        csv_path = folder / "source.csv"
        write_csv(csv_path, frame)
        script_name, extra = RECIPES[name]
        command = [sys.executable, "-s", str(RECIPE_ROOT / script_name), "--input", str(csv_path), "--output-dir", str(folder), "--stem", name, *extra]
        completed = subprocess.run(command, cwd=RECIPE_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"{name} render failed:\n{completed.stdout}\n{completed.stderr}")
        pdf_path, svg_path, png_path = (folder / f"{name}.{suffix}" for suffix in ("pdf", "svg", "png"))
        reader = PdfReader(str(pdf_path))
        page = reader.pages[0]
        width_mm = float(page.mediabox.width) * 25.4 / 72.0
        height_mm = float(page.mediabox.height) * 25.4 / 72.0
        with Image.open(png_path) as image:
            png_size = [image.width, image.height]
            image.convert("L").save(folder / f"{name}_grayscale.png", dpi=(400, 400))
        errors = []
        if len(reader.pages) != 1:
            errors.append("pdf-page-count")
        if abs(width_mm - 158) > 0.8:
            errors.append("physical-width")
        if not 91.8 <= height_mm <= 112.2:
            errors.append("physical-height")
        if png_size[0] < 2450 or png_size[1] < 1400:
            errors.append("png-resolution")
        if svg_text_count(svg_path) < 3:
            errors.append("svg-editable-text")
        contract = {
            "contract_version": "2.0-demo", "id": f"academic-regression-{name}",
            "synthetic_fixture": True, "contest_evidence_eligible": False,
            "backend": "python", "palette_id": "journal-spectrum-v2",
            "target_size_profile": "contest-body", "final_width_mm": round(width_mm, 3), "min_font_pt": 8,
            "panel_map": [{"panel": "main", "role": name, "subclaim": "visual regression only"}],
            "label_strategy": {"mode": "direct-or-external", "collision_checked": not errors},
            "data_integrity": {"source_hashes": [{"path": "source.csv", "sha256": sha256(csv_path)}], "transformation": "deterministic synthetic fixture", "manual_values_forbidden": True},
            "rasterized_layers": [],
            "outputs": {"pdf": pdf_path.name, "svg": svg_path.name, "png": png_path.name, "png_dpi": 400},
        }
        write_json(folder / "demo_contract.json", contract)
        hashes = {path.name: {"bytes": path.stat().st_size, "sha256": sha256(path)} for path in (csv_path, pdf_path, svg_path, png_path)}
        write_json(folder / "hashes.json", {"schema_version": 1, "files": hashes})
        rows.append({"id": name, "passed": not errors, "errors": errors, "pdf_size_mm": [round(width_mm, 3), round(height_mm, 3)], "png_pixels": png_size, "svg_text_nodes": svg_text_count(svg_path), "hashes": hashes})
    report = {"schema_version": 1, "suite_id": "academic-figure-regression-v1", "synthetic_fixture": True, "contest_evidence_eligible": False, "palette_id": "journal-spectrum-v2", "seed": seed, "passed": all(row["passed"] for row in rows), "figures": rows}
    write_json(output_root / "report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=20260807)
    args = parser.parse_args()
    report = render(args.output_root.resolve(), args.seed)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
