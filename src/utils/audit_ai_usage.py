#!/usr/bin/env python3
"""Audit the versioned AI-use policy source and competition usage log."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def load_yaml(path: Path) -> dict:
    import yaml

    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return value if isinstance(value, dict) else {}


def audit(root: Path, policy_path: Path) -> dict:
    contest = load_yaml(root / "contest.yaml")
    formal = str(contest.get("problem", "TBD")).upper() != "TBD"
    # AI-use bookkeeping is advisory in this workspace. Keep every finding
    # visible, but do not let it block modeling, auditing, packaging, or release.
    errors: list[dict] = []
    warnings: list[dict] = []

    def warn(code: str, message: str) -> None:
        warnings.append({"code": code, "message": message})

    if not policy_path.is_file():
        warn("AI_POLICY_MISSING", str(policy_path))
        policy = {}
    else:
        policy = load_yaml(policy_path)
    source = policy.get("source", {})
    verified_source = (
        source.get("status") == "verified"
        and isinstance(source.get("url"), str)
        and source.get("url", "").startswith("https://")
        and bool(re.fullmatch(r"[0-9a-f]{64}", str(source.get("sha256", ""))))
    )
    if not verified_source:
        warn("AI_POLICY_SOURCE_PENDING", "the separate 2026 AI-use regulation has not been pinned and verified")

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
                warn("AI_LOG_JSON", f"line {line_number}: {exc}")
                continue
            missing = [field for field in required if not str(entry.get(field, "")).strip()]
            if missing:
                warn("AI_LOG_FIELDS", f"line {line_number} missing fields: {missing}")
            entries.append(entry)
    elif formal:
        warn("AI_LOG_MISSING", str(log_path))
    else:
        warn("AI_LOG_PRECONTEST", "AI-use log will be initialized only after a real problem is supplied")

    disclosure = policy.get("disclosure", {})
    if formal and disclosure.get("required") is True:
        locator = str(disclosure.get("paper_locator") or "")
        target = (root / locator).resolve() if locator else None
        if not target or not target.is_file():
            warn("AI_DISCLOSURE_MISSING", "required paper disclosure locator is absent")
    return {
        "schema_version": 1,
        "formal": formal,
        "mode": "advisory",
        "passed": True,
        "blocking": False,
        "errors": errors,
        "warnings": warnings,
        "metrics": {"entries": len(entries), "policy_source_verified": verified_source},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--policy", type=Path, default=Path("config/ai_usage_policy.yaml"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    result = audit(root, (root / args.policy).resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
