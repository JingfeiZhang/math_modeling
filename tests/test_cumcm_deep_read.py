from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

from src.corpus.deep_read_cumcm import (
    SELECTIONS,
    _assert_cumcm_identity,
    _validate_card,
    build_card,
    cache_pdfs,
    validate_selections,
)
from src.corpus.miner import git_blob_sha1
from src.corpus.migrate_official_cumcm_2024 import PAPERS, build_card as build_official_card
from src.corpus.report_quarantine import build_report as build_quarantine_report


def test_selection_has_two_real_cumcm_papers_per_historical_year() -> None:
    assert len(SELECTIONS) == 18
    assert {item.source_id for item in SELECTIONS} == {"personqianduixue-math-model"}
    for year in range(2012, 2021):
        assert sum(item.year == year for item in SELECTIONS) == 2
    assert all(len(item.commit) == 40 and len(item.blob_sha) == 40 for item in SELECTIONS)


def test_selection_validation_uses_pinned_tree_fields(tmp_path: Path) -> None:
    grouped: dict[str, list[dict]] = {}
    for item in SELECTIONS:
        grouped.setdefault(item.source_id, []).append({"path": item.path, "blob_sha": item.blob_sha, "bytes": item.expected_bytes})
    paths = {}
    for source_id, entries in grouped.items():
        path = tmp_path / f"{source_id}.json"
        path.write_text(json.dumps({"entries": entries}, ensure_ascii=False), encoding="utf-8")
        paths[source_id] = path
    validate_selections(paths)


def test_pdf_cache_checks_git_blob_and_writes_content_addressed_object(tmp_path: Path, monkeypatch) -> None:
    import src.corpus.deep_read_cumcm as module

    content = b"%PDF-1.4\nfixture"
    selection = module.Selection(
        "cumcm-2012-a-fixture", 2012, "A", "zhanwen-mathmodel", "https://github.com/zhanwen/MathModel",
        module.ZHANWEN_COMMIT, "fixture.pdf", git_blob_sha1(content), len(content),
    )
    monkeypatch.setattr(module, "SELECTIONS", (selection,))
    records = cache_pdfs(tmp_path, fetcher=lambda _: content)
    digest = hashlib.sha256(content).hexdigest()
    assert records[0]["pdf"]["sha256"] == digest
    assert (tmp_path / "corpus" / "raw" / "objects" / "sha256" / digest[:2] / f"{digest}.pdf").read_bytes() == content


def test_generated_card_keeps_unverified_award_at_c(tmp_path: Path, monkeypatch) -> None:
    import src.corpus.deep_read_cumcm as module

    selection = module.Selection(
        "cumcm-2012-a-fixture", 2012, "A", "zhanwen-mathmodel", "https://github.com/zhanwen/MathModel",
        module.ZHANWEN_COMMIT, "fixture.pdf", "a" * 40, 10,
    )
    raw = tmp_path / "corpus" / "raw" / selection.paper_id
    raw.mkdir(parents=True)
    text = "摘要\n问题一 建立线性规划模型并得到结果。\f模型建立\n采用回归模型进行预测。\f模型检验\n误差检验和敏感性分析。\n图 1 预测曲线\f结论与改进\n模型仍受参数范围限制。\f"
    extracted = raw / "extracted-layout.txt"
    extracted.write_text(text, encoding="utf-8")
    page_records = []
    for page in range(1, 5):
        image_path = tmp_path / "corpus" / "rendered" / selection.paper_id / "pages" / f"page-{page:02d}.jpg"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (90, 120), "white").save(image_path, "JPEG")
        page_records.append({"page": page, "file": image_path.relative_to(tmp_path).as_posix()})
    manifest = {
        "pdf": {"object": "corpus/raw/objects/fixture.pdf", "sha256": "b" * 64, "git_blob_sha": "a" * 40, "bytes": 10, "pages": 4},
        "source": {"accessed": "2026-08-03"},
        "text": {"file": extracted.relative_to(tmp_path).as_posix(), "sha256": hashlib.sha256(text.encode()).hexdigest()},
        "render": {"method": "fixture", "pages": page_records, "contact_sheets": ["corpus/rendered/fixture/contact-01-04.jpg"]},
    }
    (raw / "source_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    card = build_card(tmp_path, selection, visual_reviewed=True)
    assert card["authenticity"]["level"] == "C"
    assert card["award_evidence"]["verified"] is False
    assert card["review_status"] == "evidence_deep_read"
    assert card["paper_id"] == selection.paper_id
    assert card["provenance"]["render"]["visual_review"] == "complete"
    assert _validate_card(card) == []


def test_cumcm_identity_rejects_graduate_competition_cover() -> None:
    selection = SELECTIONS[0]
    try:
        _assert_cumcm_identity(["第十一届华为杯全国研究生数学建模竞赛"], selection)
    except ValueError as exc:
        assert "graduate-contest paper" in str(exc)
    else:
        raise AssertionError("graduate competition paper was accepted as CUMCM")


def test_official_2024_cards_are_v3_a_level_without_claiming_source_pdf() -> None:
    assert len(PAPERS) == 6
    statuses = []
    for paper_id in PAPERS:
        card = build_official_card(Path(__file__).resolve().parents[1], paper_id)
        assert card["schema_version"] == "3.0"
        assert card["authenticity"]["level"] == "A"
        assert card["pdf"]["kind"] == "official_page_image_set"
        assert card["pdf"]["source_pdf_available"] is False
        assert card["pdf"]["derived_review_pdf"] == ""
        statuses.append(card["review_status"])
    assert statuses.count("evidence_deep_read") == 2
    assert statuses.count("evidence_reviewed") == 4


def test_quarantine_report_preserves_fourteen_gmcm_documents() -> None:
    report = build_quarantine_report(Path(__file__).resolve().parents[1])
    assert report["record_count"] == 14
    assert all(item["corrected_contest_family"] == "GMCM" for item in report["records"])
    assert all(item["pdf_sha256"] for item in report["records"])
