#!/usr/bin/env python3
"""Audit CUMCM 2026 AI-use disclosure, logs, and supporting evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


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


def has_value(entry: dict, field: str) -> bool:
    if field not in entry or entry[field] is None:
        return False
    if isinstance(entry[field], str):
        return bool(entry[field].strip())
    return True


def archive_contains(path: Path, filename: str) -> bool:
    if not path.is_file() or path.suffix.lower() != ".zip":
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            return any(Path(name).name == filename for name in archive.namelist())
    except zipfile.BadZipFile:
        return False


def audit(root: Path, policy_path: Path) -> dict:
    contest = load_yaml(root / "contest.yaml")
    formal = str(contest.get("problem", "TBD")).upper() != "TBD"
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
    log_path = (root / log_cfg.get("path", "output/ai_usage_log.jsonl")).resolve()
    required = list(log_cfg.get("required_fields", []))
    entries: list[dict] = []
    if log_path.is_file():
        for line_number, line in enumerate(log_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                finding("AI_LOG_JSON", f"line {line_number}: {exc}")
                continue
            missing = [field for field in required if not has_value(entry, field)]
            if missing:
                finding("AI_LOG_FIELDS", f"line {line_number} missing fields: {missing}")
            verification = entry.get("human_verification")
            if str(verification).strip().lower() in {"", "false", "none", "null", "unverified", "pending"}:
                finding("AI_LOG_UNVERIFIED_OUTPUT", f"line {line_number} does not record completed human verification")
            entries.append(entry)

    if formal and mode == "used" and log_cfg.get("required_when_used", True) and not entries:
        finding("AI_LOG_REQUIRED", "AI use is declared, but no AI usage log entries were recorded")
    if formal and mode == "not_used" and entries:
        finding("AI_STATE_CONTRADICTS_LOG", "AI state says not_used but AI usage log contains entries")

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
    support_path = (root / details_cfg.get("support_archive", "output/supporting.zip")).resolve()
    details_name = str(details_cfg.get("filename") or "AI工具使用详情.pdf")
    details_present = archive_contains(support_path, details_name)
    if formal and mode == "used" and details_cfg.get("required_when_used", True) and not details_present:
        finding("AI_DETAILS_PDF_MISSING", f"support archive must contain {details_name}")

    return {
        "schema_version": 2,
        "formal": formal,
        "mode": "strict" if formal else "precontest-advisory",
        "declared_ai_mode": mode or None,
        "passed": not errors,
        "blocking": bool(errors),
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "entries": len(entries),
            "policy_source_verified": source_verified,
            "policy_snapshot_verified": snapshot_verified,
            "details_pdf_present": details_present,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--policy", type=Path, default=Path("config/ai_usage_policy.yaml"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    policy_path = args.policy.resolve() if args.policy.is_absolute() else (Path.cwd() / args.policy).resolve()
    result = audit(root, policy_path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
