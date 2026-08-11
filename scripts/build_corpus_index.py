from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
INDEX = CORPUS / "index.csv"
FIELDS = [
    "competition",
    "year",
    "problem",
    "paper_id",
    "title",
    "award_or_label",
    "access",
    "source_url",
    "resource_url",
    "card_file",
    "card_schema_version",
    "review_status",
    "authenticity_level",
    "pdf_sha256",
    "evidence_page_count",
    "code_link_count",
    "cached_pages",
    "reported_total_pages",
    "notes",
]


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _count_list(value: Any) -> str:
    return str(len(value)) if isinstance(value, list) else "0"


def _access_label(source: Mapping[str, Any], fallback: str) -> str:
    value = _text(source.get("access") or fallback)
    if value == "public" or value.lower().startswith("public "):
        if "blob" in value.lower():
            return "public_cached_blob"
        return "public_full_text" if source.get("publisher") == "official" else "mirror_full_text"
    if value and not value.startswith(("public_", "index_only_", "mirror_", "restricted_")):
        # Preserve the source as a readable note while keeping a stable taxonomy.
        return f"index_only_{value.replace(' ', '_')}"
    return value


def _card_row(path: Path, existing: Mapping[str, str]) -> dict[str, str]:
    card = _load_json(path)
    identity = card.get("identity") if isinstance(card.get("identity"), dict) else {}
    source = card.get("source") if isinstance(card.get("source"), dict) else {}
    award = card.get("award_evidence") if isinstance(card.get("award_evidence"), dict) else {}
    authenticity = card.get("authenticity") if isinstance(card.get("authenticity"), dict) else {}
    pdf = card.get("pdf") if isinstance(card.get("pdf"), dict) else {}
    page_coverage = card.get("page_coverage") if isinstance(card.get("page_coverage"), dict) else {}

    schema = _text(card.get("schema_version"))
    if schema == "3.0":
        evidence = card.get("page_evidence")
        review_status = _text(card.get("review_status"))
        contest = identity.get("contest") or identity.get("competition")
        award_label = award.get("award") or award.get("label")
    else:
        evidence = card.get("evidence") or card.get("evidence_pages")
        review_status = _text(card.get("analysis_status") or card.get("review_status"))
        contest = card.get("competition")
        award_label = card.get("award_or_label")

    row = {field: _text(existing.get(field, "")) for field in FIELDS}
    row.update(
        {
            "competition": _text(contest or row["competition"]),
            "year": _text(identity.get("year") or card.get("year") or row["year"]),
            "problem": _text(identity.get("problem") or card.get("problem") or row["problem"]),
            "paper_id": _text(card.get("paper_id") or path.stem),
            "title": _text(identity.get("title") or card.get("title") or row["title"]),
            "award_or_label": _text(award_label or row["award_or_label"]),
            "access": _access_label(source, _text(card.get("access") or row["access"])),
            "source_url": _text(source.get("url") or card.get("source_url") or row["source_url"]),
            "card_file": path.relative_to(CORPUS / "cards").as_posix(),
            "card_schema_version": schema,
            "review_status": review_status,
            "authenticity_level": _text(authenticity.get("level")),
            "pdf_sha256": _text(pdf.get("sha256")),
            "evidence_page_count": _count_list(evidence),
            "code_link_count": _count_list(card.get("code_links")),
            "cached_pages": _text(page_coverage.get("cached_pages") or pdf.get("cached_pages") or row["cached_pages"]),
            "reported_total_pages": _text(page_coverage.get("reported_total_pages") or pdf.get("reported_total_pages") or row["reported_total_pages"]),
        }
    )
    if not row["notes"]:
        if review_status == "evidence_deep_read" and row["authenticity_level"] == "C":
            row["notes"] = "已完成内容证据级深读；奖项身份未独立核验，只迁移中性的模型、写作、排版与图件经验"
        elif review_status in {"evidence_reviewed", "evidence_deep_read"}:
            row["notes"] = "已完成证据级阅读；只迁移可由页面或代码定位支持的经验"
        elif review_status == "content_extracted":
            row["notes"] = "已完成全文提取与页码定位，但奖项真实性不足；只迁移内容结构，不作获奖经验依据"
        else:
            row["notes"] = "索引记录；不得作为获奖经验或数学正确性证据"
    return row


def _manifest_row(path: Path, existing: Mapping[str, str]) -> dict[str, str]:
    manifest = _load_json(path)
    source = manifest.get("source") if isinstance(manifest.get("source"), dict) else {}
    pdf = manifest.get("pdf") if isinstance(manifest.get("pdf"), dict) else {}
    render = manifest.get("render") if isinstance(manifest.get("render"), dict) else {}
    render_pages = render.get("pages") if isinstance(render.get("pages"), list) else []
    manifest_pages = manifest.get("pages") if isinstance(manifest.get("pages"), list) else render_pages
    paper_id = _text(manifest.get("paper_id") or path.parent.name)
    row = {field: _text(existing.get(field, "")) for field in FIELDS}
    row.update(
        {
            "competition": _text(manifest.get("competition") or manifest.get("contest") or row["competition"] or "CUMCM"),
            "year": _text(manifest.get("year") or row["year"]),
            "problem": _text(manifest.get("problem") or manifest.get("problem_id") or row["problem"]),
            "paper_id": paper_id,
            "title": _text(manifest.get("title") or row["title"]),
            "award_or_label": _text(manifest.get("award_or_label") or row["award_or_label"] or "官方论文展示"),
            "access": _text(manifest.get("access") or row["access"] or "public_page_images"),
            "source_url": _text(source.get("url") or manifest.get("source_url") or row["source_url"]),
            "cached_pages": _text(manifest.get("cached_pages") or len(manifest_pages) or row["cached_pages"]),
            "reported_total_pages": _text(manifest.get("reported_total_pages") or pdf.get("pages") or row["reported_total_pages"]),
        }
    )
    return row


def build_index() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if INDEX.exists():
        with INDEX.open(encoding="utf-8-sig", newline="") as handle:
            rows = [{field: _text(row.get(field, "")) for field in FIELDS} for row in csv.DictReader(handle)]
    by_id = {row["paper_id"]: row for row in rows if row["paper_id"]}

    for manifest_path in sorted((CORPUS / "raw").rglob("source_manifest.json")):
        paper_id = _text(_load_json(manifest_path).get("paper_id") or manifest_path.parent.name)
        by_id[paper_id] = _manifest_row(manifest_path, by_id.get(paper_id, {}))

    for card_path in sorted((CORPUS / "cards").rglob("*.json")):
        card = _load_json(card_path)
        paper_id = _text(card.get("paper_id") or card_path.stem)
        by_id[paper_id] = _card_row(card_path, by_id.get(paper_id, {}))

    return [by_id[key] for key in sorted(by_id)]


def main() -> None:
    output_rows = build_index()
    with INDEX.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(output_rows)
    print(json.dumps({"records": len(output_rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
