"""Configuration-driven prompt assembly for the modeling workflow.

This module is deliberately side-effect free.  The workflow command may persist
its returned packet and receipt under verification output, but this module never
creates competition state or edits evidence.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any


STAGES = ("P0", "P1", "P2", "P3a", "P3b", "P4", "P5", "P6")
ROLES = ("orchestrator", "solver", "literature", "visualization", "paper", "studio_release", "reviewer")
AUTHORITY_ORDER = (
    "official_rules", "project_contest_profile", "prompt_policy", "question_manifest",
    "formal_evidence", "candidate_evidence", "scratch_evidence", "external_literature",
)
RECEIPT_FIELDS = ("status", "objective", "conclusion", "evidence", "warnings", "next_action", "decision_request")
QUESTION_RE = re.compile(r"^Q[1-9][0-9]*$")
RECEIPT_STATUSES = ("PROGRESS", "PASS", "PASS_WITH_WARNINGS", "BLOCK_TRANSITION", "REOPEN_REQUIRED", "READY")
GATES = {"P0": "G0", "P1": "G0", "P2": "G1", "P3a": "G1", "P3b": "G2", "P4": "G4", "P5": "G5", "P6": "G6"}


def _load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _relative_ref(value: str) -> bool:
    path = Path(value)
    return not path.is_absolute() and not re.match(r"^[A-Za-z]:", value) and ".." not in path.parts


def load_policy(workspace_root: Path) -> dict[str, Any]:
    path = workspace_root / "config" / "prompt_policy.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"prompt policy is missing: {path}")
    policy = _load_yaml(path)
    issues = validate_policy(policy)
    schema_path = workspace_root / "config" / "schemas" / "prompt_policy.schema.json"
    if not schema_path.is_file():
        issues.append(f"prompt policy schema is missing: {schema_path}")
    else:
        from jsonschema import Draft202012Validator

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        issues.extend(error.message for error in Draft202012Validator(schema).iter_errors(policy))
    if issues:
        raise ValueError("invalid prompt policy: " + "; ".join(issues))
    return policy


def validate_policy(policy: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if policy.get("schema_version") != 1:
        issues.append("schema_version must be 1")
    if policy.get("locale") != "zh-CN" or policy.get("mode") != "progress-first":
        issues.append("locale/mode must be zh-CN/progress-first")
    if policy.get("authority_order") != list(AUTHORITY_ORDER):
        issues.append("authority_order must use the fixed V7 precedence")
    response = policy.get("response") if isinstance(policy.get("response"), dict) else {}
    if response.get("format") != "compact_receipt" or response.get("detail_mode") != "on_request":
        issues.append("response format/detail_mode are invalid")
    if response.get("required_fields") != list(RECEIPT_FIELDS):
        issues.append("response.required_fields must use the compact receipt contract")
    if list(policy.get("stages", {})) != list(STAGES):
        issues.append("stages must define P0,P1,P2,P3a,P3b,P4,P5,P6 in order")
    if set(policy.get("roles", {})) != set(ROLES):
        issues.append("roles must define exactly the seven V7 roles")
    stage_fields = {
        "gate", "objective", "allowed_actions", "blocking", "warning", "deferred",
        "stop_conditions", "escalation_conditions", "expected_artifacts",
    }
    for stage, rules in policy.get("stages", {}).items():
        if not isinstance(rules, dict):
            issues.append(f"{stage} must be an object")
            continue
        if set(rules) != stage_fields:
            issues.append(f"{stage} stage fields are incomplete or contain extras")
        if stage in GATES and rules.get("gate") != derive_gate(stage):
            issues.append(f"{stage} gate does not match the V7 mapping")
        blocking = set(rules.get("blocking", []))
        deferred = set(rules.get("deferred", []))
        overlap = sorted(blocking & deferred)
        if overlap:
            issues.append(f"{stage} blocking/deferred overlap: {overlap}")
    role_fields = {"objective", "read_scope", "write_scope", "inputs", "outputs", "protected", "stop_conditions", "decisions"}
    for role, rules in policy.get("roles", {}).items():
        if not isinstance(rules, dict) or set(rules) != role_fields:
            issues.append(f"{role} role fields are incomplete or contain extras")
    required_rules = {
        "warning_does_not_block_exploration",
        "blocking_only_blocks_current_transition",
        "deferred_not_run_before_owner_stage",
        "hash_drift_invalidates_affected_question_only",
        "no_recursive_reaudit",
    }
    if set(policy.get("rules", {})) != required_rules:
        issues.append("global rules are incomplete")
    return issues


def derive_gate(stage: str) -> str:
    if stage not in GATES:
        raise ValueError(f"unsupported prompt stage: {stage}")
    return GATES[stage]


def _required_yaml(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} is missing: {path}")
    value = _load_yaml(path)
    if not value:
        raise ValueError(f"{label} must be a non-empty object: {path}")
    return value


def _project_context(project_root: Path, project_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    project = _required_yaml(project_root / "project.yaml", "project contract")
    contest = _required_yaml(project_root / "contest.yaml", "contest profile")
    workflow = _required_yaml(project_root / "config" / "workflow.yaml", "project workflow config")
    for label, payload in (("project contract", project), ("contest profile", contest)):
        declared = str(payload.get("project_id") or "")
        if declared and declared != project_id:
            raise ValueError(f"{label} project_id mismatch: expected {project_id}, found {declared}")
    if str(project.get("project_id") or "") != project_id:
        raise ValueError("project contract must declare the selected project_id")
    return project, contest, workflow


def _question_context(project_root: Path, problem_id: str, question_id: str | None) -> tuple[str, list[str]]:
    if not question_id:
        return "", []
    if not QUESTION_RE.fullmatch(question_id):
        raise ValueError(f"question_id must match Q<number>: {question_id}")
    if not problem_id or problem_id.upper() == "TBD":
        raise ValueError(f"{question_id} requires a real problem in contest.yaml")
    path = project_root / "problems" / problem_id / "questions" / question_id / "question.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"question manifest is missing for {problem_id}/{question_id}")
    manifest = _load_yaml(path)
    if manifest.get("question_id") != question_id:
        raise ValueError(f"question manifest identity mismatch for {question_id}")
    if str(manifest.get("problem_id") or "") != problem_id:
        raise ValueError(f"question manifest problem mismatch for {problem_id}/{question_id}")
    return question_id, [path.relative_to(project_root).as_posix()]


def _expand_scope(scope: list[str], question_id: str, problem_id: str) -> list[str]:
    return [
        item.replace("{question}", question_id or "{question}").replace("{problem}", problem_id or "{problem}")
        for item in scope
    ]


def _validate_fragment(path: Path, identity_key: str, identity: str, policy_ref: str) -> None:
    fragment = _required_yaml(path, f"{identity} prompt fragment")
    if fragment.get(identity_key) != identity or fragment.get("policy_ref") != policy_ref:
        raise ValueError(f"prompt fragment identity mismatch: {path}")
    if set(fragment) != {"schema_version", identity_key, "policy_ref"} or fragment.get("schema_version") != 1:
        raise ValueError(f"prompt fragment must only reference the unified policy: {path}")


def assemble_packet(
    project_root: Path,
    project_id: str,
    stage: str,
    role: str,
    question_id: str | None = None,
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    if not project_id or not re.fullmatch(r"[A-Za-z0-9._-]+", project_id):
        raise ValueError("project_id must be an explicit safe token")
    if stage not in STAGES:
        raise ValueError(f"unsupported prompt stage: {stage}")
    if role not in ROLES:
        raise ValueError(f"unsupported prompt role: {role}")
    if stage not in ("P0", "P1") and not question_id:
        raise ValueError(f"{stage} requires an explicit question_id")
    workspace_root = workspace_root or project_root
    policy = load_policy(workspace_root)
    _required_yaml(workspace_root / "config" / "workflow.yaml", "shared workflow config")
    project, contest, _workflow = _project_context(project_root, project_id)
    stage_fragment = workspace_root / "templates" / "prompts" / "stages" / f"{stage}.yaml"
    role_fragment = workspace_root / "templates" / "prompts" / "roles" / f"{role}.yaml"
    _validate_fragment(stage_fragment, "stage", stage, f"stages.{stage}")
    _validate_fragment(role_fragment, "role", role, f"roles.{role}")
    problem_id = str(contest.get("problem") or "")
    resolved_question, question_refs = _question_context(project_root, problem_id, question_id)
    stage_rules = policy["stages"][stage]
    role_rules = policy["roles"][role]
    scope_question = resolved_question
    read_scope = _expand_scope(list(role_rules["read_scope"]), scope_question, problem_id)
    write_scope = _expand_scope(list(role_rules["write_scope"]), scope_question, problem_id)
    context_refs = [
        "project:project.yaml", "project:contest.yaml", "project:config/workflow.yaml",
        "shared:config/workflow.yaml", "shared:config/prompt_policy.yaml",
        f"shared:templates/prompts/stages/{stage}.yaml", f"shared:templates/prompts/roles/{role}.yaml",
        *(f"project:{item}" for item in question_refs),
    ]
    packet = {
        "packet_version": 1,
        "project_id": project_id,
        "stage": stage,
        "gate": derive_gate(stage),
        "role": role,
        "question_id": resolved_question,
        "objective": f"{stage_rules['objective']} {role_rules['objective']}",
        "read_scope": read_scope,
        "write_scope": write_scope,
        "context_refs": context_refs,
        "blocking_conditions": list(stage_rules["blocking"]),
        "warning_conditions": list(stage_rules["warning"]),
        "deferred_conditions": list(stage_rules["deferred"]),
        "allowed_actions": list(stage_rules["allowed_actions"]),
        "stop_conditions": [*stage_rules["stop_conditions"], *role_rules["stop_conditions"]],
        "input_contract": list(role_rules["inputs"]),
        "protected_paths": _expand_scope(list(role_rules["protected"]), scope_question, problem_id),
        "output_contract": {
            "format": "compact_receipt",
            "expected_artifacts": list(stage_rules["expected_artifacts"]),
            "role_outputs": list(role_rules["outputs"]),
            "question_scope": "all" if not resolved_question else resolved_question,
            "project_profile": project.get("profile_id") or contest.get("competition"),
        },
        "escalation_rules": [*stage_rules["escalation_conditions"], *role_rules["decisions"]],
    }
    issues = validate_packet(packet)
    if issues:
        raise ValueError("invalid assembled prompt packet: " + "; ".join(issues))
    return packet


def validate_packet(packet: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = {
        "packet_version", "project_id", "stage", "gate", "role", "question_id", "objective",
        "read_scope", "write_scope", "context_refs", "blocking_conditions", "warning_conditions",
        "deferred_conditions", "allowed_actions", "stop_conditions", "input_contract", "protected_paths",
        "output_contract", "escalation_rules",
    }
    issues.extend(f"packet missing {key}" for key in sorted(required - set(packet)))
    if packet.get("packet_version") != 1:
        issues.append("packet_version must be 1")
    if packet.get("stage") not in STAGES or packet.get("role") not in ROLES:
        issues.append("stage or role is invalid")
    stage = packet.get("stage")
    if stage not in GATES or packet.get("gate") != derive_gate(stage):
        issues.append("gate does not match stage")
    if packet.get("question_id") and not QUESTION_RE.fullmatch(str(packet["question_id"])):
        issues.append("question_id is invalid")
    if stage in GATES and stage not in ("P0", "P1") and not packet.get("question_id"):
        issues.append(f"{stage} requires question_id")
    for field in ("read_scope", "write_scope", "context_refs", "protected_paths"):
        for value in packet.get(field, []):
            scoped = value.split(":", 1)[1] if field == "context_refs" and isinstance(value, str) and value.startswith(("project:", "shared:")) else value
            if not isinstance(scoped, str) or not _relative_ref(scoped):
                issues.append(f"{field} contains an unsafe path: {value}")
    overlap = set(packet.get("blocking_conditions", [])) & set(packet.get("deferred_conditions", []))
    if overlap:
        issues.append(f"blocking/deferred overlap: {sorted(overlap)}")
    return issues


def format_receipt(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    status = str(payload.get("status", "PROGRESS"))
    if status not in RECEIPT_STATUSES:
        raise ValueError(f"invalid receipt status: {status}")
    decision = payload.get("decision_request")
    if decision is not None and not isinstance(decision, str):
        raise ValueError("decision_request must be null or a string")
    if decision is not None and not re.search(r"主模型|fallback|回退|claim|主张|官方规则|规则冲突|发布阻断", decision, re.I):
        raise ValueError("decision_request is limited to a critical decision")
    evidence = [str(item) for item in payload.get("evidence", [])]
    if any(not re.fullmatch(r"[^#]+#sha256=[0-9a-fA-F]{64}", item) for item in evidence):
        raise ValueError("receipt evidence must use path#sha256=<64 hex> locators")
    return {
        "status": status,
        "objective": str(payload.get("objective", "")),
        "conclusion": str(payload.get("conclusion", "")),
        "evidence": evidence,
        "warnings": [str(item) for item in payload.get("warnings", [])],
        "next_action": str(payload.get("next_action", "")),
        "decision_request": decision,
    }


def packet_json(packet: dict[str, Any]) -> str:
    return json.dumps(deepcopy(packet), ensure_ascii=False, indent=2) + "\n"
