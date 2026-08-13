#!/usr/bin/env python3
"""Create and inspect isolated competition projects under the shared workbench."""

from __future__ import annotations

import argparse
import json
import re
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


PROJECT_ID_RE = re.compile(r"[A-Za-z0-9._-]+")
MUTABLE_ROOTS = (
    "problems",
    "src",
    "experiments",
    "results",
    "paper",
    "output",
    "submission",
    "state",
    "sprints",
    "logs",
)


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return value if isinstance(value, dict) else {}


def dump_yaml(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")


def load_registry(hub: Path) -> dict[str, Any]:
    path = hub / "config" / "projects.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("projects"), list):
        raise ValueError("config/projects.json must contain a projects list")
    return value


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def profile_value(profiles: dict[str, Any], profile_id: str, stack: tuple[str, ...] = ()) -> dict[str, Any]:
    if profile_id in stack:
        raise ValueError("competition profile inheritance cycle: " + " -> ".join((*stack, profile_id)))
    raw = profiles.get(profile_id)
    if not isinstance(raw, dict):
        raise KeyError(f"competition profile does not exist: {profile_id}")
    parent = raw.get("extends")
    own = {key: value for key, value in raw.items() if key != "extends"}
    return deep_merge(profile_value(profiles, str(parent), (*stack, profile_id)), own) if parent else deepcopy(own)


def registered_projects(hub: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    registry = load_registry(hub)
    rows: dict[str, dict[str, Any]] = {}
    roots: set[str] = set()
    projects_root = (hub / "projects").resolve()
    for raw in registry["projects"]:
        if not isinstance(raw, dict):
            raise ValueError("every project registry entry must be an object")
        project_id = str(raw.get("id") or "")
        if not PROJECT_ID_RE.fullmatch(project_id):
            raise ValueError(f"invalid project id: {project_id!r}")
        root = (hub / str(raw.get("root") or "")).resolve()
        try:
            root.relative_to(projects_root)
        except ValueError as exc:
            raise ValueError(f"project root must stay under projects/: {project_id}") from exc
        key = str(root).lower()
        if key in roots:
            raise ValueError(f"project roots must be unique: {root}")
        if project_id in rows:
            raise ValueError(f"duplicate project id: {project_id}")
        roots.add(key)
        rows[project_id] = {**raw, "resolved_root": root}
    return registry, rows


def resolve_project(hub: Path, project_id: str) -> dict[str, Any]:
    _, projects = registered_projects(hub)
    if project_id not in projects:
        raise KeyError(f"unknown project: {project_id}")
    return projects[project_id]


def contest_payload(hub: Path, project: dict[str, Any]) -> dict[str, Any]:
    profiles_document = load_yaml(hub / "config" / "competition_profiles.yaml")
    profiles = profiles_document.get("profiles", {})
    profile = profile_value(profiles, str(project["profile"]))
    contest = deep_merge(profile, project.get("overrides", {}))
    contest.update({"schema_version": 1, "project_id": project["id"], "profile_id": project["profile"], "year": project["year"], "problem": "TBD"})
    contest.setdefault("rules_sources", list(contest.get("rules", {}).get("sources", [])))
    contest.setdefault("paths", {})
    contest["paths"].update({
        "paper_tex": "paper/main.tex",
        "paper_pdf": "output/submission.pdf",
        "support_zip": "output/supporting.zip",
        "audit_json": "output/audit.json",
    })
    contest.setdefault("workflow", {})
    contest["workflow"].update({
        "workflow_config": "config/workflow.yaml",
        "workflow_status": "output/workflow_status.json",
        "claims_pattern": "results/{problem}/claims.json",
        "shared_workspace_root": "../../..",
        "python_environment": "auto",
        "python_environment_policy": "existing_first",
        "python_environment_fallback": "math-modeling",
        "matlab_root": "D:/MATLAB/R2026a",
        "default_random_seed": 20260801,
        "pdf_environment": "math-modeling",
        "pdf_environment_policy": "explicit_prefix_only",
    })
    contest.setdefault("submission", {})
    contest["submission"].setdefault("release_manifest", "output/release/release_manifest.json")
    contest["submission"].setdefault("release_checklist", "output/release/submission_checklist.yaml")
    contest["submission"].setdefault("publish_dir", "submission")
    return contest


def scaffold(hub: Path, project_id: str, force: bool = False) -> dict[str, Any]:
    project = resolve_project(hub, project_id)
    root = Path(project["resolved_root"])
    root.mkdir(parents=True, exist_ok=True)
    for relative in MUTABLE_ROOTS:
        (root / relative).mkdir(parents=True, exist_ok=True)
    (root / "config").mkdir(parents=True, exist_ok=True)

    initialized = any((
        (root / "state" / "decision_log.json").is_file(),
        (root / "paper" / "main.tex").is_file(),
        (root / "paper" / "figure_contracts.yaml").is_file(),
        any((root / "results").glob("*/claims.json")),
        any((root / "experiments").glob("*/Q*/formal/*/run_manifest.json")),
    ))
    overwrite = force and not initialized

    contest_path = root / "contest.yaml"
    if overwrite or not contest_path.exists():
        dump_yaml(contest_path, contest_payload(hub, project))
    project_meta = {
        "schema_version": 1,
        "workflow_contract_version": 7,
        "prompt_policy_version": 1,
        "prompt_mode": "progress-first",
        "paper_prompt_mode": "external",
        "project_id": project_id,
        "profile_id": project["profile"],
        "competition": contest_payload(hub, project)["competition"],
        "year": project["year"],
        "shared_workspace_root": "../../..",
        "mutable_roots": list(MUTABLE_ROOTS),
        "state_owner": "mathmodel-skill",
        "created_for_reuse": True,
    }
    project_path = root / "project.yaml"
    if not project_path.exists() or overwrite:
        dump_yaml(project_path, project_meta)
    local_workflow = {
        "schema_version": 1,
        "project_id": project_id,
        "shared_config": "../../../config/workflow.yaml",
        "isolation": {"mutable_roots": list(MUTABLE_ROOTS), "cross_project_writes": "forbidden"},
        "visualization_design": {"strict_handoff": True},
        "literature_guided_modeling": {"strict_g5": True},
    }
    workflow_path = root / "config" / "workflow.yaml"
    if overwrite or not workflow_path.exists():
        dump_yaml(workflow_path, local_workflow)
    return project_status(hub, project_id)


def project_status(hub: Path, project_id: str) -> dict[str, Any]:
    project = resolve_project(hub, project_id)
    root = Path(project["resolved_root"])
    contest_path = root / "contest.yaml"
    contest = load_yaml(contest_path) if contest_path.is_file() else {}
    state = root / "state" / "decision_log.json"
    contract = root / "paper" / "figure_contracts.yaml"
    problem = str(contest.get("problem", "TBD"))
    return {
        "schema_version": 1,
        "project_id": project_id,
        "profile_id": project["profile"],
        "root": root.relative_to(hub).as_posix(),
        "exists": root.is_dir(),
        "phase": "ACTIVE" if state.is_file() else "PRECONTEST",
        "problem": problem,
        "state_exists": state.is_file(),
        "formal_figure_contract_exists": contract.is_file(),
        "rules_status": contest.get("rules", {}).get("status"),
    }


def preflight(hub: Path, project_id: str) -> dict[str, Any]:
    status = project_status(hub, project_id)
    root = hub / status["root"]
    project = load_yaml(root / "project.yaml") if (root / "project.yaml").is_file() else {}
    checks = [
        {"name": "project_yaml", "passed": (root / "project.yaml").is_file()},
        {"name": "contest_yaml", "passed": (root / "contest.yaml").is_file()},
        {"name": "local_workflow_config", "passed": (root / "config" / "workflow.yaml").is_file()},
        {"name": "shared_workflow_config", "passed": (hub / "config" / "workflow.yaml").is_file()},
        {"name": "shared_figure_style", "passed": (hub / "config" / "figure_style.yaml").is_file()},
        {"name": "shared_environment", "passed": (hub / "environment.yml").is_file()},
    ]
    if int(project.get("workflow_contract_version", 0) or 0) >= 7:
        checks.extend([
            {"name": "shared_prompt_policy", "passed": (hub / "config" / "prompt_policy.yaml").is_file()},
            {"name": "prompt_policy_schema", "passed": (hub / "config" / "schemas" / "prompt_policy.schema.json").is_file()},
            {"name": "prompt_packet_schema", "passed": (hub / "config" / "schemas" / "prompt_packet.schema.json").is_file()},
            {"name": "prompt_receipt_schema", "passed": (hub / "config" / "schemas" / "prompt_receipt.schema.json").is_file()},
            {"name": "prompt_stage_fragments", "passed": all((hub / "templates" / "prompts" / "stages" / f"{stage}.yaml").is_file() for stage in ("P0", "P1", "P2", "P3a", "P3b", "P4", "P5", "P6"))},
            {"name": "prompt_role_fragments", "passed": all((hub / "templates" / "prompts" / "roles" / f"{role}.yaml").is_file() for role in ("orchestrator", "solver", "literature", "visualization", "paper", "studio_release", "reviewer"))},
            {"name": "cumcm_author_prompt_card", "passed": (hub / "templates" / "prompts" / "paper" / "cumcm-2026.yaml").is_file()},
        ])
    if status["problem"].upper() == "TBD":
        checks.extend([
            {"name": "precontest_state_absent", "passed": not status["state_exists"]},
            {"name": "precontest_formal_figure_contract_absent", "passed": not status["formal_figure_contract_exists"]},
        ])
    warnings: list[dict[str, str]] = []
    if status.get("rules_status") in {"pending_official_verification", "verify_current_year"}:
        warnings.append({"code": "RULES_PENDING", "message": "current-year official rules must be verified before submission"})
    elif str(status.get("rules_status") or "").startswith("inherited_"):
        warnings.append({"code": "RULES_INHERITED", "message": "this project currently inherits the CUMCM rule profile; explicit event rules override it"})
    return {
        **status,
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
        "warnings": warnings,
        "generated_at_utc": datetime.now(UTC).isoformat(),
    }


def list_projects(hub: Path) -> dict[str, Any]:
    registry, projects = registered_projects(hub)
    return {
        "schema_version": registry.get("schema_version", 1),
        "default_project": registry.get("default_project"),
        "legacy_root_enabled": bool(registry.get("legacy_root_enabled")),
        "projects": [project_status(hub, project_id) for project_id in sorted(projects)],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--action", choices=("list", "scaffold", "status", "preflight"), required=True)
    parser.add_argument("--project")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    hub = args.root.resolve()
    try:
        if args.action == "list":
            result = list_projects(hub)
        else:
            if not args.project:
                raise ValueError(f"{args.action} requires --project")
            if args.action == "scaffold":
                result = scaffold(hub, args.project, args.force)
            elif args.action == "status":
                result = project_status(hub, args.project)
            else:
                result = preflight(hub, args.project)
    except Exception as exc:
        result = {"schema_version": 1, "passed": False, "status": "ERROR", "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("passed", True) is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
