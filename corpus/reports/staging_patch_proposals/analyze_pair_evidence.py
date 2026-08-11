from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from pypdf import PdfReader


METHODS: dict[str, tuple[re.Pattern[str], tuple[str, ...]]] = {
    "genetic_algorithm": (re.compile(r"\b(ga|mutation|cross|select|rands?)\s*\(?", re.I), ("遗传算法", "genetic algorithm")),
    "nonlinear_optimization": (re.compile(r"\b(fmincon|fminsearch|optimset|optimoptions)\s*\(", re.I), ("非线性规划", "非线性优化", "fmincon")),
    "linear_programming": (re.compile(r"\b(linprog|intlinprog|bintprog)\s*\(", re.I), ("线性规划", "整数规划", "linprog")),
    "regression": (re.compile(r"\b(regress|stepwise|polyfit|glmfit)\s*\(", re.I), ("回归", "拟合", "regression")),
    "clustering": (re.compile(r"\b(kmeans|linkage|cluster|pdist)\s*\(", re.I), ("聚类", "cluster")),
    "graph_shortest_path": (re.compile(r"\b(floyd|graphshortestpath|shortestpath)\s*\(?", re.I), ("floyd", "最短路", "最短路径")),
    "cellular_automata": (re.compile(r"\b(automata|cellular)\b", re.I), ("元胞自动机", "cellular automata")),
    "ode_simulation": (re.compile(r"\b(ode45|ode23|ode15s)\s*\(", re.I), ("微分方程", "ode45", "动力学")),
    "image_processing": (re.compile(r"\b(imread|imwrite|rgb2gray|im2bw|edge|bwlabel)\s*\(", re.I), ("图像处理", "灰度", "二值化", "边缘")),
    "interpolation": (re.compile(r"\b(interp1|interp2|spline|griddata)\s*\(", re.I), ("插值", "spline", "interpolation")),
    "statistical_test": (re.compile(r"\b(ttest|ttest2|anova1|vartest|kstest)\s*\(", re.I), ("检验", "方差分析", "t检验")),
}

RISK_RULES = {
    "destructive_file_operation": re.compile(r"\b(delete|rmdir|movefile|copyfile)\s*\(", re.I),
    "process_execution": re.compile(r"(^|[;\s])(system|dos|unix)\s*\(|^\s*!", re.I | re.M),
    "dynamic_execution": re.compile(r"\b(eval|evalin|feval|str2func|run)\s*\(", re.I),
    "network_access": re.compile(r"\b(webread|webwrite|urlread|urlwrite|ftp|tcpclient|udpport)\s*\(", re.I),
    "gui_or_manual_input": re.compile(r"\b(uigetfile|uiputfile|inputdlg|questdlg|ginput)\s*\(", re.I),
    "session_mutation": re.compile(r"\b(clear\s+all|close\s+all|restoredefaultpath|addpath\s*\(\s*genpath)\b", re.I),
    "absolute_windows_path": re.compile(r"['\"][A-Za-z]:[\\/]"),
}

PLOT_CALL = re.compile(r"\b(plot|scatter|bar|hist|histogram|surf|mesh|contour|imagesc|imshow|boxplot)\s*\(", re.I)
ASSIGNMENT = re.compile(r"(?<![<>=~])\b([A-Za-z][A-Za-z0-9_]*)\s*=(?!=)")
STRING_LITERAL = re.compile(r"['\"]([^'\"\r\n]{3,80})['\"]")
COMMON_VARIABLES = {
    "ans", "data", "figure", "length", "max", "mean", "min", "num", "ones", "size", "sum", "zeros",
}


def read_source(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    best: tuple[int, str, str] | None = None
    for encoding in ("utf-8", "gb18030", "big5", "latin-1"):
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        score = text.count("\ufffd")
        candidate = (score, encoding, text)
        if best is None or candidate[0] < best[0]:
            best = candidate
    if best is None:
        return raw.decode("utf-8", errors="replace"), "utf-8-replacement"
    return best[2], best[1]


def normalized(text: str) -> str:
    return re.sub(r"\s+", "", text).casefold()


def page_hits(pages: list[str], needle: str) -> list[int]:
    target = normalized(needle)
    if len(target) < 3:
        return []
    return [index for index, page in enumerate(pages, start=1) if target in normalized(page)]


def object_path(corpus_root: Path, record: dict[str, Any]) -> Path:
    return corpus_root / str(record["object"])


def identity_tokens(candidate: dict[str, Any]) -> list[str]:
    values: set[str] = set()
    for value in (candidate["prefix"], candidate["pdf"]["path"]):
        for token in re.split(r"[/_.\-\s]+", str(value)):
            token = token.strip()
            if re.fullmatch(r"[A-Fa-f]?\d{3,}", token):
                values.add(token)
            elif len(token) >= 3 and re.fullmatch(r"[\u3400-\u9fff]{3,}", token):
                if token not in {"国赛题目", "数学建模", "源程序"}:
                    values.add(token)
    return sorted(values, key=lambda value: (-len(value), value))


def code_lines(text: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("%", 1)[0].strip()
        compact = normalized(line)
        if 16 <= len(compact) <= 180 and not re.fullmatch(r"(clear|clc|closeall|holdon|holdoff);?", compact):
            lines.append((number, line))
    return lines


def risk_findings(text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for name, pattern in RISK_RULES.items():
        for match in pattern.finditer(text):
            findings.append(
                {
                    "rule": name,
                    "line": text.count("\n", 0, match.start()) + 1,
                    "match": match.group(0)[:120],
                }
            )
    return findings


def analyze_code(pages: list[str], source: dict[str, Any], path: Path) -> dict[str, Any]:
    text, encoding = read_source(path)
    basename = PurePosixPath(source["path"]).stem
    snippet_hits: list[dict[str, Any]] = []
    for line, snippet in code_lines(text):
        hits = page_hits(pages, snippet)
        if hits:
            snippet_hits.append({"code_line": line, "pdf_pages": hits[:4], "snippet": snippet[:140]})
        if len(snippet_hits) >= 6:
            break

    variables = sorted(
        {
            value
            for value in ASSIGNMENT.findall(text)
            if len(value) >= 3 and value.casefold() not in COMMON_VARIABLES
        },
        key=lambda value: (-len(value), value.casefold()),
    )
    variable_hits = [
        {"variable": value, "pdf_pages": hits[:4]}
        for value in variables[:80]
        if (hits := page_hits(pages, value))
    ][:12]

    labels = sorted({value.strip() for value in STRING_LITERAL.findall(text) if len(normalized(value)) >= 4})
    label_hits = [
        {"label": value, "pdf_pages": hits[:4]}
        for value in labels
        if (hits := page_hits(pages, value))
    ][:8]

    method_hits: list[dict[str, Any]] = []
    for method, (code_pattern, paper_terms) in METHODS.items():
        code_matches = list(code_pattern.finditer(text))
        if not code_matches:
            continue
        locations: list[dict[str, Any]] = []
        for term in paper_terms:
            hits = page_hits(pages, term)
            if hits:
                locations.append({"term": term, "pdf_pages": hits[:6]})
        if locations:
            method_hits.append(
                {
                    "method": method,
                    "code_lines": sorted({text.count("\n", 0, match.start()) + 1 for match in code_matches})[:10],
                    "paper_terms": locations,
                }
            )

    name_pages = page_hits(pages, basename) if len(basename) >= 4 else []
    plot_lines = [text.count("\n", 0, match.start()) + 1 for match in PLOT_CALL.finditer(text)]
    figure_pages = sorted(
        {
            page
            for marker in ("图1", "图 1", "图2", "图 2", "Figure", "Fig.")
            for page in page_hits(pages, marker)
        }
    )
    findings = risk_findings(text)
    return {
        "source": source,
        "local_path": str(path),
        "encoding": encoding,
        "execution_status": "not_executed_static_review_only",
        "risk_findings": findings,
        "filename_match": {"name": basename, "pdf_pages": name_pages[:8]},
        "source_snippet_matches": snippet_hits,
        "variable_matches": variable_hits,
        "label_matches": label_hits,
        "method_matches": method_hits,
        "plot_calls": {"code_lines": plot_lines[:20], "paper_figure_pages": figure_pages[:20]},
    }


def relation(identity: list[dict[str, Any]], code: list[dict[str, Any]]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    snippet_count = sum(len(item["source_snippet_matches"]) for item in code)
    variable_count = sum(len(item["variable_matches"]) for item in code)
    method_count = sum(len(item["method_matches"]) for item in code)
    filename_count = sum(bool(item["filename_match"]["pdf_pages"]) for item in code)
    label_count = sum(len(item["label_matches"]) for item in code)
    identity_ok = bool(identity)
    if identity_ok:
        reasons.append("paper text contains a team/control/path identity token")
    if snippet_count:
        reasons.append(f"{snippet_count} literal source-line matches are visible in the PDF")
    if method_count:
        reasons.append(f"{method_count} code-method to paper-method matches")
    if variable_count:
        reasons.append(f"{variable_count} code variables occur in the PDF")
    if filename_count:
        reasons.append(f"{filename_count} MATLAB basenames occur in the PDF")
    if label_count:
        reasons.append(f"{label_count} code labels occur in the PDF")

    if identity_ok and snippet_count >= 2:
        return "exact", reasons
    if identity_ok and (snippet_count >= 1 or method_count >= 1) and (variable_count + filename_count + label_count >= 1):
        return "strong_partial", reasons
    if identity_ok and (method_count >= 1 or variable_count + filename_count + label_count >= 2):
        return "supported_partial", reasons
    return "candidate_only", reasons


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest["source"]["commit"] != "8783d0d822f89f98aa6182dd933cc2e9f3e2ddce":
        raise ValueError("unexpected source commit")
    args.output.mkdir(parents=True, exist_ok=True)
    selected_root = args.output / "selected_matlab"
    records: list[dict[str, Any]] = []
    page_cache: dict[str, list[str]] = {}

    for candidate in manifest["candidates"]:
        pdf = candidate["pdf"]
        pdf_path = object_path(args.corpus_root, pdf)
        pdf_sha = str(pdf["sha256"])
        if pdf_sha not in page_cache:
            reader = PdfReader(str(pdf_path))
            page_cache[pdf_sha] = [(page.extract_text() or "") for page in reader.pages]
        pages = page_cache[pdf_sha]

        identity = [
            {"token": token, "pdf_pages": hits[:8]}
            for token in identity_tokens(candidate)
            if (hits := page_hits(pages, token))
        ]
        code_records: list[dict[str, Any]] = []
        for source in candidate["matlab"]:
            source_path = object_path(args.corpus_root, source)
            destination = selected_root / candidate["candidate_id"] / f"{source['blob_sha']}-{PurePosixPath(source['path']).name}"
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                shutil.copy2(source_path, destination)
            code_records.append(analyze_code(pages, source, destination))

        relationship, reasons = relation(identity, code_records)
        records.append(
            {
                "candidate_id": candidate["candidate_id"],
                "source_prefix": candidate["prefix"],
                "paper": {**pdf, "page_count": len(pages)},
                "identity_matches": identity,
                "code": code_records,
                "auxiliary_data_metadata": candidate["data"],
                "relationship": relationship,
                "relationship_reasons": reasons,
                "trusted_pair": relationship in {"exact", "strong_partial", "supported_partial"},
                "limitations": [
                    "community mirror is not independent award evidence",
                    "upstream MATLAB was statically reviewed but not executed",
                    "only the two largest representative MATLAB files were downloaded per directory",
                ],
            }
        )

    by_pdf: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_pdf[record["paper"]["sha256"]].append(record)
    canonical: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []
    for pdf_sha, group in sorted(by_pdf.items()):
        chosen = sorted(group, key=lambda item: item["candidate_id"])[0]
        aliases = sorted(item["candidate_id"] for item in group if item is not chosen)
        if aliases:
            chosen["exact_duplicate_aliases"] = aliases
            duplicates.append({"paper_sha256": pdf_sha, "canonical": chosen["candidate_id"], "aliases": aliases})
        canonical.append(chosen)

    relationship_counts = {
        name: sum(item["relationship"] == name for item in canonical)
        for name in ("exact", "strong_partial", "supported_partial", "candidate_only")
    }
    report = {
        "schema_version": 1,
        "source": manifest["source"],
        "scope": {
            "directory": "2-1国赛题目+论文",
            "canonical_candidate_count": len(canonical),
            "trusted_pair_count": sum(item["trusted_pair"] for item in canonical),
            "relationship_counts": relationship_counts,
            "downloaded_representative_matlab_count": len(
                {item["source"]["blob_sha"] for record in canonical for item in record["code"]}
            ),
        },
        "policy": {
            "same_directory_is_not_sufficient": True,
            "upstream_execution": "forbidden_until_recipe modernization and isolation",
            "award_claim": "not assessed; repository location is not award evidence",
        },
        "exact_duplicates": duplicates,
        "pairs": sorted(canonical, key=lambda item: item["candidate_id"]),
    }
    json_path = args.output / "pair_evidence.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["scope"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
