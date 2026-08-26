#!/usr/bin/env python3
"""Validate V7.2 visualization handoff shape and local project provenance."""

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
WORKSPACE_SCHEMA_FILES = tuple(SCHEMAS.values())


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


def is_workspace_root(path: Path) -> bool:
    return (path / "config" / "projects.json").is_file() and all(
        (path / "config" / "schemas" / name).is_file() for name in WORKSPACE_SCHEMA_FILES
    )


def discover_workspace_root(explicit: Path | None, manifest: Path) -> Path:
    if explicit is not None:
        root = explicit.resolve()
        if not is_workspace_root(root):
            raise ValueError(
                f"--root is not a modeling workspace with config/projects.json and visualization schemas: {root}"
            )
        return root
    starts = (manifest.resolve().parent, Path.cwd().resolve())
    seen: set[Path] = set()
    for start in starts:
        for candidate in (start, *start.parents):
            if candidate in seen:
                continue
            seen.add(candidate)
            if is_workspace_root(candidate):
                return candidate
    raise ValueError(
        "modeling workspace root was not found from the current directory or manifest path; pass --root explicitly"
    )


def resolve_input_path(value: Path, *bases: Path) -> Path:
    if value.is_absolute():
        return value.resolve()
    candidates = [(base / value).resolve() for base in bases]
    return next((candidate for candidate in candidates if candidate.exists()), candidates[0])


def discover_project_root(workspace_root: Path, manifest_path: Path) -> Path:
    for candidate in (manifest_path.parent, *manifest_path.parent.parents):
        try:
            candidate.relative_to(workspace_root)
        except ValueError:
            break
        if (candidate / "project.yaml").is_file():
            return candidate
        if candidate == workspace_root:
            break
    return workspace_root


def validate_schema(workspace_root: Path, kind: str, payload: dict[str, Any]) -> list[str]:
    schema_path = workspace_root / "config" / "schemas" / SCHEMAS[kind]
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


def manifest_issues(workspace_root: Path, project_root: Path, payload: dict[str, Any]) -> list[str]:
    issues = validate_schema(workspace_root, "manifest", payload)
    _, source_issues = current_file(
        project_root,
        payload.get("source_run_manifest"),
        payload.get("source_run_manifest_sha256"),
        "source run manifest",
    )
    issues.extend(source_issues)
    for index, item in enumerate(payload.get("source_artifacts", [])):
        if not isinstance(item, dict):
            continue
        _, artifact_issues = current_file(
            project_root,
            item.get("path"),
            item.get("sha256"),
            f"source_artifacts[{index}]",
        )
        issues.extend(artifact_issues)
    return issues


def intent_issues(
    workspace_root: Path,
    project_root: Path,
    payload: dict[str, Any],
    manifest_path: Path,
) -> list[str]:
    issues = validate_schema(workspace_root, "intent", payload)
    current, source_issues = current_file(
        project_root,
        payload.get("source_data_manifest"),
        payload.get("source_data_manifest_sha256"),
        "intent source data manifest",
    )
    issues.extend(source_issues)
    if current is not None and current.resolve() != manifest_path.resolve():
        issues.append("intent references a different data manifest")
    return issues


def brief_issues(
    workspace_root: Path,
    project_root: Path,
    payload: dict[str, Any],
    manifest_path: Path,
    intent_path: Path,
) -> list[str]:
    issues = validate_schema(workspace_root, "brief", payload)
    for value, expected_hash, label, expected_path in (
        (payload.get("source_data_manifest"), payload.get("source_data_manifest_sha256"), "brief source data manifest", manifest_path),
        (payload.get("visual_intent"), payload.get("visual_intent_sha256"), "brief visual intent", intent_path),
        (payload.get("source_script"), payload.get("source_script_sha256"), "brief source script", None),
    ):
        current, source_issues = current_file(project_root, value, expected_hash, label)
        issues.extend(source_issues)
        if current is not None and expected_path is not None and current.resolve() != expected_path.resolve():
            issues.append(f"{label} references a different file")
    for index, item in enumerate(payload.get("data_integrity", {}).get("source_hashes", [])):
        if not isinstance(item, dict):
            continue
        _, source_issues = current_file(
            project_root,
            item.get("path"),
            item.get("sha256"),
            f"data_integrity.source_hashes[{index}]",
        )
        issues.extend(source_issues)
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--intent", type=Path)
    parser.add_argument("--brief", type=Path)
    parser.add_argument(
        "--root",
        type=Path,
        help="workspace root containing config/projects.json and config/schemas (auto-discovered when omitted)",
    )
    args = parser.parse_args()
    problems: list[str] = []
    try:
        manifest_hint = args.manifest if args.manifest.is_absolute() else Path.cwd() / args.manifest
        workspace_root = discover_workspace_root(args.root, manifest_hint)
        manifest_path = resolve_input_path(args.manifest, Path.cwd(), workspace_root)
        project_root = discover_project_root(workspace_root, manifest_path)
        manifest = load_yaml(manifest_path)
        problems.extend(manifest_issues(workspace_root, project_root, manifest))
        intent_path: Path | None = None
        if args.intent:
            intent_path = resolve_input_path(args.intent, Path.cwd(), project_root, workspace_root)
            problems.extend(
                intent_issues(workspace_root, project_root, load_yaml(intent_path), manifest_path)
            )
        if args.brief:
            if intent_path is None:
                problems.append("--brief requires --intent")
            else:
                brief_path = resolve_input_path(args.brief, Path.cwd(), project_root, workspace_root)
                problems.extend(
                    brief_issues(
                        workspace_root,
                        project_root,
                        load_yaml(brief_path),
                        manifest_path,
                        intent_path,
                    )
                )
    except (OSError, ValueError, yaml.YAMLError, json.JSONDecodeError) as exc:
        problems.append(str(exc))
    if problems:
        for problem in problems:
            print(f"ERROR: {problem}")
        return 1
    print("OK: V7.2 visualization handoff shape and local provenance checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
