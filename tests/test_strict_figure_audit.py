from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfWriter


ROOT = Path(__file__).resolve().parents[1]
AUDITOR = ROOT / "skill_staging" / "modeling-paper-studio" / "scripts" / "audit_figures.py"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path, *, enhanced: bool = True) -> tuple[Path, dict]:
    paper = tmp_path / "paper"
    figures = paper / "figures"
    figures.mkdir(parents=True)
    evidence = tmp_path / "evidence.json"
    evidence.write_text('{"score": 12.5}', encoding="utf-8")
    (tmp_path / "plot.py").write_text("# fixture\n", encoding="utf-8")

    svg = figures / "result.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="158mm" height="104mm">'
        '<text x="10" y="20">main model</text></svg>',
        encoding="utf-8",
    )
    Image.new("RGB", (2488, 1638), "white").save(
        figures / "result.png", dpi=(400, 400)
    )
    writer = PdfWriter()
    writer.add_blank_page(width=158 / 25.4 * 72, height=104 / 25.4 * 72)
    with (figures / "result.pdf").open("wb") as handle:
        writer.write(handle)

    paper.joinpath("main.tex").write_text(
        "\\begin{figure}\\includegraphics{figures/result.pdf}"
        "\\caption{Main model and baseline.}\\end{figure}",
        encoding="utf-8",
    )
    digest = _sha256(evidence)
    contract = {
        "contract_version": "2.0",
        "id": "fig-result",
        "question_id": "Q1",
        "claim_id": "q1-result",
        "core_conclusion": "The main model improves the frozen score.",
        "evidence_chain": [{"locator": "evidence.json:score", "sha256": digest, "fields": ["score"]}],
        "kind": "data",
        "archetype": "model-comparison",
        "backend": "python",
        "source_data": ["evidence.json"],
        "source_script": "plot.py",
        "outputs": {
            "pdf": "paper/figures/result.pdf",
            "svg": "paper/figures/result.svg",
            "png": "paper/figures/result.png",
            "png_dpi": 400,
        },
        "baseline": "seasonal baseline",
        "axes": [{"variable": "model", "unit": "dimensionless"}, {"variable": "score", "unit": "points"}],
        "caption": "Main model and baseline score.",
        "panel_map": [{"panel": "main", "role": "comparison", "subclaim": "frozen score"}],
        "statistics": ["deterministic fixture"],
        "review_risks": ["synthetic audit fixture"],
        "final_width_mm": 158,
        "min_font_pt": 8,
    }
    if enhanced:
        contract.update({
            "core_message": "The frozen main-model score exceeds the baseline.",
            "visual_hierarchy": {
                "primary_evidence": "main model",
                "secondary_context": "baseline",
                "deemphasized": "grid",
            },
            "target_size_profile": "contest-body",
            "statistics_report": {
                "sample_size": "deterministic fixture",
                "center": "not applicable",
                "interval": "not applicable",
                "test": "not applicable",
                "multiplicity": "not applicable",
            },
            "data_integrity": {
                "source_hashes": [{"path": "evidence.json", "sha256": digest}],
                "transformation": "read score without manual override",
                "manual_values_forbidden": True,
            },
            "label_strategy": {"mode": "direct", "collision_checked": True},
            "rasterized_layers": [],
        })
    return paper, contract


def _run(paper: Path, contract: dict, *, strict: bool) -> tuple[subprocess.CompletedProcess[str], dict]:
    manifest = paper / "figure_manifest.json"
    manifest.write_text(
        json.dumps({"schema_version": "2.0", "figures": [contract]}, ensure_ascii=False),
        encoding="utf-8",
    )
    command = [sys.executable, str(AUDITOR), "--paper-dir", str(paper), "--min-dpi", "400"]
    if strict:
        command.append("--strict")
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    return completed, json.loads(completed.stdout)


def test_legacy_contract_warns_but_strict_mode_blocks(tmp_path: Path) -> None:
    paper, contract = _fixture(tmp_path, enhanced=False)
    legacy, legacy_report = _run(paper, contract, strict=False)
    strict, strict_report = _run(paper, contract, strict=True)
    assert legacy.returncode == 0, legacy.stdout + legacy.stderr
    assert any(item["code"] == "CONTRACT_ENHANCED_FIELD_MISSING" for item in legacy_report["warnings"])
    assert strict.returncode == 1
    assert any(item["code"] == "CONTRACT_ENHANCED_FIELD_MISSING" for item in strict_report["errors"])


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("small-font", "SMALL_FONT"),
        ("wrong-width", "SIZE_PROFILE_WIDTH"),
        ("stale-hash", "DATA_INTEGRITY"),
        ("svg-outlined", "SVG_TEXT_OUTLINED"),
        ("multipanel", "MULTIPANEL_JUSTIFICATION"),
    ],
)
def test_strict_audit_blocks_publication_defects(tmp_path: Path, case: str, expected: str) -> None:
    paper, contract = _fixture(tmp_path, enhanced=True)
    mutated = copy.deepcopy(contract)
    if case == "small-font":
        mutated["min_font_pt"] = 7.5
    elif case == "wrong-width":
        mutated["final_width_mm"] = 145
    elif case == "stale-hash":
        mutated["data_integrity"]["source_hashes"][0]["sha256"] = "0" * 64
    elif case == "svg-outlined":
        (paper / "figures" / "result.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="158mm" height="104mm"><path d="M0 0"/></svg>',
            encoding="utf-8",
        )
    elif case == "multipanel":
        mutated["panel_map"].append({"panel": "b", "role": "diagnostic", "subclaim": "robustness"})
    completed, report = _run(paper, mutated, strict=True)
    assert completed.returncode == 1
    assert any(item["code"] == expected for item in report["errors"]), report
