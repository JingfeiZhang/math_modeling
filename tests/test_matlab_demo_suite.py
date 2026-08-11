from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "output" / "_demos" / "matlab" / "matlab-single-figure-suite"
DEMOS = {
    "fig-01-prediction-interval": "prediction_interval",
    "fig-02-calibration": "calibration",
    "fig-03-residual-diagnostics": "residual_diagnostics",
    "fig-04-pareto-frontier": "pareto_frontier",
    "fig-05-optimization-convergence": "convergence",
    "fig-06-resource-allocation": "allocation",
    "fig-07-sensitivity-ranking": "sensitivity_ranking",
    "fig-08-robustness-matrix": "robustness_matrix",
    "fig-09-uncertainty-distribution": "uncertainty_distribution",
    "fig-10-spatial-risk-field": "spatial_risk_field",
    "fig-11-network-routes": "network_routes",
    "fig-12-service-comparison": "service_comparison",
}


def test_single_figure_suite_contains_all_export_formats() -> None:
    assert SUITE.is_dir()
    for demo_id, stem in DEMOS.items():
        folder = SUITE / demo_id
        assert folder.is_dir(), demo_id
        for suffix in ("pdf", "svg", "png"):
            artifact = folder / f"{stem}.{suffix}"
            assert artifact.is_file() and artifact.stat().st_size > 100, artifact
        with Image.open(folder / f"{stem}.png") as image:
            assert image.width >= 1100 and image.height >= 700, (demo_id, image.size)


def test_single_figure_contracts_bind_palette_and_provenance() -> None:
    for demo_id in DEMOS:
        contract = json.loads((SUITE / demo_id / "demo_contract.json").read_text(encoding="utf-8"))
        assert contract["contract_version"] == "2.0"
        assert contract["palette_id"] == "journal-spectrum-v2"
        assert contract["synthetic_fixture"] is True
        assert contract["contest_evidence_eligible"] is False
        assert contract["source_script"] == "matlab/demos/run_single_figure_suite.m"
        assert set(contract["outputs"]) >= {"pdf", "svg", "png"}
        assert contract["color_encoding"]


def test_single_figure_visual_audit_is_complete_and_light_background() -> None:
    report = json.loads((SUITE / "suite_visual_audit.json").read_text(encoding="utf-8"))
    assert report["passed"] is True
    assert len(report["demos"]) == len(DEMOS)
    assert not report["errors"]
    for row in report["demos"]:
        assert row["pdf_visual_passed"] is True
        assert row["dark_background_fraction"] < 0.35, row


def test_single_figure_hash_reproducibility_is_complete() -> None:
    report = json.loads((SUITE / "reproducibility.json").read_text(encoding="utf-8"))
    assert report["passed"] is True
    assert len(report["demos"]) == len(DEMOS)
    assert all(item["passed"] for item in report["demos"])
    assert not report["errors"]


def test_demo_audit_and_runner_enforce_single_figure_workflow() -> None:
    audit = (ROOT / "scripts" / "audit_demo_suite.py").read_text(encoding="utf-8")
    runner = (ROOT / "matlab" / "demos" / "run_single_figure_suite.m").read_text(encoding="utf-8")
    assert "DARK_BACKGROUND" in audit
    assert "normalizeFigureStyle(fig)" in runner
    assert "tiledlayout" not in runner
    assert "subplot" not in runner
