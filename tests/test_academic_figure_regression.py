from __future__ import annotations

import json
from pathlib import Path

from scripts.render_academic_figure_regression import render


def test_six_single_figure_recipes_render_at_final_size(tmp_path: Path) -> None:
    report = render(tmp_path, 20260807)
    assert report["passed"] is True, report
    assert len(report["figures"]) == 6
    assert {row["id"] for row in report["figures"]} == {
        "prediction", "calibration", "model-comparison", "pareto", "robustness", "network"
    }
    for row in report["figures"]:
        assert row["errors"] == []
        assert abs(row["pdf_size_mm"][0] - 158) <= 0.8
        assert 92 <= row["pdf_size_mm"][1] <= 112
        assert row["png_pixels"][0] >= 2450
        assert row["svg_text_nodes"] >= 3
        contract = json.loads((tmp_path / row["id"] / "demo_contract.json").read_text(encoding="utf-8"))
        assert contract["synthetic_fixture"] is True
        assert contract["contest_evidence_eligible"] is False
        assert contract["palette_id"] == "journal-spectrum-v2"
        assert contract["panel_map"][0]["panel"] == "main"
