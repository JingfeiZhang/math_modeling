#!/usr/bin/env python3
"""Audit CUMCM 2026 AI-use evidence, concise disclosure, and support packaging."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from pathlib import Path


STAGE_TITLES = {
    "problem_analysis": "问题分析与思路拓展",
    "modeling_implementation": "模型与算法实现辅助",
    "experiment_validation": "实验检查与结果分析",
    "paper_writing": "论文表达辅助",
}


def load_yaml(path: Path) -> dict:
    import yaml

    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return value if isinstance(value, dict) else {}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def has_value(entry: dict, field: str) -> bool:
    if field not in entry or entry[field] is None:
        return False
    if isinstance(entry[field], str):
        return bool(entry[field].strip())
    return True


def find_log(root: Path, cfg: dict) -> Path | None:
    for value in [cfg.get("path")] + list(cfg.get("legacy_paths", [])):
        if not value:
            continue
        path = (root / str(value)).resolve()
        if path.is_file():
            return path
    return None


def read_log(path: Path | None, finding, required: list[str]) -> list[dict]:
    entries: list[dict] = []
    if path is None:
        return entries
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            finding("AI_LOG_JSON", f"line {line_number}: {exc}")
            continue
        if not isinstance(entry, dict):
            finding("AI_LOG_JSON", f"line {line_number}: entry must be an object")
            continue
        missing = [field for field in required if not has_value(entry, field)]
        if missing:
            finding("AI_LOG_FIELDS", f"line {line_number} missing fields: {missing}")
        verification = entry.get("human_verification")
        if isinstance(verification, dict):
            verification_ok = bool(verification)
        else:
            verification_ok = str(verification).strip().lower() not in {
                "", "false", "none", "null", "unverified", "pending", "未验证", "待验证"
            }
        if not verification_ok:
            finding("AI_LOG_UNVERIFIED_OUTPUT", f"line {line_number} does not record completed human verification")
        entries.append(entry)
    return entries


def archive_member_bytes(path: Path, member_name: str) -> tuple[bytes | None, list[str]]:
    if not path.is_file() or path.suffix.lower() != ".zip":
        return None, []
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            matches = [name for name in names if name == member_name or Path(name).name == Path(member_name).name]
            if not matches:
                return None, names
            return archive.read(matches[0]), names
    except zipfile.BadZipFile:
        return None, []


def inspect_pdf_bytes(data: bytes) -> tuple[bool, int, str]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        return len(reader.pages) > 0, len(reader.pages), text
    except Exception:
        return False, 0, ""


def audit(root: Path, policy_path: Path, *, skip_support: bool = False) -> dict:
    contest = load_yaml(root / "contest.yaml")
    formal = str(contest.get("problem", "TBD")).strip().upper() != "TBD"
    errors: list[dict] = []
    warnings: list[dict] = []

    def finding(code: str, message: str, *, blocking: bool = True) -> None:
        target = errors if formal and blocking else warnings
        target.append({"code": code, "message": message})

    if not policy_path.is_file():
        finding("AI_POLICY_MISSING", str(policy_path))
        policy = {}
    else:
        policy = load_yaml(policy_path)

    source = policy.get("source", {})
    workspace_root = policy_path.parent.parent
    source_verified = source.get("status") == "verified" and str(source.get("url", "")).startswith("https://")
    snapshot_rel = str(source.get("pinned_snapshot") or "")
    snapshot_path = (workspace_root / snapshot_rel).resolve() if snapshot_rel else None
    expected_snapshot_hash = str(source.get("pinned_snapshot_sha256") or "").lower()
    snapshot_verified = False
    if snapshot_path and snapshot_path.is_file() and len(expected_snapshot_hash) == 64:
        snapshot_verified = sha256_file(snapshot_path) == expected_snapshot_hash
    if not source_verified:
        finding("AI_POLICY_SOURCE_UNVERIFIED", "official 2026 AI-use source is not marked verified")
    if not snapshot_verified:
        finding("AI_POLICY_SNAPSHOT_MISMATCH", "pinned 2026 AI-use rule snapshot is missing or its SHA-256 does not match")

    state_cfg = policy.get("state", {})
    state_path = (root / state_cfg.get("path", "output/ai_usage_state.yaml")).resolve()
    state = load_yaml(state_path) if state_path.is_file() else {}
    mode = str(state.get("mode", "")).strip().lower()
    allowed_modes = {str(value).lower() for value in state_cfg.get("allowed_modes", ["used", "not_used"])}
    if formal and state_cfg.get("required_in_formal_project", True) and not state_path.is_file():
        finding("AI_STATE_MISSING", f"explicit AI-use state is required: {state_path}")
    if formal and mode not in allowed_modes:
        finding("AI_STATE_INVALID", f"AI-use state mode must be one of {sorted(allowed_modes)}")

    log_cfg = policy.get("log", {})
    log_path = find_log(root, log_cfg)
    required = list(log_cfg.get("required_fields", []))
    entries = read_log(log_path, finding, required)
    if formal and mode == "used" and log_cfg.get("required_when_used", True) and not entries:
        finding("AI_LOG_REQUIRED", "AI use is declared, but no internal AI usage events were recorded")
    if formal and mode == "not_used" and entries:
        finding("AI_STATE_CONTRADICTS_LOG", "AI state says not_used but the internal AI usage log contains entries")

    aggregation_cfg = policy.get("aggregation", {})
    summary_path = (root / aggregation_cfg.get("output", "output/ai/stage_summary.yaml")).resolve()
    summary = load_yaml(summary_path) if summary_path.is_file() else {}
    material_stages: list[str] = []
    if formal and mode == "used" and aggregation_cfg:
        if not summary_path.is_file():
            finding("AI_STAGE_SUMMARY_MISSING", f"stage-level disclosure summary is required: {summary_path}")
        else:
            if summary.get("mode") != "used":
                finding("AI_STAGE_SUMMARY_MODE", "stage summary does not match declared AI mode")
            if not summary.get("tools"):
                finding("AI_STAGE_SUMMARY_TOOLS", "stage summary has no AI tool/model entries")
            unclassified = list(summary.get("unclassified_events", []))
            if unclassified and aggregation_cfg.get("unclassified_events_block_release", True):
                finding("AI_UNCLASSIFIED_EVENTS", f"AI events were not assigned to disclosure stages: {unclassified}")
            for stage_key, stage in summary.get("stages", {}).items():
                if isinstance(stage, dict) and stage.get("used"):
                    material_stages.append(stage_key)
            if not material_stages:
                finding("AI_STAGE_SUMMARY_EMPTY", "AI use is declared but no material disclosure stage is marked used")

    disclosure = policy.get("disclosure", {})
    generated_locator = str(disclosure.get("generated_statement_locator") or "paper/generated/ai_usage_statement.tex")
    statement_path = (root / generated_locator).resolve()
    statement_text = statement_path.read_text(encoding="utf-8") if statement_path.is_file() else ""
    if formal and disclosure.get("required") is True and not statement_path.is_file():
        finding("AI_DISCLOSURE_MISSING", f"generated AI declaration is required: {statement_path}")
    if formal and statement_text:
        if mode == "not_used":
            required_text = str(disclosure.get("no_ai_text") or "")
            if required_text and required_text not in statement_text:
                finding("AI_DISCLOSURE_MODE_MISMATCH", "paper AI declaration does not match not_used state")
        elif mode == "used":
            markers = [str(value) for value in disclosure.get("used_ai_required_markers", [])]
            missing_markers = [marker for marker in markers if marker and marker not in statement_text]
            if missing_markers:
                finding("AI_DISCLOSURE_MODE_MISMATCH", f"paper AI declaration is missing markers: {missing_markers}")

    details_cfg = policy.get("details", {})
    details_name = str(details_cfg.get("filename") or "AI工具使用详情.pdf")
    generated_tex_path = (root / details_cfg.get("generated_tex", "output/ai/generated/AI工具使用详情.tex")).resolve()
    package_source = (root / details_cfg.get("package_source", f"src/submission/manifest/{details_name}")).resolve()
    generated_tex = generated_tex_path.read_text(encoding="utf-8") if generated_tex_path.is_file() else ""
    details_present = False
    details_valid_pdf = False
    details_pages = 0
    support_names: list[str] = []

    if formal and mode == "used" and details_cfg.get("required_when_used", True):
        if not generated_tex_path.is_file():
            finding("AI_DETAILS_SOURCE_MISSING", f"generated AI details source is required: {generated_tex_path}")
        else:
            required_markers = [str(value) for value in details_cfg.get("required_section_markers", [])]
            missing = [marker for marker in required_markers if marker and marker not in generated_tex]
            if missing:
                finding("AI_DETAILS_CONTENT_MISSING", f"AI details source is missing required sections: {missing}")
            for stage_key in material_stages:
                title = STAGE_TITLES.get(stage_key)
                if title and title not in generated_tex:
                    finding("AI_DISCLOSURE_MATERIAL_OMISSION", f"material AI-use stage is absent from details: {title}")

        if skip_support:
            if package_source.is_file():
                data = package_source.read_bytes()
                details_present = True
                details_valid_pdf, details_pages, _ = inspect_pdf_bytes(data)
            else:
                finding("AI_DETAILS_PDF_MISSING", f"pre-package AI details PDF is required: {package_source}")
        else:
            support_path = (root / details_cfg.get("support_archive", "output/supporting.zip")).resolve()
            member_name = str(details_cfg.get("package_member") or f"manifest/{details_name}")
            data, support_names = archive_member_bytes(support_path, member_name)
            if data is None:
                finding("AI_DETAILS_PDF_MISSING", f"support archive must contain {member_name}")
            else:
                details_present = True
                details_valid_pdf, details_pages, _ = inspect_pdf_bytes(data)
                if package_source.is_file() and sha256_bytes(data) != sha256_file(package_source):
                    finding("AI_DETAILS_PACKAGE_DRIFT", "AI details PDF in support archive differs from the prepared package source")

        if details_present and not details_valid_pdf:
            finding("AI_DETAILS_PDF_INVALID", f"{details_name} is not a readable non-empty PDF")
        target_pages = details_cfg.get("target_pages")
        if details_valid_pdf and target_pages and details_pages > int(target_pages):
            finding("AI_DETAILS_PDF_LONG", f"AI details PDF is {details_pages} pages; concise target is {target_pages} page(s)", blocking=False)

    if formal and policy.get("release", {}).get("raw_internal_log_must_not_be_packaged", True) and not skip_support:
        forbidden_basenames = {
            Path(str(value)).name
            for value in [log_cfg.get("path")] + list(log_cfg.get("legacy_paths", []))
            if value
        }
        leaked = [name for name in support_names if Path(name).name in forbidden_basenames]
        if leaked:
            finding("AI_RAW_LOG_PACKAGED", f"internal AI log must not be submitted: {leaked}")

    return {
        "schema_version": 3,
        "formal": formal,
        "mode": "strict" if formal else "precontest-advisory",
        "declared_ai_mode": mode or None,
        "passed": not errors,
        "blocking": bool(errors),
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "entries": len(entries),
            "log_path": str(log_path) if log_path else None,
            "policy_source_verified": source_verified,
            "policy_snapshot_verified": snapshot_verified,
            "stage_summary_present": summary_path.is_file(),
            "material_stage_count": len(material_stages),
            "details_pdf_present": details_present,
            "details_pdf_valid": details_valid_pdf,
            "details_pdf_pages": details_pages,
            "support_check_skipped": skip_support,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--policy", type=Path, default=Path("config/ai_usage_policy.yaml"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skip-support", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    policy_path = args.policy.resolve() if args.policy.is_absolute() else (Path.cwd() / args.policy).resolve()
    result = audit(root, policy_path, skip_support=args.skip_support)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
