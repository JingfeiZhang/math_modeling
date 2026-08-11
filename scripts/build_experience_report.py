from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from .build_corpus_index import main as build_corpus_index
except ImportError:
    from build_corpus_index import main as build_corpus_index


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "corpus" / "index.csv"
CARDS = ROOT / "corpus" / "cards"
INTRO = ROOT / "corpus" / "experience_report_intro.md"
OUTPUT = ROOT / "corpus" / "experience_report.md"
GENERATED_OUTPUT = ROOT / "corpus" / "experience_report.generated.md"
PROGRAM_STATUS = ROOT / "corpus" / "program_status.json"
PRIVATE_SYMBOLS = str.maketrans(
    {
        "\uf061": "alpha",
        "\uf0e5": "sum",
        "\uf044": "Delta",
        "\uf02d": "-",
        "\uf071": "theta",
        "\uf03d": "=",
    }
)
PRIVATE_USE = re.compile(r"[\ue000-\uf8ff]")
MATH_ALPHANUMERIC = re.compile(r"[\U0001D400-\U0001D7FF]")
ROMAN_NUMERALS = str.maketrans({"Ⅰ": "I", "Ⅱ": "II", "Ⅲ": "III", "Ⅳ": "IV", "Ⅴ": "V", "Ⅵ": "VI", "Ⅶ": "VII", "Ⅷ": "VIII", "Ⅸ": "IX", "Ⅹ": "X", "Ⅺ": "XI", "Ⅻ": "XII"})


def normalize_report_text(value: Any) -> str:
    normalized = MATH_ALPHANUMERIC.sub(
        lambda match: unicodedata.normalize("NFKC", match.group(0)), str(value)
    ).translate(PRIVATE_SYMBOLS).translate(ROMAN_NUMERALS)
    return PRIVATE_USE.sub("[OCR符号]", normalized)


def _load_card(relative: str) -> dict[str, Any]:
    path = CARDS / relative
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _items(card: dict[str, Any], *keys: str) -> list[Any]:
    for key in keys:
        value = card.get(key)
        if isinstance(value, list) and value:
            return value
    return []


def _compact(items: list[Any], limit: int = 4) -> str:
    values: list[str] = []
    for item in items[:limit]:
        if isinstance(item, dict):
            text = (
                item.get("observation")
                or item.get("description")
                or item.get("detail")
                or item.get("model")
                or item.get("purpose")
                or item.get("rule")
                or item.get("type")
            )
        else:
            text = item
        if text:
            values.append(normalize_report_text(text))
    return "；".join(values)


def main() -> None:
    build_corpus_index()
    rows = list(csv.DictReader(INDEX.open(encoding="utf-8-sig", newline=""))) if INDEX.exists() else []
    competition_counts = Counter(row.get("competition", "unknown") for row in rows)
    access_counts = Counter(row.get("access", "unknown") for row in rows)
    review_counts = Counter(row.get("review_status", "unreviewed") or "unreviewed" for row in rows)
    authenticity_counts = Counter(row.get("authenticity_level", "legacy/ungraded") or "legacy/ungraded" for row in rows)
    code_pairs = sum(int(row.get("code_link_count", "0") or 0) for row in rows)
    try:
        program = json.loads(PROGRAM_STATUS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        program = {}
    intro = INTRO.read_text(encoding="utf-8").rstrip() if INTRO.exists() else "# 数学建模优秀论文证据报告"
    lines = [
        intro,
        "",
        "## 语料概况",
        "",
        f"- 记录数：{len(rows)}",
        f"- 赛事分布：{dict(competition_counts)}",
        f"- 访问级别：{dict(access_counts)}",
        f"- 阅读状态：{dict(review_counts)}",
        f"- 真实性级别：{dict(authenticity_counts)}",
        f"- 已记录代码链接：{code_pairs}",
        "",
    ]
    if program:
        lines.extend(
            [
                "## 42 篇深读计划",
                "",
                f"- 内容证据级深读：{program.get('content_evidence_deep_reads', 0)}/42",
                f"- 奖项已核验深读：{program.get('award_verified_deep_reads', 0)}",
                f"- 真实性分布：{program.get('authenticity_counts', {})}",
                f"- 可信论文-代码配对：{program.get('validated_paper_code_pairs', 0)}/20",
                f"- 可运行现代配方：{program.get('runnable_recipe_count', 0)}/12",
                "- C 级内容深读只用于中性的模型、验证、写作、排版和图件经验，不作为获奖身份依据。",
                "",
            ]
        )
    lines.extend(
        [
        "## 已阅读卡片",
        "",
        ]
    )
    reviewed = [
        row
        for row in rows
        if row.get("review_status") in {"evidence_reviewed", "evidence_deep_read", "content_extracted"}
    ]
    for row in reviewed:
        card = _load_card(row.get("card_file", ""))
        lines.append(f"### {row.get('competition')} {row.get('year')} {row.get('problem')} {row.get('title')}")
        lines.append("")
        lines.append(
            f"- 状态：{row.get('review_status')}；真实性：{row.get('authenticity_level') or '旧卡未分级'}；"
            f"页码证据：{row.get('evidence_page_count') or '0'}；代码链接：{row.get('code_link_count') or '0'}"
        )
        lines.append(f"- 来源：{row.get('source_url')}")
        abstract = _compact(_items(card, "abstract_structure"))
        models = _compact(_items(card, "model_chain", "models"))
        validation = _compact(_items(card, "validation_chain", "validation_structure", "validation"))
        figures = _compact(_items(card, "figures", "figure_strategy"))
        rules = _compact(_items(card, "transferable_rules", "transferable_patterns"))
        risks = _compact(_items(card, "risks"))
        for label, value in (
            ("摘要", abstract),
            ("模型链", models),
            ("验证链", validation),
            ("图表", figures),
            ("可迁移规则", rules),
            ("风险", risks),
        ):
            if value:
                lines.append(f"- {label}：{value}")
        lines.append("")
    lines.extend(
        [
            "## 固定分析维度",
            "",
            "问题抽象、假设质量、模型与问题对应关系、baseline、敏感性分析、误差与稳健性、图表可读性、摘要信息密度、结论边界、代码可复现性。",
            "",
            "## 使用原则",
            "",
            "经验用于迁移写作、验证和图件组织方法，不复制论文文本、数据或结论。A/B 级卡片仍不等于数学正确性认证；通过内容门禁的 C 级卡片可用于中性的内容与版式经验，但不能形成获奖论文经验；未通过内容门禁的 C 级与全部 D 级记录只用于发现和索引。",
        ]
    )
    content = normalize_report_text("\n".join(lines)) + "\n"
    OUTPUT.write_text(content, encoding="utf-8")
    GENERATED_OUTPUT.write_text(content, encoding="utf-8")
    print(json.dumps({"output": "corpus/experience_report.md", "records": len(rows)}, ensure_ascii=True))


if __name__ == "__main__":
    main()
