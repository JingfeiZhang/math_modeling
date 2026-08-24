"""Semantic, metric, algorithm-evidence, and abstract contracts.

The contracts are intentionally separate from question evidence. They describe
what a question means and what evidence a later transition must prove; they do
not create claims or change competition state.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

CONTRACT_NAMES = ("semantics", "metrics", "algorithm_evidence", "abstract")
CONTRACT_FILES = {
    "semantics": ("semantic_contract.yaml", "semantic_contract.schema.json"),
    "metrics": ("metric_contract.yaml", "metric_contract.schema.json"),
    "algorithm_evidence": ("algorithm_evidence.yaml", "algorithm_evidence.schema.json"),
    "abstract": ("abstract_contract.yaml", "abstract_contract.schema.json"),
}
CONTRACT_STATES = {"DRAFT", "READY", "LOCKED", "STALE"}
RELATIVE_PATH_RE = re.compile(r"^(?![A-Za-z]:|/|\\\\).+")


def _yaml_load(path: Path) -> dict[str, Any]:
    import yaml

    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _yaml_dump(path: Path, value: dict[str, Any]) -> None:
    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _question_interface_hash(path: Path) -> str:
    """Hash the question contract without recursively hashing its contract refs."""

    payload = _yaml_load(path)
    payload.pop("quality_contracts", None)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def contracts_dir(root: Path, problem: str, question: str) -> Path:
    return root / "problems" / problem / "questions" / question / "contracts"


def question_set_path(root: Path, problem: str) -> Path:
    return root / "problems" / problem / "questions" / "question_set.yaml"


def write_question_set_manifest(root: Path, problem: str) -> Path:
    """Write a derived, project-local index of every question interface."""

    members: list[dict[str, str]] = []
    base = root / "problems" / problem / "questions"
    for path in sorted(base.glob("Q*/question.yaml"), key=lambda item: int(item.parent.name[1:])):
        members.append(
            {
                "question_id": path.parent.name,
                "path": _relative(root, path),
                "interface_sha256": _question_interface_hash(path),
            }
        )
    if not members:
        raise ValueError(f"question set is empty for problem {problem}")
    destination = question_set_path(root, problem)
    _yaml_dump(
        destination,
        {
            "schema_version": 1,
            "problem_id": problem,
            "questions": members,
        },
    )
    return destination


def contracts_enabled(root: Path) -> bool:
    project = root / "project.yaml"
    if project.is_file():
        payload = _yaml_load(project)
        if int(payload.get("workflow_contract_version", 0) or 0) >= 7:
            return True
    return False


def _template_root(workspace_root: Path | None) -> Path:
    root = workspace_root or Path(__file__).resolve().parents[2]
    return root / "templates" / "workflow"


def _schema_root(workspace_root: Path | None) -> Path:
    root = workspace_root or Path(__file__).resolve().parents[2]
    return root / "config" / "schemas"


def _ref(path: Path, root: Path) -> dict[str, str]:
    return {"path": _relative(root, path), "sha256": _sha256(path)}


def create_quality_contracts(
    root: Path,
    problem: str,
    question: str,
    question_count: int,
    source_problem: str,
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    """Create draft contract files and return question-manifest references."""

    target = contracts_dir(root, problem, question)
    target.mkdir(parents=True, exist_ok=True)
    template_root = _template_root(workspace_root)
    created: dict[str, str] = {}
    for name, (template_name, _) in CONTRACT_FILES.items():
        destination = (
            root / "problems" / problem / "contracts" / template_name
            if name == "abstract"
            else target / template_name
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            source = template_root / template_name
            if not source.is_file():
                raise FileNotFoundError(f"quality contract template is missing: {source}")
            shutil.copy2(source, destination)
        payload = _yaml_load(destination)
        payload["problem_id"] = problem
        if name != "abstract":
            payload["question_id"] = question
        if name == "semantics":
            payload.setdefault("source_problem", {})["path"] = source_problem
            source_path = (root / source_problem).resolve()
            if source_path.is_file():
                payload["source_problem"]["sha256"] = _sha256(source_path)
        elif name in {"metrics", "algorithm_evidence"}:
            question_path = root / "problems" / problem / "questions" / question / "question.yaml"
            payload.setdefault("source_question", {})["path"] = _relative(root, question_path)
            source_path = question_path.resolve()
            if source_path.is_file():
                payload["source_question"]["sha256"] = _question_interface_hash(source_path)
        if name == "abstract":
            payload["question_count"] = question_count
            source_path = write_question_set_manifest(root, problem)
            payload.setdefault("source_question_set", {})["path"] = _relative(root, source_path)
            payload["source_question_set"]["sha256"] = _sha256(source_path)
            payload["questions"] = [
                {
                    "question_id": f"Q{index}",
                    "method_required": True,
                    "subject_required": True,
                    "conclusion_required": True,
                    "validation_required": True,
                    "boundary_required": True,
                    "method": "",
                    "subject": "",
                    "conclusion": "",
                    "validation": "",
                    "boundary": "",
                    "claim_ids": [],
                }
                for index in range(1, question_count + 1)
            ]
        _yaml_dump(destination, payload)
        created[name] = _relative(root, destination)
    references = {
        name: _ref(
            root / "problems" / problem / "contracts" / file_name
            if name == "abstract"
            else target / file_name,
            root,
        )
        for name, (file_name, _) in CONTRACT_FILES.items()
    }
    return {"references": references, "created": created}


def refresh_quality_contract_references(root: Path, problem: str, question: str | None = None) -> dict[str, Any]:
    """Refresh derived hashes after a human has reviewed contract edits."""

    all_question_paths = sorted((root / "problems" / problem / "questions").glob("Q*/question.yaml"))
    question_paths = all_question_paths
    if question:
        question_paths = [path for path in question_paths if path.parent.name == question]
    if not question_paths:
        raise FileNotFoundError("no matching question manifests were found")
    selected = {path.resolve() for path in question_paths}
    existing_set_path = question_set_path(root, problem)
    if question and existing_set_path.is_file():
        existing_set = _yaml_load(existing_set_path)
        recorded = {
            str(item.get("question_id")): str(item.get("interface_sha256"))
            for item in existing_set.get("questions", [])
            if isinstance(item, dict)
        }
        for path in all_question_paths:
            if path.resolve() not in selected and recorded.get(path.parent.name) != _question_interface_hash(path):
                raise ValueError(f"unselected question interface has drifted: {path.parent.name}")
    question_set = write_question_set_manifest(root, problem)
    first_payload = _yaml_load(question_paths[0])
    first_refs = first_payload.get("quality_contracts", {})
    abstract_reference = first_refs.get("abstract") if isinstance(first_refs, dict) else None
    if not isinstance(abstract_reference, dict) or not isinstance(abstract_reference.get("path"), str):
        raise ValueError("shared abstract contract reference is missing")
    abstract_path = (root / abstract_reference["path"]).resolve()
    if not abstract_path.is_file():
        raise FileNotFoundError(f"shared abstract contract is missing: {abstract_reference['path']}")
    abstract = _yaml_load(abstract_path)
    abstract_source = abstract.setdefault("source_question_set", {})
    abstract_source["path"] = _relative(root, question_set)
    abstract_source["sha256"] = _sha256(question_set)
    _yaml_dump(abstract_path, abstract)
    abstract_hash = _sha256(abstract_path)
    updated: list[str] = []
    for path in all_question_paths:
        payload = _yaml_load(path)
        refs = payload.get("quality_contracts")
        if not isinstance(refs, dict):
            raise ValueError(f"quality contracts are missing from {path.parent.name}")
        names = ("semantics", "metrics", "algorithm_evidence") if path.resolve() in selected else ()
        for name in names:
            reference = refs.get(name)
            if not isinstance(reference, dict) or not isinstance(reference.get("path"), str):
                raise ValueError(f"quality contract reference is missing: {path.parent.name}/{name}")
            contract_path = (root / reference["path"]).resolve()
            if not contract_path.is_file():
                raise FileNotFoundError(f"quality contract is missing: {reference['path']}")
            contract = _yaml_load(contract_path)
            source_key = "source_problem" if name == "semantics" else "source_question"
            source = contract.setdefault(source_key, {})
            if name in {"metrics", "algorithm_evidence"}:
                source["path"] = _relative(root, path)
                source["sha256"] = _question_interface_hash(path)
            else:
                source_path = (root / str(source.get("path", ""))).resolve()
                if not source_path.is_file():
                    raise FileNotFoundError(f"semantic source problem is missing: {source.get('path')}")
                source["sha256"] = _sha256(source_path)
            _yaml_dump(contract_path, contract)
            reference["sha256"] = _sha256(contract_path)
        abstract_ref = refs.get("abstract")
        if not isinstance(abstract_ref, dict):
            raise ValueError(f"quality contract reference is missing: {path.parent.name}/abstract")
        abstract_ref["path"] = _relative(root, abstract_path)
        abstract_ref["sha256"] = abstract_hash
        _yaml_dump(path, payload)
        if path.resolve() in selected:
            updated.append(_relative(root, path))
    return {
        "status": "REFRESHED",
        "problem": problem,
        "question": question,
        "question_set": _relative(root, question_set),
        "updated": updated,
    }


def _load_schema(schema_name: str, workspace_root: Path | None) -> dict[str, Any]:
    path = _schema_root(workspace_root) / schema_name
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_issues(payload: dict[str, Any], schema_name: str, workspace_root: Path | None) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return []
    schema = _load_schema(schema_name, workspace_root)
    return [error.message for error in sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda item: list(item.path))[:8]]


def _reference_issues(root: Path, reference: Any, name: str) -> tuple[list[str], Path | None]:
    if not isinstance(reference, dict):
        return [f"{name} reference must be an object"], None
    path_value = reference.get("path")
    digest = reference.get("sha256")
    if not isinstance(path_value, str) or not RELATIVE_PATH_RE.fullmatch(path_value):
        return [f"{name}.path must be a relative project path"], None
    resolved = (root / path_value).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return [f"{name}.path escapes project root"], None
    issues: list[str] = []
    if not resolved.is_file():
        issues.append(f"{name} file is missing: {path_value}")
        return issues, resolved
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest.lower()):
        issues.append(f"{name}.sha256 must be a SHA-256")
    elif digest.lower() != _sha256(resolved):
        issues.append(f"{name} hash drift: {path_value}")
    return issues, resolved


def _source_reference_issues(root: Path, payload: dict[str, Any], source_key: str, name: str) -> list[str]:
    """Validate a contract's inner source pointer and its semantic hash.

    The outer ``question.yaml`` reference protects the contract file itself.  A
    contract also carries a source pointer so changing the problem statement or
    question interface invalidates only the affected contract.  Question
    sources are hashed without ``quality_contracts`` to avoid recursive drift.
    """

    source = payload.get(source_key)
    if not isinstance(source, dict):
        return [f"{name}.{source_key} must be an object"]
    path_value = source.get("path")
    digest = source.get("sha256")
    if not isinstance(path_value, str) or not RELATIVE_PATH_RE.fullmatch(path_value):
        return [f"{name}.{source_key}.path must be a relative project path"]
    resolved = (root / path_value).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return [f"{name}.{source_key}.path escapes project root"]
    if not resolved.is_file():
        return [f"{name}.{source_key} file is missing: {path_value}"]
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest.lower()):
        return [f"{name}.{source_key}.sha256 must be a SHA-256"]
    actual = _question_interface_hash(resolved) if source_key == "source_question" else _sha256(resolved)
    if digest.lower() != actual:
        return [f"{name}.{source_key} hash drift: {path_value}"]
    if source_key == "source_question_set":
        question_set = _yaml_load(resolved)
        members = question_set.get("questions")
        if isinstance(members, list):
            member_issues: list[str] = []
            expected_ids = {str(item.get("question_id")) for item in payload.get("questions", []) if isinstance(item, dict)}
            member_ids = {str(item.get("question_id")) for item in members if isinstance(item, dict)}
            if int(payload.get("question_count", 0) or 0) != len(members) or expected_ids != member_ids:
                member_issues.append("abstract question set does not match its synthesis coverage")
            for member in members:
                if not isinstance(member, dict):
                    member_issues.append("abstract question set contains an invalid member")
                    continue
                member_path = root / str(member.get("path", ""))
                if not member_path.is_file():
                    member_issues.append(f"abstract question member is missing: {member.get('question_id', 'unknown')}")
                    continue
                if member.get("interface_sha256") != _question_interface_hash(member_path):
                    member_issues.append(f"abstract question member hash drift: {member.get('question_id', 'unknown')}")
            return member_issues
    return []


def load_quality_bundle(root: Path, question_payload: dict[str, Any], workspace_root: Path | None = None) -> tuple[dict[str, dict[str, Any]], list[str]]:
    refs = question_payload.get("quality_contracts")
    if not isinstance(refs, dict):
        return {}, []
    bundle: dict[str, dict[str, Any]] = {}
    issues: list[str] = []
    for name in CONTRACT_NAMES:
        reference = refs.get(name)
        ref_issues, path = _reference_issues(root, reference, f"quality_contracts.{name}")
        issues.extend(ref_issues)
        if path is None or not path.is_file():
            continue
        try:
            payload = _yaml_load(path)
        except Exception as exc:
            issues.append(f"{name} cannot be read: {exc}")
            continue
        schema_name = CONTRACT_FILES[name][1]
        issues.extend(f"{name}: {item}" for item in _schema_issues(payload, schema_name, workspace_root))
        source_key = {
            "semantics": "source_problem",
            "metrics": "source_question",
            "algorithm_evidence": "source_question",
            "abstract": "source_question_set",
        }[name]
        issues.extend(_source_reference_issues(root, payload, source_key, name))
        if payload.get("status") not in CONTRACT_STATES:
            issues.append(f"{name}.status is invalid")
        bundle[name] = payload
    return bundle, issues


def _semantic_issues(payload: dict[str, Any], strict: bool) -> list[str]:
    issues: list[str] = []
    inputs = payload.get("inputs", [])
    outputs = payload.get("outputs", [])
    scenarios = payload.get("scenarios", [])
    if strict and payload.get("status") not in {"READY", "LOCKED"}:
        issues.append("semantics contract is not READY or LOCKED")
    elif not strict and payload.get("status") not in {"READY", "LOCKED"}:
        issues.append("semantics contract is still draft")
    if strict and not outputs:
        issues.append("semantics has no declared outputs")
    if strict and any(item.get("required") and not item.get("unit") for item in outputs if isinstance(item, dict)):
        issues.append("required output has no unit")
    if strict and any(
        item.get("role") == "decision"
        and (
            item.get("fixed_by_statement") is True
            or str(item.get("id", "")).lower() in {"fixed_load", "fixed_demand", "load"}
        )
        for item in inputs
        if isinstance(item, dict)
    ):
        issues.append("fixed load-like input is declared as a decision variable")
    if strict and any(item.get("required") and item.get("coverage_mode") not in {"full", "sampled", "local-window"} for item in scenarios if isinstance(item, dict)):
        issues.append("required scenario has no coverage mode")
    return issues


def _prediction_task(question_payload: dict[str, Any] | None, semantic_payload: dict[str, Any] | None = None) -> bool:
    values: list[str] = []
    if question_payload:
        problem = question_payload.get("problem", {})
        if isinstance(problem, dict):
            values.extend((str(problem.get("type", "")), str(problem.get("target", ""))))
    if semantic_payload:
        task = semantic_payload.get("task", {})
        if isinstance(task, dict):
            values.extend((str(task.get("type", "")), str(task.get("objective", ""))))
    text = " ".join(values).casefold()
    return any(token in text for token in ("forecast", "prediction", "predict", "预测"))


def _metric_definition(item: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "id",
        "name",
        "formula",
        "direction",
        "unit",
        "numerator",
        "denominator",
        "aggregation",
        "time_window",
        "target_definition",
        "horizon",
        "forecast_form",
        "interval_definition",
        "baseline",
    )
    return {key: item.get(key) for key in keys if key in item}


def _metric_issues(
    payload: dict[str, Any],
    strict: bool,
    question_payload: dict[str, Any] | None = None,
    semantic_payload: dict[str, Any] | None = None,
) -> list[str]:
    issues: list[str] = []
    metrics = payload.get("metrics", [])
    if strict and payload.get("status") not in {"READY", "LOCKED"}:
        issues.append("metrics contract is not READY or LOCKED")
    elif not strict and payload.get("status") not in {"READY", "LOCKED"}:
        issues.append("metrics contract is still draft")
    required = [item for item in metrics if isinstance(item, dict) and item.get("required")]
    if strict and not required:
        issues.append("metrics contract has no required metric")
    for item in required:
        label = str(item.get("id") or item.get("name") or "metric")
        if not item.get("formula") or not item.get("unit") or not item.get("baseline"):
            issues.append(f"required metric incomplete: {label}")
        formula = str(item.get("formula", ""))
        if strict and any(token in formula.lower() for token in ("/", "rate", "ratio", "%")) and not item.get("denominator"):
            issues.append(f"metric denominator is missing: {label}")
        reference_range = item.get("reference_range")
        if reference_range is not None and not item.get("reference_source"):
            issues.append(f"metric reference source is missing: {label}")
        if strict and _prediction_task(question_payload, semantic_payload):
            if not item.get("target_definition") or not item.get("horizon") or not item.get("time_window"):
                issues.append(f"prediction metric lacks target, horizon, or scoring window: {label}")
            if item.get("forecast_form") in {"interval", "quantile"} and not item.get("interval_definition"):
                issues.append(f"prediction uncertainty definition is missing: {label}")
    if strict and question_payload:
        problem = question_payload.get("problem", {})
        expected_values = problem.get("evaluation_metrics", []) if isinstance(problem, dict) else []
        expected = {str(value).strip().casefold() for value in expected_values if str(value).strip()}
        declared = {
            str(item.get("name") or item.get("id") or "").strip().casefold()
            for item in required
            if isinstance(item, dict)
        }
        for required_name in sorted(expected):
            if not any(required_name == candidate or required_name in candidate for candidate in declared):
                issues.append(f"question-required metric is missing from contract: {required_name}")
    return issues


def _relative_artifact_exists(root: Path | None, value: Any) -> bool:
    if root is None or not isinstance(value, str) or not value.strip() or not RELATIVE_PATH_RE.fullmatch(value):
        return False
    path = (root / value.split(":", 1)[0]).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return False
    return path.is_file()


def _algorithm_issues(payload: dict[str, Any], strict: bool, root: Path | None = None) -> list[str]:
    issues: list[str] = []
    if strict and payload.get("status") not in {"READY", "LOCKED"}:
        issues.append("algorithm evidence contract is not READY or LOCKED")
    elif not strict and payload.get("status") not in {"READY", "LOCKED"}:
        issues.append("algorithm evidence contract is still draft")
    mode = payload.get("objective_mode")
    if strict and mode in {"pareto", "epsilon-constraint"}:
        coverage = payload.get("scenario_coverage", [])
        covered = [
            item
            for item in coverage
            if isinstance(item, dict)
            and item.get("covered") is True
            and item.get("scenario_id")
            and _relative_artifact_exists(root, item.get("result_locator"))
            and item.get("parameter_value") is not None
            and bool(item.get("objective_vector"))
            and (mode != "pareto" or item.get("non_dominated") is True)
        ]
        unique_ids = {str(item.get("scenario_id")) for item in covered}
        if len(covered) < 3 or len(unique_ids) < 3:
            issues.append("multi-objective evidence needs at least three reported alternatives or sweeps")
    search_mode = payload.get("search_mode")
    evidence_type = payload.get("evidence_type")
    substantive_search = payload.get("substantive_search", True)
    if strict and search_mode in {"heuristic", "stochastic"} and substantive_search and evidence_type != "convergence_trace":
        issues.append("heuristic or stochastic search needs a convergence trace")
    if strict and evidence_type == "convergence_trace" and not _relative_artifact_exists(root, payload.get("trace_locator")):
        issues.append("algorithm evidence trace locator is missing or unreadable")
    if strict and search_mode == "stochastic" and int(payload.get("seed_count", 0) or 0) < 3:
        issues.append("stochastic search needs at least three seeds")
    if strict and search_mode == "stochastic" and len(payload.get("seed_runs", [])) < 3:
        issues.append("stochastic search needs at least three seed run references")
    elif strict and search_mode == "stochastic" and root is not None:
        missing_seed_runs = [value for value in payload.get("seed_runs", []) if not _relative_artifact_exists(root, value)]
        if missing_seed_runs:
            issues.append("stochastic seed run evidence is missing or unreadable")
    if strict and search_mode == "exact" and evidence_type not in {"optimality_gap", "enumeration_coverage", "solver_status"}:
        issues.append("exact search needs an optimality-gap or enumeration-coverage record")
    if strict and evidence_type in {"optimality_gap", "enumeration_coverage", "solver_status"}:
        locator = payload.get("solver_evidence_locator") or payload.get("trace_locator")
        if root is not None and not _relative_artifact_exists(root, locator):
            issues.append("solver evidence locator is missing or unreadable")
    scope = payload.get("scope", {}) if isinstance(payload.get("scope"), dict) else {}
    if strict and scope.get("coverage_mode") == "local-window" and not scope.get("window"):
        issues.append("local-window scope must declare its window")
    if strict and scope.get("coverage_mode") == "local-window":
        claim_text = " ".join(str(item) for item in scope.get("claim_language", [])).casefold()
        if not any(token in claim_text for token in ("local", "window", "局部", "窗口", "有限")):
            issues.append("local-window scope must constrain the allowed claim language")
        if not scope.get("forbidden_language"):
            issues.append("local-window scope must declare forbidden global claim language")
    if strict and mode == "weighted":
        claim_text = " ".join(str(item) for item in scope.get("claim_language", [])).casefold()
        if not any(token in claim_text for token in ("fixed preference", "fixed weight", "固定偏好", "固定权重", "单方案")):
            issues.append("fixed-weight optimization must declare a fixed-preference single-solution boundary")
    return issues


def _abstract_issues(payload: dict[str, Any], strict: bool) -> list[str]:
    if not strict:
        return []
    issues: list[str] = []
    if payload.get("status") not in {"READY", "LOCKED"}:
        issues.append("abstract contract is not READY or LOCKED")
    if payload.get("background", {}).get("max_lines") not in {3, 4}:
        issues.append("abstract background must be limited to three or four lines")
    expected = int(payload.get("question_count", 0) or 0)
    actual = {str(item.get("question_id")) for item in payload.get("questions", []) if isinstance(item, dict)}
    if expected and actual != {f"Q{i}" for i in range(1, expected + 1)}:
        issues.append("abstract contract does not cover every question")
    required_flags = (
        "method_required",
        "subject_required",
        "conclusion_required",
        "validation_required",
        "boundary_required",
    )
    for item in payload.get("questions", []):
        if isinstance(item, dict) and not all(item.get(flag) is True for flag in required_flags):
            issues.append(f"abstract question coverage is incomplete: {item.get('question_id', 'unknown')}")
        if isinstance(item, dict):
            missing = [field for field in ("method", "subject", "conclusion", "validation", "boundary") if not str(item.get(field, "")).strip()]
            if missing:
                issues.append(f"abstract synthesis fields are incomplete: {item.get('question_id', 'unknown')} ({', '.join(missing)})")
            if not item.get("claim_ids"):
                issues.append(f"abstract has no frozen-claim allowlist: {item.get('question_id', 'unknown')}")
    final_summary = payload.get("final_summary", {})
    if not isinstance(final_summary, dict) or not all(str(final_summary.get(field, "")).strip() for field in ("contribution", "limitation")):
        issues.append("abstract final contribution and limitation are incomplete")
    return issues


def quality_contract_issues(
    root: Path,
    question_payload: dict[str, Any],
    *,
    strict: bool,
    workspace_root: Path | None = None,
    include_abstract: bool = False,
) -> list[str]:
    bundle, issues = load_quality_bundle(root, question_payload, workspace_root)
    if not bundle:
        return ["quality contracts are missing"] if strict else []
    issues.extend(_semantic_issues(bundle.get("semantics", {}), strict))
    issues.extend(_metric_issues(bundle.get("metrics", {}), strict, question_payload, bundle.get("semantics", {})))
    issues.extend(_algorithm_issues(bundle.get("algorithm_evidence", {}), strict, root))
    if include_abstract:
        issues.extend(_abstract_issues(bundle.get("abstract", {}), strict))
    return issues


def transition_contract_issues(
    root: Path,
    question_payload: dict[str, Any],
    *,
    transition: str,
    workspace_root: Path | None = None,
) -> list[str]:
    """Return only the contract checks owned by a workflow transition."""

    strict = transition in {"candidate", "formal", "g3", "g4", "g5", "g6"}
    bundle, issues = load_quality_bundle(root, question_payload, workspace_root)
    if not bundle:
        return ["quality contracts are missing"] if strict else []
    issues.extend(_semantic_issues(bundle.get("semantics", {}), strict))
    issues.extend(_metric_issues(bundle.get("metrics", {}), strict, question_payload, bundle.get("semantics", {})))
    if transition in {"formal", "g3", "g4", "g5", "g6"}:
        issues.extend(_algorithm_issues(bundle.get("algorithm_evidence", {}), True, root))
    if transition in {"g5", "g6"}:
        issues.extend(_abstract_issues(bundle.get("abstract", {}), True))
    return issues


def abstract_text_issues(root: Path, question_payload: dict[str, Any]) -> list[str]:
    """Validate the actual abstract against the shared synthesis contract."""

    bundle, issues = load_quality_bundle(root, question_payload)
    if issues or not bundle:
        return []
    contract = bundle.get("abstract", {})
    if contract.get("status") not in {"READY", "LOCKED"}:
        return []
    abstract_path = next(
        (
            path
            for path in (
                root / "paper" / "sections" / "abstract.tex",
                root / "paper" / "sections" / "00_abstract.tex",
            )
            if path.is_file()
        ),
        None,
    )
    if abstract_path is None:
        return ["abstract source is missing"]
    text = abstract_path.read_text(encoding="utf-8").lower()
    terms = [str(item).lower() for item in contract.get("forbidden_terms", []) if str(item).strip()]
    algorithm_scope = bundle.get("algorithm_evidence", {}).get("scope", {})
    if isinstance(algorithm_scope, dict):
        terms.extend(str(item).lower() for item in algorithm_scope.get("forbidden_language", []) if str(item).strip())
    found = [term for term in terms if term in text]
    result = [f"abstract contains internal workflow terms: {', '.join(found)}"] if found else []
    for item in contract.get("questions", []):
        if not isinstance(item, dict):
            continue
        for field in ("method", "subject", "conclusion", "validation", "boundary"):
            anchor = str(item.get(field, "")).strip().lower()
            if anchor and anchor not in text:
                result.append(f"abstract is missing {item.get('question_id')}/{field} anchor")
    final_summary = contract.get("final_summary", {})
    if isinstance(final_summary, dict):
        for field in ("contribution", "limitation"):
            anchor = str(final_summary.get(field, "")).strip().lower()
            if anchor and anchor not in text:
                result.append(f"abstract is missing final {field} anchor")
    claims_path = root / "results" / str(contract.get("problem_id", "")) / "claims.json"
    claims = _yaml_load(claims_path) if claims_path.suffix in {".yaml", ".yml"} else {}
    if claims_path.is_file() and claims_path.suffix == ".json":
        value = json.loads(claims_path.read_text(encoding="utf-8"))
        claims = value if isinstance(value, dict) else {}
    frozen = {
        str(item.get("id")): item
        for item in claims.get("claims", [])
        if isinstance(item, dict) and item.get("status") == "frozen"
    }
    for item in contract.get("questions", []):
        if not isinstance(item, dict):
            continue
        unknown = sorted(str(claim_id) for claim_id in item.get("claim_ids", []) if str(claim_id) not in frozen)
        if unknown:
            result.append(f"abstract claim allowlist is not frozen for {item.get('question_id')}: {', '.join(unknown)}")
    return result


def build_quality_contract_snapshot(question_payload: dict[str, Any]) -> dict[str, Any]:
    """Create the immutable contract-side portion stored in a run manifest."""

    refs = question_payload.get("quality_contracts", {})
    bundle = question_payload.get("_quality_bundle", {})
    if not isinstance(refs, dict) or not isinstance(bundle, dict):
        return {}
    metrics = bundle.get("metrics", {}).get("metrics", [])
    semantics = bundle.get("semantics", {})
    algorithm = bundle.get("algorithm_evidence", {})
    return {
        "contract_hashes": {
            name: refs.get(name, {}).get("sha256")
            for name in ("semantics", "metrics", "algorithm_evidence")
            if isinstance(refs.get(name), dict)
        },
        "metric_definitions": [
            {
                "name": str(item.get("name", "")),
                "unit": str(item.get("unit", "")),
                "baseline": str(item.get("baseline", "")),
                "definition_sha256": _canonical_hash(_metric_definition(item)),
            }
            for item in metrics
            if isinstance(item, dict) and item.get("required")
        ],
        "input_roles": [
            {"id": str(item.get("id", "")), "role": str(item.get("role", ""))}
            for item in semantics.get("inputs", [])
            if isinstance(item, dict)
        ],
        "model_variables": [
            {"id": str(item.get("id", "")), "role": str(item.get("role", "")), "source_input_id": item.get("source_input_id")}
            for item in semantics.get("model_variable_map", [])
            if isinstance(item, dict)
        ],
        "required_scenarios": [
            {"scenario_id": str(item.get("id", "")), "scope": str(item.get("coverage_mode", ""))}
            for item in semantics.get("scenarios", [])
            if isinstance(item, dict) and item.get("required")
        ],
        "algorithm_scope": algorithm.get("scope", {}),
    }


def run_contract_issues(
    question_payload: dict[str, Any],
    run_manifest: dict[str, Any],
    *,
    strict: bool,
    root: Path | None = None,
) -> list[str]:
    """Compare a run's declared metrics and scope with the question contracts."""

    if not strict:
        return []
    bundle = question_payload.get("_quality_bundle", {})
    metric_contract = bundle.get("metrics", {}) if isinstance(bundle, dict) else {}
    required = {
        str(item.get("name")): item
        for item in metric_contract.get("metrics", [])
        if isinstance(item, dict) and item.get("required")
    }
    declared = {
        str(item.get("name")): item
        for item in run_manifest.get("metrics", [])
        if isinstance(item, dict)
    }
    snapshots = {
        str(item.get("name")): item
        for item in run_manifest.get("metric_snapshot", [])
        if isinstance(item, dict)
    }
    issues: list[str] = []
    missing = sorted(set(required) - set(declared))
    if missing:
        issues.append(f"formal run is missing required metrics: {', '.join(missing)}")
    for name, contract_metric in required.items():
        run_metric = declared.get(name)
        snapshot = snapshots.get(name)
        if run_metric and str(run_metric.get("unit", "")) != str(contract_metric.get("unit", "")):
            issues.append(f"formal metric unit differs from contract: {name}")
        if not snapshot or snapshot.get("value") is None:
            issues.append(f"formal metric snapshot is unresolved: {name}")
        elif str(snapshot.get("unit", "")) != str(contract_metric.get("unit", "")):
            issues.append(f"formal metric snapshot unit differs from contract: {name}")
    expected_snapshot = build_quality_contract_snapshot(question_payload)
    actual_snapshot = run_manifest.get("quality_contract_snapshot")
    if not isinstance(actual_snapshot, dict):
        issues.append("formal run has no quality contract snapshot")
        return issues
    if actual_snapshot.get("contract_hashes") != expected_snapshot.get("contract_hashes"):
        issues.append("formal run quality contract hashes have drifted")
    expected_definitions = {
        str(item.get("name")): item.get("definition_sha256")
        for item in expected_snapshot.get("metric_definitions", [])
    }
    actual_definitions = {
        str(item.get("name")): item.get("definition_sha256")
        for item in actual_snapshot.get("metric_definitions", [])
        if isinstance(item, dict)
    }
    if expected_definitions != actual_definitions:
        issues.append("formal run metric definitions differ from contract")
    expected_roles = {str(item.get("id")): str(item.get("role")) for item in expected_snapshot.get("input_roles", [])}
    actual_roles = {str(item.get("id")): str(item.get("role")) for item in run_manifest.get("input_roles", []) if isinstance(item, dict)}
    if expected_roles != actual_roles:
        issues.append("formal run input roles differ from semantics contract")
    fixed_inputs = {identifier for identifier, role in expected_roles.items() if role == "fixed"}
    expected_variables = {
        (str(item.get("id")), str(item.get("role")), str(item.get("source_input_id") or ""))
        for item in expected_snapshot.get("model_variables", [])
        if isinstance(item, dict)
    }
    actual_variables = {
        (str(item.get("id")), str(item.get("role")), str(item.get("source_input_id") or ""))
        for item in run_manifest.get("model_variables", [])
        if isinstance(item, dict)
    }
    if expected_variables != actual_variables:
        issues.append("formal run model variables differ from semantics contract")
    decisions = {
        str(item.get("source_input_id") or item.get("id"))
        for item in run_manifest.get("model_variables", [])
        if isinstance(item, dict) and item.get("role") == "decision"
    }
    if fixed_inputs & decisions:
        issues.append("formal model turns fixed inputs into decision variables")
    required_scenarios = {str(item.get("scenario_id")): str(item.get("scope")) for item in expected_snapshot.get("required_scenarios", [])}
    actual_scenarios = {
        str(item.get("scenario_id")): item
        for item in run_manifest.get("scenario_coverage", [])
        if isinstance(item, dict)
    }
    uncovered = sorted(identifier for identifier in required_scenarios if not actual_scenarios.get(identifier, {}).get("covered"))
    if uncovered:
        issues.append(f"formal run does not cover required scenarios: {', '.join(uncovered)}")
    scope_rank = {"local-window": 0, "sampled": 1, "full": 2}
    for identifier, required_scope in required_scenarios.items():
        actual = actual_scenarios.get(identifier, {})
        if actual.get("covered") and scope_rank.get(str(actual.get("scope")), -1) < scope_rank.get(required_scope, 99):
            issues.append(f"formal scenario scope is narrower than required: {identifier}")
        if actual.get("covered") and root is not None and not _relative_artifact_exists(root, actual.get("result_locator")):
            issues.append(f"formal scenario evidence locator is missing or unreadable: {identifier}")
    return issues


def metric_evidence_issues(root: Path, question_payload: dict[str, Any], *, gate: str) -> list[str]:
    """Close the metric-to-run-to-claim-to-paper handoff at G4/G5."""

    bundle, load_issues = load_quality_bundle(root, question_payload)
    if load_issues:
        return load_issues
    contract_metrics = [
        item
        for item in bundle.get("metrics", {}).get("metrics", [])
        if isinstance(item, dict) and item.get("required")
    ]
    problem_id = str(question_payload.get("problem_id", ""))
    question_id = str(question_payload.get("question_id", ""))
    claims_path = root / "results" / problem_id / "claims.json"
    claims_payload: dict[str, Any] = {}
    if claims_path.is_file():
        value = json.loads(claims_path.read_text(encoding="utf-8"))
        claims_payload = value if isinstance(value, dict) else {}
    frozen = {
        str(item.get("id")): item
        for item in claims_payload.get("claims", [])
        if isinstance(item, dict)
        and item.get("question_id") == question_id
        and item.get("status") == "frozen"
    }
    paper = question_payload.get("paper", {}) if isinstance(question_payload.get("paper"), dict) else {}
    declared_tables = {str(value) for value in paper.get("table_ids", [])}
    declared_figures = {str(value) for value in paper.get("figure_ids", [])}
    paper_section = _paper_section_text(root, paper)
    table_blocks = _paper_table_blocks(root)
    figure_contracts = _figure_contracts_by_id(root)
    issues: list[str] = []
    for metric in contract_metrics:
        name = str(metric.get("name") or metric.get("id") or "metric")
        locator = str(metric.get("run_metric_locator") or metric.get("evidence_locator") or "")
        locator_path = locator.split(":", 1)[0]
        if not locator_path or not _relative_artifact_exists(root, locator_path):
            issues.append(f"metric has no readable run evidence locator: {name}")
        claim_ids = {str(value) for value in metric.get("claim_ids", []) if value}
        if not claim_ids:
            issues.append(f"metric has no frozen claim mapping: {name}")
        for claim_id in sorted(claim_ids):
            claim = frozen.get(claim_id)
            if claim is None:
                issues.append(f"metric claim is not frozen: {name}/{claim_id}")
            elif str(claim.get("unit", "")) != str(metric.get("unit", "")):
                issues.append(f"metric claim unit differs from contract: {name}/{claim_id}")
        reference_range = metric.get("reference_range")
        if isinstance(reference_range, list) and len(reference_range) == 2:
            actual_locator = str(metric.get("reference_actual_locator") or locator)
            actual_value = _structured_locator_value(root, actual_locator)
            if not isinstance(actual_value, (int, float)):
                issues.append(f"metric reference-range value is unresolved: {name}")
            elif not (float(reference_range[0]) <= float(actual_value) <= float(reference_range[1])) and not str(
                metric.get("out_of_range_explanation", "")
            ).strip():
                issues.append(f"metric is outside its reference range without explanation: {name}")
        if gate.lower() in {"g5", "g6"}:
            table_ids = {str(value) for value in metric.get("table_ids", []) if value}
            figure_ids = {str(value) for value in metric.get("figure_ids", []) if value}
            if not table_ids and not figure_ids:
                issues.append(f"metric has no paper table or figure mapping: {name}")
            unknown_tables = sorted(table_ids - declared_tables)
            unknown_figures = sorted(figure_ids - declared_figures)
            if unknown_tables:
                issues.append(f"metric table mapping is not declared by question: {name}/{', '.join(unknown_tables)}")
            if unknown_figures:
                issues.append(f"metric figure mapping is not declared by question: {name}/{', '.join(unknown_figures)}")
            if claim_ids and not any(_has_frozen_claim(paper_section, claim_id) for claim_id in claim_ids):
                issues.append(f"question section does not use a mapped frozen claim: {name}")
            for table_id in sorted(table_ids):
                block = table_blocks.get(table_id, "")
                if not block:
                    issues.append(f"metric table label is missing from paper sources: {name}/{table_id}")
                    continue
                if claim_ids and not any(_has_frozen_claim(block, claim_id) for claim_id in claim_ids):
                    issues.append(f"metric table does not use a mapped frozen claim: {name}/{table_id}")
                if not _paper_unit_is_bound(block, str(metric.get("unit", "")), claim_ids):
                    issues.append(f"metric table unit is not bound to the contract: {name}/{table_id}")
            for figure_id in sorted(figure_ids):
                contract = figure_contracts.get(figure_id)
                if contract is None:
                    issues.append(f"metric figure contract is missing: {name}/{figure_id}")
                    continue
                if str(contract.get("claim_id", "")) not in claim_ids:
                    issues.append(f"metric figure uses a different frozen claim: {name}/{figure_id}")
                if not _figure_unit_is_bound(contract, str(metric.get("unit", ""))):
                    issues.append(f"metric figure unit differs from the contract: {name}/{figure_id}")
    return issues


TABLE_ENV_RE = re.compile(
    r"\\begin\{(?P<kind>table\*?|longtable)\}(?P<body>.*?)\\end\{(?P=kind)\}",
    re.DOTALL,
)


def _paper_section_text(root: Path, paper: dict[str, Any]) -> str:
    value = paper.get("section")
    if not isinstance(value, str) or not RELATIVE_PATH_RE.fullmatch(value):
        return ""
    path = (root / "paper" / value).resolve()
    try:
        path.relative_to((root / "paper").resolve())
    except ValueError:
        return ""
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _paper_table_blocks(root: Path) -> dict[str, str]:
    blocks: dict[str, str] = {}
    paper_root = root / "paper"
    for folder in (paper_root / "sections", paper_root / "tables"):
        if not folder.is_dir():
            continue
        for path in sorted(folder.rglob("*.tex")):
            text = path.read_text(encoding="utf-8")
            for match in TABLE_ENV_RE.finditer(text):
                block = match.group(0)
                for label in re.findall(r"\\label\s*\{([^{}]+)\}", block):
                    blocks[label.strip()] = block
    return blocks


def _figure_contracts_by_id(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "paper" / "figure_contracts.yaml"
    if not path.is_file():
        return {}
    payload = _yaml_load(path)
    return {
        str(item.get("id")): item
        for item in payload.get("figures", [])
        if isinstance(item, dict) and item.get("id")
    }


def _has_frozen_claim(text: str, claim_id: str) -> bool:
    pattern = rf"\\FrozenClaim\s*\{{\s*{re.escape(claim_id)}\s*\}}"
    return bool(re.search(pattern, text))


def _has_frozen_claim_unit(text: str, claim_id: str) -> bool:
    pattern = rf"\\FrozenClaimUnit\s*\{{\s*{re.escape(claim_id)}\s*\}}"
    return bool(re.search(pattern, text))


def _normalise_tex_unit(value: str) -> str:
    return re.sub(r"[\\{}\s]", "", value).casefold()


def _paper_unit_is_bound(text: str, unit: str, claim_ids: set[str]) -> bool:
    if any(_has_frozen_claim_unit(text, claim_id) for claim_id in claim_ids):
        return True
    normalised_unit = _normalise_tex_unit(unit)
    return bool(normalised_unit) and normalised_unit in _normalise_tex_unit(text)


def _figure_unit_is_bound(contract: dict[str, Any], unit: str) -> bool:
    axes = contract.get("axes", [])
    units = {
        _normalise_tex_unit(str(item.get("unit", "")))
        for item in axes
        if isinstance(item, dict) and item.get("unit")
    }
    expected = _normalise_tex_unit(unit)
    return bool(expected) and expected in units


def _structured_locator_value(root: Path, locator: str) -> Any:
    if not locator:
        return None
    raw, _, selector = locator.partition(":")
    if not _relative_artifact_exists(root, raw):
        return None
    path = root / raw
    try:
        if path.suffix.lower() == ".json":
            value: Any = json.loads(path.read_text(encoding="utf-8"))
        elif path.suffix.lower() in {".yaml", ".yml"}:
            value = _yaml_load(path)
        else:
            return None
        for token in selector.split(".") if selector else []:
            value = value[int(token)] if isinstance(value, list) else value[token]
        return value
    except (OSError, ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError):
        return None
