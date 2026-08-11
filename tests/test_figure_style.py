from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

from src.utils.figure_style import load_style, palette, publication_profile, validate_grayscale


ROOT = Path(__file__).resolve().parents[1]


def test_palette_is_shared_and_grayscale_safe() -> None:
    config = load_style()
    assert config["palette_id"] == "journal-spectrum-v2"
    assert palette()["primary"] == "#5292F7"
    assert config["categorical_order"] == [
        "#CC247C", "#E95351", "#F7A24F", "#FBEB66",
        "#4EA660", "#79CAFB", "#5292F7", "#AA77E9",
    ]
    assert validate_grayscale()["passed"]
    assert config["style"]["export"]["png_dpi"] == 400
    profile = publication_profile()
    assert profile["line_width_pt"] < config["style"]["line_width_pt"]
    assert profile["confidence_band_alpha"] <= 0.12
    assert profile["max_legend_entries"] == 3


def test_matlab_palette_matches_yaml() -> None:
    config = yaml.safe_load((ROOT / "config" / "figure_style.yaml").read_text(encoding="utf-8"))
    matlab = (ROOT / "matlab" / "plotting" / "applyModelingStyle.m").read_text(encoding="utf-8")
    for name, value in config["colors"].items():
        rgb = [round(int(value[index : index + 2], 16) / 255, 8) for index in (1, 3, 5)]
        literal = ", ".join(f"{item:.8f}" for item in rgb)
        assert literal in matlab, f"MATLAB palette missing {name}: {literal}"


def test_no_unregistered_source_hex_colors() -> None:
    output = ROOT / "output" / "test_figure_style_audit.json"
    result = subprocess.run(
        [sys.executable, str(ROOT / "src" / "utils" / "audit_figure_style.py"), "--output", str(output)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["unexpected_colors"] == []


def test_palette_preview_exports_triplet() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "render_figure_palette.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for suffix in (".pdf", ".svg", ".png"):
        assert (ROOT / "output" / f"figure_palette_preview{suffix}").stat().st_size > 500


def test_contract_palette_metadata_warns_legacy_and_blocks_strict(tmp_path: Path) -> None:
    manifest = tmp_path / "figure_contracts.yaml"
    manifest.write_text(
        "schema_version: '2.0'\nfigures:\n  - id: fig-legacy\n    palette_id: ''\n    color_encoding: []\n",
        encoding="utf-8",
    )
    legacy = subprocess.run(
        [sys.executable, str(ROOT / "src" / "utils" / "audit_figure_style.py"), "--manifest", str(manifest), "--output", str(tmp_path / "legacy.json")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert legacy.returncode == 0
    assert json.loads((tmp_path / "legacy.json").read_text(encoding="utf-8"))["warnings"]
    strict = subprocess.run(
        [sys.executable, str(ROOT / "src" / "utils" / "audit_figure_style.py"), "--manifest", str(manifest), "--strict", "--output", str(tmp_path / "strict.json")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert strict.returncode == 1
    assert json.loads((tmp_path / "strict.json").read_text(encoding="utf-8"))["errors"]
