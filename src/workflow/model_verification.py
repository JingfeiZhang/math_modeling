"""Pure model-verification report assembly for one competition question.

This module deliberately has no workflow-state side effects. It normalises the
V7.2 semantic, metric, and algorithm contract evidence against one run manifest.
A caller may persist the derived report or turn ``blocking_issues`` into a
transition gate. An optional run-level override remains available for tests and
future schema migration::

    model_verification:
      requirement_coverage: [{requirement_id, kind, covered, evidence_locator}]
      small_instance_oracle:
        {status, method, expected_known, matches_expected, evidence_locator}
      invariants: [{invariant_id, status, evidence_locator}]
      baseline_comparison:
        {status, metric_id, main_value, baseline_value, direction,
         evidence_locator, main_advantages, decision, rationale}
      task_specific_validation:
        {task_type, checks: [{id, status, evidence_locator}]}
      reproducibility:
        {status, replay_count, matches, evidence_locator}
      robustness:
        {status, dimensions, worst_case_reported, evidence_locator}

Legacy contracts remain readable. Missing V7.2 fields are compatibility
warnings unless ``verification_profile: 1`` opts the question into strict
Formal validation.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

PASS_STATES = {"PASS", "PASSED", "READY"}
CONSTRAINT_KINDS = {"hard", "boundary", "mutual_exclusion"}


def _objects(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _text(value: Any) -> str:
    return str(value or "").strip()


def _passed(value: Any) -> bool:
    if value is True:
        return True
    return _text(value).upper() in PASS_STATES


def _has_locator(item: dict[str, Any]) -> bool:
    return bool(_text(item.get("evidence_locator") or item.get("locator")))


def _quality_bundle(question: dict[str, Any], bundle: dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(bundle, dict):
        return bundle
    embedded = question.get("_quality_bundle")
    return embedded if isinstance(embedded, dict) else {}


def _task_type(question: dict[str, Any], bundle: dict[str, Any]) -> str:
    # A reviewed question profile is the authoritative task classification.  The
    # text heuristic below is retained only for legacy manifests without a
    # profile, so a word such as "prediction" in an optimization objective does
    # not accidentally activate prediction validation.
    profile = question.get("question_profile")
    if isinstance(profile, dict):
        task_types = {
            _text(item).casefold()
            for item in profile.get("task_types", [])
            if _text(item)
        }
        feature_tags = {
            _text(item).casefold()
            for item in profile.get("feature_tags", [])
            if _text(item)
        }
        active = {
            _text(item).casefold()
            for item in profile.get("active_checks", [])
            if _text(item)
        }
        inactive = {
            _text(item).casefold()
            for item in profile.get("not_applicable_checks", [])
            if _text(item)
        }
        if "prediction_delivery" in active or "prediction" in task_types or "forecast_target" in feature_tags:
            return "prediction"
        if "physical_state" in active or "mechanism" in task_types or "physical_constraints" in feature_tags:
            return "mechanistic"
        if {"classification", "evaluation"} & task_types or "classification_evaluation" in active:
            return "evaluation"
        if {"optimization", "scheduling", "decision", "multi_objective"} & task_types:
            return "optimization"
        # Explicitly marked non-applicability must suppress the legacy text
        # heuristic.  Use the generic validation family for the remaining task.
        if inactive or task_types:
            return "generic"
    semantic_task = bundle.get("semantics", {}).get("task", {})
    problem = question.get("problem", {})
    values = []
    if isinstance(semantic_task, dict):
        values.extend((semantic_task.get("type"), semantic_task.get("objective")))
    if isinstance(problem, dict):
        values.extend((problem.get("type"), problem.get("target")))
    text = " ".join(_text(value).casefold() for value in values)
    families = (
        ("prediction", ("predict", "forecast", "预测", "时间序列")),
        ("optimization", ("optim", "schedul", "routing", "优化", "调度", "路径", "决策")),
        ("mechanistic", ("mechan", "physical", "differential", "机理", "物理", "微分", "动力学")),
        ("evaluation", ("evaluat", "rank", "score", "评价", "排序", "综合得分")),
    )
    for family, tokens in families:
        if any(token in text for token in tokens):
            return family
    search_mode = _text(bundle.get("algorithm_evidence", {}).get("search_mode")).casefold()
    if search_mode == "forecast":
        return "prediction"
    if search_mode in {"exact", "heuristic", "stochastic", "hybrid"}:
        return "optimization"
    return "generic"


def _expected_requirements(bundle: dict[str, Any]) -> list[dict[str, str]]:
    semantics = bundle.get("semantics", {})
    metrics = bundle.get("metrics", {})
    coverage = _objects(semantics.get("requirement_coverage"))
    expected: list[dict[str, str]] = [
        {"requirement_id": _text(item.get("requirement_id")), "kind": "requirement"}
        for item in coverage
        if _text(item.get("requirement_id"))
    ]
    expected.extend(
        {"requirement_id": _text(item.get("id")), "kind": "output"}
        for item in _objects(semantics.get("outputs"))
        if item.get("required") is True and _text(item.get("id"))
    )
    expected.extend(
        {"requirement_id": _text(item.get("id") or item.get("name")), "kind": "metric"}
        for item in _objects(metrics.get("metrics"))
        if item.get("required") is True and _text(item.get("id") or item.get("name"))
    )
    expected.extend(
        {"requirement_id": _text(item.get("id")), "kind": "constraint"}
        for item in _objects(semantics.get("constraints"))
        if item.get("kind") in CONSTRAINT_KINDS and _text(item.get("id"))
    )
    expected.extend(
        {"requirement_id": _text(item.get("id")), "kind": "scenario"}
        for item in _objects(semantics.get("scenarios"))
        if item.get("required") is True and _text(item.get("id"))
    )
    return list({(item["kind"], item["requirement_id"]): item for item in expected}.values())


def _required_invariants(bundle: dict[str, Any]) -> list[str]:
    algorithm_invariants = _objects(bundle.get("algorithm_evidence", {}).get("invariants"))
    if algorithm_invariants:
        return [_text(item.get("id")) for item in algorithm_invariants if _text(item.get("id"))]
    return [
        _text(item.get("id"))
        for item in _objects(bundle.get("semantics", {}).get("constraints"))
        if item.get("kind") in CONSTRAINT_KINDS and _text(item.get("id"))
    ]


def _issue(code: str, section: str, detail: str) -> dict[str, str]:
    return {"code": code, "section": section, "detail": detail}


def _required_task_checks(task_type: str, bundle: dict[str, Any]) -> list[tuple[str, set[str]]]:
    groups: dict[str, list[tuple[str, set[str]]]] = {
        "prediction": [
            ("out_of_sample", {"out_of_sample", "rolling_validation", "blocked_validation", "group_validation"}),
            ("data_leakage", {"data_leakage", "leakage_check"}),
        ],
        "optimization": [
            ("feasibility", {"feasibility", "hard_constraints"}),
            (
                "search_quality",
                {"search_quality", "optimality_gap", "solver_status", "enumeration_coverage", "convergence"},
            ),
        ],
        "mechanistic": [
            ("dimensional_consistency", {"dimensional_consistency", "unit_consistency"}),
            ("boundary_conditions", {"boundary_conditions", "initial_boundary_conditions"}),
            ("conservation_or_limit_case", {"conservation", "limit_case", "conservation_or_limit_case"}),
        ],
        "evaluation": [
            ("indicator_direction", {"indicator_direction", "direction_check"}),
            ("sensitivity", {"weight_sensitivity", "normalization_sensitivity", "sensitivity"}),
            ("stability", {"ranking_stability", "stability"}),
        ],
        "generic": [("problem_validation", {"problem_validation", "out_of_sample", "scenario_validation"})],
    }
    required = list(groups[task_type])
    metrics = _objects(bundle.get("metrics", {}).get("metrics"))
    if task_type == "prediction" and any(
        item.get("required") is True and item.get("forecast_form") in {"interval", "quantile", "distribution"}
        for item in metrics
    ):
        required.append(("uncertainty_coverage", {"uncertainty_coverage", "interval_coverage", "calibration"}))
    return required


def _verification_profile(question: dict[str, Any], bundle: dict[str, Any]) -> int:
    candidates = [question.get("verification_profile"), bundle.get("verification_profile")]
    candidates.extend(
        contract.get("verification_profile")
        for contract in bundle.values()
        if isinstance(contract, dict)
    )
    return 1 if 1 in candidates else 0


def _contract_task_checks(bundle: dict[str, Any], task_type: str) -> list[dict[str, Any]]:
    metrics = bundle.get("metrics", {})
    algorithm = bundle.get("algorithm_evidence", {})
    protocol = metrics.get("validation_protocol")
    protocol = protocol if isinstance(protocol, dict) else {}
    invariants = _objects(algorithm.get("invariants"))
    robustness = _objects(algorithm.get("robustness"))
    evidence_type = _text(algorithm.get("evidence_type"))
    solver_locator = _text(algorithm.get("solver_evidence_locator") or algorithm.get("trace_locator"))
    documented_na = (
        protocol.get("applicable") is False
        and protocol.get("status") in {"READY", "VERIFIED"}
        and _text(protocol.get("not_applicable_reason"))
    )
    protocol_passed = (
        protocol.get("status") == "VERIFIED" and _text(protocol.get("evidence_locator"))
    ) or documented_na
    checks: list[dict[str, Any]] = []

    def add(identifier: str, passed: bool, locator: Any) -> None:
        checks.append({"id": identifier, "status": "PASS" if passed else "FAIL", "evidence_locator": _text(locator)})

    if task_type == "prediction":
        strategy = _text(protocol.get("strategy"))
        add(
            "out_of_sample",
            protocol_passed and strategy in {"holdout", "rolling-origin", "grouped", "spatial-block", "nested"},
            protocol.get("evidence_locator"),
        )
        add(
            "data_leakage",
            protocol_passed and bool([value for value in protocol.get("leakage_checks", []) if _text(value)]),
            protocol.get("evidence_locator"),
        )
        uncertainty_required = any(
            item.get("required") is True and item.get("forecast_form") in {"interval", "quantile", "distribution"}
            for item in _objects(metrics.get("metrics"))
        )
        if uncertainty_required:
            add(
                "uncertainty_coverage",
                protocol_passed and bool(protocol.get("uncertainty_outputs")),
                protocol.get("evidence_locator"),
            )
    elif task_type == "optimization":
        feasibility = [item for item in invariants if item.get("kind") == "feasibility"]
        add(
            "feasibility",
            bool(feasibility) and all(item.get("passed") is True and _has_locator(item) for item in feasibility),
            feasibility[0].get("evidence_locator") if feasibility else "",
        )
        add(
            evidence_type if evidence_type in {"optimality_gap", "solver_status", "enumeration_coverage"} else "search_quality",
            evidence_type in {"optimality_gap", "solver_status", "enumeration_coverage", "convergence_trace"}
            and bool(solver_locator),
            solver_locator,
        )
    elif task_type == "mechanistic":
        for identifier, kind in (
            ("dimensional_consistency", "dimensional"),
            ("boundary_conditions", "boundary"),
            ("conservation_or_limit_case", "conservation"),
        ):
            matches = [item for item in invariants if item.get("kind") == kind]
            add(
                identifier,
                (
                    bool(matches) and all(item.get("passed") is True and _has_locator(item) for item in matches)
                )
                or (
                    identifier == "conservation_or_limit_case"
                    and any(
                        item.get("applicable") is True
                        and item.get("method") == "known-limit"
                        and item.get("passed") is True
                        and _has_locator(item)
                        for item in _objects(algorithm.get("oracle_cases"))
                    )
                ),
                (
                    matches[0].get("evidence_locator")
                    if matches
                    else next(
                        (
                            item.get("evidence_locator")
                            for item in _objects(algorithm.get("oracle_cases"))
                            if item.get("method") == "known-limit"
                        ),
                        "",
                    )
                ),
            )
    elif task_type == "evaluation":
        required_metrics = [item for item in _objects(metrics.get("metrics")) if item.get("required") is True]
        add(
            "indicator_direction",
            bool(required_metrics) and all(_text(item.get("direction")) for item in required_metrics),
            protocol.get("evidence_locator"),
        )
        add(
            "sensitivity",
            bool(robustness) and all(item.get("passed") is True and _has_locator(item) for item in robustness),
            robustness[0].get("evidence_locator") if robustness else "",
        )
        add("stability", bool(protocol_passed), protocol.get("evidence_locator"))
    else:
        add("problem_validation", bool(protocol_passed), protocol.get("evidence_locator"))
    return checks


def _contract_verification(bundle: dict[str, Any], run_manifest: dict[str, Any], task_type: str) -> dict[str, Any]:
    """Normalise V7.2 contract evidence to the internal report interface."""

    semantics = bundle.get("semantics", {})
    metrics = bundle.get("metrics", {})
    algorithm = bundle.get("algorithm_evidence", {})
    coverage: list[dict[str, Any]] = []
    for item in _objects(semantics.get("requirement_coverage")):
        documented_na = item.get("status") == "not-applicable" and bool(_text(item.get("validation_method")))
        covered = item.get("status") == "verified" or documented_na
        locator = item.get("evidence_locator") or (
            "contract:requirement-not-applicable" if documented_na else ""
        )
        mappings = [("requirement", item.get("requirement_id"))]
        if item.get("output_id"):
            mappings.append(("output", item.get("output_id")))
        if item.get("metric_id"):
            mappings.append(("metric", item.get("metric_id")))
        mappings.extend(("constraint", value) for value in item.get("constraint_ids", []) if _text(value))
        mappings.extend(("scenario", value) for value in item.get("scenario_ids", []) if _text(value))
        coverage.extend(
            {
                "requirement_id": identifier,
                "kind": kind,
                "covered": covered,
                "evidence_locator": locator,
            }
            for kind, identifier in mappings
        )

    oracle_cases = _objects(algorithm.get("oracle_cases"))
    applicable_oracles = [item for item in oracle_cases if item.get("applicable") is True]
    documented_na = bool(oracle_cases) and not applicable_oracles and all(
        item.get("applicable") is False and _text(item.get("not_applicable_reason")) for item in oracle_cases
    )
    oracle_passed = bool(applicable_oracles) and all(
        item.get("passed") is True and _has_locator(item) and _text(item.get("expected_result"))
        for item in applicable_oracles
    )
    oracle = {
        "status": "PASS" if oracle_passed or documented_na else "FAIL",
        "method": ", ".join(_text(item.get("method")) for item in applicable_oracles) or "not-applicable",
        "expected_known": oracle_passed or documented_na,
        "matches_expected": oracle_passed or documented_na,
        "evidence_locator": (
            applicable_oracles[0].get("evidence_locator")
            if applicable_oracles
            else "contract:oracle-not-applicable" if documented_na else ""
        ),
        "not_applicable_reason": "; ".join(
            _text(item.get("not_applicable_reason")) for item in oracle_cases if item.get("applicable") is False
        ),
        "_explicit_failure": any(item.get("applicable") is True and item.get("passed") is False for item in oracle_cases),
    }

    invariants = [
        {
            "invariant_id": item.get("id"),
            "status": "PASS" if item.get("passed") is True else "FAIL",
            "evidence_locator": item.get("evidence_locator"),
            "_explicit_failure": item.get("passed") is False,
        }
        for item in _objects(algorithm.get("invariants"))
    ]

    comparisons = _objects(algorithm.get("model_comparison"))
    main = next((item for item in comparisons if item.get("role") == "main"), {})
    baseline = next((item for item in comparisons if item.get("role") == "baseline"), {})
    same_metric = bool(main and baseline) and main.get("primary_metric") == baseline.get("primary_metric")
    comparable = bool(main and baseline) and main.get("comparable_output") is True and baseline.get("comparable_output") is True
    comparison_ready = (
        comparable
        and same_metric
        and main.get("metric_value") is not None
        and baseline.get("metric_value") is not None
        and _has_locator(main)
        and _has_locator(baseline)
    )
    direction = next(
        (
            _text(item.get("direction"))
            for item in _objects(metrics.get("metrics"))
            if item.get("id") == main.get("primary_metric")
        ),
        "",
    )
    retained = next((item for item in comparisons if item.get("retained") is True), {})
    comparison = {
        "status": "PASS" if comparison_ready else "FAIL",
        "comparable": comparable,
        "metric_id": main.get("primary_metric"),
        "main_value": main.get("metric_value"),
        "baseline_value": baseline.get("metric_value"),
        "direction": direction,
        "evidence_locator": main.get("evidence_locator"),
        "main_advantages": [main.get("retained_reason") or main.get("improvement")]
        if main.get("retained") is True and (main.get("retained_reason") or main.get("improvement") is not None)
        else [],
        "decision": "baseline_selected" if retained.get("role") == "baseline" else "main_selected",
        "rationale": retained.get("retained_reason", ""),
        "_explicit_failure": any(item.get("comparable_output") is False for item in (main, baseline) if item),
    }

    search_mode = _text(algorithm.get("search_mode")).casefold()
    replay = run_manifest.get("replay")
    replay = replay if isinstance(replay, dict) else {}
    checks = run_manifest.get("checks")
    checks = checks if isinstance(checks, dict) else {}
    if search_mode == "stochastic":
        replay_count = int(algorithm.get("seed_count", 0) or 0)
        reproducible = replay_count >= 3 and len(algorithm.get("seed_runs", [])) >= 3
        replay_locator = _text(algorithm.get("seed_runs", [""])[0] if algorithm.get("seed_runs") else "")
    else:
        replay_count = int(replay.get("count", 0) or 0)
        reproducible = checks.get("deterministic") is True and replay_count >= 2
        replay_locator = "run_manifest:replay" if replay else ""

    robustness_items = _objects(algorithm.get("robustness"))
    robustness_passed = bool(robustness_items) and all(
        item.get("passed") is True and _has_locator(item) for item in robustness_items
    )
    robustness = {
        "status": "PASS" if robustness_passed else "FAIL",
        "dimensions": [item.get("perturbation") for item in robustness_items],
        "worst_case_reported": bool(robustness_items)
        and all(_text(item.get("result")) and _text(item.get("boundary")) for item in robustness_items),
        "evidence_locator": robustness_items[0].get("evidence_locator") if robustness_items else "",
        "_explicit_failure": any(item.get("passed") is False for item in robustness_items),
    }
    return {
        "requirement_coverage": coverage,
        "small_instance_oracle": oracle,
        "invariants": invariants,
        "baseline_comparison": comparison,
        "task_specific_validation": {
            "task_type": task_type,
            "checks": _contract_task_checks(bundle, task_type),
        },
        "reproducibility": {
            "status": "PASS" if reproducible else "FAIL",
            "replay_count": replay_count,
            "matches": reproducible,
            "evidence_locator": replay_locator,
        },
        "robustness": robustness,
    }


def _contract_evidence_locators(bundle: dict[str, Any]) -> list[tuple[str, str]]:
    """Collect only authored evidence pointers, excluding source and paper locators."""

    locators: list[tuple[str, str]] = []

    def add(section: str, value: Any) -> None:
        if _text(value):
            locators.append((section, _text(value)))

    semantics = bundle.get("semantics", {})
    metrics = bundle.get("metrics", {})
    algorithm = bundle.get("algorithm_evidence", {})
    for item in _objects(semantics.get("requirement_coverage")):
        add("requirement_coverage", item.get("evidence_locator"))
    protocol = metrics.get("validation_protocol")
    if isinstance(protocol, dict):
        add("task_specific_validation", protocol.get("evidence_locator"))
    for item in _objects(algorithm.get("oracle_cases")):
        if item.get("applicable") is True:
            add("small_instance_oracle", item.get("input_locator"))
            add("small_instance_oracle", item.get("evidence_locator"))
    for field, section in (
        ("invariants", "invariants"),
        ("model_comparison", "baseline_comparison"),
        ("robustness", "robustness"),
        ("scenario_coverage", "task_specific_validation"),
    ):
        for item in _objects(algorithm.get(field)):
            add(section, item.get("evidence_locator") or item.get("result_locator"))
    add("task_specific_validation", algorithm.get("trace_locator"))
    add("task_specific_validation", algorithm.get("solver_evidence_locator"))
    for locator in algorithm.get("seed_runs", []) if isinstance(algorithm.get("seed_runs"), list) else []:
        add("reproducibility", locator)
    return list(dict.fromkeys(locators))


def build_model_verification_report(
    question: dict[str, Any],
    quality_bundle: dict[str, Any] | None,
    run_manifest: dict[str, Any],
    *,
    strict_formal: bool = False,
    phase: str | None = None,
) -> dict[str, Any]:
    """Build a normalised, issue-coded report without mutating its inputs."""

    bundle = _quality_bundle(question, quality_bundle)
    task_type = _task_type(question, bundle)
    verification = _contract_verification(bundle, run_manifest, task_type)
    run_verification = run_manifest.get("model_verification")
    run_verification = run_verification if isinstance(run_verification, dict) else {}
    verification.update(run_verification)
    profile = _verification_profile(question, bundle)
    phase = _text(phase).casefold() or ("formal" if strict_formal else "exploration")
    if phase not in {"exploration", "candidate", "formal"}:
        raise ValueError("phase must be exploration, candidate, or formal")
    full_formal_enforcement = strict_formal and profile == 1
    blocking: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    def record(
        condition: bool,
        code: str,
        section: str,
        detail: str,
        *,
        critical: bool = True,
        explicit_failure: bool = False,
    ) -> None:
        if condition:
            return
        issue = _issue(code, section, detail)
        blocks_transition = (
            full_formal_enforcement and critical
        ) or (phase in {"candidate", "formal"} and explicit_failure)
        (blocking if blocks_transition else warnings).append(issue)

    if profile != 1 and not run_verification:
        record(
            False,
            "MODEL_VERIFICATION_EXTENSION_MISSING",
            "compatibility",
            "run manifest has no model_verification extension",
        )

    expected = _expected_requirements(bundle)
    coverage = _objects(verification.get("requirement_coverage"))
    coverage_map = {
        (_text(item.get("kind")), _text(item.get("requirement_id") or item.get("id"))): item
        for item in coverage
    }
    missing_requirements: list[str] = []
    failed_requirements: list[str] = []
    explicitly_failed_constraints: list[str] = []
    for requirement in expected:
        key = (requirement["kind"], requirement["requirement_id"])
        item = coverage_map.get(key) or coverage_map.get(("", requirement["requirement_id"]))
        label = f"{requirement['kind']}:{requirement['requirement_id']}"
        if item is None:
            missing_requirements.append(label)
        elif item.get("covered") is not True or not _has_locator(item):
            failed_requirements.append(label)
            if requirement["kind"] == "constraint" and item.get("covered") is False:
                explicitly_failed_constraints.append(label)
    record(
        not missing_requirements,
        "REQUIREMENT_COVERAGE_MISSING",
        "requirement_coverage",
        f"required items have no coverage record: {', '.join(missing_requirements)}",
    )
    record(
        not failed_requirements,
        "REQUIREMENT_COVERAGE_FAILED",
        "requirement_coverage",
        f"required items are uncovered or unlocated: {', '.join(failed_requirements)}",
        explicit_failure=bool(explicitly_failed_constraints),
    )

    oracle = verification.get("small_instance_oracle")
    oracle = oracle if isinstance(oracle, dict) else {}
    oracle_ready = bool(oracle) and (
        _passed(oracle.get("status"))
        and bool(_text(oracle.get("method")))
        and oracle.get("expected_known") is True
        and oracle.get("matches_expected") is True
        and _has_locator(oracle)
    )
    record(
        oracle_ready,
        "SMALL_INSTANCE_ORACLE_MISSING_OR_FAILED",
        "small_instance_oracle",
        "small-instance oracle must have a known expected result, match it, and cite evidence",
        explicit_failure=oracle.get("_explicit_failure") is True
        or (bool(run_verification.get("small_instance_oracle")) and (
            oracle.get("matches_expected") is False
            or (_text(oracle.get("status")) and not _passed(oracle.get("status")))
        )),
    )

    expected_invariants = _required_invariants(bundle)
    invariants = _objects(verification.get("invariants"))
    invariant_map = {_text(item.get("invariant_id") or item.get("id")): item for item in invariants}
    missing_invariants = [
        invariant_id
        for invariant_id in expected_invariants
        if invariant_id not in invariant_map
    ]
    failed_invariants = [
        invariant_id
        for invariant_id in expected_invariants
        if invariant_id in invariant_map
        and (
            not _passed(invariant_map[invariant_id].get("status"))
            or not _has_locator(invariant_map[invariant_id])
        )
    ]
    invalid_invariants = missing_invariants + failed_invariants
    record(
        not invalid_invariants,
        "INVARIANT_CHECK_MISSING_OR_FAILED",
        "invariants",
        f"hard or boundary invariants are not proven: {', '.join(invalid_invariants)}",
        explicit_failure=any(
            invariant_map[item].get("_explicit_failure") is True
            or (
                bool(run_verification.get("invariants"))
                and _text(invariant_map[item].get("status"))
                and not _passed(invariant_map[item].get("status"))
            )
            for item in failed_invariants
        ),
    )

    baseline = verification.get("baseline_comparison")
    baseline = baseline if isinstance(baseline, dict) else {}
    required_metrics = {
        _text(item.get("id") or item.get("name"))
        for item in _objects(bundle.get("metrics", {}).get("metrics"))
        if item.get("required") is True
    }
    baseline_metric = _text(baseline.get("metric_id") or baseline.get("metric"))
    manifest_checks = run_manifest.get("checks")
    manifest_checks = manifest_checks if isinstance(manifest_checks, dict) else {}
    comparable = baseline.get("comparable") is True or manifest_checks.get("baseline_comparable") is True
    baseline_ready = (
        _passed(baseline.get("status"))
        and comparable
        and baseline_metric in required_metrics
        and baseline.get("main_value") is not None
        and baseline.get("baseline_value") is not None
        and _text(baseline.get("direction")) in {"minimize", "maximize", "target", "report-only"}
        and _has_locator(baseline)
    )
    record(
        baseline_ready,
        "BASELINE_COMPARISON_INCOMPLETE",
        "baseline_comparison",
        "baseline must be comparable and report the same required metric, values, direction, and evidence",
        explicit_failure=baseline.get("_explicit_failure") is True
        or manifest_checks.get("baseline_comparable") is False
        or (
            bool(run_verification.get("baseline_comparison"))
            and (
                baseline.get("comparable") is False
            or (_text(baseline.get("status")) and not _passed(baseline.get("status")))
            or (bool(baseline_metric) and baseline_metric not in required_metrics)
            )
        ),
    )
    decision = _text(baseline.get("decision")).casefold()
    advantages = [value for value in baseline.get("main_advantages", []) if _text(value)] if isinstance(baseline.get("main_advantages"), list) else []
    selection_justified = bool(advantages) or (
        decision in {"baseline_selected", "simpler_model_selected"} and bool(_text(baseline.get("rationale")))
    )
    record(
        selection_justified,
        "MODEL_VALUE_NOT_DEMONSTRATED",
        "baseline_comparison",
        "the retained model has no demonstrated advantage and no justified simpler-model selection",
    )
    algorithm = bundle.get("algorithm_evidence", {})
    comparisons = _objects(algorithm.get("model_comparison"))
    challenger_justified = any(item.get("role") == "challenger" for item in comparisons) or bool(
        _text(algorithm.get("challenger_not_applicable_reason"))
    )
    record(
        challenger_justified,
        "CHALLENGER_JUSTIFICATION_MISSING",
        "baseline_comparison",
        "provide one lightweight challenger or a reviewed reason why it is not applicable",
    )

    task_validation = verification.get("task_specific_validation")
    task_validation = task_validation if isinstance(task_validation, dict) else {}
    task_checks = {
        _text(item.get("id")).casefold(): item for item in _objects(task_validation.get("checks")) if _text(item.get("id"))
    }
    missing_task_checks: list[str] = []
    for label, aliases in _required_task_checks(task_type, bundle):
        matching = [task_checks[alias] for alias in aliases if alias in task_checks]
        if not matching or not any(_passed(item.get("status")) and _has_locator(item) for item in matching):
            missing_task_checks.append(label)
    declared_task_type = _text(task_validation.get("task_type")).casefold()
    task_type_matches = not declared_task_type or declared_task_type == task_type
    record(
        task_type_matches,
        "TASK_TYPE_MISMATCH",
        "task_specific_validation",
        f"declared task type {declared_task_type or '<missing>'} differs from derived type {task_type}",
    )
    record(
        not missing_task_checks,
        "TASK_VALIDATION_INCOMPLETE",
        "task_specific_validation",
        f"{task_type} validation lacks: {', '.join(missing_task_checks)}",
    )

    reproducibility = verification.get("reproducibility")
    reproducibility = reproducibility if isinstance(reproducibility, dict) else {}
    stochastic = _text(algorithm.get("search_mode")).casefold() == "stochastic"
    minimum_replays = 3 if stochastic else 2
    replay_count = int(reproducibility.get("replay_count", 0) or 0)
    reproducible = (
        _passed(reproducibility.get("status"))
        and reproducibility.get("matches") is True
        and replay_count >= minimum_replays
        and _has_locator(reproducibility)
    )
    record(
        reproducible,
        "REPRODUCIBILITY_INCOMPLETE",
        "reproducibility",
        f"reproducibility needs {minimum_replays} matching runs and an evidence locator",
    )

    robustness = verification.get("robustness")
    robustness = robustness if isinstance(robustness, dict) else {}
    dimensions = [value for value in robustness.get("dimensions", []) if _text(value)] if isinstance(robustness.get("dimensions"), list) else []
    robust = (
        _passed(robustness.get("status"))
        and bool(dimensions)
        and robustness.get("worst_case_reported") is True
        and _has_locator(robustness)
    )
    record(
        robust,
        "ROBUSTNESS_INCOMPLETE_OR_FAILED",
        "robustness",
        "robustness must cover at least one perturbation, report the worst case, and cite evidence",
    )

    if manifest_checks.get("core_constraints_passed") is False:
        record(
            False,
            "CORE_CONSTRAINTS_FAILED",
            "run",
            "run manifest reports failed core constraints",
            explicit_failure=True,
        )
    if run_manifest.get("status") not in {None, "PASS"}:
        record(
            False,
            "RUN_NOT_PASSING",
            "run",
            "run manifest status is not PASS",
            explicit_failure=True,
        )
    if phase == "formal" and run_manifest.get("run_mode") not in {None, "formal"}:
        record(False, "RUN_NOT_FORMAL", "run", "strict Formal verification requires run_mode=formal")

    scope = algorithm.get("scope") if isinstance(algorithm, dict) else {}
    scope = scope if isinstance(scope, dict) else {}
    claim_boundaries = [_text(value) for value in scope.get("claim_language", []) if _text(value)]
    if scope.get("coverage_mode") == "local-window" and not claim_boundaries:
        claim_boundaries.append("Only local-window improvement may be reported.")

    status = "BLOCK_TRANSITION" if blocking else "PASS_WITH_WARNINGS" if warnings else "READY"
    checks = {
        "requirement_coverage": {
            "expected": expected,
            "covered_count": len(expected) - len(missing_requirements) - len(failed_requirements),
            "missing": missing_requirements,
            "failed": failed_requirements,
        },
        "small_instance_oracle": {"passed": oracle_ready, "method": _text(oracle.get("method"))},
        "invariants": {"required": expected_invariants, "missing": missing_invariants, "failed": failed_invariants},
        "baseline_comparison": {
            "passed": baseline_ready,
            "selection_justified": selection_justified,
            "challenger_justified": challenger_justified,
        },
        "task_specific_validation": {"task_type": task_type, "missing": missing_task_checks},
        "reproducibility": {"passed": reproducible, "minimum_replays": minimum_replays, "actual_replays": replay_count},
        "robustness": {"passed": robust, "dimensions": dimensions},
    }
    return {
        "schema_version": 1,
        "problem_id": _text(run_manifest.get("problem_id") or question.get("problem_id")),
        "question_id": _text(run_manifest.get("question_id") or question.get("question_id")),
        "run_id": _text(run_manifest.get("run_id")),
        "phase": phase,
        "strict_formal": strict_formal and profile == 1,
        "verification_profile": profile,
        "compatibility_mode": profile != 1,
        "task_type": task_type,
        "status": status,
        "checks": checks,
        "sections": checks,
        "claim_boundaries": claim_boundaries,
        "blocking_issues": blocking,
        "warnings": warnings,
    }


def evaluate_model_verification(
    root: Path,
    question_payload: dict[str, Any],
    bundle: dict[str, Any] | None,
    run_manifest: dict[str, Any],
    manifest_path: Path | str | None = None,
    *,
    strict: bool = False,
    phase: str | None = None,
) -> dict[str, Any]:
    """Workflow-facing wrapper that adds a project-relative source locator."""

    report = build_model_verification_report(
        question_payload,
        bundle,
        run_manifest,
        strict_formal=strict,
        phase=phase,
    )
    if manifest_path is not None:
        source = Path(manifest_path)
        if not source.is_absolute():
            source = root / source
        try:
            report["source_manifest"] = source.resolve().relative_to(root.resolve()).as_posix()
        except ValueError as exc:
            raise ValueError("manifest_path must remain within the project root") from exc
        if source.is_file():
            report["source_manifest_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
        else:
            issue = _issue("SOURCE_MANIFEST_MISSING", "source_manifest", "source run manifest does not exist")
            target = report["blocking_issues"] if strict and report.get("verification_profile") == 1 else report["warnings"]
            target.append(issue)

    locator_issues: list[dict[str, str]] = []
    for section, locator in _contract_evidence_locators(bundle or _quality_bundle(question_payload, None)):
        locator_path = locator.split(":", 1)[0]
        candidate = (root / locator_path).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            locator_issues.append(
                _issue("EVIDENCE_LOCATOR_ESCAPES_PROJECT", section, f"evidence locator escapes project root: {locator}")
            )
            continue
        if not candidate.is_file():
            locator_issues.append(
                _issue("EVIDENCE_LOCATOR_MISSING", section, f"evidence locator is missing: {locator}")
            )
    if locator_issues:
        target = report["blocking_issues"] if strict and report.get("verification_profile") == 1 else report["warnings"]
        target.extend(locator_issues)
    report["status"] = (
        "BLOCK_TRANSITION"
        if report["blocking_issues"]
        else "PASS_WITH_WARNINGS"
        if report["warnings"]
        else "READY"
    )
    return report


def write_model_verification_report(root: Path, report: dict[str, Any]) -> Path:
    """Persist a derived report under output/_verification, never as evidence."""

    errors = validate_model_verification_report(report)
    if errors:
        raise ValueError("; ".join(errors))
    parts = [_text(report.get(field)) for field in ("problem_id", "question_id", "run_id")]
    if any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", part) for part in parts):
        raise ValueError("report identifiers are not safe path segments")
    destination = root / "output" / "_verification" / "model-verification" / parts[0] / parts[1] / parts[2]
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "model_verification_report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def validate_model_verification_report(report: dict[str, Any]) -> list[str]:
    """Return structural errors for a generated or deserialised report."""

    errors: list[str] = []
    if report.get("schema_version") != 1:
        errors.append("model verification report schema_version must be 1")
    if report.get("status") not in {"READY", "PASS_WITH_WARNINGS", "BLOCK_TRANSITION"}:
        errors.append("model verification report status is invalid")
    for field in ("problem_id", "question_id", "run_id", "task_type"):
        if not _text(report.get(field)):
            errors.append(f"model verification report {field} is missing")
    if not isinstance(report.get("sections"), dict):
        errors.append("model verification report sections must be an object")
    for field in ("blocking_issues", "warnings"):
        if not isinstance(report.get(field), list):
            errors.append(f"model verification report {field} must be an array")
    if report.get("status") == "BLOCK_TRANSITION" and not report.get("blocking_issues"):
        errors.append("BLOCK_TRANSITION report must contain blocking issues")
    if report.get("status") == "READY" and (report.get("blocking_issues") or report.get("warnings")):
        errors.append("READY report cannot contain issues")
    source_digest = report.get("source_manifest_sha256")
    if source_digest is not None and not re.fullmatch(r"[0-9a-f]{64}", _text(source_digest)):
        errors.append("model verification source_manifest_sha256 must be a SHA-256")
    return errors
