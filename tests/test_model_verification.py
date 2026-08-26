from __future__ import annotations

from copy import deepcopy

from src.workflow.model_verification import (
    build_model_verification_report,
    evaluate_model_verification,
    validate_model_verification_report,
    write_model_verification_report,
)


def quality_bundle(task_type: str = "prediction", *, search_mode: str = "forecast") -> dict:
    return {
        "semantics": {
            "task": {"type": task_type, "objective": "solve the stated task"},
            "outputs": [{"id": "answer", "required": True}],
            "constraints": [{"id": "capacity", "kind": "hard"}],
            "scenarios": [{"id": "base", "required": True, "coverage_mode": "full"}],
        },
        "metrics": {
            "metrics": [
                {
                    "id": "mae",
                    "name": "MAE",
                    "required": True,
                    "direction": "minimize",
                    "forecast_form": "point",
                }
            ]
        },
        "algorithm_evidence": {
            "verification_profile": 1,
            "search_mode": search_mode,
            "challenger_not_applicable_reason": "the baseline is the only useful lightweight challenger",
            "scope": {"coverage_mode": "full", "claim_language": ["validated on the declared scenarios"]},
        },
    }


def contract_only_bundle() -> dict:
    bundle = quality_bundle()
    bundle["semantics"]["verification_profile"] = 1
    bundle["semantics"]["requirement_coverage"] = [
        {
            "requirement_id": "req-answer",
            "source_locator": "problem.txt:Q1",
            "output_id": "answer",
            "metric_id": "mae",
            "constraint_ids": ["capacity"],
            "scenario_ids": ["base"],
            "validation_method": "rolling-origin",
            "evidence_locator": "evidence/requirements.json:req-answer",
            "status": "verified",
        }
    ]
    bundle["metrics"].update(
        verification_profile=1,
        validation_protocol={
            "status": "VERIFIED",
            "applicable": True,
            "strategy": "rolling-origin",
            "split_unit": "time",
            "holdout_scope": "last window",
            "leakage_checks": ["features use past data only"],
            "primary_metric_ids": ["mae"],
            "uncertainty_outputs": [],
            "acceptance_criteria": [
                {
                    "id": "beat-baseline",
                    "metric_id": "mae",
                    "comparator": "baseline",
                    "operator": "less-than",
                    "rationale": "main model should reduce error",
                }
            ],
            "evidence_locator": "evidence/validation.json:summary",
        },
    )
    bundle["algorithm_evidence"].update(
        oracle_cases=[
            {
                "id": "tiny",
                "applicable": True,
                "method": "hand-calculation",
                "input_locator": "evidence/oracle-input.json",
                "expected_result": "mae=0",
                "passed": True,
                "evidence_locator": "evidence/oracle.json:tiny",
            }
        ],
        invariants=[
            {
                "id": "capacity",
                "kind": "feasibility",
                "statement": "capacity is respected",
                "check_method": "assertion",
                "passed": True,
                "evidence_locator": "evidence/invariants.json:capacity",
            }
        ],
        model_comparison=[
            {
                "id": "base",
                "model_id": "naive",
                "role": "baseline",
                "comparable_output": True,
                "primary_metric": "mae",
                "metric_value": 2.0,
                "evidence_locator": "evidence/comparison.json:base",
            },
            {
                "id": "main",
                "model_id": "main",
                "role": "main",
                "comparable_output": True,
                "primary_metric": "mae",
                "metric_value": 1.0,
                "improvement": 0.5,
                "retained": True,
                "retained_reason": "lower out-of-sample MAE",
                "evidence_locator": "evidence/comparison.json:main",
            },
        ],
        robustness=[
            {
                "id": "noise",
                "perturbation": "input noise",
                "metric": "mae",
                "result": "within tolerance",
                "boundary": "noise <= 5%",
                "passed": True,
                "evidence_locator": "evidence/robustness.json:noise",
            }
        ],
    )
    return bundle


def complete_verification(task_type: str = "prediction") -> dict:
    task_checks = {
        "prediction": ["rolling_validation", "data_leakage", "residual_diagnostics"],
        "optimization": ["feasibility", "optimality_gap"],
        "mechanistic": ["dimensional_consistency", "boundary_conditions", "conservation"],
        "evaluation": ["indicator_direction", "weight_sensitivity", "ranking_stability"],
        "generic": ["problem_validation"],
    }[task_type]
    return {
        "requirement_coverage": [
            {"requirement_id": "answer", "kind": "output", "covered": True, "evidence_locator": "results.json:answer"},
            {"requirement_id": "mae", "kind": "metric", "covered": True, "evidence_locator": "results.json:mae"},
            {"requirement_id": "capacity", "kind": "constraint", "covered": True, "evidence_locator": "checks.json:capacity"},
            {"requirement_id": "base", "kind": "scenario", "covered": True, "evidence_locator": "scenarios.json:base"},
        ],
        "small_instance_oracle": {
            "status": "PASS",
            "method": "manual enumeration",
            "expected_known": True,
            "matches_expected": True,
            "evidence_locator": "verification.json:oracle",
        },
        "invariants": [{"invariant_id": "capacity", "status": "PASS", "evidence_locator": "checks.json:capacity"}],
        "baseline_comparison": {
            "status": "PASS",
            "comparable": True,
            "metric_id": "mae",
            "main_value": 1.0,
            "baseline_value": 2.0,
            "direction": "minimize",
            "evidence_locator": "results.json:comparison",
            "main_advantages": ["lower MAE"],
            "decision": "main_selected",
            "rationale": "lower error",
        },
        "task_specific_validation": {
            "task_type": task_type,
            "checks": [
                {"id": check, "status": "PASS", "evidence_locator": f"validation.json:{check}"}
                for check in task_checks
            ],
        },
        "reproducibility": {
            "status": "PASS",
            "replay_count": 2,
            "matches": True,
            "evidence_locator": "replay.json:summary",
        },
        "robustness": {
            "status": "PASS",
            "dimensions": ["capacity perturbation"],
            "worst_case_reported": True,
            "evidence_locator": "robustness.json:summary",
        },
    }


def manifest(verification: dict | None, *, schema_version: int = 2, search_mode: str = "forecast") -> dict:
    value = {
        "schema_version": schema_version,
        "problem_id": "C",
        "question_id": "Q1",
        "run_id": "formal-1",
        "run_mode": "formal",
        "status": "PASS",
        "checks": {"baseline_comparable": True, "deterministic": search_mode != "stochastic"},
    }
    if verification is not None:
        value["model_verification"] = verification
    return value


def test_complete_prediction_report_is_ready_and_pure() -> None:
    question = {"problem_id": "C", "question_id": "Q1", "problem": {"type": "prediction"}}
    bundle = quality_bundle()
    run = manifest(complete_verification())
    before = deepcopy((question, bundle, run))

    report = build_model_verification_report(question, bundle, run, strict_formal=True)

    assert report["status"] == "READY"
    assert report["blocking_issues"] == []
    assert report["warnings"] == []
    assert report["sections"]["requirement_coverage"]["covered_count"] == 4
    assert report["claim_boundaries"] == ["validated on the declared scenarios"]
    assert validate_model_verification_report(report) == []
    assert (question, bundle, run) == before


def test_question_profile_overrides_legacy_text_task_detection() -> None:
    question = {
        "problem_id": "C",
        "question_id": "Q1",
        "problem": {"type": "optimization", "target": "预测压力下的资源配置"},
        "question_profile": {
            "task_types": ["optimization"],
            "active_checks": ["problem_interface"],
            "not_applicable_checks": ["prediction_delivery"],
        },
    }
    report = build_model_verification_report(
        question,
        quality_bundle("optimization", search_mode="exact"),
        manifest(None, search_mode="exact"),
        strict_formal=False,
    )
    assert report["sections"]["task_specific_validation"]["task_type"] == "optimization"


def test_question_profile_feature_tags_activate_specialized_validation() -> None:
    question = {
        "problem_id": "C",
        "question_id": "Q1",
        "problem": {"type": "analysis", "target": "状态分析"},
        "question_profile": {
            "task_types": ["analysis"],
            "feature_tags": ["physical_constraints"],
        },
    }
    report = build_model_verification_report(
        question,
        quality_bundle("analysis", search_mode="hybrid"),
        manifest(None, search_mode="hybrid"),
        strict_formal=False,
    )
    assert report["sections"]["task_specific_validation"]["task_type"] == "mechanistic"


def test_contract_only_formal_evidence_is_ready_without_run_extension() -> None:
    run = manifest(None)
    run["replay"] = {"required": True, "count": 2}
    report = build_model_verification_report(
        {"problem_id": "C", "question_id": "Q1", "problem": {"type": "prediction"}},
        contract_only_bundle(),
        run,
        strict_formal=True,
        phase="formal",
    )
    assert report["status"] == "READY"
    assert report["warnings"] == []
    assert report["checks"]["small_instance_oracle"]["passed"] is True


def test_contract_only_explicit_oracle_and_baseline_failure_block_formal() -> None:
    bundle = contract_only_bundle()
    bundle["algorithm_evidence"]["oracle_cases"][0]["passed"] = False
    bundle["algorithm_evidence"]["model_comparison"][0]["comparable_output"] = False
    run = manifest(None)
    run["replay"] = {"required": True, "count": 2}
    report = build_model_verification_report(
        {"problem_id": "C", "question_id": "Q1", "problem": {"type": "prediction"}},
        bundle,
        run,
        strict_formal=True,
    )
    codes = {item["code"] for item in report["blocking_issues"]}
    assert "SMALL_INSTANCE_ORACLE_MISSING_OR_FAILED" in codes
    assert "BASELINE_COMPARISON_INCOMPLETE" in codes


def test_requirement_coverage_cannot_omit_required_output_mapping() -> None:
    bundle = contract_only_bundle()
    bundle["semantics"]["requirement_coverage"][0].pop("output_id")
    run = manifest(None)
    run["replay"] = {"required": True, "count": 2}
    report = build_model_verification_report(
        {"problem_id": "C", "question_id": "Q1", "problem": {"type": "prediction"}},
        bundle,
        run,
        strict_formal=True,
    )
    assert any(
        item["code"] == "REQUIREMENT_COVERAGE_MISSING" and "output:answer" in item["detail"]
        for item in report["blocking_issues"]
    )


def test_formal_requires_challenger_or_omission_reason() -> None:
    bundle = contract_only_bundle()
    bundle["algorithm_evidence"]["challenger_not_applicable_reason"] = ""
    run = manifest(None)
    run["replay"] = {"required": True, "count": 2}
    report = build_model_verification_report(
        {"problem_id": "C", "question_id": "Q1", "problem": {"type": "prediction"}},
        bundle,
        run,
        strict_formal=True,
    )
    assert any(item["code"] == "CHALLENGER_JUSTIFICATION_MISSING" for item in report["blocking_issues"])


def test_legacy_manifest_without_extension_is_compatibility_warning() -> None:
    report = build_model_verification_report(
        {"problem_id": "C", "question_id": "Q1"},
        {},
        manifest(None, schema_version=1),
        strict_formal=True,
    )

    assert report["status"] == "PASS_WITH_WARNINGS"
    assert report["compatibility_mode"] is True
    assert report["blocking_issues"] == []
    assert any(item["code"] == "MODEL_VERIFICATION_EXTENSION_MISSING" for item in report["warnings"])


def test_old_contract_without_profile_stays_warning_only_in_formal() -> None:
    bundle = quality_bundle()
    bundle["algorithm_evidence"].pop("verification_profile")
    report = build_model_verification_report(
        {"problem_id": "C", "question_id": "Q1"},
        bundle,
        manifest(None),
        strict_formal=True,
    )
    assert report["verification_profile"] == 0
    assert report["status"] == "PASS_WITH_WARNINGS"
    assert report["blocking_issues"] == []


def test_modern_strict_formal_blocks_missing_contract_verification_evidence() -> None:
    report = build_model_verification_report(
        {"problem_id": "C", "question_id": "Q1"},
        quality_bundle(),
        manifest(None),
        strict_formal=True,
    )

    assert report["status"] == "BLOCK_TRANSITION"
    codes = {item["code"] for item in report["blocking_issues"]}
    assert "REQUIREMENT_COVERAGE_MISSING" in codes
    assert "SMALL_INSTANCE_ORACLE_MISSING_OR_FAILED" in codes
    assert "REPRODUCIBILITY_INCOMPLETE" in codes


def test_non_strict_modeling_turns_all_gaps_into_warnings() -> None:
    report = build_model_verification_report(
        {"problem_id": "C", "question_id": "Q1"},
        quality_bundle(),
        manifest({}),
        strict_formal=False,
    )

    assert report["status"] == "PASS_WITH_WARNINGS"
    assert report["blocking_issues"] == []
    assert any(item["code"] == "REQUIREMENT_COVERAGE_MISSING" for item in report["warnings"])


def test_candidate_blocks_explicit_failures_but_not_missing_full_evidence() -> None:
    run = manifest(
        {
            "small_instance_oracle": {"status": "FAIL", "matches_expected": False},
            "baseline_comparison": {"status": "FAIL", "comparable": False, "metric_id": "mae"},
        }
    )
    run["checks"]["core_constraints_passed"] = False
    report = build_model_verification_report(
        {"problem_id": "C", "question_id": "Q1"},
        quality_bundle(),
        run,
        phase="candidate",
    )
    codes = {item["code"] for item in report["blocking_issues"]}
    assert codes >= {
        "SMALL_INSTANCE_ORACLE_MISSING_OR_FAILED",
        "BASELINE_COMPARISON_INCOMPLETE",
        "CORE_CONSTRAINTS_FAILED",
    }
    assert any(item["code"] == "REPRODUCIBILITY_INCOMPLETE" for item in report["warnings"])


def test_candidate_uses_manifest_baseline_and_constraint_failures_without_extension() -> None:
    run = manifest(None)
    run["checks"].update(baseline_comparable=False, core_constraints_passed=False)
    report = build_model_verification_report(
        {"problem_id": "C", "question_id": "Q1"},
        quality_bundle(),
        run,
        phase="candidate",
    )
    codes = {item["code"] for item in report["blocking_issues"]}
    assert "BASELINE_COMPARISON_INCOMPLETE" in codes
    assert "CORE_CONSTRAINTS_FAILED" in codes
    assert any(item["code"] == "REPRODUCIBILITY_INCOMPLETE" for item in report["warnings"])


def test_failed_oracle_invariant_and_requirement_block_only_the_report() -> None:
    verification = complete_verification()
    verification["small_instance_oracle"]["matches_expected"] = False
    verification["invariants"][0]["status"] = "FAIL"
    verification["requirement_coverage"][0]["covered"] = False

    report = build_model_verification_report(
        {"problem_id": "C", "question_id": "Q1"},
        quality_bundle(),
        manifest(verification),
        strict_formal=True,
    )

    codes = {item["code"] for item in report["blocking_issues"]}
    assert codes >= {
        "REQUIREMENT_COVERAGE_FAILED",
        "SMALL_INSTANCE_ORACLE_MISSING_OR_FAILED",
        "INVARIANT_CHECK_MISSING_OR_FAILED",
    }


def test_baseline_requires_same_metric_and_model_value_argument() -> None:
    verification = complete_verification()
    comparison = verification["baseline_comparison"]
    comparison["metric_id"] = "different"
    comparison["main_advantages"] = []
    comparison["decision"] = "main_selected"

    report = build_model_verification_report(
        {"problem_id": "C", "question_id": "Q1"},
        quality_bundle(),
        manifest(verification),
        strict_formal=True,
    )

    codes = {item["code"] for item in report["blocking_issues"]}
    assert "BASELINE_COMPARISON_INCOMPLETE" in codes
    assert "MODEL_VALUE_NOT_DEMONSTRATED" in codes


def test_prediction_interval_requires_calibration_or_coverage() -> None:
    bundle = quality_bundle()
    bundle["metrics"]["metrics"][0]["forecast_form"] = "interval"
    report = build_model_verification_report(
        {"problem_id": "C", "question_id": "Q1"},
        bundle,
        manifest(complete_verification()),
        strict_formal=True,
    )

    assert report["sections"]["task_specific_validation"]["missing"] == ["uncertainty_coverage"]
    assert any(item["code"] == "TASK_VALIDATION_INCOMPLETE" for item in report["blocking_issues"])


def test_exact_optimization_accepts_gap_check_instead_of_convergence() -> None:
    bundle = quality_bundle("optimization", search_mode="exact")
    verification = complete_verification("optimization")
    report = build_model_verification_report(
        {"problem_id": "C", "question_id": "Q1", "problem": {"type": "optimization"}},
        bundle,
        manifest(verification),
        strict_formal=True,
    )

    assert report["status"] == "READY"


def test_stochastic_search_requires_three_matching_replays() -> None:
    bundle = quality_bundle("optimization", search_mode="stochastic")
    verification = complete_verification("optimization")
    run = manifest(verification, search_mode="stochastic")

    failed = build_model_verification_report(
        {"problem_id": "C", "question_id": "Q1", "problem": {"type": "optimization"}},
        bundle,
        run,
        strict_formal=True,
    )
    assert failed["sections"]["reproducibility"]["minimum_replays"] == 3
    assert any(item["code"] == "REPRODUCIBILITY_INCOMPLETE" for item in failed["blocking_issues"])

    run["model_verification"]["reproducibility"]["replay_count"] = 3
    passed = build_model_verification_report(
        {"problem_id": "C", "question_id": "Q1", "problem": {"type": "optimization"}},
        bundle,
        run,
        strict_formal=True,
    )
    assert passed["status"] == "READY"


def test_report_structure_validation_rejects_inconsistent_ready_status() -> None:
    report = {
        "schema_version": 1,
        "problem_id": "C",
        "question_id": "Q1",
        "run_id": "r1",
        "task_type": "prediction",
        "status": "READY",
        "sections": {},
        "blocking_issues": [],
        "warnings": [{"code": "X"}],
    }
    assert "READY report cannot contain issues" in validate_model_verification_report(report)
    report["source_manifest_sha256"] = "not-a-hash"
    assert "model verification source_manifest_sha256 must be a SHA-256" in validate_model_verification_report(report)


def test_workflow_wrapper_and_writer_use_verification_output_only(tmp_path) -> None:
    manifest_path = tmp_path / "experiments/C/Q1/formal/formal-1/run_manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text("{}\n", encoding="utf-8")
    report = evaluate_model_verification(
        tmp_path,
        {"problem_id": "C", "question_id": "Q1"},
        quality_bundle(),
        manifest(complete_verification()),
        "experiments/C/Q1/formal/formal-1/run_manifest.json",
        strict=True,
    )
    path = write_model_verification_report(tmp_path, report)
    assert report["source_manifest"] == "experiments/C/Q1/formal/formal-1/run_manifest.json"
    assert len(report["source_manifest_sha256"]) == 64
    assert path.relative_to(tmp_path).as_posix() == (
        "output/_verification/model-verification/C/Q1/formal-1/model_verification_report.json"
    )
    assert not (tmp_path / "state").exists()
    assert not (tmp_path / "results").exists()


def test_evaluate_blocks_missing_contract_evidence_locator_in_strict_profile(tmp_path) -> None:
    run = manifest(None)
    run["replay"] = {"required": True, "count": 2}
    report = evaluate_model_verification(
        tmp_path,
        {"problem_id": "C", "question_id": "Q1", "problem": {"type": "prediction"}},
        contract_only_bundle(),
        run,
        strict=True,
        phase="formal",
    )
    assert report["status"] == "BLOCK_TRANSITION"
    assert any(item["code"] == "EVIDENCE_LOCATOR_MISSING" for item in report["blocking_issues"])
