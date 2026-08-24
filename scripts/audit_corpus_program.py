from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from src.corpus.miner import is_award_verified_deep_read, validate_paper_card  # noqa: E402


SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")
TARGETS = {"cumcm": 24, "mcm_icm": 12, "gmcm": 6}
OFFICIAL_CUMCM_2024_IDS = (
    "cumcm-2024-a163",
    "cumcm-2024-b159",
    "cumcm-2024-c038",
    "cumcm-2024-d033",
    "cumcm-2024-e010",
    "cumcm-2024-e061",
)


def load_card(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"card is not an object: {path}")
    return value


def group_for(card: dict[str, Any]) -> str:
    identity = card.get("identity") if isinstance(card.get("identity"), dict) else {}
    contest = str(identity.get("contest") or card.get("competition") or "").upper()
    if contest == "CUMCM":
        return "cumcm"
    if contest in {"MCM", "ICM"}:
        return "mcm_icm"
    if contest == "GMCM":
        return "gmcm"
    return "other"


def valid_code_pair(link: Any) -> bool:
    if not isinstance(link, dict):
        return False
    relationship = str(link.get("relationship") or link.get("status") or "").lower()
    commit = str(link.get("commit") or "")
    digest = str(link.get("sha256") or "")
    evidence = link.get("evidence") or link.get("locator") or link.get("match")
    return relationship in {"exact", "partial", "validated", "strong_partial", "supported_partial"} and bool(
        SHA40.fullmatch(commit) and SHA64.fullmatch(digest) and evidence
    )


def external_code_pair_ids(root: Path) -> set[str]:
    path = root / "corpus" / "reports" / "code-recipe-mining.json"
    if not path.is_file():
        return set()
    try:
        payload = load_card(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return set()
    identifiers: set[str] = set()
    for pair in payload.get("pairs", []):
        if not isinstance(pair, dict) or pair.get("trusted_pair") is not True:
            continue
        identifier = str(pair.get("candidate_id") or pair.get("paper_id") or "").strip()
        if identifier:
            identifiers.add(identifier)
    return identifiers


def audit(root: Path) -> dict[str, Any]:
    card_root = root / "corpus" / "cards"
    selected_paths = sorted(
        list((card_root / "deep-read-cumcm").glob("*.json"))
        + list((card_root / "deep-read-mcm-gmcm").glob("*.json"))
        + [card_root / f"{paper_id}.json" for paper_id in OFFICIAL_CUMCM_2024_IDS if (card_root / f"{paper_id}.json").is_file()]
    )
    cards: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    for path in selected_paths:
        try:
            card = load_card(path)
            errors = validate_paper_card(card, require_deep_read=False)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            invalid.append({"card": path.relative_to(root).as_posix(), "errors": [str(exc)]})
            continue
        if errors:
            invalid.append({"card": path.relative_to(root).as_posix(), "errors": errors})
        cards.append(card)

    groups = Counter(group_for(card) for card in cards)
    levels = Counter(str(card.get("authenticity", {}).get("level", "unknown")) for card in cards)
    statuses = Counter(str(card.get("review_status", "unknown")) for card in cards)
    content_deep = [
        card
        for card in cards
        if card.get("review_status") == "evidence_deep_read"
        and not validate_paper_card(card, require_deep_read=True)
    ]
    award_verified_deep = [card for card in content_deep if is_award_verified_deep_read(card)]
    card_code_pair_ids = {
        str(card.get("paper_id"))
        for card in cards
        if any(valid_code_pair(link) for link in card.get("code_links", []))
    }
    code_pair_ids = card_code_pair_ids | external_code_pair_ids(root)
    code_pairs = len(code_pair_ids)
    recipe_reports = list((root / "corpus" / "recipes").glob("*/run_report.json"))
    runnable_recipes = 0
    for path in recipe_reports:
        try:
            if str(load_card(path).get("status", "")).upper() in {"PASS", "PASSED", "SUCCESS"}:
                runnable_recipes += 1
        except (OSError, ValueError, json.JSONDecodeError):
            continue

    target_checks = {
        name: {"target": target, "observed": groups.get(name, 0), "passed": groups.get(name, 0) >= target}
        for name, target in TARGETS.items()
    }
    target_checks["paper_code_pairs"] = {"target": 20, "observed": code_pairs, "passed": code_pairs >= 20}
    target_checks["runnable_recipes"] = {"target": 12, "observed": runnable_recipes, "passed": runnable_recipes >= 12}
    target_checks["content_evidence_deep_reads"] = {
        "target": sum(TARGETS.values()),
        "observed": len(content_deep),
        "passed": len(content_deep) >= sum(TARGETS.values()),
    }
    all_passed = not invalid and all(item["passed"] for item in target_checks.values())
    return {
        "schema_version": 1,
        "status": "PASS" if all_passed else "PARTIAL",
        "selected_cards": len(cards),
        "group_counts": dict(sorted(groups.items())),
        "authenticity_counts": dict(sorted(levels.items())),
        "review_status_counts": dict(sorted(statuses.items())),
        "content_evidence_deep_reads": len(content_deep),
        "award_verified_deep_reads": len(award_verified_deep),
        "strict_evidence_deep_reads": len(award_verified_deep),
        "validated_paper_code_pairs": code_pairs,
        "validated_paper_code_pair_ids": sorted(code_pair_ids),
        "runnable_recipe_count": runnable_recipes,
        "targets": target_checks,
        "invalid_cards": invalid,
        "interpretation": (
            "Quantity, content evidence, award authenticity, code pairing, and runnable reproduction are separate gates. "
            "Level C content deep reads may support neutral layout/model lessons but must not be described as award-winning papers."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# 语料扩展验收",
        "",
        f"- 状态：{report['status']}",
        f"- 选中卡片：{report['selected_cards']}",
        f"- 真实性：{report['authenticity_counts']}",
        f"- 阅读状态：{report['review_status_counts']}",
        f"- 内容证据级深读：{report['content_evidence_deep_reads']}",
        f"- 奖项已核验深读：{report['award_verified_deep_reads']}",
        f"- 已验证论文-代码配对：{report['validated_paper_code_pairs']}",
        f"- 可运行现代配方：{report['runnable_recipe_count']}",
        "",
        "## 目标",
        "",
        "| 项目 | 目标 | 实际 | 通过 |",
        "|---|---:|---:|:---:|",
    ]
    for name, item in report["targets"].items():
        lines.append(f"| {name} | {item['target']} | {item['observed']} | {'是' if item['passed'] else '否'} |")
    lines.extend(["", report["interpretation"], ""])
    if report["invalid_cards"]:
        lines.extend(["## 无效卡片", ""])
        for item in report["invalid_cards"]:
            lines.append(f"- `{item['card']}`：{'；'.join(item['errors'])}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the 42-paper evidence deep-read program without inflating counts.")
    parser.add_argument("--root", type=Path, default=WORKSPACE_ROOT)
    parser.add_argument("--output", type=Path, default=Path("corpus/program_status.json"))
    parser.add_argument("--markdown", type=Path, default=Path("corpus/program_status.md"))
    args = parser.parse_args()
    root = args.root.resolve()
    report = audit(root)
    output = args.output if args.output.is_absolute() else root / args.output
    markdown = args.markdown if args.markdown.is_absolute() else root / args.markdown
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "selected_cards": report["selected_cards"]}, ensure_ascii=True))
    return 0 if not report["invalid_cards"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
