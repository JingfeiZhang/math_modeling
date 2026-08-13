from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest
import yaml

import src.workflow.competition_workflow as competition_workflow
from src.workflow.competition_workflow import (
    archive_work,
    checkpoint,
    freeze,
    initialize,
    paper_evidence,
    preflight,
    promote,
    quickcheck,
    record_run,
    resolve_run_config,
    status,
    validate,
)


ROOT = Path(__file__).resolve().parents[1]


def dump_yaml(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")


def scaffold_workspace(root: Path) -> None:
    dump_yaml(root / "contest.yaml", {"competition": "CUMCM", "year": 2026, "problem": "TBD", "deadline": "2026-09-13T20:00:00+08:00"})
    for relative in (
        "config/workflow.yaml",
        "skills.lock.yaml",
        "templates/figures/figure_contract_v2.schema.json",
        "templates/figures/figure_contract_v2.template.yaml",
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        source = ROOT / relative
        if source.exists():
            shutil.copy2(source, target)
        else:
            target.write_text("{}\n", encoding="utf-8")
    question_template = root / "templates" / "workflow" / "question.yaml"
    question_template.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "templates" / "workflow" / "question.yaml", question_template)
    decision = root / "skill_staging" / "handsomeZR-mathmodel-skill" / "templates" / "shared" / "decision_log.json"
    decision.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "skill_staging" / "handsomeZR-mathmodel-skill" / "templates" / "shared" / "decision_log.json", decision)


def test_precontest_protection_and_real_problem_initialization(tmp_path: Path) -> None:
    scaffold_workspace(tmp_path)
    assert preflight(tmp_path)["passed"] is True
    assert not (tmp_path / "state" / "decision_log.json").exists()
    assert not (tmp_path / "paper" / "figure_contracts.yaml").exists()
    problem_file = tmp_path / "problems" / "problem.txt"
    problem_file.parent.mkdir(parents=True)
    problem_file.write_text("问题一 建立评价模型。\n问题二 给出优化方案。", encoding="utf-8")
    with pytest.raises(ValueError, match="TBD"):
        initialize(tmp_path, "TBD", problem_file)
    assert not (tmp_path / "state" / "decision_log.json").exists()

    result = initialize(tmp_path, "C", problem_file)
    assert result["questions"] == ["Q1", "Q2"]
    question = yaml.safe_load((tmp_path / "problems" / "C" / "questions" / "Q1" / "question.yaml").read_text(encoding="utf-8"))
    assert question["schema_version"] == 2
    assert question["evidence"]["paper_evidence_runs"] == []
    assert question["paper"]["section"] == "sections/question_1.tex"
    assert set(question["paper"]["argument_contract"].values()) == {"pending"}
    state = json.loads((tmp_path / "state" / "decision_log.json").read_text(encoding="utf-8"))
    assert state["problem"] == "C"
    assert state["stages"]["5"]["qi_count"] == 2
    contracts = yaml.safe_load((tmp_path / "paper" / "figure_contracts.yaml").read_text(encoding="utf-8"))
    assert contracts == {"schema_version": "2.0", "figures": []}
    structure = (tmp_path / "paper" / "generated" / "question_structure.tex").read_text(encoding="utf-8")
    assert "\\MathModelQuestionCount}{2}" in structure
    assert "\\input{sections/question_1.tex}" in structure
    assert "\\input{sections/question_2.tex}" in structure
    assert "question_3.tex" not in structure
    blueprint = yaml.safe_load((tmp_path / "paper" / "generated" / "paper_blueprint.yaml").read_text(encoding="utf-8"))
    assert blueprint["contract"] == "CUMCM-paper-structure-v3"
    assert blueprint["derived"] is True
    assert blueprint["question_count"] == 2
    assert [item["question_id"] for item in blueprint["questions"]] == ["Q1", "Q2"]
    assert initialize(tmp_path, "C", problem_file)["status"] == "RESUMED"


@pytest.mark.parametrize("question_count", [3, 4])
def test_initialize_generates_only_real_question_sections(tmp_path: Path, question_count: int) -> None:
    scaffold_workspace(tmp_path)
    problem_file = tmp_path / "problems" / "problem.txt"
    problem_file.parent.mkdir(parents=True)
    markers = ["一", "二", "三", "四"][:question_count]
    problem_file.write_text("\n".join(f"问题{marker} 完成第{index}项任务。" for index, marker in enumerate(markers, start=1)), encoding="utf-8")

    result = initialize(tmp_path, "C", problem_file)

    assert result["questions"] == [f"Q{index}" for index in range(1, question_count + 1)]
    structure = (tmp_path / "paper" / "generated" / "question_structure.tex").read_text(encoding="utf-8")
    for index in range(1, question_count + 1):
        assert f"\\input{{sections/question_{index}.tex}}" in structure
    assert f"question_{question_count + 1}.tex" not in structure


def test_precontest_status_lists_nonformal_actions(tmp_path: Path) -> None:
    scaffold_workspace(tmp_path)
    report = status(tmp_path)
    assert report["phase"] == "PRECONTEST"
    assert report["state_exists"] is False
    assert report["allowed_actions"] == ["preflight", "status", "corpus", "template", "tooling"]
    assert not (tmp_path / "state" / "decision_log.json").exists()


def build_q1_evidence(root: Path) -> None:
    question_path = root / "problems" / "C" / "questions" / "Q1" / "question.yaml"
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    question["problem"]["inputs"] = ["题面数据"]
    question["problem"]["type"] = "约束优化"
    question["problem"]["outputs"] = ["可行调度方案"]
    question["problem"]["constraints"] = ["资源非负"]
    question["problem"]["evaluation_metrics"] = ["目标值（万元）"]
    question["problem"]["dependencies"] = []
    question["problem"]["key_conflicts"] = ["目标值与资源占用"]
    question["model_selection"] = {
        "primary": "优化模型",
        "rationale": "直接表达目标与资源约束",
        "baseline": "原方案",
        "rejected_alternatives": ["无约束排序"],
    }
    question["method"] = {
        "main": {"name": "优化模型", "rationale": "直接对应目标", "implementation": "src/q1.py"},
        "baseline": {"name": "原方案", "implementation": "src/q1.py", "comparable_output": True},
        "fallback": {"name": "启发式", "trigger": "主模型超时"},
    }
    question["risk_probes"] = [{"id": "rp1", "risk": "参数扰动", "status": "PASS"}]
    question["assumptions"] = [{"id": "a1", "statement": "资源容量在求解期内固定", "test": "容量压力测试"}]
    question["decisions"] = [{"id": "d1", "status": "confirmed", "evidence_ref": "problems/problem.txt"}]
    question["evidence"]["robustness"] = "experiments/C/Q1/run1/robustness.json"
    question["evidence"]["runs"] = ["experiments/C/Q1/run1/run_manifest.json"]
    question["evidence"]["result_claim_ids"] = ["q1-score"]
    question["evidence"]["validation_claim_ids"] = ["q1-validation"]
    question["evidence"]["boundary_claim_ids"] = ["q1-boundary"]
    question["paper"]["table_ids"] = ["tab-q1-result"]
    question["paper"]["figure_ids"] = ["fig-q1"]
    question["paper"]["code_refs"] = ["src/q1.py"]
    question["paper"]["downstream_interfaces"] = []
    question["paper"]["argument_contract"] = {key: "complete" for key in question["paper"]["argument_contract"]}
    dump_yaml(question_path, question)

    runner = root / "src" / "q1.py"
    runner.parent.mkdir(parents=True, exist_ok=True)
    runner.write_text("print('q1')\n", encoding="utf-8")
    experiment = root / "experiments" / "C" / "Q1" / "run1"
    experiment.mkdir(parents=True)
    result_path = experiment / "results.json"
    result_path.write_text(json.dumps({"metrics": {"score": 12.5}}), encoding="utf-8")
    (experiment / "robustness.json").write_text(json.dumps({"passed": True}), encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "run_id": "run1",
        "problem_id": "C",
        "question_id": "Q1",
        "engine": "python",
        "command": ["python", "src/q1.py"],
        "environment": {"python": "3.13"},
        "code": {"runner": "src/q1.py", "sha256": hashlib.sha256(runner.read_bytes()).hexdigest()},
        "random_seed": 7,
        "methods": [{"name": "优化模型", "role": "main"}, {"name": "原方案", "role": "baseline"}],
        "inputs": [],
        "artifacts": [{"path": "experiments/C/Q1/run1/results.json", "bytes": result_path.stat().st_size, "sha256": hashlib.sha256(result_path.read_bytes()).hexdigest()}],
        "metrics": [{"name": "score", "unit": "万元", "locator": "results.json:metrics.score"}],
        "started_at_utc": "2026-08-03T00:00:00+00:00",
        "duration_seconds": 0.1,
        "status": "PASS",
    }
    (experiment / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    claims = {
        "schema_version": 1,
        "problem_id": "C",
        "claims": [
            {"id": "q1-score", "question_id": "Q1", "statement": "优化目标值", "locator": "experiments/C/Q1/run1/results.json:metrics.score", "unit": "万元", "status": "verified"},
            {"id": "q1-validation", "question_id": "Q1", "statement": "压力测试通过", "locator": "experiments/C/Q1/run1/robustness.json:passed", "unit": "boolean", "status": "verified"},
            {"id": "q1-boundary", "question_id": "Q1", "statement": "结论适用于固定容量", "locator": "experiments/C/Q1/run1/robustness.json:passed", "unit": "boolean", "status": "verified"},
        ],
    }
    claims_path = root / "results" / "C" / "claims.json"
    claims_path.parent.mkdir(parents=True, exist_ok=True)
    claims_path.write_text(json.dumps(claims, ensure_ascii=False), encoding="utf-8")


def test_gates_baseline_freeze_and_hash_invalidation(tmp_path: Path) -> None:
    scaffold_workspace(tmp_path)
    problem_file = tmp_path / "problems" / "problem.txt"
    problem_file.parent.mkdir(parents=True)
    problem_file.write_text("问题一 建立评价模型。", encoding="utf-8")
    initialize(tmp_path, "C", problem_file)
    question_path = tmp_path / "problems" / "C" / "questions" / "Q1" / "question.yaml"
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    question["problem"]["inputs"] = ["数据"]
    question["problem"]["evaluation_metrics"] = ["误差（%）"]
    question["method"]["fallback"] = [{"name": "A", "trigger": "x"}, {"name": "B", "trigger": "y"}]
    dump_yaml(question_path, question)
    assert validate(tmp_path, "C", "G1", "Q1")["passed"] is False

    build_q1_evidence(tmp_path)
    assert validate(tmp_path, "C", "G3", "Q1")["passed"] is True
    frozen = freeze(tmp_path, "C", "Q1", "decision-1")
    assert frozen["gate"]["passed"] is True
    claims = json.loads((tmp_path / "results" / "C" / "claims.json").read_text(encoding="utf-8"))
    assert claims["claims"][0]["value"] == 12.5
    assert claims["claims"][0]["status"] == "frozen"

    figure_root = tmp_path / "experiments" / "C" / "Q1" / "run1" / "figures"
    figure_root.mkdir()
    for suffix, content in (("pdf", b"%PDF fixture"), ("svg", b"<svg/>"), ("png", b"PNG fixture")):
        (figure_root / f"main.{suffix}").write_bytes(content)
    result_path = tmp_path / "experiments" / "C" / "Q1" / "run1" / "results.json"
    evidence_hash = hashlib.sha256(result_path.read_bytes()).hexdigest()
    dump_yaml(
        tmp_path / "paper" / "figure_contracts.yaml",
        {
            "schema_version": "2.0",
            "figures": [{
                "contract_version": "2.0", "id": "fig-q1", "question_id": "Q1", "claim_id": "q1-score", "kind": "data",
                "core_conclusion": "优化模型达到给定目标值", "evidence_chain": [{"locator": "experiments/C/Q1/run1/results.json:metrics.score", "sha256": evidence_hash, "fields": ["metrics.score"]}],
                "archetype": "paired-comparison",
                "backend": "python", "baseline": "原方案", "axes": [{"variable": "方案", "unit": "无量纲"}, {"variable": "目标值", "unit": "万元"}], "caption": "优化方案与原方案的目标值。",
                "panel_map": [{"panel": "main", "role": "主模型与基线", "subclaim": "优化目标值"}], "review_risks": ["fixture only"],
                "core_message": "优化方案相对原方案达到经冻结证据支持的目标值",
                "visual_hierarchy": {"primary": "优化方案", "secondary": "原方案", "annotation_priority": ["目标值"]},
                "target_size_profile": "contest-body",
                "statistics_report": {"sample_size": "deterministic fixture", "center": "not applicable", "interval": "not applicable", "test": "not applicable", "multiple_comparison": "not applicable"},
                "data_integrity": {"source_hashes": [{"path": "experiments/C/Q1/run1/results.json", "sha256": evidence_hash}], "transformation": "read metrics.score without manual override", "manual_values_forbidden": True},
                "label_strategy": {"mode": "direct", "collision_checked": True},
                "rasterized_layers": [],
                "palette_id": "journal-spectrum-v2",
                "color_encoding": [{"role": "primary", "meaning": "优化方案", "secondary_encoding": "solid line"}, {"role": "baseline", "meaning": "原方案", "secondary_encoding": "dashed line"}],
                "final_width_mm": 158, "min_font_pt": 8,
                "source_data": ["experiments/C/Q1/run1/results.json"], "source_script": "src/q1.py",
                "outputs": {"pdf": "experiments/C/Q1/run1/figures/main.pdf", "svg": "experiments/C/Q1/run1/figures/main.svg", "png": "experiments/C/Q1/run1/figures/main.png", "png_dpi": 400},
                "statistics": ["deterministic"],
            }],
        },
    )
    assert validate(tmp_path, "C", "G5", "Q1")["passed"] is True

    result_path = tmp_path / "experiments" / "C" / "Q1" / "run1" / "results.json"
    result_path.write_text(json.dumps({"metrics": {"score": 13.0}}), encoding="utf-8")
    assert validate(tmp_path, "C", "G4", "Q1")["passed"] is False


def test_cross_question_claim_handoff_is_rejected(tmp_path: Path) -> None:
    scaffold_workspace(tmp_path)
    problem_file = tmp_path / "problems" / "problem.txt"
    problem_file.parent.mkdir(parents=True)
    problem_file.write_text("问题一 建立评价模型。\n问题二 给出优化方案。", encoding="utf-8")
    initialize(tmp_path, "C", problem_file)
    build_q1_evidence(tmp_path)

    claims_path = tmp_path / "results" / "C" / "claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"].append(
        {
            "id": "q2-score",
            "question_id": "Q2",
            "statement": "问题二目标值",
            "locator": "experiments/C/Q1/run1/results.json:metrics.score",
            "unit": "万元",
            "status": "verified",
        }
    )
    claims_path.write_text(json.dumps(claims, ensure_ascii=False), encoding="utf-8")
    question_path = tmp_path / "problems" / "C" / "questions" / "Q1" / "question.yaml"
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    question["evidence"]["result_claim_ids"] = ["q2-score"]
    dump_yaml(question_path, question)

    report = validate(tmp_path, "C", "G3", "Q1", write=False)
    resolution = next(item for item in report["checks"] if item["name"] == "claim_handoff_ids_resolve")

    assert report["passed"] is False
    assert resolution["passed"] is False
    assert "q2-score" in resolution["detail"]


def test_table_only_question_can_pass_g5_without_figure_contract(tmp_path: Path) -> None:
    scaffold_workspace(tmp_path)
    problem_file = tmp_path / "problems" / "problem.txt"
    problem_file.parent.mkdir(parents=True)
    problem_file.write_text("问题一 建立评价模型。", encoding="utf-8")
    initialize(tmp_path, "C", problem_file)
    build_q1_evidence(tmp_path)
    freeze(tmp_path, "C", "Q1", "decision-table-only")

    question_path = tmp_path / "problems" / "C" / "questions" / "Q1" / "question.yaml"
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    question["paper"]["figure_ids"] = []
    question["paper"]["table_ids"] = ["tab-q1-result"]
    dump_yaml(question_path, question)
    dump_yaml(tmp_path / "paper" / "figure_contracts.yaml", {"schema_version": "2.0", "figures": []})

    report = validate(tmp_path, "C", "G5", "Q1", write=False, strict=True)
    bindings = next(item for item in report["checks"] if item["name"] == "G5_result_artifact_binding")
    contracts = next(item for item in report["checks"] if item["name"] == "G5_figure_contracts")

    assert report["passed"] is True, [item for item in report["checks"] if not item["passed"]]
    assert bindings["passed"] is True
    assert contracts["passed"] is True


def test_g4_does_not_require_paper_main_tex(tmp_path: Path) -> None:
    scaffold_workspace(tmp_path)
    problem_file = tmp_path / "problems" / "problem.txt"
    problem_file.parent.mkdir(parents=True)
    problem_file.write_text("问题一 建立评价模型。", encoding="utf-8")
    initialize(tmp_path, "C", problem_file)
    build_q1_evidence(tmp_path)
    freeze(tmp_path, "C", "Q1", "decision-g4")
    main_tex = tmp_path / "paper" / "main.tex"
    if main_tex.exists():
        main_tex.unlink()

    report = validate(tmp_path, "C", "G4", "Q1", write=False, strict=True)

    assert report["passed"] is True, [item for item in report["checks"] if not item["passed"]]
    assert not main_tex.exists()
    assert all(item["name"] != "G5_paper_static_audit" for item in report["checks"])


def test_g0_through_g4_never_run_latex_pdf_or_package_deep_audits(tmp_path: Path, monkeypatch) -> None:
    scaffold_workspace(tmp_path)
    problem_file = tmp_path / "problems" / "problem.txt"
    problem_file.parent.mkdir(parents=True)
    problem_file.write_text("问题一 建立评价模型。", encoding="utf-8")
    initialize(tmp_path, "C", problem_file)
    build_q1_evidence(tmp_path)

    calls: list[tuple] = []

    def reject_subprocess(*args, **kwargs):
        calls.append(args)
        raise AssertionError("G0-G4 must not launch paper or package deep audits")

    monkeypatch.setattr(competition_workflow.subprocess, "run", reject_subprocess)
    reports = [validate(tmp_path, "C", gate, "Q1", write=False, strict=True) for gate in ("G0", "G1", "G2", "G3")]
    freeze(tmp_path, "C", "Q1", "decision-no-deep-audit")
    reports.append(validate(tmp_path, "C", "G4", "Q1", write=False, strict=True))

    assert calls == []
    assert all(
        item["name"] not in {"G5_paper_static_audit", "G6_audit_report"}
        for report in reports
        for item in report["checks"]
    )


def test_legacy_v1_manifest_is_compatible_unless_strict(tmp_path: Path) -> None:
    scaffold_workspace(tmp_path)
    problem_file = tmp_path / "problems" / "problem.txt"
    problem_file.parent.mkdir(parents=True)
    problem_file.write_text("问题一 建立评价模型。", encoding="utf-8")
    initialize(tmp_path, "C", problem_file)
    question_path = tmp_path / "problems" / "C" / "questions" / "Q1" / "question.yaml"
    dump_yaml(question_path, {
        "schema_version": 1,
        "problem_id": "C",
        "question_id": "Q1",
        "source_problem": "problems/problem.txt",
        "problem": {
            "target": "建立评价模型",
            "inputs": ["题面数据"],
            "constraints": [],
            "evaluation_metrics": ["误差"],
        },
        "method": {
            "main": {"name": "", "rationale": "", "implementation": ""},
            "baseline": {"name": "", "implementation": "", "comparable_output": False},
            "fallback": None,
        },
        "assumptions": [],
        "risk_probes": [],
        "decisions": [],
        "evidence": {"runs": [], "robustness": "", "figures": []},
        "paper": {"section": "", "figure_ids": []},
        "status": "DRAFT",
    })

    assert validate(tmp_path, "C", "G0", "Q1", write=False)["passed"] is True
    strict = validate(tmp_path, "C", "G0", "Q1", write=False, strict=True)
    assert strict["passed"] is False
    assert any(item["name"] == "question_manifest_schema_version" and not item["passed"] for item in strict["checks"])


def _write_lifecycle_run(root: Path, run_id: str, level: str = "scratch") -> tuple[Path, Path]:
    runner = root / "src" / "q1_lifecycle.py"
    runner.parent.mkdir(parents=True, exist_ok=True)
    runner.write_text("print('lifecycle')\n", encoding="utf-8")
    experiment_root = root / "experiments" / "C" / "Q1" / level / run_id
    experiment_root.mkdir(parents=True, exist_ok=True)
    result = experiment_root / "results.json"
    result.write_text(json.dumps({"metrics": {"score": 12.5}}), encoding="utf-8")
    config_path = root / "experiments" / "configs" / f"{run_id}.yaml"
    dump_yaml(config_path, {
        "schema_version": 2,
        "experiment_id": run_id,
        "problem": "C",
        "question": "Q1",
        "engine": "python",
        "runner": "src/q1_lifecycle.py",
        "seed": 20260801,
        "output_root": f"experiments/C/Q1/{level}",
        "arguments": [],
        "diagnostic_arguments": [],
        "run_mode": level,
        "level": level,
        "mode": "probe",
        "purpose": "candidate" if level == "candidate" else "exploration",
        "formal_candidate": level == "candidate",
        "parent_run_id": None,
        "source_run_id": None,
        "checkpoint_id": None,
        "primary_metric": "score",
        "checks": {
            "input_output_match": True,
            "units_defined": True,
            "core_constraints_passed": True,
            "deterministic": True,
            "baseline_comparable": True,
        },
        "reuse_contract": {"seed": False, "environment": False, "code": False, "inputs": False, "methods": False, "parameters": False},
        "replay": {"required": True, "count": 2},
        "methods": [{"name": "main", "role": "main"}, {"name": "fifo", "role": "baseline"}],
        "inputs": [],
        "metrics": [{
            "name": "score",
            "unit": "dimensionless",
            "locator": f"experiments/C/Q1/{level}/{run_id}/results.json:metrics.score",
            "primary": True,
        }],
    })
    return config_path, result


def _initialize_lifecycle_workspace(root: Path) -> Path:
    scaffold_workspace(root)
    problem_file = root / "problems" / "problem.txt"
    problem_file.parent.mkdir(parents=True)
    problem_file.write_text("问题一 建立约束优化模型。", encoding="utf-8")
    initialize(root, "C", problem_file)
    return root / "problems" / "C" / "questions" / "Q1" / "question.yaml"


def test_nonformal_run_checkpoint_and_promote_are_separated(tmp_path: Path) -> None:
    question_path = _initialize_lifecycle_workspace(tmp_path)
    config_path, _ = _write_lifecycle_run(tmp_path, "run-lifecycle", "scratch")

    manifest = record_run(
        tmp_path,
        config_path,
        ["python", "src/q1_lifecycle.py"],
        {"python": "3.13"},
        "2026-08-11T00:00:00+00:00",
        0.1,
        True,
    )

    assert manifest["schema_version"] == 2
    assert manifest["lifecycle"]["formal"] is False
    assert (tmp_path / "experiments" / "C" / "Q1" / "scratch" / "run-lifecycle" / "probe_receipt.json").is_file()
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    assert question["evidence"]["runs"] == []
    assert quickcheck(tmp_path, "C", "Q1", strict=True)["passed"] is True

    checked = checkpoint(tmp_path, "C", "Q1", strict=True)
    assert checked["passed"] is True
    candidate_manifest = tmp_path / "experiments" / "C" / "Q1" / "candidate" / "run-lifecycle" / "run_manifest.json"
    assert candidate_manifest.is_file()
    assert (candidate_manifest.parent / "candidate_receipt.json").is_file()
    assert not (tmp_path / "experiments" / "C" / "Q1" / "scratch" / "run-lifecycle").exists()
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    assert question["evidence"]["runs"] == []

    promoted = promote(tmp_path, "C", "Q1", "run-lifecycle")
    assert promoted["status"] == "FORMAL"
    formal_manifest = tmp_path / promoted["manifest"]
    assert formal_manifest.is_file()
    assert not candidate_manifest.exists()
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    assert question["evidence"]["runs"] == [promoted["manifest"]]
    formal = json.loads(formal_manifest.read_text(encoding="utf-8"))
    assert formal["level"] == "formal"
    assert formal["lifecycle"]["formal"] is True
    assert formal["artifacts"][0]["path"].startswith("experiments/C/Q1/formal/run-lifecycle/")


def test_quickcheck_defers_unverified_contracts_by_default(tmp_path: Path) -> None:
    _initialize_lifecycle_workspace(tmp_path)
    config_path, _ = _write_lifecycle_run(tmp_path, "run-light", "scratch")
    record_run(
        tmp_path,
        config_path,
        ["python", "src/q1_lifecycle.py"],
        {"python": "3.13"},
        "2026-08-11T00:00:00+00:00",
        0.1,
        True,
    )
    manifest_path = tmp_path / "experiments" / "C" / "Q1" / "scratch" / "run-light" / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["checks"]["core_constraints_passed"] = False
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    report = quickcheck(tmp_path, "C", "Q1")

    assert report["passed"] is True
    assert report["outcome"] == "PASS_WITH_WARNINGS"
    assert any(item["name"] == "quickcheck_contract_incomplete" for item in report["warnings"])
    assert quickcheck(tmp_path, "C", "Q1", strict=True)["passed"] is False


def test_candidate_checkpoint_does_not_require_figure_brief(tmp_path: Path) -> None:
    question_path = _initialize_lifecycle_workspace(tmp_path)
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    question["paper"]["figure_ids"] = ["fig-q1-main"]
    question_path.write_text(yaml.safe_dump(question, allow_unicode=True, sort_keys=False), encoding="utf-8")
    config_path, _ = _write_lifecycle_run(tmp_path, "run-no-brief", "candidate")
    record_run(
        tmp_path,
        config_path,
        ["python", "src/q1_lifecycle.py"],
        {"python": "3.13"},
        "2026-08-11T00:00:00+00:00",
        0.1,
        True,
    )

    report = checkpoint(tmp_path, "C", "Q1")

    assert report["passed"] is True
    assert report["outcome"] == "PASS_WITH_WARNINGS"
    assert any(item["name"] == "candidate_figure_brief_deferred" for item in report["warnings"])


def test_candidate_checkpoint_defers_determinism_but_promotion_blocks(tmp_path: Path) -> None:
    _initialize_lifecycle_workspace(tmp_path)
    config_path, _ = _write_lifecycle_run(tmp_path, "run-determinism-pending", "candidate")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["checks"]["deterministic"] = False
    config["replay"] = {"required": False, "count": 1}
    dump_yaml(config_path, config)
    record_run(
        tmp_path,
        config_path,
        ["python", "src/q1_lifecycle.py"],
        {"python": "3.13"},
        "2026-08-11T00:00:00+00:00",
        0.1,
        True,
    )

    report = checkpoint(tmp_path, "C", "Q1")

    assert report["passed"] is True
    assert report["outcome"] == "PASS_WITH_WARNINGS"
    assert {item["name"] for item in report["warnings"]} >= {
        "candidate_determinism_deferred",
        "candidate_replay_deferred",
    }
    with pytest.raises(ValueError, match="deterministic"):
        promote(tmp_path, "C", "Q1", "run-determinism-pending")


def test_candidate_can_promote_before_independent_replay_but_g3_rejects_it(tmp_path: Path) -> None:
    _initialize_lifecycle_workspace(tmp_path)
    config_path, _ = _write_lifecycle_run(tmp_path, "run-replay-pending", "candidate")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["replay"] = {"required": False, "count": 1}
    dump_yaml(config_path, config)
    record_run(
        tmp_path,
        config_path,
        ["python", "src/q1_lifecycle.py"],
        {"python": "3.13"},
        "2026-08-11T00:00:00+00:00",
        0.1,
        True,
    )

    report = checkpoint(tmp_path, "C", "Q1")
    promoted = promote(tmp_path, "C", "Q1", "run-replay-pending")
    formal_checks: list[dict] = []
    competition_workflow.validate_run_manifest(tmp_path, tmp_path / promoted["manifest"], formal_checks)
    lifecycle_check = next(item for item in formal_checks if item["name"] == "formal_lifecycle_contract")

    assert report["passed"] is True
    assert any(item["name"] == "candidate_replay_deferred" for item in report["warnings"])
    assert promoted["status"] == "FORMAL"
    assert lifecycle_check["passed"] is False
    assert lifecycle_check["detail"] == "replays=1"


def test_candidate_core_constraint_failure_blocks_default_checkpoint(tmp_path: Path) -> None:
    _initialize_lifecycle_workspace(tmp_path)
    config_path, _ = _write_lifecycle_run(tmp_path, "run-core-constraint-fail", "candidate")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["checks"]["core_constraints_passed"] = False
    dump_yaml(config_path, config)
    record_run(
        tmp_path,
        config_path,
        ["python", "src/q1_lifecycle.py"],
        {"python": "3.13"},
        "2026-08-11T00:00:00+00:00",
        0.1,
        True,
    )

    report = checkpoint(tmp_path, "C", "Q1")

    assert report["passed"] is False
    assert report["outcome"] == "BLOCK_TRANSITION"
    assert "core_constraints_passed" in next(
        item["detail"] for item in report["checks"] if item["name"] == "checkpoint_run"
    )


def _write_paper_evidence_run(root: Path, formal_path: Path, run_id: str, score: float) -> tuple[Path, Path]:
    formal = json.loads(formal_path.read_text(encoding="utf-8"))
    run_root = root / "experiments" / "C" / "Q1" / "paper-evidence" / run_id
    run_root.mkdir(parents=True, exist_ok=True)
    result = run_root / "results.json"
    result.write_text(json.dumps({"metrics": {"score": score}}), encoding="utf-8")
    config_path = root / "experiments" / "configs" / f"{run_id}.yaml"
    dump_yaml(config_path, {
        "schema_version": 2,
        "experiment_id": run_id,
        "problem": "C",
        "question": "Q1",
        "engine": "python",
        "runner": formal["code"]["runner"],
        "seed": formal["random_seed"],
        "output_root": "experiments/C/Q1/paper-evidence",
        "arguments": [],
        "diagnostic_arguments": [],
        "run_mode": "paper-evidence",
        "level": "paper-evidence",
        "mode": "probe",
        "purpose": "paper",
        "formal_candidate": False,
        "parent_run_id": formal["run_id"],
        "source_run_id": formal["run_id"],
        "source_manifest": formal_path.relative_to(root).as_posix(),
        "source_manifest_sha256": hashlib.sha256(formal_path.read_bytes()).hexdigest(),
        "evidence_scope": "diagnostic",
        "checkpoint_id": None,
        "primary_metric": "score",
        "checks": {
            "input_output_match": True,
            "units_defined": True,
            "core_constraints_passed": True,
            "deterministic": True,
            "baseline_comparable": True,
        },
        "reuse_contract": {"seed": True, "environment": True, "code": True, "inputs": True, "methods": True, "parameters": True},
        "replay": {"required": True, "count": 2},
        "methods": [{"name": "main", "role": "main"}, {"name": "fifo", "role": "baseline"}],
        "inputs": [],
        "metrics": [{
            "name": "score",
            "unit": "dimensionless",
            "locator": f"experiments/C/Q1/paper-evidence/{run_id}/results.json:metrics.score",
            "primary": True,
        }],
    })
    record_run(root, config_path, ["python", formal["code"]["runner"]], formal["environment"], "2026-08-11T01:00:00+00:00", 0.1, True)
    return config_path, result


def test_paper_evidence_reopens_on_primary_metric_drift(tmp_path: Path) -> None:
    question_path = _initialize_lifecycle_workspace(tmp_path)
    config_path, _ = _write_lifecycle_run(tmp_path, "run-paper", "candidate")
    record_run(tmp_path, config_path, ["python", "src/q1_lifecycle.py"], {"python": "3.13"}, "2026-08-11T00:00:00+00:00", 0.1, True)
    assert checkpoint(tmp_path, "C", "Q1", strict=True)["passed"] is True
    promoted = promote(tmp_path, "C", "Q1", "run-paper")
    formal_path = tmp_path / promoted["manifest"]
    evidence_config, _ = _write_paper_evidence_run(tmp_path, formal_path, "q1-paper", 12.5)
    ready = paper_evidence(tmp_path, "C", "Q1", evidence_config, strict=True)
    assert ready["status"] == "READY"
    drift_config, _ = _write_paper_evidence_run(tmp_path, formal_path, "q1-paper-drift", 13.0)
    reopened = paper_evidence(tmp_path, "C", "Q1", drift_config, strict=True)
    assert reopened["status"] == "REOPEN_REQUIRED"
    assert "primary metric drifted" in reopened["reason"]
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    assert question["evidence"]["runs"] == [promoted["manifest"]]
    assert question["evidence"]["paper_evidence_runs"] == [ready["manifest"]]


def test_paper_evidence_reopens_when_parent_manifest_hash_changes(tmp_path: Path) -> None:
    _initialize_lifecycle_workspace(tmp_path)
    config_path, _ = _write_lifecycle_run(tmp_path, "run-parent-drift", "candidate")
    record_run(tmp_path, config_path, ["python", "src/q1_lifecycle.py"], {"python": "3.13"}, "2026-08-11T00:00:00+00:00", 0.1, True)
    assert checkpoint(tmp_path, "C", "Q1", strict=True)["passed"] is True
    promoted = promote(tmp_path, "C", "Q1", "run-parent-drift")
    formal_path = tmp_path / promoted["manifest"]
    evidence_config, _ = _write_paper_evidence_run(tmp_path, formal_path, "q1-parent-drift", 12.5)
    formal = json.loads(formal_path.read_text(encoding="utf-8"))
    formal["environment"]["drift_marker"] = True
    formal_path.write_text(json.dumps(formal, ensure_ascii=False, indent=2), encoding="utf-8")

    reopened = paper_evidence(tmp_path, "C", "Q1", evidence_config, strict=True)

    assert reopened["status"] == "REOPEN_REQUIRED"
    assert "source manifest hash drifted" in reopened["reason"]


def test_archive_work_moves_only_scratch_runs(tmp_path: Path) -> None:
    _initialize_lifecycle_workspace(tmp_path)
    config_path, _ = _write_lifecycle_run(tmp_path, "run-archive", "scratch")
    record_run(tmp_path, config_path, ["python", "src/q1_lifecycle.py"], {"python": "3.13"}, "2026-08-11T00:00:00+00:00", 0.1, True)

    report = archive_work(tmp_path, "C", "Q1")

    assert report["count"] == 1
    archived = tmp_path / report["archived"][0]
    assert (archived / "run_manifest.json").is_file()
    assert (archived / "archive_receipt.json").is_file()
    assert not (tmp_path / "experiments" / "C" / "Q1" / "scratch" / "run-archive").exists()


@pytest.mark.parametrize("failed_check", ["core_constraints_passed", "deterministic", "baseline_comparable"])
def test_failed_candidate_check_cannot_promote(tmp_path: Path, failed_check: str) -> None:
    _initialize_lifecycle_workspace(tmp_path)
    config_path, _ = _write_lifecycle_run(tmp_path, f"run-fail-{failed_check}", "candidate")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["checks"][failed_check] = False
    dump_yaml(config_path, config)
    record_run(tmp_path, config_path, ["python", "src/q1_lifecycle.py"], {"python": "3.13"}, "2026-08-11T00:00:00+00:00", 0.1, True)

    report = checkpoint(tmp_path, "C", "Q1", strict=True)

    assert report["passed"] is False
    with pytest.raises(ValueError, match="not promotion-ready"):
        promote(tmp_path, "C", "Q1", f"run-fail-{failed_check}")


def test_legacy_config_defaults_formal_and_record_binds_question_evidence(tmp_path: Path) -> None:
    question_path = _initialize_lifecycle_workspace(tmp_path)
    runner = tmp_path / "src" / "legacy.py"
    runner.parent.mkdir(parents=True, exist_ok=True)
    runner.write_text("print('legacy')\n", encoding="utf-8")
    run_root = tmp_path / "experiments" / "C" / "Q1" / "legacy-run"
    run_root.mkdir(parents=True)
    (run_root / "result.json").write_text(json.dumps({"score": 1.0}), encoding="utf-8")
    config_path = tmp_path / "experiments" / "configs" / "legacy.yaml"
    dump_yaml(config_path, {
        "experiment_id": "legacy-run",
        "problem": "C",
        "question": "Q1",
        "engine": "python",
        "runner": "src/legacy.py",
        "seed": 1,
        "output_root": "experiments/C/Q1",
        "methods": [{"name": "main", "role": "main"}, {"name": "baseline", "role": "baseline"}],
        "metrics": [{"name": "score", "unit": "dimensionless", "locator": "experiments/C/Q1/legacy-run/result.json:score"}],
        "inputs": [],
    })

    resolved = resolve_run_config(tmp_path, config_path)
    manifest = record_run(tmp_path, config_path, ["python", "src/legacy.py"], {"python": "3.13"}, "2026-08-11T00:00:00+00:00", 0.1, True)

    assert resolved["run_mode"] == "formal"
    assert manifest["schema_version"] == 1
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    assert question["evidence"]["runs"] == ["experiments/C/Q1/legacy-run/run_manifest.json"]


def test_active_status_does_not_run_deep_paper_audits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _initialize_lifecycle_workspace(tmp_path)

    def fail_subprocess(*args: object, **kwargs: object) -> object:
        raise AssertionError("status must not launch a subprocess")

    monkeypatch.setattr("src.workflow.competition_workflow.subprocess.run", fail_subprocess)
    report = status(tmp_path)

    assert report["phase"] == "ACTIVE"
    assert report["gates"]["G5"] == "NOT_RUN"
    assert report["gates"]["G6"] == "NOT_RUN"
