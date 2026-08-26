#!/usr/bin/env python3
"""Audit a CUMCM paper and its submission-side reports."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError:
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def pdf_pages(path: Path) -> list[str]:
    """Return one entry per physical page; blank pages must not disappear."""

    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required for the submission PDF audit") from exc
    reader = PdfReader(str(path))
    return [page.extract_text() or "" for page in reader.pages]


def pdf_metadata(path: Path) -> tuple[list[dict], str | None]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        return [], f"pypdf is required for PDF metadata audit: {exc}"
    try:
        metadata = PdfReader(str(path)).metadata or {}
    except Exception as exc:
        return [], f"could not parse PDF metadata: {exc}"
    findings: list[dict] = []
    author = str(metadata.get("/Author", "") or metadata.get("author", "")).strip()
    if author:
        findings.append({"code": "PDF_AUTHOR_METADATA", "message": f"submission PDF contains author metadata: {author[:120]}"})
    patterns = (
        (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), "email"),
        (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "phone"),
        (re.compile(r"(?i)[A-Z]:[\\/]Users[\\/][^\s\"']+"), "absolute-user-path"),
        (re.compile(r"(?:姓名|学号|队号|指导教师|联系方式|邮箱|作者单位|学校|学院)\s*[:：=]", re.I), "identity-label"),
    )
    for key, value in metadata.items():
        text = str(value or "")
        for pattern, label in patterns:
            if pattern.search(text):
                findings.append({"code": "PDF_IDENTITY_METADATA", "message": f"metadata {key} contains {label}"})
    return findings, None


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def audit(root: Path, strict: bool = False, skip_package: bool = False) -> dict:
    config = load_yaml(root / "contest.yaml")
    format_cfg = config.get("format", {})
    submission_cfg = config.get("submission", {})
    searchable_policy = str(
        submission_cfg.get("searchable_pdf_policy", format_cfg.get("searchable_pdf_policy", "required"))
    ).strip().lower()
    page_limit_policy = str(format_cfg.get("paper_body_limit_policy", "required")).strip().lower()
    recommended_body_pages = int(format_cfg.get("paper_body_max_pages", 30))
    hard_body_pages = int(format_cfg.get("paper_body_hard_max_pages", recommended_body_pages))
    hard_total_raw = format_cfg.get("paper_total_hard_max_pages")
    hard_total_pages = int(hard_total_raw) if hard_total_raw not in (None, "", False) else None
    paper_path = root / config.get("paths", {}).get("paper_pdf", "output/submission.pdf")
    support_path = root / config.get("paths", {}).get("support_zip", "output/supporting.zip")
    result: dict = {
        "schema_version": 4,
        "paper": str(paper_path),
        "strict": strict,
        "checks": [],
        "warnings": [],
        "linked_reports": {},
        "status": "PASS",
    }

    def add(name: str, passed: bool, detail: str) -> None:
        result["checks"].append({"name": name, "passed": passed, "detail": detail})
        if not passed:
            result["status"] = "FAIL"

    def warn(name: str, detail: str) -> None:
        result["checks"].append({"name": name, "passed": True, "severity": "warning", "detail": detail})
        result["warnings"].append({"name": name, "detail": detail})

    exists = paper_path.exists()
    add("paper_exists", exists, str(paper_path))
    if exists:
        max_bytes = int(format_cfg.get("paper_max_mb", 20) * 1024 * 1024)
        add("paper_size", paper_path.stat().st_size <= max_bytes, f"{paper_path.stat().st_size} <= {max_bytes} bytes")
        try:
            page_texts = pdf_pages(paper_path)
            parser_ok = True
            parser_detail = "pypdf parsed the PDF"
        except RuntimeError as exc:
            page_texts = []
            parser_ok = False
            parser_detail = str(exc)
        add("pdf_parser", parser_ok, parser_detail)
        text = "\n".join(page_texts)
        pages = len(page_texts) if page_texts else None
        if pages is not None:
            if hard_total_pages is not None and pages > hard_total_pages:
                add("paper_total_pages", False, f"{pages} > configured total hard limit {hard_total_pages}")
            else:
                detail = f"{pages} physical pages"
                if hard_total_pages is None:
                    detail += "; official appendix page count is unlimited and body pages are checked separately"
                add("paper_total_pages", True, detail)
        else:
            add("paper_page_count", False, "No PDF page-count parser is available")

        min_chars = int(format_cfg.get("searchable_pdf_min_chars_per_page", 20))
        min_ratio = float(format_cfg.get("searchable_pdf_min_page_ratio", 0.8))
        searchable_pages = sum(len(re.sub(r"\s+", "", page)) >= min_chars for page in page_texts)
        ratio = searchable_pages / pages if pages else 0.0
        result["searchable_pdf"] = {
            "pages": pages or 0,
            "searchable_pages": searchable_pages,
            "ratio": round(ratio, 4),
            "min_chars_per_page": min_chars,
            "required_ratio": min_ratio,
            "policy": searchable_policy,
        }
        if pages is None or searchable_pages == 0:
            if searchable_policy == "recommended":
                warn("searchable_pdf", "PDF has no searchable text layer; this is an internal recommendation, not a 2026 format requirement")
            else:
                add("searchable_pdf", False, "PDF has no searchable text layer")
        elif ratio < min_ratio:
            detail = f"searchable page ratio {ratio:.3f} is below {min_ratio:.3f}"
            if searchable_policy == "recommended":
                warn("searchable_pdf", detail + "; policy is an internal recommendation")
            else:
                add("searchable_pdf", not strict, detail)
        else:
            add("searchable_pdf", True, f"searchable page ratio {ratio:.3f}")

        first_page = page_texts[0] if page_texts else ""
        abstract_found = bool(re.search(r"摘要|Abstract", first_page, re.IGNORECASE))
        add("abstract_on_first_page", abstract_found, "electronic paper first page must be the abstract page")

        commitment_hits = [token for token in ("承诺书", "编号专用页") if token in first_page]
        add(
            "electronic_excludes_commitment_and_number_pages",
            not commitment_hits,
            "forbidden first-page markers: " + ", ".join(commitment_hits),
        )

        forbidden = ["学校名称", "学院名称", "参赛者姓名", "队号", "学号", "赛区名称"]
        hits = [token for token in forbidden if token in text]
        identity_patterns = (
            re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
            re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
            re.compile(r"(?i)[A-Z]:[\\/]Users[\\/][^\s\"']+"),
        )
        hits.extend(pattern.pattern for pattern in identity_patterns if pattern.search(text))
        add("anonymous_identity", not hits, "forbidden tokens: " + ", ".join(hits))
        metadata_findings, metadata_error = pdf_metadata(paper_path)
        add("pdf_metadata_parser", metadata_error is None, metadata_error or "PDF metadata parsed")
        for finding in metadata_findings:
            add(finding["code"], False, finding["message"])

        log_path = root / "paper" / "main.log"
        body_match = re.search(r"MATHMODEL:CUMCM_BODY_PAGES=(\d+)", log_path.read_text(encoding="utf-8", errors="ignore")) if log_path.is_file() else None
        body_pages = int(body_match.group(1)) if body_match else None
        result["body_pages"] = body_pages
        if body_pages is None:
            add("body_page_budget", False, "main.log does not contain the CUMCM body-page marker")
        elif body_pages > hard_body_pages:
            add("body_page_budget", False, f"{body_pages} > hard limit {hard_body_pages}")
        elif body_pages > recommended_body_pages and page_limit_policy == "recommended":
            warn("body_page_budget", f"{body_pages} pages exceed the recommended {recommended_body_pages}-page budget but remain within the {hard_body_pages}-page hard cap")
        else:
            add("body_page_budget", body_pages <= recommended_body_pages, str(body_pages))

    if support_path.exists() and not skip_package:
        max_support = int(format_cfg.get("support_max_mb", 20) * 1024 * 1024)
        add("support_size", support_path.stat().st_size <= max_support, f"{support_path.stat().st_size} <= {max_support} bytes")
    elif not skip_package:
        add("support_exists", False, "supporting archive has not been created")

    for name, relative in (
        ("latex", "output/paper_audit.json"),
        ("figures", "output/figure_audit.json"),
        ("figure_style", "output/figure_style_audit.json"),
        ("pdf_visual", "output/pdf_visual_audit.json"),
        ("code_parity", "output/code_parity_audit.json"),
        ("ai_usage", "output/ai_usage_audit.json"),
        ("package", "output/package_audit.json"),
    ):
        if skip_package and name == "package":
            continue
        path = root / relative
        if not path.is_file():
            add(f"{name}_report_exists", False, f"missing linked audit report: {path}")
            continue
        try:
            report = load_json(path)
        except json.JSONDecodeError as exc:
            add(f"{name}_report_valid", False, f"invalid JSON report: {exc}")
            continue
        result["linked_reports"][name] = {"path": str(path), "passed": report.get("passed", report.get("status") == "PASS")}
        if report.get("passed") is False or report.get("status") == "FAIL":
            add(f"{name}_report_passed", False, f"linked audit report contains errors: {path}")
        else:
            add(f"{name}_report_passed", True, f"linked audit report passed: {path}")

    report_path = root / config.get("paths", {}).get("audit_json", "output/audit.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a modeling contest submission package.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--skip-package", action="store_true")
    args = parser.parse_args()
    result = audit(args.root.resolve(), strict=args.strict, skip_package=args.skip_package)
    return 1 if args.strict and result["status"] != "PASS" else 0


if __name__ == "__main__":
    sys.exit(main())
