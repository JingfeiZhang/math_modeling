from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

from scripts.audit_python_figure_suite import audit_suite
from src.demos.python_figure_suite import generate_suite


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_python_single_figure_suite_is_publication_ready_and_deterministic(tmp_path: Path) -> None:
    primary = tmp_path / "primary"
    reference = tmp_path / "reference"
    first = generate_suite(primary, 20260807)
    second = generate_suite(reference, 20260807)

    assert first["figure_count"] == second["figure_count"] == 10
    assert first["backend"] == "python"
    assert first["palette_id"] == "journal-spectrum-v2"
    assert first["style_profile"] == "publication-minimal"

    for figure in first["figures"]:
        folder = primary / figure["folder"]
        stem = figure["stem"]
        contract = _load(folder / "demo_contract.json")
        layout = _load(folder / "layout_audit.json")

        assert contract["synthetic_fixture"] is True
        assert contract["contest_evidence_eligible"] is False
        assert contract["outputs"]["png_dpi"] == 400
        assert contract["min_font_pt"] >= 8
        assert contract["panel_map"] == [
            {
                "panel": "main",
                "role": contract["archetype"],
                "subclaim": contract["core_conclusion"],
            }
        ]
        assert layout["passed"] is True
        assert layout["primary_axes_count"] == 1
        assert layout["auxiliary_axes_count"] <= 1
        assert layout["figure_axes_count"] == 1 + layout["auxiliary_axes_count"]
        assert not layout["errors"]
        assert layout["visual_hierarchy"]["legend_entries"] <= 3

        with Image.open(folder / f"{stem}.png") as image:
            assert image.width >= 2200
            assert image.height >= 1250
        assert len(PdfReader(folder / f"{stem}.pdf").pages) == 1
        assert "<text" in (folder / f"{stem}.svg").read_text(encoding="utf-8")

    report = audit_suite(primary, dpi=120, reference_root=reference)
    assert report["passed"] is True, report["errors"]
    assert report["determinism"]["passed"] is True
    assert all(row["data_equal"] for row in report["determinism"]["figures"])
    assert all(row["svg_canonical_equal"] for row in report["determinism"]["figures"])
    assert all(row["png_pixel_equal"] for row in report["determinism"]["figures"])
