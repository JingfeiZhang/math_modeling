from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_corpus_program import audit, valid_code_pair
from scripts.build_experience_report import normalize_report_text
from src.corpus.miner import build_paper_card


def make_deep_card() -> dict:
    record = {
        "paper_id": "cumcm-2023-a-001",
        "identity": {"contest": "CUMCM", "year": 2023, "problem": "A", "team_id": "001", "title": "fixture"},
        "source": {
            "url": "https://official.example/paper",
            "publisher": "official",
            "accessible": True,
            "fulltext": True,
        },
        "award_evidence": {
            "verified": True,
            "official_url": "https://official.example/display",
            "contest": "CUMCM",
            "year": 2023,
            "problem": "A",
            "team_id": "001",
            "award": "official display",
        },
        "pdf": {"sha256": "a" * 64, "pages": 20, "local_path": "corpus/raw/a.pdf"},
        "review_status": "evidence_deep_read",
        "page_evidence": [{"page": 1, "observation": "abstract evidence", "locator": "PDF p.1", "render": "pages/01.png", "derivation": "visual"}],
        "abstract_structure": [{"page": 1, "role": "result", "detail": "quantified result"}],
        "model_chain": [{"page": 4, "question": "Q1", "model": "MILP"}],
        "validation_chain": [{"type": "baseline", "locator": "p.10"}],
        "figures": [{"page": 8, "type": "sensitivity", "role": "robustness", "lesson": "show stability under perturbation"}],
        "code_links": [
            {
                "relationship": "exact",
                "commit": "b" * 40,
                "sha256": "c" * 64,
                "evidence": "variables and output match p.8",
            }
        ],
        "transferable_rules": ["bind every abstract number to a result table"],
        "risks": ["fixture does not establish mathematical correctness"],
    }
    return build_paper_card(record, require_deep_read=True)


def test_program_audit_separates_quantity_from_completion(tmp_path: Path) -> None:
    folder = tmp_path / "corpus" / "cards" / "deep-read-cumcm"
    folder.mkdir(parents=True)
    card = make_deep_card()
    (folder / "fixture.json").write_text(json.dumps(card), encoding="utf-8")
    report = audit(tmp_path)
    assert report["status"] == "PARTIAL"
    assert report["selected_cards"] == 1
    assert report["content_evidence_deep_reads"] == 1
    assert report["award_verified_deep_reads"] == 1
    assert report["strict_evidence_deep_reads"] == 1
    assert report["validated_paper_code_pairs"] == 1
    assert report["targets"]["cumcm"]["passed"] is False
    assert report["invalid_cards"] == []


def test_code_pair_needs_hashes_relationship_and_evidence() -> None:
    assert valid_code_pair(
        {"relationship": "partial", "commit": "a" * 40, "sha256": "b" * 64, "locator": "p.5 Figure 2"}
    )
    assert not valid_code_pair({"relationship": "exact", "commit": "a" * 40, "sha256": "b" * 64})
    assert valid_code_pair(
        {"relationship": "strong_partial", "commit": "a" * 40, "sha256": "b" * 64, "evidence": "variable and output match"}
    )


def test_program_audit_counts_external_pairs_and_success_recipes(tmp_path: Path) -> None:
    report_root = tmp_path / "corpus" / "reports"
    report_root.mkdir(parents=True)
    (report_root / "code-recipe-mining.json").write_text(
        json.dumps({"pairs": [{"candidate_id": "pair-1", "trusted_pair": True}, {"candidate_id": "candidate-only", "trusted_pair": False}]}),
        encoding="utf-8",
    )
    recipe = tmp_path / "corpus" / "recipes" / "recipe-1"
    recipe.mkdir(parents=True)
    (recipe / "run_report.json").write_text(json.dumps({"status": "success"}), encoding="utf-8")
    report = audit(tmp_path)
    assert report["validated_paper_code_pairs"] == 1
    assert report["validated_paper_code_pair_ids"] == ["pair-1"]
    assert report["runnable_recipe_count"] == 1


def test_experience_report_normalizes_ocr_private_symbols() -> None:
    value = normalize_report_text("\uf061 + \uf0e5 + \uf044 + \uf02d + \uf071 + \uf03d + Ⅰ + 𝑥 + \ue123")
    assert value == "alpha + sum + Delta + - + theta + = + I + x + [OCR符号]"
