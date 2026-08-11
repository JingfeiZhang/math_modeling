from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence


REJECTED_MARKERS = ("中国研究生数学建模竞赛", "全国研究生数学建模竞赛", "研究生数学建模竞赛", "研究生创新实践")


def build_report(root: Path) -> dict[str, Any]:
    quarantine = root / "corpus" / "quarantine" / "gmcm-misclassified-as-cumcm"
    records: list[dict[str, Any]] = []
    for card_path in sorted((quarantine / "cards").glob("*.json")):
        card = json.loads(card_path.read_text(encoding="utf-8"))
        paper_id = card["paper_id"]
        text_path = quarantine / "raw" / paper_id / "extracted-layout.txt"
        pages = text_path.read_text(encoding="utf-8", errors="replace").split("\f")
        matches: list[dict[str, Any]] = []
        for page_number, text in enumerate(pages[:5], start=1):
            compact = "".join(text.split())
            for marker in REJECTED_MARKERS:
                if marker in compact:
                    matches.append({"page": page_number, "marker": marker, "locator": f"quarantine PDF p.{page_number}"})
        source = card.get("source", {})
        records.append({"paper_id": paper_id, "original_claimed_contest": card.get("identity", {}).get("contest"), "corrected_contest_family": "GMCM", "reason": "graduate-contest identity marker found in the document; excluded from CUMCM counts", "identity_markers": matches, "source_repository": source.get("repository", ""), "source_commit": source.get("commit", ""), "source_path": source.get("path", ""), "pdf_sha256": card.get("pdf", {}).get("sha256", ""), "quarantined_card": card_path.relative_to(root).as_posix()})
    report = {"schema_version": 1, "quarantine": "gmcm-misclassified-as-cumcm", "record_count": len(records), "action": "preserved and excluded from CUMCM metrics; no files deleted", "records": records}
    json_path = quarantine / "quarantine_report.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# GMCM 误分类隔离报告", "", f"共隔离 {len(records)} 篇。所有文件均保留，仅从 CUMCM 计数和经验结论中排除。", "", "| Paper ID | 身份证据 | 固定来源 |", "|---|---|---|"]
    for item in records:
        evidence = "；".join(f"p.{match['page']} {match['marker']}" for match in item["identity_markers"]) or "前五页文本层未提取到标记，仍按既有人工身份复核隔离"
        source = f"{item['source_repository']}@{item['source_commit'][:12]} `{item['source_path']}`"
        lines.append(f"| `{item['paper_id']}` | {evidence} | {source} |")
    (quarantine / "quarantine_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report documents quarantined after GMCM/CUMCM identity correction.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    print(json.dumps(build_report(args.root.resolve()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
