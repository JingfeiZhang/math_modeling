"""Validate the workspace prompt policy and compact prompt contracts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.workflow.prompt_policy import load_policy, validate_packet, validate_policy  # noqa: E402


def load_document(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    value = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    if not isinstance(value, dict):
        raise ValueError(f"prompt document must be an object: {path}")
    return value


def schema_issues(root: Path, schema_name: str, payload: dict) -> list[str]:
    schema = json.loads((root / "config" / "schemas" / schema_name).read_text(encoding="utf-8"))
    return [error.message for error in Draft202012Validator(schema).iter_errors(payload)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--packet", type=Path)
    args = parser.parse_args()
    root = args.workspace_root.resolve()
    try:
        policy = load_policy(root)
        issues = validate_policy(policy)
        issues.extend(schema_issues(root, "prompt_policy.schema.json", policy))
        if args.packet:
            packet = load_document(args.packet)
            issues.extend(validate_packet(packet))
            issues.extend(schema_issues(root, "prompt_packet.schema.json", packet))
        if issues:
            print(json.dumps({"passed": False, "errors": issues}, ensure_ascii=False, indent=2))
            return 1
        print(json.dumps({"passed": True, "stages": list(policy["stages"]), "roles": list(policy["roles"])}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"passed": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
