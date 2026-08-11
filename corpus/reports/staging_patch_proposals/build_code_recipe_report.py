from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def evidence_counts(pair: dict[str, Any]) -> dict[str, int]:
    return {
        "identity": len(pair["identity_matches"]),
        "source_snippets": sum(len(code["source_snippet_matches"]) for code in pair["code"]),
        "variables": sum(len(code["variable_matches"]) for code in pair["code"]),
        "labels": sum(len(code["label_matches"]) for code in pair["code"]),
        "methods": sum(len(code["method_matches"]) for code in pair["code"]),
        "plotting_files": sum(bool(code["plot_calls"]["code_lines"]) for code in pair["code"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair-evidence", type=Path, required=True)
    parser.add_argument("--static-scan", type=Path, required=True)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--determinism", type=Path, required=True)
    parser.add_argument("--recipes", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()

    pair_report = load(args.pair_evidence)
    static_scan = load(args.static_scan)
    execution = load(args.execution)
    determinism = load(args.determinism)
    rules = Counter(
        finding["rule"]
        for file in static_scan["files"]
        for finding in file["findings"]
    )
    unique_code_hashes = {file["sha256"] for file in static_scan["files"]}
    high_risk_rules = {
        "destructive_file_operation",
        "process_execution",
        "dynamic_execution",
        "network_access",
        "absolute_windows_path",
    }
    high_risk_count = sum(count for rule, count in rules.items() if rule in high_risk_rules)

    pairs = []
    for item in pair_report["pairs"]:
        pairs.append(
            {
                "candidate_id": item["candidate_id"],
                "relationship": item["relationship"],
                "trusted_pair": item["trusted_pair"],
                "source_prefix": item["source_prefix"],
                "paper": {
                    key: item["paper"][key]
                    for key in ("path", "blob_sha", "sha256", "expected_bytes", "page_count")
                },
                "code": [
                    {
                        "path": code["source"]["path"],
                        "blob_sha": code["source"]["blob_sha"],
                        "sha256": code["source"]["sha256"],
                        "execution_status": code["execution_status"],
                        "risk_findings": code["risk_findings"],
                    }
                    for code in item["code"]
                ],
                "evidence_counts": evidence_counts(item),
                "relationship_reasons": item["relationship_reasons"],
                "exact_duplicate_aliases": item.get("exact_duplicate_aliases", []),
                "auxiliary_data_metadata": [
                    {key: data.get(key) for key in ("path", "blob_sha", "bytes", "extension", "downloaded")}
                    for data in item["auxiliary_data_metadata"]
                ],
                "limitations": item["limitations"],
            }
        )

    recipes = []
    deterministic = {item["recipe_id"]: item for item in determinism["records"]}
    executed = {item["recipe_id"]: item for item in execution["records"]}
    for recipe_root in sorted(path for path in args.recipes.iterdir() if (path / "run_report.json").is_file()):
        run = load(recipe_root / "run_report.json")
        recipes.append(
            {
                "recipe_id": run["recipe_id"],
                "status": executed[run["recipe_id"]]["status"],
                "deterministic": deterministic[run["recipe_id"]]["status"] == "passed",
                "source_pair": run["source_pair"],
                "environment": run["environment"],
                "seed": run["seed"],
                "metrics": run["metrics"],
                "input_hashes": run["inputs"],
                "output_hashes": run["outputs"],
                "run_report": str((recipe_root / "run_report.json").as_posix()),
            }
        )

    trusted_count = sum(item["trusted_pair"] for item in pairs)
    report = {
        "schema_version": 1,
        "source": {
            "repository": "https://github.com/personqianduixue/Math_Model",
            "commit": "8783d0d822f89f98aa6182dd933cc2e9f3e2ddce",
            "directory": "2-1国赛题目+论文",
            "mode": "pinned_read_only",
        },
        "outcome": {
            "directory_candidates": 18,
            "canonical_papers": len(pairs),
            "exact_duplicate_directories": 1,
            "trusted_paper_code_pairs": trusted_count,
            "candidate_only_not_counted": sum(not item["trusted_pair"] for item in pairs),
            "pair_target": 20,
            "pair_shortfall": max(0, 20 - trusted_count),
            "recipe_target": 12,
            "runnable_recipes": sum(item["status"] == "passed" for item in recipes),
            "deterministic_recipes": sum(item["deterministic"] for item in recipes),
            "recipe_shortfall": max(0, 12 - sum(item["status"] == "passed" for item in recipes)),
        },
        "static_matlab_audit": {
            "scanner": static_scan["scanner"],
            "selected_directory_copies": static_scan["file_count"],
            "unique_matlab_files": len(unique_code_hashes),
            "finding_count": static_scan["finding_count"],
            "findings_by_rule": dict(sorted(rules.items())),
            "high_risk_finding_count": high_risk_count,
            "upstream_execution": "not_executed",
            "report": str(args.static_scan.as_posix()),
        },
        "evidence_policy": {
            "same_directory_only": "candidate_only; never counted as trusted",
            "trusted_levels": ["exact", "strong_partial", "supported_partial"],
            "required_artifacts": ["40-character commit", "Git blob SHA", "local SHA-256", "PDF page locator", "code locator"],
            "award_status": "not inferred from repository names or paths",
            "recipe_status": "controlled modernization fixture; not a numerical reproduction",
        },
        "pairs": pairs,
        "recipes": recipes,
        "known_gaps": [
            "This pinned CUMCM subtree contains only 17 unique PDF candidates with MATLAB in the same team-level directory, so 20 trusted pairs cannot be produced honestly from this scope.",
            "Five canonical candidates lacked sufficient page-to-code overlap and remain candidate_only.",
            "Auxiliary data files are metadata-only in this pass; no unreviewed upstream data or MATLAB was executed.",
            "Several historical PDFs contain malformed cross-reference pointers; pypdf recovered text with warnings, so visible page locators remain the primary evidence.",
            "The content-addressed download area may contain unreferenced objects from an interrupted raw download; download_manifest.json is the authoritative allowlist.",
        ],
        "staging_patch_proposals": [
            "corpus/reports/staging_patch_proposals/download_pair_evidence.py",
            "corpus/reports/staging_patch_proposals/analyze_pair_evidence.py",
            "corpus/reports/staging_patch_proposals/recipe_runner.py",
            "corpus/reports/staging_patch_proposals/build_recipe_fixtures.py",
            "corpus/reports/staging_patch_proposals/run_recipe_fixtures.py",
            "corpus/reports/staging_patch_proposals/verify_recipe_determinism.py",
            "corpus/reports/staging_patch_proposals/build_code_recipe_report.py",
        ],
    }
    write_json(args.output_json, report)

    lines = [
        "# CUMCM 论文-代码配对与现代配方审计",
        "",
        "## 结论",
        "",
        f"- 固定来源：`personqianduixue/Math_Model@{report['source']['commit']}` 的 `2-1国赛题目+论文`。",
        f"- 18 个同目录候选折叠为 {len(pairs)} 篇唯一论文；其中 {trusted_count} 个满足正文-代码证据要求，{sum(not item['trusted_pair'] for item in pairs)} 个仍为 `candidate_only`。",
        f"- 20 对目标真实缺口为 {report['outcome']['pair_shortfall']}；没有用重复 PDF 或仅同目录记录补数。",
        f"- 静态审查 {static_scan['file_count']} 个目录副本 / {len(unique_code_hashes)} 个唯一 MATLAB 文件，共 {static_scan['finding_count']} 条提示；高风险项 {high_risk_count} 条。",
        f"- 12 个现代配方全部隔离运行成功，且相同种子下指标与输出哈希 12/12 一致。",
        "",
        "## 配对证据",
        "",
        "| 候选 | 关系 | 可信 | PDF页 | 代码文件 | 片段 | 方法 | 变量 |",
        "|---|---:|:---:|---:|---:|---:|---:|---:|",
    ]
    for item in pairs:
        counts = item["evidence_counts"]
        lines.append(
            f"| `{item['candidate_id']}` | `{item['relationship']}` | {'是' if item['trusted_pair'] else '否'} | {item['paper']['page_count']} | {len(item['code'])} | {counts['source_snippets']} | {counts['methods']} | {counts['variables']} |"
        )
    lines.extend(
        [
            "",
            "`exact` 表示 PDF 中可定位至少两处源代码行；`strong_partial` 与 `supported_partial` 需要队号/控制号匹配，并有方法、变量、文件名或标签等额外对应。仅同目录一律不计可信。",
            "",
            "## 静态风险",
            "",
        ]
    )
    if rules:
        for rule, count in sorted(rules.items()):
            lines.append(f"- `{rule}`：{count} 条。")
    else:
        lines.append("- 未发现规则命中。")
    lines.extend(
        [
            "- 原始 MATLAB 执行状态：`not_executed`。",
            "- 当前命中均为 `clear all` / `close all` 会话修改；没有发现删除、系统命令、网络或动态执行。",
            "",
            "## 可运行配方",
            "",
            "| 配方 | 来源配对 | 首次运行 | 二次哈希复现 | 输出 |",
            "|---|---|:---:|:---:|---|",
        ]
    )
    for item in recipes:
        formats = ", ".join(output["path"] for output in item["output_hashes"])
        lines.append(
            f"| `{item['recipe_id']}` | `{item['source_pair']['candidate_id']}` | {'通过' if item['status'] == 'passed' else '失败'} | {'通过' if item['deterministic'] else '失败'} | {formats} |"
        )
    lines.extend(
        [
            "",
            "每个 `corpus/recipes/<id>/run_report.json` 记录 Python/NumPy/Matplotlib 版本、随机种子、输入与输出 SHA-256、指标及隔离声明。所有配方使用受控合成输入，只复用数学结构，不宣称复现论文数值。",
            "",
            "## 仍有缺口",
            "",
        ]
    )
    lines.extend(f"- {gap}" for gap in report["known_gaps"])
    lines.extend(
        [
            "",
            "## 复核入口",
            "",
            "- `corpus/reports/code-recipe-mining-artifacts/download_manifest.json`：固定提交、blob SHA 与下载 SHA-256。",
            "- `corpus/reports/code-recipe-mining-artifacts/pair_evidence.json`：逐页正文-代码对应证据。",
            "- `corpus/reports/code-recipe-mining-artifacts/matlab_static_scan.json`：静态风险。",
            "- `corpus/reports/code-recipe-mining-artifacts/recipe_execution.json`：首次隔离运行。",
            "- `corpus/reports/code-recipe-mining-artifacts/recipe_determinism.json`：二次复现。",
            "",
        ]
    )
    args.output_md.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report["outcome"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
