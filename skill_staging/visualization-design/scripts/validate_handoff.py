#!/usr/bin/env python3
"""Validate V5 visualization handoff shape and current project provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
    from jsonschema import Draft202012Validator
except ImportError as exc:  # pragma: no cover - depends on the invoking Python environment
    raise SystemExit(
        "visualization-design validation requires PyYAML and jsonschema; "
        "run this script with the workspace Python environment"
    ) from exc


SCHEMAS = {
    "manifest": "figure_data_manifest.schema.json",
    "intent": "visual_intent.schema.json",
    "brief": "figure_brief.schema.json",
}


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project_path(root: Path, value: str, label: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        raise ValueError(f"{label} must be project-relative: {value}")
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} escapes the project root: {value}") from exc
    return resolved


def validate_schema(root: Path, kind: str, payload: dict[str, Any]) -> list[str]:
    schema_path = root / "config" / "schemas" / SCHEMAS[kind]
    if not schema_path.is_file():
        return [f"schema is missing: {schema_path}"]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(payload),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    return [
        f"{kind}.{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
        for error in errors
    ]


def current_file(root: Path, value: Any, expected_hash: Any, label: str) -> tuple[Path | None, list[str]]:
    if not isinstance(value, str) or not value:
        return None, [f"{label} path is missing"]
    try:
        path = project_path(root, value, label)
    except ValueError as exc:
        return None, [str(exc)]
    if not path.is_file():
        return None, [f"{label} does not exist: {value}"]
    if expected_hash != sha256(path):
        return None, [f"{label} hash is missing or stale: {value}"]
    return path, []


def manifest_issues(root: Path, payload: dict[str, Any]) -> list[str]:
    issues = validate_schema(root, "manifest", payload)
    _, source_issues = current_file(
        root,
        payload.get("source_run_manifest"),
        payload.get("source_run_manifest_sha256"),
        "source run manifest",
    )
    issues.extend(source_issues)
    for index, item in enumerate(payload.get("source_artifacts", [])):
        if not isinstance(item, dict):
            continue
        _, artifact_issues = current_file(
            root,
            item.get("path"),
            item.get("sha256"),
            f"source_artifacts[{index}]",
        )
        issues.extend(artifact_issues)
    return issues


def intent_issues(root: Path, payload: dict[str, Any], manifest_path: Path) -> list[str]:
    issues = validate_schema(root, "intent", payload)
    current, source_issues = current_file(
        root,
        payload.get("source_data_manifest"),
        payload.get("source_data_manifest_sha256"),
        "intent source data manifest",
    )
    issues.extend(source_issues)
    if current is not None and current.resolve() != manifest_path.resolve():
        issues.append("intent references a different data manifest")
    return issues


def brief_issues(root: Path, payload: dict[str, Any], manifest_path: Path, intent_path: Path) -> list[str]:
    issues = validate_schema(root, "brief", payload)
    for value, expected_hash, label, expected_path in (
        (payload.get("source_data_manifest"), payload.get("source_data_manifest_sha256"), "brief source data manifest", manifest_path),
        (payload.get("visual_intent"), payload.get("visual_intent_sha256"), "brief visual intent", intent_path),
        (payload.get("source_script"), payload.get("source_script_sha256"), "brief source script", None),
    ):
        current, source_issues = current_file(root, value, expected_hash, label)
        issues.extend(source_issues)
        if current is not None and expected_path is not None and current.resolve() != expected_path.resolve():
            issues.append(f"{label} references a different file")
    for index, item in enumerate(payload.get("data_integrity", {}).get("source_hashes", [])):
        if not isinstance(item, dict):
            continue
        _, source_issues = current_file(root, item.get("path"), item.get("sha256"), f"data_integrity.source_hashes[{index}]")
        issues.extend(source_issues)
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--intent", type=Path)
    parser.add_argument("--brief", type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args()
    root = args.root.resolve()
    problems: list[str] = []
    try:
        manifest_path = args.manifest.resolve()
        manifest = load_yaml(manifest_path)
        problems.extend(manifest_issues(root, manifest))
        intent_path: Path | None = None
        if args.intent:
            intent_path = args.intent.resolve()
            problems.extend(intent_issues(root, load_yaml(intent_path), manifest_path))
        if args.brief:
            if intent_path is None:
                problems.append("--brief requires --intent")
            else:
                problems.extend(brief_issues(root, load_yaml(args.brief.resolve()), manifest_path, intent_path))
    except (OSError, ValueError, yaml.YAMLError, json.JSONDecodeError) as exc:
        problems.append(str(exc))
    if problems:
        for problem in problems:
            print(f"ERROR: {problem}")
        return 1
    print("OK: V5 visualization handoff shape and provenance checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
