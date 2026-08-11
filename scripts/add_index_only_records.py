from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
INDEX = CORPUS / "index.csv"
FIELDS = [
    "competition", "year", "problem", "paper_id", "title", "award_or_label", "access",
    "source_url", "resource_url", "card_file", "cached_pages", "reported_total_pages", "notes",
]

RECORDS = [
    ("MCM", 2025, "A", "mcm-2025-a-index", "MCM 2025 Problem A official results index", "https://www.contest.comap.com/undergraduate/contests/mcm/contests/2025/results/index.html", "https://www.contest.comap.com/undergraduate/contests/mcm/contests/2025/results/2025_MCM_Problem_A_Results.pdf"),
    ("MCM", 2025, "B", "mcm-2025-b-index", "MCM 2025 Problem B official results index", "https://www.contest.comap.com/undergraduate/contests/mcm/contests/2025/results/index.html", "https://www.contest.comap.com/undergraduate/contests/mcm/contests/2025/results/2025_MCM_Problem_B_Results.pdf"),
    ("MCM", 2025, "C", "mcm-2025-c-index", "MCM 2025 Problem C official results index", "https://www.contest.comap.com/undergraduate/contests/mcm/contests/2025/results/index.html", "https://www.contest.comap.com/undergraduate/contests/mcm/contests/2025/results/2025_MCM_Problem_C_Results.pdf"),
    ("ICM", 2025, "D", "icm-2025-d-index", "ICM 2025 Problem D official results index", "https://www.contest.comap.com/undergraduate/contests/mcm/contests/2025/results/index.html", "https://www.contest.comap.com/undergraduate/contests/mcm/contests/2025/results/2025_ICM_Problem_D_Results.pdf"),
    ("MathorCup", 2025, "index", "mathorcup-2025-index", "MathorCup 2025 official competition index", "https://www.mathorcup.org/", "https://www.saikr.com/vse/mathorcup/2025"),
    ("MathorCup", 2024, "index", "mathorcup-2024-index", "MathorCup 2024 official competition index", "https://www.mathorcup.org/", "https://www.saikr.com/vse/mathorcup/2024"),
    ("MathorCup", 2023, "index", "mathorcup-2023-index", "MathorCup 2023 official competition index", "https://www.mathorcup.org/", "https://www.saikr.com/vse/mathorcup/2023"),
    ("APMCM", 2025, "index", "apmcm-2025-index", "APMCM 2025 official competition index", "https://apmcm.org/", "https://www.saikr.com/vse/apmcm/2025"),
    ("APMCM", 2024, "index", "apmcm-2024-index", "APMCM 2024 official competition index", "https://apmcm.org/", "https://www.saikr.com/vse/apmcm/2024"),
    ("APMCM", 2023, "index", "apmcm-2023-index", "APMCM 2023 official competition index", "https://apmcm.org/", "https://www.saikr.com/vse/apmcm/2023"),
    ("HuashuCup", 2025, "index", "huashu-2025-index", "华数杯 2025 official competition index", "https://www.huashubei.com/", "https://www.huashubei.com/"),
]


def main() -> None:
    with INDEX.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_id = {row["paper_id"]: row for row in rows}
    cards = CORPUS / "cards"
    cards.mkdir(parents=True, exist_ok=True)
    for competition, year, problem, paper_id, title, source_url, resource_url in RECORDS:
        by_id.setdefault(
            paper_id,
            {
                "competition": competition,
                "year": str(year),
                "problem": problem,
                "paper_id": paper_id,
                "title": title,
                "award_or_label": "official_results_index",
                "access": "index_only_official_results",
                "source_url": source_url,
                "resource_url": resource_url,
                "card_file": f"{paper_id}.json",
                "cached_pages": "",
                "reported_total_pages": "",
                "notes": "仅作为官方赛事/结果索引；未读取论文全文，不用于版式或模型结论",
            },
        )
        card_path = cards / f"{paper_id}.json"
        if not card_path.exists():
            card_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "paper_id": paper_id,
                        "analysis_status": "official_results_index_only",
                        "competition": competition,
                        "year": year,
                        "problem": problem,
                        "title": title,
                        "source_url": source_url,
                        "resource_url": resource_url,
                        "models": [],
                        "validation": [],
                        "transferable_patterns": [],
                        "risks": ["没有公开全文证据，不推断模型、图表质量或获奖原因"],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
    for paper_id, row in by_id.items():
        if row.get("card_file"):
            continue
        row["card_file"] = f"{paper_id}.json"
        card_path = cards / f"{paper_id}.json"
        if not card_path.exists():
            card_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "paper_id": paper_id,
                        "analysis_status": "official_results_index_only",
                        "competition": row.get("competition"),
                        "year": row.get("year"),
                        "problem": row.get("problem"),
                        "title": row.get("title"),
                        "source_url": row.get("source_url"),
                        "resource_url": row.get("resource_url"),
                        "models": [],
                        "validation": [],
                        "transferable_patterns": [],
                        "risks": ["没有公开全文证据，不推断模型、图表质量或获奖原因"],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
    output = [by_id[key] for key in sorted(by_id)]
    with INDEX.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(output)
    print(json.dumps({"records": len(output), "index_only_added": len(RECORDS)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
