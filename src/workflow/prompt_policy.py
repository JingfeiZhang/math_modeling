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
DECISION_REQUEST_RE = re.compile(
    r"主模型|模型选择|模型取舍|fallback|回退|claim|主张|结论边界|适用范围|官方规则|规则冲突|模板冲突|发布阻断|交付结果",
    re.I,
)
GATES = {"P0": "G0", "P1": "G0", "P2": "G1", "P3a": "G1", "P3b": "G2", "P4": "G4", "P5": "G4", "P6": "G6"}
GATE_SEQUENCES = {
    "P0": ("G0",), "P1": ("G0",), "P2": ("G1",), "P3a": ("G1",),
    "P3b": ("G2",), "P4": ("G3", "G4"), "P5": ("G4",), "P6": ("G5", "G6"),
}
ROLE_STAGES = {
    "P0": ("orchestrator",),
    "P1": ("orchestrator", "solver", "literature", "paper"),
    "P2": ("orchestrator", "solver", "literature"),
    "P3a": ("orchestrator", "solver", "literature", "visualization"),
    "P3b": ("orchestrator", "solver", "literature", "visualization"),
    "P4": ("orchestrator", "solver", "paper", "reviewer"),
    "P5": ("orchestrator", "paper", "visualization", "literature", "reviewer"),
    "P6": ("orchestrator", "studio_release", "reviewer"),
}
EXECUTION_SEMANTICS = {
    "warning": "record-and-continue",
    "blocking": "current-transition-only",
    "deferred": "do-not-run-before-owner-stage",
    "hash_drift": "affected-question-only",
    "reaudit": "no-recursive-reaudit",
    "continuation": "continue-editing-replay-and-recheckpoint",
    "note": "当前检查只阻断本次阶段转换，不阻断本问题继续建模、修改、复跑或重新 checkpoint。",
}
SHARED_KNOWLEDGE_PHASES = ("P1", "P2", "P3a", "P3b")
SHARED_KNOWLEDGE_ROLES = ("solver", "literature")
SHARED_KNOWLEDGE_MODULES = "references/competition-knowledge/modules"
SHARED_KNOWLEDGE_PLAYBOOKS_INDEX = "references/competition-knowledge/playbooks/index.md"
ALGORITHM_SOURCE_PHASES = ("P1", "P2", "P3a", "P3b")
ALGORITHM_SOURCE_ROLES = ("solver",)
ALGORITHM_SOURCE_CARDS = "references/algorithm-sources/cards"
STATISTICS_GUIDANCE_PHASES = ("P1", "P2", "P3a", "P3b")
STATISTICS_GUIDANCE_ROLES = ("solver",)
STATISTICS_GUIDANCE_ROUTES = (
    "data_profile", "relation_selection", "assumption_diagnostics",
    "effect_size_interval", "result_interpretation_boundary",
)
STATISTICS_GUIDANCE_STAGE_ROUTES = {
    "P1": ("data_profile", "relation_selection"),
    "P2": ("analysis_route", "assumption_diagnostics", "effect_size_interval"),
    "P3a": ("statistical_diagnostics", "robust_alternative", "result_interpretation"),
    "P3b": ("statistical_diagnostics", "result_interpretation_boundary"),
}
STATISTICS_GUIDANCE_OUTPUTS = {
    "P1": ("观测单位、响应类型、特征类型和分组结构", "候选关系分析路线"),
    "P2": ("同输出统计baseline", "假设探针", "效应量或区间摘要"),
    "P3a": ("残差或校准诊断", "稳健替代建议", "结果—原因—意义—边界草案"),
    "P3b": ("统计诊断结论", "适用范围和结果边界"),
}


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
    knowledge = policy.get("shared_knowledge")
    knowledge_fields = {"index", "phases", "solver_roles", "literature_roles", "contest_evidence_eligible", "formal_stages"}
    if not isinstance(knowledge, dict) or set(knowledge) != knowledge_fields:
        issues.append("shared_knowledge fields are incomplete or contain extras")
    else:
        index = knowledge.get("index")
        if not isinstance(index, str) or not _relative_ref(index):
            issues.append("shared_knowledge.index must be a safe relative path")
        if knowledge.get("phases") != list(SHARED_KNOWLEDGE_PHASES):
            issues.append("shared_knowledge.phases must cover P1-P3 only")
        if knowledge.get("solver_roles") != ["solver"] or knowledge.get("literature_roles") != ["literature"]:
            issues.append("shared_knowledge role bindings are invalid")
        if knowledge.get("contest_evidence_eligible") is not False:
            issues.append("shared_knowledge must never be contest evidence")
        if knowledge.get("formal_stages") != ["P4", "P5", "P6"]:
            issues.append("shared_knowledge.formal_stages must be P4-P6")
    statistics = policy.get("statistics_guidance")
    statistics_fields = {
        "index", "modules", "cards", "phases", "roles", "contest_evidence_eligible",
        "missing_behavior", "routes", "stage_routes",
    }
    if not isinstance(statistics, dict) or set(statistics) != statistics_fields:
        issues.append("statistics_guidance fields are incomplete or contain extras")
    else:
        for field in ("index", "modules", "cards"):
            if not isinstance(statistics.get(field), str) or not _relative_ref(statistics[field]):
                issues.append(f"statistics_guidance.{field} must be a safe relative path")
        if statistics.get("phases") != list(STATISTICS_GUIDANCE_PHASES):
            issues.append("statistics_guidance.phases must cover P1-P3 only")
        if statistics.get("roles") != list(STATISTICS_GUIDANCE_ROLES):
            issues.append("statistics_guidance.roles must be solver only")
        if statistics.get("contest_evidence_eligible") is not False:
            issues.append("statistics_guidance must never be contest evidence")
        if statistics.get("missing_behavior") != "warning":
            issues.append("statistics_guidance.missing_behavior must be warning")
        if statistics.get("routes") != list(STATISTICS_GUIDANCE_ROUTES):
            issues.append("statistics_guidance.routes are invalid")
        if statistics.get("stage_routes") != {stage: list(routes) for stage, routes in STATISTICS_GUIDANCE_STAGE_ROUTES.items()}:
            issues.append("statistics_guidance.stage_routes are invalid")
    algorithm_sources = policy.get("algorithm_sources")
    algorithm_source_fields = {
        "mirror", "index", "index_relpath", "sources", "cards", "skeletons", "phases",
        "roles", "contest_evidence_eligible", "formal_stages", "local_only", "sync_action",
    }
    if not isinstance(algorithm_sources, dict) or set(algorithm_sources) != algorithm_source_fields:
        issues.append("algorithm_sources fields are incomplete or contain extras")
    else:
        for field in ("mirror", "index", "index_relpath", "sources", "cards", "skeletons"):
            if not isinstance(algorithm_sources.get(field), str) or not _relative_ref(algorithm_sources[field]):
                issues.append(f"algorithm_sources.{field} must be a safe relative path")
        if algorithm_sources.get("phases") != list(ALGORITHM_SOURCE_PHASES):
            issues.append("algorithm_sources.phases must cover P1-P3 only")
        if algorithm_sources.get("roles") != list(ALGORITHM_SOURCE_ROLES):
            issues.append("algorithm_sources.roles must be solver only")
        if algorithm_sources.get("contest_evidence_eligible") is not False:
            issues.append("algorithm_sources must never be contest evidence")
        if algorithm_sources.get("formal_stages") != ["P4", "P5", "P6"]:
            issues.append("algorithm_sources.formal_stages must be P4-P6")
        if algorithm_sources.get("local_only") is not True:
            issues.append("algorithm_sources.local_only must be true")
        if algorithm_sources.get("sync_action") != "sync":
            issues.append("algorithm_sources.sync_action must be sync")
    response = policy.get("response") if isinstance(policy.get("response"), dict) else {}
    if response.get("format") != "compact_receipt" or response.get("chat_format") != "markdown_summary" or response.get("detail_mode") != "on_request":
        issues.append("response format/detail_mode are invalid")
    if response.get("required_fields") != list(RECEIPT_FIELDS):
        issues.append("response.required_fields must use the compact receipt contract")
    if response.get("omit_empty_sections") is not True:
        issues.append("response.omit_empty_sections must be true")
    if list(policy.get("stages", {})) != list(STAGES):
        issues.append("stages must define P0,P1,P2,P3a,P3b,P4,P5,P6 in order")
    if set(policy.get("roles", {})) != set(ROLES):
        issues.append("roles must define exactly the seven V7 roles")
    if policy.get("role_stages") != {stage: list(roles) for stage, roles in ROLE_STAGES.items()}:
        issues.append("role_stages must use the V7 stage-role compatibility matrix")
    if policy.get("gate_sequence") != {stage: list(gates) for stage, gates in GATE_SEQUENCES.items()}:
        issues.append("gate_sequence must use the V7 stage gate sequence")
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
        "execution_semantics",
    }
    if set(policy.get("rules", {})) != required_rules:
        issues.append("global rules are incomplete")
    elif policy["rules"].get("execution_semantics") != EXECUTION_SEMANTICS:
        issues.append("rules.execution_semantics must use the progress-first semantics")
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
    if role not in ROLE_STAGES.get(stage, ()):
        allowed = ", ".join(ROLE_STAGES.get(stage, ()))
        raise ValueError(f"role {role} is not allowed for {stage}; allowed roles: {allowed}")
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
        "project:project.yaml", "project:contest.yaml",
        f"shared:templates/prompts/stages/{stage}.yaml", f"shared:templates/prompts/roles/{role}.yaml",
        *(f"project:{item}" for item in question_refs),
    ]
    knowledge = policy["shared_knowledge"]
    knowledge_enabled = stage in knowledge["phases"] and role in SHARED_KNOWLEDGE_ROLES
    knowledge_notice = "共享教材速查卡仅用于 P1-P3 的模型方向、检索关键词和风险探针；统计资料优先支持数据画像、变量关系到检验/回归/分类的路线选择、假设诊断、效应量和结果—原因—意义—边界表达；不属于学术文献、Formal 证据或竞赛 claims。"
    algorithm_sources = policy["algorithm_sources"]
    algorithm_sources_enabled = stage in algorithm_sources["phases"] and role in algorithm_sources["roles"]
    algorithm_sources_notice = "外部算法卡仅用于 P1-P3 的候选算法、baseline 设计和风险探针；不执行外部代码，也不属于 Formal 证据、claims 或发布材料。"
    statistics_guidance = policy["statistics_guidance"]
    statistics_enabled = stage in statistics_guidance["phases"] and role in statistics_guidance["roles"]
    statistics_notice = (
        "统计资料仅用于 P1-P3 的数据画像、变量关系路线、假设诊断、效应量/区间、稳健替代和结果边界；"
        "不属于学术文献、Formal 证据、claims 或发布材料。经验阈值只能作为风险提示。"
    )
    assembly_warnings: list[str] = []
    if knowledge_enabled:
        read_scope.append(knowledge["index"])
        if role == "solver":
            read_scope.extend(["references/competition-knowledge/cards", SHARED_KNOWLEDGE_MODULES, SHARED_KNOWLEDGE_PLAYBOOKS_INDEX])
        context_refs.append(f"shared:{knowledge['index']}")
        if role == "solver":
            context_refs.extend([f"shared:{SHARED_KNOWLEDGE_MODULES}", f"shared:{SHARED_KNOWLEDGE_PLAYBOOKS_INDEX}"])
    packet = {
        "packet_version": 1,
        "project_id": project_id,
        "stage": stage,
        "gate": derive_gate(stage),
        "gate_sequence": list(GATE_SEQUENCES[stage]),
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
            "chat_format": "markdown_summary",
            "expected_artifacts": list(stage_rules["expected_artifacts"]),
            "role_outputs": list(role_rules["outputs"]),
            "question_scope": "all" if not resolved_question else resolved_question,
            "project_profile": project.get("profile_id") or contest.get("competition"),
        },
        "escalation_rules": [*stage_rules["escalation_conditions"], *role_rules["decisions"]],
        "execution_semantics": deepcopy(EXECUTION_SEMANTICS),
        "assembly_warnings": assembly_warnings,
    }
    if statistics_enabled:
        for ref in (statistics_guidance["index"], statistics_guidance["modules"], statistics_guidance["cards"]):
            if ref not in read_scope:
                read_scope.append(ref)
            shared_ref = f"shared:{ref}"
            if shared_ref not in context_refs:
                context_refs.append(shared_ref)
        packet["output_contract"]["statistics_guidance"] = {
            "index": statistics_guidance["index"],
            "modules": statistics_guidance["modules"],
            "cards": statistics_guidance["cards"],
            "route_ids": list(statistics_guidance["stage_routes"][stage]),
            "expected_outputs": list(STATISTICS_GUIDANCE_OUTPUTS[stage]),
            "contest_evidence_eligible": False,
            "usage": statistics_notice,
        }
        for ref, label in (
            (statistics_guidance["index"], "统计指导索引"),
            (statistics_guidance["modules"], "统计指导模块"),
            (statistics_guidance["cards"], "统计指导卡片"),
        ):
            if not (workspace_root / ref).exists():
                assembly_warnings.append(f"{label}不可用；继续当前任务，不以此阻断探索。")
    elif role == "literature" and stage in statistics_guidance["phases"]:
        packet["warning_conditions"].append("统计资料仅可转化为检索关键词，不作为学术文献或模型证据。")
    if knowledge_enabled:
        packet["output_contract"]["shared_knowledge"] = {
            "index": knowledge["index"],
            "contest_evidence_eligible": False,
            "usage": knowledge_notice,
        }
        if role == "solver":
            packet["output_contract"]["shared_knowledge"]["solver_support"] = [
                knowledge["index"],
                "references/competition-knowledge/cards",
                SHARED_KNOWLEDGE_MODULES,
                SHARED_KNOWLEDGE_PLAYBOOKS_INDEX,
            ]
        if not (workspace_root / knowledge["index"]).is_file():
            assembly_warnings.append("共享教材速查索引不可用；继续当前任务，不以此阻断探索。")
        if role == "literature":
            packet["warning_conditions"].append(knowledge_notice)
    if algorithm_sources_enabled:
        read_scope.extend([
            algorithm_sources["mirror"], algorithm_sources["index"], algorithm_sources["index_relpath"],
            algorithm_sources["cards"], algorithm_sources["skeletons"],
        ])
        context_refs.extend([
            f"shared:{algorithm_sources['mirror']}", f"shared:{algorithm_sources['index']}",
            f"shared:{algorithm_sources['index_relpath']}", f"shared:{algorithm_sources['cards']}",
            f"shared:{algorithm_sources['skeletons']}",
        ])
        packet["output_contract"]["algorithm_sources"] = {
            "mirror": algorithm_sources["mirror"],
            "index": algorithm_sources["index"],
            "index_relpath": algorithm_sources["index_relpath"],
            "cards": algorithm_sources["cards"],
            "skeletons": algorithm_sources["skeletons"],
            "local_only": True,
            "sync_action": "sync",
            "contest_evidence_eligible": False,
            "usage": algorithm_sources_notice + " 仅在显式 sync 后读取本地镜像；缺失时记录 warning，不联网。",
        }
        if not (workspace_root / algorithm_sources["mirror"]).is_dir():
            assembly_warnings.append("本地算法镜像目录不可用；请显式执行 reference-library sync，继续当前任务，不以此阻断探索。")
        if not (workspace_root / algorithm_sources["index"]).is_file():
            assembly_warnings.append("外部算法速查索引不可用；继续当前任务，不以此阻断探索。")
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
        "output_contract", "escalation_rules", "gate_sequence", "execution_semantics", "assembly_warnings",
    }
    issues.extend(f"packet missing {key}" for key in sorted(required - set(packet)))
    if packet.get("packet_version") != 1:
        issues.append("packet_version must be 1")
    if packet.get("stage") not in STAGES or packet.get("role") not in ROLES:
        issues.append("stage or role is invalid")
    stage = packet.get("stage")
    if stage not in GATES or packet.get("gate") != derive_gate(stage):
        issues.append("gate does not match stage")
    if stage in GATE_SEQUENCES and packet.get("gate_sequence") != list(GATE_SEQUENCES[stage]):
        issues.append("gate_sequence does not match stage")
    if stage in ROLE_STAGES and packet.get("role") not in ROLE_STAGES[stage]:
        issues.append("role is not allowed for stage")
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
    if packet.get("execution_semantics") != EXECUTION_SEMANTICS:
        issues.append("execution_semantics does not match the progress-first policy")
    if not isinstance(packet.get("assembly_warnings"), list):
        issues.append("assembly_warnings must be a list")
    output_contract = packet.get("output_contract")
    if not isinstance(output_contract, dict):
        issues.append("output_contract must be an object")
    else:
        if output_contract.get("format") != "compact_receipt" or output_contract.get("chat_format") != "markdown_summary":
            issues.append("output_contract format is invalid")
        knowledge = output_contract.get("shared_knowledge")
        if isinstance(knowledge, dict) and knowledge.get("contest_evidence_eligible") is not False:
            issues.append("shared knowledge cannot be contest evidence")
        statistics = output_contract.get("statistics_guidance")
        statistics_enabled = stage in STATISTICS_GUIDANCE_PHASES and packet.get("role") in STATISTICS_GUIDANCE_ROLES
        if statistics_enabled and not isinstance(statistics, dict):
            issues.append("early solver packets must include statistics_guidance")
        if not statistics_enabled and statistics is not None:
            issues.append("statistics_guidance is only allowed for P1-P3 solver packets")
        if isinstance(statistics, dict):
            if statistics.get("contest_evidence_eligible") is not False:
                issues.append("statistics guidance cannot be contest evidence")
            for field in ("index", "modules", "cards"):
                value = statistics.get(field)
                if not isinstance(value, str) or not _relative_ref(value):
                    issues.append(f"statistics_guidance.{field} must be a safe relative path")
                if isinstance(value, str) and any(
                    value == scope or value.startswith(f"{scope}/") or scope.startswith(f"{value}/")
                    for scope in packet.get("write_scope", [])
                ):
                    issues.append("statistics guidance must not overlap project write_scope")
            if not isinstance(statistics.get("route_ids"), list) or not statistics.get("route_ids"):
                issues.append("statistics_guidance.route_ids must be non-empty")
            if not isinstance(statistics.get("expected_outputs"), list) or not statistics.get("expected_outputs"):
                issues.append("statistics_guidance.expected_outputs must be non-empty")
        algorithm_sources = output_contract.get("algorithm_sources")
        if isinstance(algorithm_sources, dict):
            if algorithm_sources.get("contest_evidence_eligible") is not False:
                issues.append("algorithm sources cannot be contest evidence")
            if algorithm_sources.get("local_only") is not True or algorithm_sources.get("sync_action") != "sync":
                issues.append("algorithm sources must be local-only and explicitly synced")
    return issues


def format_receipt(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    status = str(payload.get("status", "PROGRESS"))
    if status not in RECEIPT_STATUSES:
        raise ValueError(f"invalid receipt status: {status}")
    decision = payload.get("decision_request")
    if decision is not None and not isinstance(decision, str):
        raise ValueError("decision_request must be null or a string")
    if decision is not None and not DECISION_REQUEST_RE.search(decision):
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


def format_receipt_markdown(receipt: dict[str, Any]) -> str:
    """Render the machine receipt as a compact, human-readable chat summary."""
    normalized = format_receipt(receipt)
    status_labels = {
        "PROGRESS": "进行中", "PASS": "通过", "PASS_WITH_WARNINGS": "通过，但有提醒",
        "BLOCK_TRANSITION": "阻断本次转换", "REOPEN_REQUIRED": "需要局部重开", "READY": "已就绪",
    }
    lines = [f"**{status_labels[normalized['status']]}**"]
    if normalized["objective"]:
        lines.extend(["", f"**目标**：{normalized['objective']}"])
    if normalized["conclusion"]:
        lines.extend(["", f"**结论**：{normalized['conclusion']}"])
    if normalized["evidence"]:
        lines.extend(["", "**依据**"])
        lines.extend(f"- `{item}`" for item in normalized["evidence"])
    if normalized["warnings"]:
        lines.extend(["", "**提醒**"])
        lines.extend(f"- {item}" for item in normalized["warnings"])
    if normalized["next_action"]:
        lines.extend(["", f"**下一步**：{normalized['next_action']}"])
    if normalized["decision_request"]:
        lines.extend(["", f"**需要确认**：{normalized['decision_request']}"])
    return "\n".join(lines) + "\n"


def packet_json(packet: dict[str, Any]) -> str:
    return json.dumps(deepcopy(packet), ensure_ascii=False, indent=2) + "\n"
