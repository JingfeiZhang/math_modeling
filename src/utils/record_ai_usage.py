#!/usr/bin/env python3
"""Append one internal AI-usage event for an initialized CUMCM project.

This is an agent-facing helper, not a submission artifact. It keeps raw AI use
inside the project output tree so humans only need to confirm adoption and
verification instead of maintaining JSONL by hand.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
from datetime import datetime
from pathlib import Path
from typing import TextIO


def load_yaml(path: Path) -> dict:
    import yaml

    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return value if isinstance(value, dict) else {}


def lock_file(handle: TextIO) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(0, os.SEEK_END)
        # Lock one byte at the current end. Ensure the file contains at least
        # one byte so msvcrt.locking has a concrete range to lock.
        if handle.tell() == 0:
            handle.write("\n")
            handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


def unlock_file(handle: TextIO) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def append_event(path: Path, event: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8", newline="\n") as handle:
        lock_file(handle)
        try:
            handle.seek(0, os.SEEK_END)
            handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            unlock_file(handle)


def build_event(args: argparse.Namespace) -> dict:
    timestamp = args.timestamp or datetime.now().astimezone().isoformat(timespec="seconds")
    event_id = args.event_id or f"AI-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(3)}"
    event = {
        "event_id": event_id,
        "timestamp": timestamp,
        "tool": args.tool,
        "model_version": args.model_version,
        "purpose": args.purpose,
        "stage": args.stage,
        "prompt_summary": args.prompt_summary,
        "output_used": args.output_used,
        "human_verification": args.human_verification,
    }
    if args.disclosure_stage:
        event["disclosure_stage"] = args.disclosure_stage
    if args.ai_role:
        event["ai_role"] = args.ai_role
    if args.human_modification:
        event["human_modification"] = args.human_modification
    if args.reviewer:
        event["reviewer"] = args.reviewer
    if args.evidence_locator:
        event["evidence_locator"] = args.evidence_locator
    if args.question:
        event["question"] = args.question
    return event


def validate_event(event: dict, policy: dict) -> list[str]:
    required = list(policy.get("log", {}).get("required_fields", []))
    problems: list[str] = []
    for field in required:
        value = event.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            problems.append(field)
    allowed_roles = set(policy.get("log", {}).get("ai_roles", []))
    roles = event.get("ai_role", [])
    if isinstance(roles, str):
        roles = [roles]
    invalid_roles = [role for role in roles if allowed_roles and role not in allowed_roles]
    if invalid_roles:
        problems.append("invalid ai_role: " + ", ".join(invalid_roles))
    return problems


def ensure_used_state(root: Path, policy: dict) -> Path:
    state_cfg = policy.get("state", {})
    state_path = (root / state_cfg.get("path", "output/ai_usage_state.yaml")).resolve()
    if state_path.is_file():
        state = load_yaml(state_path)
        mode = str(state.get("mode") or "").strip().lower()
        if mode == "not_used":
            raise SystemExit("AI usage cannot be recorded because the project state is explicitly not_used")
        if mode != "used":
            raise SystemExit(f"invalid AI usage state in {state_path}: {mode or '<empty>'}")
        return state_path

    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("mode: used\n", encoding="utf-8")
    return state_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--tool", required=True)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--purpose", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--prompt-summary", required=True)
    parser.add_argument("--output-used", required=True)
    parser.add_argument("--human-verification", required=True)
    parser.add_argument("--disclosure-stage", choices=("problem_analysis", "modeling_implementation", "experiment_validation", "paper_writing"))
    parser.add_argument("--ai-role", action="append", default=[])
    parser.add_argument("--human-modification")
    parser.add_argument("--reviewer")
    parser.add_argument("--evidence-locator")
    parser.add_argument("--question")
    parser.add_argument("--event-id")
    parser.add_argument("--timestamp")
    args = parser.parse_args()

    root = args.root.resolve()
    policy = load_yaml(args.policy.resolve())
    contest = load_yaml(root / "contest.yaml")
    if str(contest.get("problem", "TBD")).strip().upper() == "TBD":
        raise SystemExit("refusing to create AI-use state in a precontest TBD project")

    event = build_event(args)
    problems = validate_event(event, policy)
    if problems:
        raise SystemExit("invalid AI usage event: " + "; ".join(problems))

    state_path = ensure_used_state(root, policy)
    target = (root / policy.get("log", {}).get("path", "output/ai/raw_usage.jsonl")).resolve()
    append_event(target, event)
    print(
        json.dumps(
            {"status": "RECORDED", "event_id": event["event_id"], "path": str(target), "state": str(state_path)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
