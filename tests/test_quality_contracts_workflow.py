from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

from src.workflow.competition_workflow import checkpoint, initialize, model_verify, promote, quickcheck, record_run
from src.workflow.quality_contracts import (
    abstract_text_issues,
    metric_evidence_issues,
    refresh_quality_contract_references,
    transition_contract_issues,
)


ROOT = Path(__file__).resolve().parents[1]


def dump_yaml(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")


def make_v7_root(root: Path, problem_text: str = "问题一 完成一个评价输出。") -> Path:
    dump_yaml(root / "contest.yaml", {"competition": "CUMCM", "year": 2026, "problem": "TBD"})
    dump_yaml(root / "project.yaml", {"project_id": "fixture-v7", "workflow_contract_version": 7})
    for relative in ("config/workflow.yaml", "skills.lock.yaml", "templates/figures/figure_contract_v2.schema.json", "templates/figures/figure_contract_v2.template.yaml"):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        source = ROOT / relative
        if source.is_file():
            shutil.copy2(source, target)
        else:
            target.write_text("{}\n", encoding="utf-8")
    (root / "templates/workflow").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "templates/workflow/question.yaml", root / "templates/workflow/question.yaml")
    decision = ROOT / "skill_staging/handsomeZR-mathmodel-skill/templates/shared/decision_log.json"
    target_decision = root / "skill_staging/handsomeZR-mathmodel-skill/templates/shared/decision_log.json"
    target_decision.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(decision, target_decision)
    problem = root / "problems/input.txt"
    problem.parent.mkdir(parents=True, exist_ok=True)
    problem.write_text(problem_text, encoding="utf-8")
    initialize(root, "C", problem, workspace_root=ROOT)
    return root / "problems/C/questions/Q1/question.yaml"


def test_v7_initialize_creates_quality_contract_refs(tmp_path: Path) -> None:
    question_path = make_v7_root(tmp_path)
    payload = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    assert set(payload["quality_contracts"]) == {"semantics", "metrics", "algorithm_evidence", "abstract"}
    for reference in payload["quality_contracts"].values():
        assert (tmp_path / reference["path"]).is_file()


def test_candidate_transition_blocks_missing_required_metric(tmp_path: Path) -> None:
    question_path = make_v7_root(tmp_path)
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    refs = question["quality_contracts"]
    for name in ("semantics", "metrics"):
        path = tmp_path / refs[name]["path"]
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
        value["status"] = "READY"
        if name == "semantics":
            value["outputs"] = [{"id": "answer", "type": "scalar", "unit": "u", "required": True}]
        else:
            value["metrics"] = [{"id": "m", "name": "score", "formula": "x", "direction": "minimize", "unit": "u", "required": True, "baseline": "base"}]
        path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")
    issues = transition_contract_issues(tmp_path, question, transition="candidate", workspace_root=ROOT)
    assert not any("required metric" in item for item in issues)


def test_formal_transition_rejects_unbounded_stochastic_search(tmp_path: Path) -> None:
    question_path = make_v7_root(tmp_path)
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    path = tmp_path / question["quality_contracts"]["algorithm_evidence"]["path"]
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    value.update({"status": "READY", "search_mode": "stochastic", "evidence_type": "none", "seed_count": 1})
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")
    issues = transition_contract_issues(tmp_path, question, transition="formal", workspace_root=ROOT)
    assert any("convergence trace" in item or "three seeds" in item for item in issues)


def test_contract_source_hash_drift_is_reported(tmp_path: Path) -> None:
    question_path = make_v7_root(tmp_path)
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    (tmp_path / "problems" / "input.txt").write_text("题面已发生变化。", encoding="utf-8")
    issues = transition_contract_issues(tmp_path, question, transition="candidate", workspace_root=ROOT)
    assert any("source_problem hash drift" in item for item in issues)


def test_question_required_metric_cannot_be_replaced_by_unrelated_metric(tmp_path: Path) -> None:
    question_path = make_v7_root(tmp_path)
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    question["problem"]["evaluation_metrics"] = ["运行成本"]
    question_path.write_text(yaml.safe_dump(question, allow_unicode=True, sort_keys=False), encoding="utf-8")
    metrics_path = tmp_path / question["quality_contracts"]["metrics"]["path"]
    metrics = yaml.safe_load(metrics_path.read_text(encoding="utf-8"))
    metrics.update({
        "status": "READY",
        "metrics": [{"id": "score", "name": "综合得分", "formula": "x", "direction": "minimize", "unit": "分", "required": True, "baseline": "base"}],
    })
    metrics_path.write_text(yaml.safe_dump(metrics, allow_unicode=True, sort_keys=False), encoding="utf-8")
    issues = transition_contract_issues(tmp_path, question, transition="candidate", workspace_root=ROOT)
    assert any("question-required metric" in item for item in issues)


def test_fixed_load_cannot_be_declared_as_decision_input(tmp_path: Path) -> None:
    question_path = make_v7_root(tmp_path)
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    path = tmp_path / question["quality_contracts"]["semantics"]["path"]
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    value.update({
        "status": "READY",
        "inputs": [{"id": "fixed_load", "role": "decision", "unit": "kW", "source": "problem"}],
        "outputs": [{"id": "answer", "type": "scalar", "unit": "u", "required": True}],
    })
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")
    issues = transition_contract_issues(tmp_path, question, transition="candidate", workspace_root=ROOT)
    assert any("fixed load-like input" in item for item in issues)


def test_pareto_contract_requires_multiple_reported_alternatives(tmp_path: Path) -> None:
    question_path = make_v7_root(tmp_path)
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    path = tmp_path / question["quality_contracts"]["algorithm_evidence"]["path"]
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    value.update({
        "status": "READY",
        "objective_mode": "pareto",
        "scenario_coverage": [
            {"scenario_id": "w1", "covered": True, "scope": "full"},
            {"scenario_id": "w2", "covered": True, "scope": "full"},
        ],
    })
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")
    issues = transition_contract_issues(tmp_path, question, transition="formal", workspace_root=ROOT)
    assert any("three reported alternatives" in item for item in issues)


def test_exact_solver_can_use_optimality_gap_without_convergence_trace(tmp_path: Path) -> None:
    question_path = make_v7_root(tmp_path)
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    path = tmp_path / question["quality_contracts"]["algorithm_evidence"]["path"]
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    evidence = tmp_path / "experiments/C/Q1/evidence/solver.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps({"status": "OPTIMAL", "gap": 0.0}), encoding="utf-8")
    value.update(
        {
            "status": "READY",
            "search_mode": "exact",
            "evidence_type": "optimality_gap",
            "solver_evidence_locator": "experiments/C/Q1/evidence/solver.json",
        }
    )
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")
    issues = transition_contract_issues(tmp_path, question, transition="formal", workspace_root=ROOT)
    assert not any("exact search needs" in item for item in issues)
    assert not any("solver evidence locator" in item for item in issues)


def test_local_window_requires_explicit_boundary(tmp_path: Path) -> None:
    question_path = make_v7_root(tmp_path)
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    path = tmp_path / question["quality_contracts"]["algorithm_evidence"]["path"]
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    value.update({"status": "READY", "scope": {"coverage_mode": "local-window", "claim_language": [], "window": ""}})
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")
    issues = transition_contract_issues(tmp_path, question, transition="formal", workspace_root=ROOT)
    assert any("local-window scope" in item for item in issues)


def test_local_window_with_explicit_claim_boundary_is_accepted(tmp_path: Path) -> None:
    question_path = make_v7_root(tmp_path)
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    evidence = tmp_path / "experiments/C/Q1/evidence/solver.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps({"status": "OPTIMAL", "gap": 0.0}), encoding="utf-8")
    path = tmp_path / question["quality_contracts"]["algorithm_evidence"]["path"]
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    value.update(
        {
            "status": "READY",
            "solver_evidence_locator": "experiments/C/Q1/evidence/solver.json",
            "scope": {
                "coverage_mode": "local-window",
                "window": "72h",
                "claim_language": ["72 小时局部窗口结果"],
                "forbidden_language": ["全时域最优", "全局最优"],
            },
        }
    )
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")
    issues = transition_contract_issues(tmp_path, question, transition="formal", workspace_root=ROOT)
    assert not any("local-window scope" in item for item in issues)


def test_abstract_contract_requires_method_result_validation_and_boundary_for_each_question(tmp_path: Path) -> None:
    question_path = make_v7_root(tmp_path)
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    path = tmp_path / question["quality_contracts"]["abstract"]["path"]
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    value.update({"status": "READY", "questions": [{"question_id": "Q1", "method_required": True, "subject_required": True, "conclusion_required": False, "validation_required": True, "boundary_required": True, "claim_ids": []}]})
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")
    issues = transition_contract_issues(tmp_path, question, transition="g5", workspace_root=ROOT)
    assert any("abstract question coverage is incomplete" in item for item in issues)


def test_abstract_contract_requires_result_when_result_tracking_is_enabled(tmp_path: Path) -> None:
    question_path = make_v7_root(tmp_path)
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    path = tmp_path / question["quality_contracts"]["abstract"]["path"]
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    value.update(
        {
            "status": "READY",
            "questions": [
                {
                    "question_id": "Q1",
                    "method_required": True,
                    "subject_required": True,
                    "result_required": True,
                    "conclusion_required": True,
                    "validation_required": True,
                    "boundary_required": True,
                    "method": "method",
                    "subject": "subject",
                    "result": "",
                    "conclusion": "conclusion",
                    "validation": "validation",
                    "boundary": "boundary",
                    "claim_ids": ["q1"],
                }
            ],
            "final_summary": {"contribution": "contribution", "limitation": "limitation"},
        }
    )
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")
    refresh_quality_contract_references(tmp_path, "C", "Q1")
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    issues = transition_contract_issues(tmp_path, question, transition="g5", workspace_root=ROOT)
    assert any("abstract synthesis fields are incomplete" in item and "result" in item for item in issues)


def prepare_candidate_contracts(root: Path, *, unit: str = "u", fixed_input: bool = False) -> Path:
    question_path = root / "problems/C/questions/Q1/question.yaml"
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    question["problem"].update(
        {
            "type": "optimization",
            "inputs": ["load"],
            "outputs": ["answer"],
            "constraints": ["load is fixed"],
            "evaluation_metrics": ["score"],
        }
    )
    question_path.write_text(yaml.safe_dump(question, allow_unicode=True, sort_keys=False), encoding="utf-8")
    refs = question["quality_contracts"]
    semantics_path = root / refs["semantics"]["path"]
    semantics = yaml.safe_load(semantics_path.read_text(encoding="utf-8"))
    semantics.update(
        {
            "status": "READY",
            "inputs": [
                {
                    "id": "load",
                    "role": "fixed" if fixed_input else "observed",
                    "unit": "kW",
                    "source": "problem",
                    "fixed_by_statement": fixed_input,
                }
            ],
            "outputs": [{"id": "answer", "type": "scalar", "unit": unit, "required": True}],
            "scenarios": [{"id": "base", "required": True, "coverage_mode": "full"}],
        }
    )
    semantics_path.write_text(yaml.safe_dump(semantics, allow_unicode=True, sort_keys=False), encoding="utf-8")
    metrics_path = root / refs["metrics"]["path"]
    metrics = yaml.safe_load(metrics_path.read_text(encoding="utf-8"))
    metrics.update(
        {
            "status": "READY",
            "metrics": [
                {
                    "id": "score",
                    "name": "score",
                    "formula": "sum(cost)",
                    "direction": "minimize",
                    "unit": unit,
                    "aggregation": "sum",
                    "time_window": "full",
                    "required": True,
                    "baseline": "base",
                }
            ],
        }
    )
    metrics_path.write_text(yaml.safe_dump(metrics, allow_unicode=True, sort_keys=False), encoding="utf-8")
    solver_evidence = root / "experiments/C/Q1/evidence/solver.json"
    solver_evidence.parent.mkdir(parents=True, exist_ok=True)
    solver_evidence.write_text(json.dumps({"status": "OPTIMAL", "gap": 0.0}), encoding="utf-8")
    algorithm_path = root / refs["algorithm_evidence"]["path"]
    algorithm = yaml.safe_load(algorithm_path.read_text(encoding="utf-8"))
    algorithm.update(
        {
            "status": "READY",
            "search_mode": "exact",
            "evidence_type": "optimality_gap",
            "solver_evidence_locator": "experiments/C/Q1/evidence/solver.json",
        }
    )
    algorithm_path.write_text(yaml.safe_dump(algorithm, allow_unicode=True, sort_keys=False), encoding="utf-8")
    refresh_quality_contract_references(root, "C")
    return question_path


def write_candidate_run(
    root: Path,
    *,
    unit: str = "u",
    fixed_input: bool = False,
    cover_scenario: bool = True,
) -> Path:
    runner = root / "src/q1.py"
    runner.parent.mkdir(parents=True, exist_ok=True)
    runner.write_text("print('ok')\n", encoding="utf-8")
    run_root = root / "experiments/C/Q1/candidate/run-quality"
    run_root.mkdir(parents=True, exist_ok=True)
    result = run_root / "results.json"
    result.write_text(json.dumps({"score": 12.0}), encoding="utf-8")
    config = root / "experiments/configs/run-quality.yaml"
    dump_yaml(
        config,
        {
            "schema_version": 2,
            "experiment_id": "run-quality",
            "problem": "C",
            "question": "Q1",
            "engine": "python",
            "runner": "src/q1.py",
            "seed": 20260825,
            "output_root": "experiments/C/Q1/candidate",
            "arguments": [],
            "diagnostic_arguments": [],
            "run_mode": "candidate",
            "level": "candidate",
            "mode": "probe",
            "purpose": "candidate",
            "formal_candidate": True,
            "primary_metric": "score",
            "input_roles": [{"id": "load", "role": "fixed" if fixed_input else "observed"}],
            "model_variables": ([{"id": "load", "role": "decision", "source_input_id": "load"}] if fixed_input else []),
            "scenario_coverage": ([{"scenario_id": "base", "covered": True, "scope": "full", "result_locator": "experiments/C/Q1/candidate/run-quality/results.json"}] if cover_scenario else []),
            "checks": {
                "input_output_match": True,
                "units_defined": True,
                "core_constraints_passed": True,
                "deterministic": True,
                "baseline_comparable": True,
            },
            "reuse_contract": {"seed": False, "environment": False, "code": False, "inputs": False, "methods": False, "parameters": False},
            "replay": {"required": True, "count": 2},
            "methods": [{"name": "main", "role": "main"}, {"name": "base", "role": "baseline"}],
            "inputs": [],
            "metrics": [{"name": "score", "unit": unit, "locator": "results.json:score", "primary": True}],
        },
    )
    record_run(root, config, ["python", "src/q1.py"], {"python": "3.13"}, "2026-08-25T00:00:00+00:00", 0.1, True)
    return config


def test_quickcheck_warns_but_does_not_block_draft_quality_contracts(tmp_path: Path) -> None:
    make_v7_root(tmp_path)
    write_candidate_run(tmp_path, cover_scenario=False)
    report = quickcheck(tmp_path, "C", "Q1")
    assert report["passed"] is True
    assert any(item["name"] == "QUALITY_CONTRACT_INCOMPLETE" for item in report["warnings"])


def test_model_verify_writes_only_a_derived_candidate_report(tmp_path: Path) -> None:
    make_v7_root(tmp_path)
    prepare_candidate_contracts(tmp_path)
    write_candidate_run(tmp_path)
    state_before = (tmp_path / "state/decision_log.json").read_bytes()

    report = model_verify(tmp_path, "C", "Q1", "run-quality")

    assert report["passed"] is True
    assert report["status"] == "PASS_WITH_WARNINGS"
    assert (tmp_path / report["report"]).is_file()
    assert (tmp_path / "state/decision_log.json").read_bytes() == state_before


def test_checkpoint_blocks_an_explicit_failed_oracle_only_for_that_transition(tmp_path: Path) -> None:
    question_path = make_v7_root(tmp_path)
    prepare_candidate_contracts(tmp_path)
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    algorithm_path = tmp_path / question["quality_contracts"]["algorithm_evidence"]["path"]
    algorithm = yaml.safe_load(algorithm_path.read_text(encoding="utf-8"))
    algorithm["oracle_cases"] = [
        {
            "id": "tiny",
            "applicable": True,
            "method": "hand-calculation",
            "expected_result": "score=0",
            "passed": False,
            "evidence_locator": "experiments/C/Q1/evidence/solver.json",
        }
    ]
    algorithm_path.write_text(yaml.safe_dump(algorithm, allow_unicode=True, sort_keys=False), encoding="utf-8")
    refresh_quality_contract_references(tmp_path, "C", "Q1")
    write_candidate_run(tmp_path)

    report = checkpoint(tmp_path, "C", "Q1")

    assert report["passed"] is False
    assert any("small-instance oracle" in item["detail"] for item in report["checks"])
    assert (tmp_path / "experiments/C/Q1/candidate/run-quality/run_manifest.json").is_file()


def test_promote_creates_formal_run_but_leaves_incomplete_verification_for_g3(tmp_path: Path) -> None:
    make_v7_root(tmp_path)
    prepare_candidate_contracts(tmp_path)
    write_candidate_run(tmp_path)
    assert checkpoint(tmp_path, "C", "Q1")["passed"] is True

    report = promote(tmp_path, "C", "Q1", "run-quality")

    assert report["status"] == "FORMAL"
    assert report["outcome"] == "G3_REVIEW_REQUIRED"
    assert report["model_verification_status"] == "BLOCK_TRANSITION"
    assert (tmp_path / report["model_verification"]).is_file()


def test_promote_rewrites_quality_contract_evidence_locators_to_formal_run(tmp_path: Path) -> None:
    question_path = make_v7_root(tmp_path)
    prepare_candidate_contracts(tmp_path)
    write_candidate_run(tmp_path)
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    candidate_prefix = "experiments/C/Q1/candidate/run-quality"
    formal_prefix = "experiments/C/Q1/formal/run-quality"
    result_locator = f"{candidate_prefix}/results.json:score"

    semantics_path = tmp_path / question["quality_contracts"]["semantics"]["path"]
    semantics = yaml.safe_load(semantics_path.read_text(encoding="utf-8"))
    semantics["requirement_coverage"] = [
        {
            "requirement_id": "answer-required",
            "source_locator": "problem statement",
            "output_id": "answer",
            "metric_id": "score",
            "validation_method": "known result",
            "evidence_locator": result_locator,
            "status": "verified",
        }
    ]
    semantics["outputs"][0]["source_locator"] = f"{candidate_prefix}/statement-only.txt"
    dump_yaml(semantics_path, semantics)

    metrics_path = tmp_path / question["quality_contracts"]["metrics"]["path"]
    metrics = yaml.safe_load(metrics_path.read_text(encoding="utf-8"))
    metrics["metrics"][0].update(
        {
            "evidence_locator": result_locator,
            "run_metric_locator": result_locator,
            "reference_actual_locator": result_locator,
        }
    )
    metrics["validation_protocol"] = {
        "status": "VERIFIED",
        "applicable": True,
        "strategy": "scenario",
        "primary_metric_ids": ["score"],
        "acceptance_criteria": [
            {
                "id": "score-check",
                "metric_id": "score",
                "comparator": "baseline",
                "operator": "less-or-equal",
                "rationale": "compare the same output",
            }
        ],
        "evidence_locator": result_locator,
    }
    dump_yaml(metrics_path, metrics)

    algorithm_path = tmp_path / question["quality_contracts"]["algorithm_evidence"]["path"]
    algorithm = yaml.safe_load(algorithm_path.read_text(encoding="utf-8"))
    algorithm.update(
        {
            "trace_locator": result_locator,
            "solver_evidence_locator": result_locator,
            "seed_runs": [result_locator, result_locator],
            "scenario_coverage": [
                {"scenario_id": "base", "covered": True, "scope": "full", "result_locator": result_locator}
            ],
            "oracle_cases": [
                {
                    "id": "tiny",
                    "applicable": True,
                    "method": "hand-calculation",
                    "input_locator": result_locator,
                    "expected_result": "score=12",
                    "passed": True,
                    "evidence_locator": result_locator,
                }
            ],
            "invariants": [
                {
                    "id": "feasible",
                    "kind": "feasibility",
                    "statement": "all hard constraints hold",
                    "check_method": "direct check",
                    "passed": True,
                    "evidence_locator": result_locator,
                }
            ],
            "model_comparison": [
                {
                    "id": "baseline",
                    "model_id": "base",
                    "role": "baseline",
                    "comparable_output": True,
                    "primary_metric": "score",
                    "metric_value": 15.0,
                    "evidence_locator": result_locator,
                },
                {
                    "id": "main",
                    "model_id": "main",
                    "role": "main",
                    "comparable_output": True,
                    "primary_metric": "score",
                    "metric_value": 12.0,
                    "retained": True,
                    "retained_reason": "lower score",
                    "evidence_locator": result_locator,
                },
            ],
            "robustness": [
                {
                    "id": "load-perturbation",
                    "perturbation": "load +/- 5%",
                    "metric": "score",
                    "result": "feasible",
                    "boundary": "+/- 5%",
                    "passed": True,
                    "evidence_locator": result_locator,
                }
            ],
        }
    )
    dump_yaml(algorithm_path, algorithm)
    refresh_quality_contract_references(tmp_path, "C", "Q1")
    assert checkpoint(tmp_path, "C", "Q1")["passed"] is True

    report = promote(tmp_path, "C", "Q1", "run-quality")

    assert set(report["quality_contracts_rewritten"]) == {
        question["quality_contracts"]["semantics"]["path"],
        question["quality_contracts"]["metrics"]["path"],
        question["quality_contracts"]["algorithm_evidence"]["path"],
    }
    for contract_path in (semantics_path, metrics_path, algorithm_path):
        contract_text = contract_path.read_text(encoding="utf-8")
        assert result_locator not in contract_text
        assert f"{formal_prefix}/results.json:score" in contract_text
    promoted_semantics = yaml.safe_load(semantics_path.read_text(encoding="utf-8"))
    assert promoted_semantics["outputs"][0]["source_locator"] == f"{candidate_prefix}/statement-only.txt"
    promoted_manifest = json.loads((tmp_path / report["manifest"]).read_text(encoding="utf-8"))
    refreshed_question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    assert promoted_manifest["quality_contract_snapshot"]["contract_hashes"] == {
        name: refreshed_question["quality_contracts"][name]["sha256"]
        for name in ("semantics", "metrics", "algorithm_evidence")
    }
    verification = json.loads((tmp_path / report["model_verification"]).read_text(encoding="utf-8"))
    assert not any(item["code"] == "EVIDENCE_LOCATOR_MISSING" for item in verification["blocking_issues"])
    assert (tmp_path / formal_prefix / "results.json").is_file()


def test_checkpoint_can_bind_reviewed_contracts_after_candidate_run(tmp_path: Path) -> None:
    make_v7_root(tmp_path)
    write_candidate_run(tmp_path)
    prepare_candidate_contracts(tmp_path)
    report = checkpoint(tmp_path, "C", "Q1", strict=True)
    assert report["passed"] is True


def test_checkpoint_blocks_metric_unit_mismatch(tmp_path: Path) -> None:
    make_v7_root(tmp_path)
    prepare_candidate_contracts(tmp_path, unit="万元")
    write_candidate_run(tmp_path, unit="元")
    report = checkpoint(tmp_path, "C", "Q1", strict=True)
    assert report["passed"] is False
    assert any("metric unit differs" in item["detail"] for item in report["checks"])


def test_checkpoint_blocks_uncovered_required_scenario(tmp_path: Path) -> None:
    make_v7_root(tmp_path)
    prepare_candidate_contracts(tmp_path)
    write_candidate_run(tmp_path, cover_scenario=False)
    report = checkpoint(tmp_path, "C", "Q1", strict=True)
    assert report["passed"] is False
    assert any("required scenarios" in item["detail"] for item in report["checks"])


def test_checkpoint_blocks_fixed_input_used_as_decision_variable(tmp_path: Path) -> None:
    make_v7_root(tmp_path)
    prepare_candidate_contracts(tmp_path, fixed_input=True)
    write_candidate_run(tmp_path, fixed_input=True)
    report = checkpoint(tmp_path, "C", "Q1", strict=True)
    assert report["passed"] is False
    assert any("fixed inputs" in item["detail"] for item in report["checks"])


def test_contract_drift_after_checkpoint_blocks_promotion(tmp_path: Path) -> None:
    make_v7_root(tmp_path)
    question_path = prepare_candidate_contracts(tmp_path)
    write_candidate_run(tmp_path)
    assert checkpoint(tmp_path, "C", "Q1", strict=True)["passed"] is True
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    metric_path = tmp_path / question["quality_contracts"]["metrics"]["path"]
    metric = yaml.safe_load(metric_path.read_text(encoding="utf-8"))
    metric["metrics"][0]["aggregation"] = "daily-sum"
    metric_path.write_text(yaml.safe_dump(metric, allow_unicode=True, sort_keys=False), encoding="utf-8")
    refresh_quality_contract_references(tmp_path, "C", "Q1")
    try:
        promote(tmp_path, "C", "Q1", "run-quality")
    except ValueError as exc:
        assert "contract hashes have drifted" in str(exc) or "metric definitions differ" in str(exc)
    else:
        raise AssertionError("promotion must reject a changed quality contract")


def test_abstract_question_set_detects_change_in_another_question(tmp_path: Path) -> None:
    question_path = make_v7_root(tmp_path, "问题一 完成评价。\n问题二 完成优化。")
    q2_path = tmp_path / "problems/C/questions/Q2/question.yaml"
    q2 = yaml.safe_load(q2_path.read_text(encoding="utf-8"))
    q2["problem"]["target"] = "发生变化的第二问接口"
    q2_path.write_text(yaml.safe_dump(q2, allow_unicode=True, sort_keys=False), encoding="utf-8")
    q1 = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    issues = transition_contract_issues(tmp_path, q1, transition="candidate", workspace_root=ROOT)
    assert any("abstract question member hash drift: Q2" in item for item in issues)
    assert not any("metrics.source_question hash drift" in item for item in issues)


def test_prediction_contract_requires_target_horizon_and_window(tmp_path: Path) -> None:
    question_path = make_v7_root(tmp_path)
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    question["problem"]["type"] = "prediction"
    question["problem"]["evaluation_metrics"] = ["score"]
    question_path.write_text(yaml.safe_dump(question, allow_unicode=True, sort_keys=False), encoding="utf-8")
    refresh_quality_contract_references(tmp_path, "C", "Q1")
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    metrics_path = tmp_path / question["quality_contracts"]["metrics"]["path"]
    metrics = yaml.safe_load(metrics_path.read_text(encoding="utf-8"))
    metrics.update({
        "status": "READY",
        "metrics": [{"id": "score", "name": "score", "formula": "mae", "direction": "minimize", "unit": "u", "required": True, "baseline": "base"}],
    })
    metrics_path.write_text(yaml.safe_dump(metrics, allow_unicode=True, sort_keys=False), encoding="utf-8")
    refresh_quality_contract_references(tmp_path, "C", "Q1")
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    issues = transition_contract_issues(tmp_path, question, transition="candidate", workspace_root=ROOT)
    assert any("prediction metric lacks target" in item for item in issues)


def test_question_profile_can_disable_heuristic_prediction_detection(tmp_path: Path) -> None:
    question_path = make_v7_root(tmp_path)
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    question["problem"]["type"] = "optimization"
    question["problem"]["target"] = "预测压力下的资源配置"
    question["question_profile"] = {
        "task_types": ["optimization"],
        "feature_tags": [],
        "active_checks": ["problem_interface"],
        "not_applicable_checks": ["prediction_delivery"],
        "status": "READY",
        "source": "manual_and_derived",
    }
    question_path.write_text(yaml.safe_dump(question, allow_unicode=True, sort_keys=False), encoding="utf-8")
    refresh_quality_contract_references(tmp_path, "C", "Q1")
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    metrics_path = tmp_path / question["quality_contracts"]["metrics"]["path"]
    metrics = yaml.safe_load(metrics_path.read_text(encoding="utf-8"))
    metrics["status"] = "READY"
    metrics["metrics"] = [{"id": "score", "name": "score", "formula": "x", "direction": "minimize", "unit": "u", "required": True, "baseline": "base"}]
    metrics_path.write_text(yaml.safe_dump(metrics, allow_unicode=True, sort_keys=False), encoding="utf-8")
    refresh_quality_contract_references(tmp_path, "C", "Q1")
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    issues = transition_contract_issues(tmp_path, question, transition="candidate", workspace_root=ROOT)
    assert not any("prediction metric lacks target" in item for item in issues)


def test_reference_range_requires_explanation_when_formal_value_is_outside(tmp_path: Path) -> None:
    question_path = make_v7_root(tmp_path)
    prepare_candidate_contracts(tmp_path)
    result = tmp_path / "experiments/C/Q1/formal/run/results.json"
    result.parent.mkdir(parents=True, exist_ok=True)
    result.write_text(json.dumps({"score": 12.0}), encoding="utf-8")
    claims = tmp_path / "results/C/claims.json"
    claims.parent.mkdir(parents=True, exist_ok=True)
    claims.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "problem_id": "C",
                "claims": [
                    {"id": "q1-score", "question_id": "Q1", "status": "frozen", "unit": "u", "value": 12.0}
                ],
            }
        ),
        encoding="utf-8",
    )
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    question["paper"]["table_ids"] = ["tab-q1-score"]
    question_path.write_text(yaml.safe_dump(question, allow_unicode=True, sort_keys=False), encoding="utf-8")
    metric_path = tmp_path / question["quality_contracts"]["metrics"]["path"]
    metric = yaml.safe_load(metric_path.read_text(encoding="utf-8"))
    metric["metrics"][0].update(
        {
            "run_metric_locator": "experiments/C/Q1/formal/run/results.json:score",
            "claim_ids": ["q1-score"],
            "table_ids": ["tab-q1-score"],
            "reference_range": [0.0, 10.0],
            "reference_source": "standard",
            "reference_actual_locator": "experiments/C/Q1/formal/run/results.json:score",
            "out_of_range_explanation": "",
        }
    )
    metric_path.write_text(yaml.safe_dump(metric, allow_unicode=True, sort_keys=False), encoding="utf-8")
    refresh_quality_contract_references(tmp_path, "C", "Q1")
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    issues = metric_evidence_issues(tmp_path, question, gate="g5")
    assert any("outside its reference range" in item for item in issues)


def test_metric_table_and_body_must_use_the_mapped_frozen_claim(tmp_path: Path) -> None:
    question_path = make_v7_root(tmp_path)
    prepare_candidate_contracts(tmp_path)
    result = tmp_path / "experiments/C/Q1/formal/run/results.json"
    result.parent.mkdir(parents=True, exist_ok=True)
    result.write_text(json.dumps({"score": 12.0}), encoding="utf-8")
    claims = tmp_path / "results/C/claims.json"
    claims.parent.mkdir(parents=True, exist_ok=True)
    claims.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "problem_id": "C",
                "claims": [
                    {
                        "id": "q1-score",
                        "question_id": "Q1",
                        "status": "frozen",
                        "unit": "u",
                        "value": 12.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    question["paper"]["table_ids"] = ["tab-q1-score"]
    question_path.write_text(
        yaml.safe_dump(question, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    metric_path = tmp_path / question["quality_contracts"]["metrics"]["path"]
    metric = yaml.safe_load(metric_path.read_text(encoding="utf-8"))
    metric["metrics"][0].update(
        {
            "run_metric_locator": "experiments/C/Q1/formal/run/results.json:score",
            "claim_ids": ["q1-score"],
            "table_ids": ["tab-q1-score"],
        }
    )
    metric_path.write_text(
        yaml.safe_dump(metric, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    section = tmp_path / "paper" / question["paper"]["section"]
    section.parent.mkdir(parents=True, exist_ok=True)
    section.write_text(
        "结果为 11 u。\\begin{table}\\caption{主结果}"
        "\\begin{tabular}{cc}指标&数值（u）\\\\score&11\\end{tabular}"
        "\\label{tab-q1-score}\\end{table}",
        encoding="utf-8",
    )
    refresh_quality_contract_references(tmp_path, "C", "Q1")
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    issues = metric_evidence_issues(tmp_path, question, gate="g5")
    assert any("question section does not use a mapped frozen claim" in item for item in issues)
    assert any("metric table does not use a mapped frozen claim" in item for item in issues)

    section.write_text(
        "结果为 \\FrozenClaim{q1-score}\\FrozenClaimUnit{q1-score}。"
        "\\begin{table}\\caption{主结果}"
        "\\begin{tabular}{cc}指标&数值\\\\score&"
        "\\FrozenClaim{q1-score}\\FrozenClaimUnit{q1-score}\\end{tabular}"
        "\\label{tab-q1-score}\\end{table}",
        encoding="utf-8",
    )
    issues = metric_evidence_issues(tmp_path, question, gate="g5")
    assert not any("mapped frozen claim" in item for item in issues)
    assert not any("table unit is not bound" in item for item in issues)


def test_metric_figure_claim_and_unit_must_match_the_contract(tmp_path: Path) -> None:
    question_path = make_v7_root(tmp_path)
    prepare_candidate_contracts(tmp_path)
    result = tmp_path / "experiments/C/Q1/formal/run/results.json"
    result.parent.mkdir(parents=True, exist_ok=True)
    result.write_text(json.dumps({"score": 12.0}), encoding="utf-8")
    claims = tmp_path / "results/C/claims.json"
    claims.parent.mkdir(parents=True, exist_ok=True)
    claims.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "problem_id": "C",
                "claims": [
                    {
                        "id": "q1-score",
                        "question_id": "Q1",
                        "status": "frozen",
                        "unit": "u",
                        "value": 12.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    question["paper"]["figure_ids"] = ["fig-q1-score"]
    question_path.write_text(
        yaml.safe_dump(question, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    metric_path = tmp_path / question["quality_contracts"]["metrics"]["path"]
    metric = yaml.safe_load(metric_path.read_text(encoding="utf-8"))
    metric["metrics"][0].update(
        {
            "run_metric_locator": "experiments/C/Q1/formal/run/results.json:score",
            "claim_ids": ["q1-score"],
            "figure_ids": ["fig-q1-score"],
        }
    )
    metric_path.write_text(
        yaml.safe_dump(metric, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    section = tmp_path / "paper" / question["paper"]["section"]
    section.parent.mkdir(parents=True, exist_ok=True)
    section.write_text("结果为 \\FrozenClaim{q1-score}。", encoding="utf-8")
    contracts = tmp_path / "paper/figure_contracts.yaml"
    dump_yaml(
        contracts,
        {
            "figures": [
                {
                    "id": "fig-q1-score",
                    "question_id": "Q1",
                    "claim_id": "q1-other",
                    "axes": [{"variable": "score", "unit": "wrong-unit"}],
                }
            ]
        },
    )
    refresh_quality_contract_references(tmp_path, "C", "Q1")
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    issues = metric_evidence_issues(tmp_path, question, gate="g5")
    assert any("figure uses a different frozen claim" in item for item in issues)
    assert any("figure unit differs" in item for item in issues)


def test_actual_abstract_must_contain_contract_anchors_and_frozen_claims(tmp_path: Path) -> None:
    question_path = make_v7_root(tmp_path)
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    abstract_path = tmp_path / question["quality_contracts"]["abstract"]["path"]
    contract = yaml.safe_load(abstract_path.read_text(encoding="utf-8"))
    contract.update(
        {
            "status": "READY",
            "final_summary": {"contribution": "统一评价", "limitation": "仅适用于当前样本"},
            "questions": [
                {
                    "question_id": "Q1",
                    "method_required": True,
                    "subject_required": True,
                    "conclusion_required": True,
                    "validation_required": True,
                    "boundary_required": True,
                    "method": "线性模型",
                    "subject": "评价任务",
                    "conclusion": "成本降低",
                    "validation": "基线比较",
                    "boundary": "固定容量",
                    "claim_ids": ["q1-score"],
                }
            ],
        }
    )
    abstract_path.write_text(yaml.safe_dump(contract, allow_unicode=True, sort_keys=False), encoding="utf-8")
    claims = tmp_path / "results/C/claims.json"
    claims.parent.mkdir(parents=True, exist_ok=True)
    claims.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "problem_id": "C",
                "claims": [{"id": "q1-score", "question_id": "Q1", "status": "frozen", "unit": "%", "value": 5.0}],
            }
        ),
        encoding="utf-8",
    )
    paper_abstract = tmp_path / "paper/sections/abstract.tex"
    paper_abstract.parent.mkdir(parents=True, exist_ok=True)
    paper_abstract.write_text(
        "研究评价任务，采用线性模型，结果表明成本降低，并通过基线比较验证；结论限于固定容量。"
        "全文贡献在于统一评价，主要限制为仅适用于当前样本。",
        encoding="utf-8",
    )
    refresh_quality_contract_references(tmp_path, "C")
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    assert abstract_text_issues(tmp_path, question) == []
