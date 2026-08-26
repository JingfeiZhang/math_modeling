from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from src.utils import record_ai_usage  # noqa: E402


def policy() -> dict:
    return {
        "state": {"path": "output/ai_usage_state.yaml"},
        "log": {
            "path": "output/ai/raw_usage.jsonl",
            "required_fields": [
                "timestamp",
                "tool",
                "model_version",
                "purpose",
                "stage",
                "prompt_summary",
                "output_used",
                "human_verification",
            ],
            "ai_roles": ["candidate_generation", "code_debugging"],
        },
    }


def test_first_recorded_event_marks_project_used(tmp_path: Path) -> None:
    root = tmp_path / "project"
    (root / "output").mkdir(parents=True)
    (root / "contest.yaml").write_text("problem: A\n", encoding="utf-8")

    args = argparse.Namespace(
        timestamp="2026-09-10T19:00:00+08:00",
        event_id="AI-test",
        tool="ChatGPT",
        model_version="GPT-X",
        purpose="比较候选模型",
        stage="P1",
        prompt_summary="比较候选方案",
        output_used="modified",
        human_verification="checked against problem statement",
        disclosure_stage="problem_analysis",
        ai_role=["candidate_generation"],
        human_modification="删除不满足约束的方案",
        reviewer=None,
        evidence_locator=None,
        question="Q1",
    )
    event = record_ai_usage.build_event(args)
    assert record_ai_usage.validate_event(event, policy()) == []

    state_path = record_ai_usage.ensure_used_state(root, policy())
    target = root / "output" / "ai" / "raw_usage.jsonl"
    record_ai_usage.append_event(target, event)

    assert yaml.safe_load(state_path.read_text(encoding="utf-8"))["mode"] == "used"
    lines = [line for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 1
    saved = json.loads(lines[0])
    assert saved["event_id"] == "AI-test"
    assert saved["human_modification"] == "删除不满足约束的方案"


def test_not_used_state_rejects_new_ai_event(tmp_path: Path) -> None:
    root = tmp_path / "project"
    state = root / "output" / "ai_usage_state.yaml"
    state.parent.mkdir(parents=True)
    state.write_text("mode: not_used\n", encoding="utf-8")

    try:
        record_ai_usage.ensure_used_state(root, policy())
    except SystemExit as exc:
        assert "not_used" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("not_used state must reject AI recording")
