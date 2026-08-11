from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from src.workflow.competition_workflow import (
    checkpoint,
    figure_brief,
    figure_data,
    figure_intent,
    figure_promote,
    figure_qa,
    figure_render,
    freeze,
    initialize,
    paper_evidence,
    promote,
    record_run,
    validate,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "config" / "schemas"


def dump_yaml(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")


def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scaffold_workspace(root: Path) -> Path:
    dump_yaml(
        root / "contest.yaml",
        {
            "competition": "CUMCM",
            "year": 2026,
            "problem": "TBD",
            "deadline": "2026-09-13T20:00:00+08:00",
        },
    )
    for relative in (
        "config/workflow.yaml",
        "config/schemas/figure_data_manifest.schema.json",
        "config/schemas/visual_intent.schema.json",
        "config/schemas/figure_brief.schema.json",
        "skills.lock.yaml",
        "templates/figures/figure_contract_v2.schema.json",
        "templates/figures/figure_contract_v2.template.yaml",
        "templates/workflow/question.yaml",
        "skill_staging/handsomeZR-mathmodel-skill/templates/shared/decision_log.json",
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    problem_file = root / "problems" / "problem.txt"
    problem_file.parent.mkdir(parents=True, exist_ok=True)
    problem_file.write_text("问题一 建立约束优化模型。", encoding="utf-8")
    initialize(root, "C", problem_file)
    return root / "problems" / "C" / "questions" / "Q1" / "question.yaml"


def write_run(root: Path, run_id: str, level: str) -> tuple[Path, Path]:
    runner = root / "src" / "q1_model.py"
    runner.parent.mkdir(parents=True, exist_ok=True)
    runner.write_text("print('q1')\n", encoding="utf-8")
    run_root = root / "experiments" / "C" / "Q1" / level / run_id
    run_root.mkdir(parents=True, exist_ok=True)
    result = run_root / "results.json"
    result.write_text(json.dumps({"metrics": {"score": 12.5, "baseline": 10.0}}), encoding="utf-8")
    config = root / "experiments" / "configs" / f"{run_id}.yaml"
    dump_yaml(
        config,
        {
            "schema_version": 2,
            "experiment_id": run_id,
            "problem": "C",
            "question": "Q1",
            "engine": "python",
            "runner": "src/q1_model.py",
            "seed": 20260811,
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
            "reuse_contract": {
                "seed": False,
                "environment": False,
                "code": False,
                "inputs": False,
                "methods": False,
                "parameters": False,
            },
            "replay": {"required": True, "count": 2},
            "methods": [
                {"name": "优化模型", "role": "main"},
                {"name": "原方案", "role": "baseline"},
            ],
            "inputs": [],
            "metrics": [
                {
                    "name": "score",
                    "unit": "万元",
                    "locator": f"experiments/C/Q1/{level}/{run_id}/results.json:metrics.score",
                    "primary": True,
                }
            ],
        },
    )
    record_run(
        root,
        config,
        ["python", "src/q1_model.py"],
        {"python": "3.13"},
        "2026-08-11T00:00:00+00:00",
        0.1,
        True,
    )
    return config, result


def prepare_formal_question(root: Path, run_id: str = "run-v5") -> tuple[Path, Path, Path]:
    question_path = scaffold_workspace(root)
    write_run(root, run_id, "candidate")
    assert checkpoint(root, "C", "Q1", strict=True)["passed"] is True
    promoted = promote(root, "C", "Q1", run_id)
    formal_manifest = root / promoted["manifest"]
    result = formal_manifest.parent / "results.json"
    robustness = formal_manifest.parent / "robustness.json"
    robustness.write_text(json.dumps({"passed": True, "boundary": "fixed capacity"}), encoding="utf-8")

    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    question["problem"].update(
        {
            "type": "约束优化",
            "inputs": ["题面数据"],
            "outputs": ["可行调度方案"],
            "constraints": ["资源非负"],
            "evaluation_metrics": ["目标值（万元）"],
            "dependencies": [],
            "key_conflicts": ["目标值与资源占用"],
        }
    )
    question["model_selection"] = {
        "primary": "优化模型",
        "rationale": "直接表达目标与资源约束",
        "baseline": "原方案",
        "rejected_alternatives": ["无约束排序"],
    }
    question["method"] = {
        "main": {"name": "优化模型", "rationale": "直接对应目标", "implementation": "src/q1_model.py"},
        "baseline": {"name": "原方案", "implementation": "src/q1_model.py", "comparable_output": True},
        "fallback": {"name": "启发式", "trigger": "主模型超时"},
    }
    question["risk_probes"] = [{"id": "rp1", "risk": "参数扰动", "status": "PASS"}]
    question["assumptions"] = [{"id": "a1", "statement": "容量固定", "test": "容量压力测试"}]
    question["decisions"] = [
        {"id": "decision-model-q1", "status": "confirmed", "evidence_ref": "problems/problem.txt"},
        {"id": "decision-figure-q1", "status": "confirmed", "evidence_ref": promoted["manifest"]},
    ]
    question["evidence"]["robustness"] = robustness.relative_to(root).as_posix()
    question["evidence"]["result_claim_ids"] = ["q1-score"]
    question["evidence"]["validation_claim_ids"] = ["q1-validation"]
    question["evidence"]["boundary_claim_ids"] = ["q1-boundary"]
    question["paper"]["table_ids"] = ["tab-q1-result"]
    question["paper"]["figure_ids"] = []
    question["paper"]["code_refs"] = ["src/q1_model.py"]
    question["paper"]["downstream_interfaces"] = []
    question["paper"]["argument_contract"] = {
        key: "complete" for key in question["paper"]["argument_contract"]
    }
    dump_yaml(question_path, question)

    claims_path = root / "results" / "C" / "claims.json"
    claims_path.parent.mkdir(parents=True, exist_ok=True)
    claims_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "problem_id": "C",
                "claims": [
                    {
                        "id": "q1-score",
                        "question_id": "Q1",
                        "statement": "优化目标值",
                        "locator": f"{result.relative_to(root).as_posix()}:metrics.score",
                        "unit": "万元",
                        "status": "verified",
                    },
                    {
                        "id": "q1-validation",
                        "question_id": "Q1",
                        "statement": "压力测试通过",
                        "locator": f"{robustness.relative_to(root).as_posix()}:passed",
                        "unit": "boolean",
                        "status": "verified",
                    },
                    {
                        "id": "q1-boundary",
                        "question_id": "Q1",
                        "statement": "适用于固定容量",
                        "locator": f"{robustness.relative_to(root).as_posix()}:boundary",
                        "unit": "text",
                        "status": "verified",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    frozen = freeze(root, "C", "Q1", "decision-model-q1")
    assert frozen["gate"]["passed"] is True
    return question_path, formal_manifest, result


def figure_data_config(root: Path, run_id: str, result: Path) -> Path:
    config = root / "experiments" / "configs" / f"{run_id}-figure-data.yaml"
    dump_yaml(
        config,
        {
            "manifest_id": f"figdata-{run_id}",
            "problem_id": "C",
            "question_id": "Q1",
            "source_artifacts": [
                {"path": result.relative_to(root).as_posix(), "fields": ["metrics.score", "metrics.baseline"]}
            ],
            "data_profile": {
                "row_count": 1,
                "column_count": 2,
                "variable_types": {"metrics.score": "number", "metrics.baseline": "number"},
                "units": {"metrics.score": "万元", "metrics.baseline": "万元"},
                "observation_unit": "方案",
                "missingness": {"metrics.score": 0, "metrics.baseline": 0},
            },
            "comparators": {"baseline": "原方案", "thresholds": ["不低于基线"]},
            "uncertainty": {"definition": "确定性求解，无抽样区间", "observation_or_replication_unit": "固定实例"},
            "read_only_transformations": ["读取 metrics.score 与 metrics.baseline"],
            "reader_question": "优化模型是否优于原方案？",
            "claim_candidates": ["q1-score"],
            "paper_targets": ["sections/question_1.tex#results"],
        },
    )
    return config


def intent_config(root: Path, run_id: str) -> Path:
    config = root / "experiments" / "configs" / f"{run_id}-intent.yaml"
    dump_yaml(
        config,
        {
            "intent_id": f"intent-{run_id}",
            "reader_question": "优化模型是否优于原方案？",
            "evidence_role": "main",
            "artifact_decision": "figure",
            "candidate_archetypes": [
                {"name": "paired-comparison", "rationale": "直接比较同指标", "rejection_reason": None},
                {"name": "radar", "rationale": "可展示多指标", "rejection_reason": "当前只有一个主指标"},
            ],
            "required_encodings": {"x": "方案", "y": "目标值", "group": None, "secondary": "标记形状"},
            "comparison": "原方案",
            "risks": ["柱高差可能夸大相对提升"],
            "paper_slot": "sections/question_1.tex#results",
            "status": "READY",
        },
    )
    return config


def write_render_fixture(root: Path) -> Path:
    script = root / "src" / "render_figure_fixture.py"
    script.write_text(
        "from __future__ import annotations\n"
        "import sys\n"
        "from pathlib import Path\n"
        "from PIL import Image\n"
        "out = Path(sys.argv[1])\n"
        "out.mkdir(parents=True, exist_ok=True)\n"
        "image = Image.new('RGB', (2488, 1600), 'white')\n"
        "image.save(out / 'fig-q1-main.pdf', 'PDF', resolution=400.0)\n"
        "(out / 'fig-q1-main.svg').write_text(\"<svg xmlns='http://www.w3.org/2000/svg'><text x='1' y='10'>Q1</text></svg>\", encoding='utf-8')\n"
        "image.save(out / 'fig-q1-main.png', 'PNG', dpi=(400, 400))\n",
        encoding="utf-8",
    )
    return script


def brief_config(
    root: Path,
    run_id: str,
    result: Path,
    status: str = "APPROVED",
    level: str = "formal",
) -> Path:
    script = write_render_fixture(root)
    output_root = f"experiments/C/Q1/{level}/{run_id}/figure-staging/fig-q1-main/outputs"
    config = root / "experiments" / "configs" / f"{run_id}-brief.yaml"
    payload = valid_brief_payload()
    payload.update(
        {
            "brief_id": "fig-q1-main",
            "run_id": run_id,
            "claim_id": "q1-score",
            "evidence_chain": [
                {
                    "locator": f"{result.relative_to(root).as_posix()}:metrics.score",
                    "sha256": sha256(result),
                    "fields": ["metrics.score"],
                }
            ],
            "source_data": [result.relative_to(root).as_posix()],
            "source_script": script.relative_to(root).as_posix(),
            "source_script_sha256": sha256(script),
            "render_command": ["{python}", script.relative_to(root).as_posix(), "{output_dir}"],
            "outputs": {
                "pdf": f"{output_root}/fig-q1-main.pdf",
                "svg": f"{output_root}/fig-q1-main.svg",
                "png": f"{output_root}/fig-q1-main.png",
                "png_dpi": 400,
            },
            "data_integrity": {
                "source_hashes": [{"path": result.relative_to(root).as_posix(), "sha256": sha256(result)}],
                "transformation": "read-only comparison",
                "manual_values_forbidden": True,
            },
            "status": status,
            "approval": {
                "decision_id": "decision-figure-q1",
                "approved_by": "root-agent",
                "approved_at_utc": "2026-08-11T02:00:00+00:00",
            },
        }
    )
    if status not in {"APPROVED", "RENDERED", "QA_PASSED", "CONTRACT_READY"}:
        payload.pop("approval", None)
    for derived in (
        "schema_version",
        "question_id",
        "source_data_manifest",
        "source_data_manifest_sha256",
        "visual_intent",
        "visual_intent_sha256",
        "contest_evidence_eligible",
        "created_at_utc",
    ):
        payload.pop(derived, None)
    dump_yaml(config, payload)
    return config


def valid_data_payload() -> dict:
    digest = "a" * 64
    return {
        "schema_version": 1,
        "manifest_id": "figdata-fixture",
        "problem_id": "C",
        "question_id": "Q1",
        "run_id": "run-1",
        "level": "formal",
        "status": "DATA_READY",
        "source_run_manifest": "experiments/C/Q1/formal/run-1/run_manifest.json",
        "source_run_manifest_sha256": digest,
        "source_artifacts": [{"path": "experiments/C/Q1/formal/run-1/results.json", "sha256": digest, "fields": ["metrics.score"]}],
        "data_profile": {
            "row_count": 1,
            "column_count": 1,
            "variable_types": {"metrics.score": "number"},
            "units": {"metrics.score": "万元"},
            "observation_unit": "方案",
            "missingness": {"metrics.score": 0},
        },
        "comparators": {"baseline": "原方案", "thresholds": []},
        "uncertainty": {"definition": "确定性", "observation_or_replication_unit": "固定实例"},
        "read_only_transformations": ["none"],
        "reader_question": "主模型是否优于基线？",
        "claim_candidates": ["q1-score"],
        "paper_targets": ["question-1-results"],
        "contest_evidence_eligible": True,
        "created_at_utc": "2026-08-11T00:00:00+00:00",
    }


def valid_intent_payload() -> dict:
    return {
        "schema_version": 1,
        "intent_id": "intent-fixture",
        "question_id": "Q1",
        "run_id": "run-1",
        "source_data_manifest": "experiments/C/Q1/formal/run-1/figure_data_manifest.yaml",
        "source_data_manifest_sha256": "a" * 64,
        "reader_question": "主模型是否优于基线？",
        "evidence_role": "main",
        "artifact_decision": "figure",
        "candidate_archetypes": [{"name": "paired-comparison", "rationale": "同指标比较", "rejection_reason": None}],
        "required_encodings": {"x": "方案", "y": "目标值", "group": None, "secondary": "marker"},
        "comparison": "原方案",
        "risks": ["纵轴截断"],
        "paper_slot": "question-1-results",
        "status": "READY",
        "contest_evidence_eligible": True,
        "created_at_utc": "2026-08-11T00:00:00+00:00",
    }


def valid_brief_payload() -> dict:
    digest = "a" * 64
    result = "experiments/C/Q1/formal/run-1/results.json"
    return {
        "schema_version": 1,
        "brief_id": "fig-q1-main",
        "question_id": "Q1",
        "run_id": "run-1",
        "source_data_manifest": "experiments/C/Q1/formal/run-1/figure_data_manifest.yaml",
        "source_data_manifest_sha256": digest,
        "visual_intent": "experiments/C/Q1/formal/run-1/visual_intent.yaml",
        "visual_intent_sha256": digest,
        "claim_id": "q1-score",
        "core_conclusion": "优化模型的目标值高于原方案",
        "core_message": "主模型优于基线",
        "evidence_chain": [{"locator": f"{result}:metrics.score", "sha256": digest, "fields": ["metrics.score"]}],
        "decision": {
            "artifact_type": "figure",
            "archetype": "paired-comparison",
            "alternatives": [{"kind": "table", "rejected_reason": "图形更适合突出差异"}],
            "rationale": "直接比较同一指标",
        },
        "encodings": {"x": "方案", "y": "目标值", "color": "方案", "marker": "方案", "facet": None, "units": {"目标值": "万元"}},
        "visual_hierarchy": {"primary_evidence": "优化模型", "secondary_context": "原方案", "deemphasized": "网格"},
        "panel_map": [{"panel": "main", "role": "主结果", "subclaim": "主模型优于基线"}],
        "labels": {"strategy": "direct", "collision_check_required": True, "annotations": []},
        "legend": "直接标签，不使用图例",
        "palette_id": "journal-spectrum-v2",
        "color_encoding": [{"role": "primary", "meaning": "优化模型", "secondary_encoding": "solid + circle"}],
        "backend": "python",
        "target_size_profile": "contest-body",
        "final_width_mm": 158,
        "min_font_pt": 8,
        "source_data": [result],
        "source_script": "src/render_figure_fixture.py",
        "source_script_sha256": "0" * 64,
        "render_command": ["{python}", "src/render_figure_fixture.py", "{output_dir}"],
        "outputs": {
            "pdf": "experiments/C/Q1/formal/run-1/figure-staging/fig-q1-main/outputs/fig-q1-main.pdf",
            "svg": "experiments/C/Q1/formal/run-1/figure-staging/fig-q1-main/outputs/fig-q1-main.svg",
            "png": "experiments/C/Q1/formal/run-1/figure-staging/fig-q1-main/outputs/fig-q1-main.png",
            "png_dpi": 400,
        },
        "baseline": "原方案",
        "axes": [{"variable": "方案", "unit": "无量纲"}, {"variable": "目标值", "unit": "万元"}],
        "caption": "优化模型与原方案的目标值比较。",
        "statistics": ["确定性实例"],
        "statistics_report": {"sample_size": "1 instance", "center": "not applicable", "interval": "not applicable", "test": "not applicable", "multiplicity": "not applicable"},
        "data_integrity": {"source_hashes": [{"path": result, "sha256": digest}], "transformation": "read-only", "manual_values_forbidden": True},
        "label_strategy": {"mode": "direct", "collision_checked": False},
        "rasterized_layers": [],
        "review_risks": ["纵轴范围可能夸大差异"],
        "read_only_transformations": ["none"],
        "status": "APPROVED",
        "qa_expectations": ["SVG text remains editable"],
        "approval": {"decision_id": "decision-figure-q1", "approved_by": "root-agent", "approved_at_utc": "2026-08-11T00:00:00+00:00"},
        "contest_evidence_eligible": True,
        "created_at_utc": "2026-08-11T00:00:00+00:00",
    }


@pytest.mark.parametrize(
    ("schema_name", "factory"),
    [
        ("figure_data_manifest.schema.json", valid_data_payload),
        ("visual_intent.schema.json", valid_intent_payload),
        ("figure_brief.schema.json", valid_brief_payload),
    ],
)
def test_v5_visualization_schema_accepts_valid_fixture(schema_name: str, factory) -> None:
    Draft202012Validator(load_schema(schema_name)).validate(factory())


@pytest.mark.parametrize(
    ("schema_name", "factory", "mutation"),
    [
        ("figure_data_manifest.schema.json", valid_data_payload, lambda value: value.pop("reader_question")),
        ("figure_data_manifest.schema.json", valid_data_payload, lambda value: value["source_artifacts"][0].update(path="C:/absolute/results.json")),
        ("figure_data_manifest.schema.json", valid_data_payload, lambda value: value.update(source_run_manifest_sha256="bad")),
        ("figure_data_manifest.schema.json", valid_data_payload, lambda value: value["data_profile"].pop("units")),
        ("figure_data_manifest.schema.json", valid_data_payload, lambda value: value.update(level="scratch")),
        ("figure_data_manifest.schema.json", valid_data_payload, lambda value: value.update(contest_evidence_eligible=False)),
        ("visual_intent.schema.json", valid_intent_payload, lambda value: value.update(source_data_manifest="/absolute/intent.yaml")),
        ("visual_intent.schema.json", valid_intent_payload, lambda value: value.update(source_data_manifest_sha256="bad")),
        ("figure_brief.schema.json", valid_brief_payload, lambda value: value.update(source_data=["D:/absolute/results.json"])),
        ("figure_brief.schema.json", valid_brief_payload, lambda value: value.update(visual_intent_sha256="bad")),
        ("figure_brief.schema.json", valid_brief_payload, lambda value: value["encodings"].update(units={})),
    ],
)
def test_v5_visualization_schema_rejects_invalid_fixture(schema_name: str, factory, mutation) -> None:
    payload = factory()
    mutation(payload)
    assert list(Draft202012Validator(load_schema(schema_name)).iter_errors(payload))


def test_visualization_skill_design_contract_examples_match_current_schemas() -> None:
    reference = (ROOT / "skill_staging" / "visualization-design" / "references" / "design-contract.md").read_text(encoding="utf-8")
    examples = re.findall(r"```yaml\n(.*?)\n```", reference, flags=re.DOTALL)

    assert len(examples) >= 2
    for schema_name, source in zip(("visual_intent.schema.json", "figure_brief.schema.json"), examples, strict=True):
        payload = yaml.safe_load(source)
        Draft202012Validator(load_schema(schema_name)).validate(payload)
        assert isinstance(payload["created_at_utc"], str)


def test_scratch_stops_at_intent_and_creates_no_formal_evidence(tmp_path: Path) -> None:
    scaffold_workspace(tmp_path)
    _, result = write_run(tmp_path, "scratch-visual", "scratch")
    data_config = figure_data_config(tmp_path, "scratch-visual", result)
    intent = intent_config(tmp_path, "scratch-visual")

    data_result = figure_data(tmp_path, "C", "Q1", "scratch-visual", data_config)
    intent_result = figure_intent(tmp_path, "C", "Q1", "scratch-visual", intent)

    assert data_result["contest_evidence_eligible"] is False
    assert intent_result["status"] == "INTENT_READY"
    claims = json.loads((tmp_path / "results" / "C" / "claims.json").read_text(encoding="utf-8"))
    assert claims["claims"] == []
    assert yaml.safe_load((tmp_path / "paper" / "figure_contracts.yaml").read_text(encoding="utf-8"))["figures"] == []
    with pytest.raises(ValueError, match="Scratch.*INTENT_READY|Scratch.*brief"):
        figure_brief(
            tmp_path,
            "C",
            "Q1",
            "scratch-visual",
            tmp_path / intent_result["intent"],
            brief_config(tmp_path, "scratch-visual", result, status="REVIEWED"),
        )


def test_candidate_can_review_brief_but_cannot_enter_formal_gates(tmp_path: Path) -> None:
    scaffold_workspace(tmp_path)
    _, result = write_run(tmp_path, "candidate-visual", "candidate")
    data_result = figure_data(tmp_path, "C", "Q1", "candidate-visual", figure_data_config(tmp_path, "candidate-visual", result))
    intent_result = figure_intent(tmp_path, "C", "Q1", "candidate-visual", intent_config(tmp_path, "candidate-visual"))
    brief_result = figure_brief(
        tmp_path,
        "C",
        "Q1",
        "candidate-visual",
        tmp_path / intent_result["intent"],
        brief_config(tmp_path, "candidate-visual", result, status="REVIEWED", level="candidate"),
    )

    assert data_result["contest_evidence_eligible"] is False
    assert brief_result["status"] == "BRIEF_READY"
    assert yaml.safe_load((tmp_path / brief_result["brief"]).read_text(encoding="utf-8"))["contest_evidence_eligible"] is False
    assert validate(tmp_path, "C", "G3", "Q1", write=False, strict=True)["passed"] is False
    assert validate(tmp_path, "C", "G4", "Q1", write=False, strict=True)["passed"] is False


def test_visual_handoff_survives_scratch_candidate_formal_promotion(tmp_path: Path) -> None:
    scaffold_workspace(tmp_path)
    run_id = "lifecycle-visual"
    _, scratch_result = write_run(tmp_path, run_id, "scratch")
    figure_data(tmp_path, "C", "Q1", run_id, figure_data_config(tmp_path, run_id, scratch_result))
    scratch_intent = figure_intent(tmp_path, "C", "Q1", run_id, intent_config(tmp_path, run_id))

    assert checkpoint(tmp_path, "C", "Q1", strict=True)["passed"] is True
    candidate_root = tmp_path / "experiments" / "C" / "Q1" / "candidate" / run_id
    candidate_result = candidate_root / "results.json"
    candidate_intent = candidate_root / "visual_intent.yaml"
    assert candidate_intent == tmp_path / scratch_intent["intent"].replace("/scratch/", "/candidate/")
    candidate_brief_result = figure_brief(
        tmp_path,
        "C",
        "Q1",
        run_id,
        candidate_intent,
        brief_config(tmp_path, run_id, candidate_result, status="REVIEWED", level="candidate"),
    )
    assert candidate_brief_result["brief_status"] == "REVIEWED"

    promoted = promote(tmp_path, "C", "Q1", run_id)
    formal_manifest = tmp_path / promoted["manifest"]
    formal_root = formal_manifest.parent
    data_path = formal_root / "figure_data_manifest.yaml"
    intent_path = formal_root / "visual_intent.yaml"
    brief_path = formal_root / "figure_briefs" / "fig-q1-main.yaml"
    data = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    intent = yaml.safe_load(intent_path.read_text(encoding="utf-8"))
    brief = yaml.safe_load(brief_path.read_text(encoding="utf-8"))

    assert data["level"] == "formal"
    assert data["status"] == "DATA_READY"
    assert data["contest_evidence_eligible"] is True
    assert data["source_run_manifest"] == formal_manifest.relative_to(tmp_path).as_posix()
    assert data["source_run_manifest_sha256"] == sha256(formal_manifest)
    assert data["source_artifacts"][0]["path"] == (formal_root / "results.json").relative_to(tmp_path).as_posix()
    assert data["source_artifacts"][0]["sha256"] == sha256(formal_root / "results.json")

    assert intent["status"] == "READY"
    assert intent["contest_evidence_eligible"] is True
    assert intent["source_data_manifest"] == data_path.relative_to(tmp_path).as_posix()
    assert intent["source_data_manifest_sha256"] == sha256(data_path)

    assert brief["status"] == "REVIEWED"
    assert brief["contest_evidence_eligible"] is True
    assert brief["source_data_manifest"] == data_path.relative_to(tmp_path).as_posix()
    assert brief["source_data_manifest_sha256"] == sha256(data_path)
    assert brief["visual_intent"] == intent_path.relative_to(tmp_path).as_posix()
    assert brief["visual_intent_sha256"] == sha256(intent_path)
    assert brief["source_data"] == [(formal_root / "results.json").relative_to(tmp_path).as_posix()]
    assert brief["evidence_chain"][0]["locator"].startswith(
        (formal_root / "results.json").relative_to(tmp_path).as_posix() + ":"
    )
    assert brief["data_integrity"]["source_hashes"][0]["path"] == (
        formal_root / "results.json"
    ).relative_to(tmp_path).as_posix()
    assert all("/scratch/" not in path and "/candidate/" not in path for path in (
        data["source_run_manifest"],
        data["source_artifacts"][0]["path"],
        intent["source_data_manifest"],
        brief["source_data_manifest"],
        brief["visual_intent"],
        brief["source_data"][0],
        brief["evidence_chain"][0]["locator"],
    ))


def test_lifecycle_transition_marks_changed_plotting_code_stale(tmp_path: Path) -> None:
    scaffold_workspace(tmp_path)
    run_id = "changed-plot-code"
    _, result = write_run(tmp_path, run_id, "candidate")
    figure_data(tmp_path, "C", "Q1", run_id, figure_data_config(tmp_path, run_id, result))
    intent = figure_intent(tmp_path, "C", "Q1", run_id, intent_config(tmp_path, run_id))
    brief_result = figure_brief(
        tmp_path,
        "C",
        "Q1",
        run_id,
        tmp_path / intent["intent"],
        brief_config(tmp_path, run_id, result, status="REVIEWED", level="candidate"),
    )
    reviewed_brief = yaml.safe_load((tmp_path / brief_result["brief"]).read_text(encoding="utf-8"))
    reviewed_hash = reviewed_brief["source_script_sha256"]
    source_script = tmp_path / reviewed_brief["source_script"]
    source_script.write_text(source_script.read_text(encoding="utf-8") + "\n# changed after review\n", encoding="utf-8")

    assert checkpoint(tmp_path, "C", "Q1", strict=True)["passed"] is True
    promoted = promote(tmp_path, "C", "Q1", run_id)
    formal_brief = Path(tmp_path / promoted["manifest"]).parent / "figure_briefs" / "fig-q1-main.yaml"
    payload = yaml.safe_load(formal_brief.read_text(encoding="utf-8"))

    assert payload["status"] == "STALE"
    assert payload["source_script_sha256"] == reviewed_hash
    assert payload["source_script_sha256"] != sha256(source_script)


def prepare_ready_paper_evidence(root: Path, run_id: str = "paper-visual") -> tuple[Path, Path, Path]:
    _, formal_manifest, _ = prepare_formal_question(root, "formal-parent")
    formal = json.loads(formal_manifest.read_text(encoding="utf-8"))
    child_root = root / "experiments" / "C" / "Q1" / "paper-evidence" / run_id
    child_root.mkdir(parents=True, exist_ok=True)
    child_result = child_root / "results.json"
    child_result.write_text(json.dumps({"metrics": {"score": 12.5, "baseline": 10.0}}), encoding="utf-8")
    config = root / "experiments" / "configs" / f"{run_id}.yaml"
    dump_yaml(
        config,
        {
            "schema_version": 2,
            "experiment_id": run_id,
            "problem": "C",
            "question": "Q1",
            "engine": "python",
            "runner": formal["code"]["runner"],
            "seed": formal["random_seed"],
            "output_root": "experiments/C/Q1/paper-evidence",
            "arguments": list(formal.get("arguments", [])),
            "diagnostic_arguments": [],
            "run_mode": "paper-evidence",
            "level": "paper-evidence",
            "mode": "probe",
            "purpose": "paper",
            "formal_candidate": False,
            "parent_run_id": formal["run_id"],
            "source_run_id": formal["run_id"],
            "source_manifest": formal_manifest.relative_to(root).as_posix(),
            "source_manifest_sha256": sha256(formal_manifest),
            "evidence_scope": "figure_support",
            "checkpoint_id": None,
            "primary_metric": "score",
            "checks": {
                "input_output_match": True,
                "units_defined": True,
                "core_constraints_passed": True,
                "deterministic": True,
                "baseline_comparable": True,
            },
            "reuse_contract": {
                "seed": True,
                "environment": True,
                "code": True,
                "inputs": True,
                "methods": True,
                "parameters": True,
            },
            "replay": {"required": True, "count": 2},
            "methods": deepcopy(formal["methods"]),
            "inputs": [],
            "metrics": [
                {
                    "name": "score",
                    "unit": "万元",
                    "locator": f"experiments/C/Q1/paper-evidence/{run_id}/results.json:metrics.score",
                    "primary": True,
                }
            ],
        },
    )
    record_run(
        root,
        config,
        ["python", formal["code"]["runner"]],
        deepcopy(formal["environment"]),
        "2026-08-11T03:00:00+00:00",
        0.1,
        True,
    )
    ready = paper_evidence(root, "C", "Q1", config, strict=True)
    assert ready["status"] == "READY"
    child_manifest = child_root / "run_manifest.json"
    return formal_manifest, child_manifest, child_result


@pytest.mark.parametrize("drift_target", ["parent", "child"])
def test_ready_paper_evidence_manifest_drift_blocks_figure_data_and_render(
    tmp_path: Path,
    drift_target: str,
) -> None:
    run_id = f"paper-{drift_target}"
    formal_manifest, child_manifest, child_result = prepare_ready_paper_evidence(tmp_path, run_id)
    figure_data(tmp_path, "C", "Q1", run_id, figure_data_config(tmp_path, run_id, child_result))
    intent_result = figure_intent(tmp_path, "C", "Q1", run_id, intent_config(tmp_path, run_id))
    brief_result = figure_brief(
        tmp_path,
        "C",
        "Q1",
        run_id,
        tmp_path / intent_result["intent"],
        brief_config(tmp_path, run_id, child_result, level="paper-evidence"),
    )
    brief_path = tmp_path / brief_result["brief"]
    drift_path = formal_manifest if drift_target == "parent" else child_manifest
    drifted = json.loads(drift_path.read_text(encoding="utf-8"))
    drifted["post_ready_drift"] = drift_target
    drift_path.write_text(json.dumps(drifted, ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="paper-evidence|READY|stale|hash"):
        figure_render(tmp_path, "C", "Q1", run_id, brief_path)
    with pytest.raises(ValueError, match="paper-evidence|READY|stale|hash"):
        figure_data(tmp_path, "C", "Q1", run_id, figure_data_config(tmp_path, run_id, child_result))


def prepare_approved_brief(root: Path, run_id: str = "run-v5") -> tuple[Path, Path, Path, Path]:
    question_path, formal_manifest, result = prepare_formal_question(root, run_id)
    data_result = figure_data(root, "C", "Q1", run_id, figure_data_config(root, run_id, result))
    intent_result = figure_intent(root, "C", "Q1", run_id, intent_config(root, run_id))
    brief_result = figure_brief(
        root,
        "C",
        "Q1",
        run_id,
        root / intent_result["intent"],
        brief_config(root, run_id, result),
    )
    assert data_result["contest_evidence_eligible"] is True
    return question_path, formal_manifest, result, root / brief_result["brief"]


def test_formal_declared_figure_requires_current_approved_brief(tmp_path: Path) -> None:
    question_path, _, _, brief_path = prepare_approved_brief(tmp_path)
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    question["paper"]["figure_ids"] = ["fig-q1-main"]
    dump_yaml(question_path, question)

    assert validate(tmp_path, "C", "G3", "Q1", write=False, strict=True)["passed"] is True
    assert validate(tmp_path, "C", "G4", "Q1", write=False, strict=True)["passed"] is True

    brief = yaml.safe_load(brief_path.read_text(encoding="utf-8"))
    brief["source_data_manifest_sha256"] = "0" * 64
    dump_yaml(brief_path, brief)
    report = validate(tmp_path, "C", "G3", "Q1", write=False, strict=True)
    design_check = next(item for item in report["checks"] if item["name"] == "G3_figure_brief")

    assert report["passed"] is False
    assert design_check["passed"] is False


def test_source_data_drift_blocks_render_before_qa(tmp_path: Path) -> None:
    _, _, result, brief_path = prepare_approved_brief(tmp_path)
    result.write_text(json.dumps({"metrics": {"score": 99.0, "baseline": 10.0}}), encoding="utf-8")

    with pytest.raises(ValueError, match="stale|hash"):
        figure_render(tmp_path, "C", "Q1", "run-v5", brief_path)


def test_undeclared_evidence_field_blocks_render(tmp_path: Path) -> None:
    _, _, _, brief_path = prepare_approved_brief(tmp_path)
    brief = yaml.safe_load(brief_path.read_text(encoding="utf-8"))
    brief["evidence_chain"][0]["fields"] = ["metrics.unregistered"]
    dump_yaml(brief_path, brief)

    with pytest.raises(ValueError, match="undeclared fields"):
        figure_render(tmp_path, "C", "Q1", "run-v5", brief_path)


def test_renderer_cannot_write_outside_figure_staging(tmp_path: Path) -> None:
    _, _, _, brief_path = prepare_approved_brief(tmp_path)
    brief = yaml.safe_load(brief_path.read_text(encoding="utf-8"))
    source_script = tmp_path / brief["source_script"]
    source_script.write_text(
        source_script.read_text(encoding="utf-8")
        + "\ntarget = Path('paper/sections/unauthorized-render-write.tex')\n"
        + "target.parent.mkdir(parents=True, exist_ok=True)\n"
        + "target.write_text('changed', encoding='utf-8')\n",
        encoding="utf-8",
    )
    brief["source_script_sha256"] = sha256(source_script)
    dump_yaml(brief_path, brief)

    with pytest.raises(RuntimeError, match="outside its staging directory"):
        figure_render(tmp_path, "C", "Q1", "run-v5", brief_path)


def test_renderer_cannot_reuse_stale_staging_outputs(tmp_path: Path) -> None:
    _, _, _, brief_path = prepare_approved_brief(tmp_path)
    figure_render(tmp_path, "C", "Q1", "run-v5", brief_path)
    brief = yaml.safe_load(brief_path.read_text(encoding="utf-8"))
    source_script = tmp_path / brief["source_script"]
    source_script.write_text("from __future__ import annotations\n", encoding="utf-8")
    brief["source_script_sha256"] = sha256(source_script)
    dump_yaml(brief_path, brief)

    with pytest.raises(FileNotFoundError, match="did not create"):
        figure_render(tmp_path, "C", "Q1", "run-v5", brief_path)
    assert not any((tmp_path / path).exists() for key, path in brief["outputs"].items() if key != "png_dpi")


@pytest.mark.parametrize("decision", ["text", "none"])
def test_strict_g5_accepts_current_text_or_none_design_decision(tmp_path: Path, decision: str) -> None:
    question_path, formal_manifest, result = prepare_formal_question(tmp_path)
    dump_yaml(tmp_path / "project.yaml", {"workflow_contract_version": 5})
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    question["paper"]["table_ids"] = []
    question["paper"]["figure_ids"] = []
    question["evidence"]["runs"] = [formal_manifest.relative_to(tmp_path).as_posix()]
    dump_yaml(question_path, question)
    figure_data(tmp_path, "C", "Q1", "run-v5", figure_data_config(tmp_path, "run-v5", result))
    config_path = intent_config(tmp_path, "run-v5")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["artifact_decision"] = decision
    dump_yaml(config_path, config)
    figure_intent(tmp_path, "C", "Q1", "run-v5", config_path)

    report = validate(tmp_path, "C", "G5", "Q1", write=False, strict=True)
    decision_check = next(item for item in report["checks"] if item["name"] == "G5_nonfigure_design_decision")

    assert report["passed"] is True, [item for item in report["checks"] if not item["passed"]]
    assert decision_check["passed"] is True


def test_render_qa_promote_rejects_unapproved_or_failed_then_succeeds(tmp_path: Path) -> None:
    question_path, _, _, brief_path = prepare_approved_brief(tmp_path)
    rendered = figure_render(tmp_path, "C", "Q1", "run-v5", brief_path)
    assert rendered["status"] == "RENDERED"
    rendered_brief = yaml.safe_load(brief_path.read_text(encoding="utf-8"))
    rendered_brief["label_strategy"]["collision_checked"] = True
    dump_yaml(brief_path, rendered_brief)
    output_dir = tmp_path / "experiments" / "C" / "Q1" / "formal" / "run-v5" / "figure-staging" / "fig-q1-main" / "outputs"
    qa = figure_qa(tmp_path, "C", "Q1", "run-v5", brief_path, output_dir)
    qa_path = tmp_path / qa["qa"]
    assert qa["passed"] is True

    approved_brief = yaml.safe_load(brief_path.read_text(encoding="utf-8"))
    approved_qa = json.loads(qa_path.read_text(encoding="utf-8"))

    unapproved = deepcopy(approved_brief)
    unapproved["status"] = "REVIEWED"
    unapproved.pop("approval", None)
    dump_yaml(brief_path, unapproved)
    with pytest.raises(ValueError, match="not QA-passed"):
        figure_promote(tmp_path, "C", "Q1", "fig-q1-main", brief_path, qa_path)

    dump_yaml(brief_path, approved_brief)
    failed_qa = deepcopy(approved_qa)
    failed_qa["passed"] = False
    failed_qa["status"] = "FAIL"
    qa_path.write_text(json.dumps(failed_qa, ensure_ascii=False, indent=2), encoding="utf-8")
    with pytest.raises(ValueError, match="QA is missing, failed, or stale"):
        figure_promote(tmp_path, "C", "Q1", "fig-q1-main", brief_path, qa_path)

    qa_path.write_text(json.dumps(approved_qa, ensure_ascii=False, indent=2), encoding="utf-8")
    promoted = figure_promote(tmp_path, "C", "Q1", "fig-q1-main", brief_path, qa_path)

    assert promoted["status"] == "CONTRACT_READY"
    for suffix in ("pdf", "svg", "png"):
        assert (tmp_path / "paper" / "figures" / f"fig-q1-main.{suffix}").is_file()
    contracts = yaml.safe_load((tmp_path / "paper" / "figure_contracts.yaml").read_text(encoding="utf-8"))
    contract = contracts["figures"][0]
    assert contract["design_handoff"]["design_status"] == "APPROVED"
    assert contract["outputs"]["png_dpi"] == 400
    question = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    assert question["paper"]["figure_ids"] == ["fig-q1-main"]
    report = validate(tmp_path, "C", "G5", "Q1", write=False, strict=True)
    assert report["passed"] is True, [item for item in report["checks"] if not item["passed"]]

    prepare_script = ROOT / "src" / "utils" / "prepare_paper_figures.py"

    def run_prepare(manifest: Path, report_name: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        output = tmp_path / "output" / report_name
        completed = subprocess.run(
            [
                sys.executable,
                str(prepare_script),
                "--root",
                str(tmp_path),
                "--manifest",
                str(manifest),
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        return completed, json.loads(output.read_text(encoding="utf-8"))

    contracts_path = tmp_path / "paper" / "figure_contracts.yaml"
    prepared, prepared_report = run_prepare(contracts_path, "prepare-valid.json")
    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    assert prepared_report["passed"] is True

    legacy = deepcopy(contracts)
    legacy["figures"][0].pop("design_handoff")
    legacy_path = tmp_path / "paper" / "figure_contracts-legacy.yaml"
    dump_yaml(legacy_path, legacy)
    legacy_result, legacy_report = run_prepare(legacy_path, "prepare-legacy.json")
    assert legacy_result.returncode == 0, legacy_result.stdout + legacy_result.stderr
    assert legacy_report["passed"] is True

    stale = deepcopy(contracts)
    stale["figures"][0]["design_handoff"]["figure_brief_sha256"] = "0" * 64
    stale_path = tmp_path / "paper" / "figure_contracts-stale.yaml"
    dump_yaml(stale_path, stale)
    stale_result, stale_report = run_prepare(stale_path, "prepare-stale.json")
    assert stale_result.returncode != 0
    assert any(item["code"] == "DESIGN_HANDOFF" for item in stale_report["errors"])


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        ("output/release/CCM2604653.pdf", "f2a637d4d4359aaf754f444cde40e33490004122b09dc1602aeaaa29fc6f4b1f"),
        ("output/release/CCM2604653附件.zip", "c69b86a0453290bda03fbfda6901d475661cd57df1d079ce0ba5a9cbe7468ac0"),
        ("results/C/claims.json", "99b298cc561645f5077065db153ed7ab5ac346bc0a718f33bd7dd771a9d3a11e"),
        ("paper/figure_contracts.yaml", "1b5be1056793e584bfe72651629867a168171de088209228dd05a920070d7aa5"),
    ],
)
def test_sealed_huashu_release_evidence_hashes_do_not_drift(relative: str, expected: str) -> None:
    sealed_root = ROOT / "projects" / "huashu-cup" / "2026"
    assert sha256(sealed_root / relative) == expected
