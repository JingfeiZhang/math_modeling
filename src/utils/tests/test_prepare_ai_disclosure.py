from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from src.utils import aggregate_ai_usage, prepare_ai_disclosure  # noqa: E402


def write_policy(workspace: Path) -> Path:
    snapshot = workspace / "config" / "rules" / "cumcm_ai_2026.yaml"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text("status: verified\n", encoding="utf-8")
    digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    policy = workspace / "config" / "ai_usage_policy.yaml"
    policy.write_text(
        yaml.safe_dump(
            {
                "source": {
                    "status": "verified",
                    "url": "https://www.mcm.edu.cn/rule",
                    "pinned_snapshot": "config/rules/cumcm_ai_2026.yaml",
                    "pinned_snapshot_sha256": digest,
                },
                "state": {"path": "output/ai_usage_state.yaml", "allowed_modes": ["used", "not_used"]},
                "log": {
                    "path": "output/ai/raw_usage.jsonl",
                    "required_when_used": True,
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
                },
                "aggregation": {
                    "output": "output/ai/stage_summary.yaml",
                    "purposes_per_stage_max": 6,
                    "prompt_themes_per_stage_max": 2,
                    "human_actions_per_stage_max": 4,
                },
                "disclosure": {
                    "generated_statement_locator": "paper/generated/ai_usage_statement.tex",
                    "no_ai_text": "本参赛队在竞赛过程中未使用任何AI工具。",
                },
                "details": {
                    "generated_tex": "output/ai/generated/AI工具使用详情.tex",
                    "generated_pdf": "output/ai/generated/AI工具使用详情.pdf",
                    "package_source": "src/submission/manifest/AI工具使用详情.pdf",
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return policy


def make_project(root: Path, mode: str = "used") -> None:
    (root / "output" / "ai").mkdir(parents=True, exist_ok=True)
    (root / "paper" / "generated").mkdir(parents=True, exist_ok=True)
    (root / "contest.yaml").write_text("problem: B\n", encoding="utf-8")
    (root / "output" / "ai_usage_state.yaml").write_text(f"mode: {mode}\n", encoding="utf-8")


def write_events(root: Path) -> None:
    events = [
        {
            "event_id": "AI-1",
            "timestamp": "2026-09-10T19:00:00+08:00",
            "tool": "ChatGPT",
            "model_version": "GPT-X",
            "purpose": "比较候选模型",
            "stage": "P1",
            "prompt_summary": "根据题目条件比较候选方法",
            "ai_role": ["candidate_generation", "concept_explanation"],
            "output_used": "modified",
            "human_verification": "checked against problem constraints",
            "human_modification": "删除不满足题意的方案并重写约束",
        },
        {
            "event_id": "AI-2",
            "timestamp": "2026-09-11T01:00:00+08:00",
            "tool": "ChatGPT",
            "model_version": "GPT-X",
            "purpose": "代码实现与调试",
            "stage": "P3a",
            "prompt_summary": "检查求解程序的索引和约束实现",
            "ai_role": ["code_generation_assistance", "code_debugging"],
            "output_used": "modified",
            "human_verification": "reran baseline and constraint checks",
            "human_modification": "修改边界条件并重新运行",
        },
        {
            "event_id": "AI-3",
            "timestamp": "2026-09-12T12:00:00+08:00",
            "tool": "ChatGPT",
            "model_version": "GPT-X",
            "purpose": "结果解释与稳健性检查",
            "stage": "P4",
            "prompt_summary": "根据正式结果提出敏感性检查建议",
            "ai_role": ["result_interpretation", "robustness_suggestion"],
            "output_used": "verified_accepted",
            "human_verification": "verified with formal reruns",
        },
        {
            "event_id": "AI-4",
            "timestamp": "2026-09-13T08:00:00+08:00",
            "tool": "ChatGPT",
            "model_version": "GPT-X",
            "purpose": "论文表达整理",
            "stage": "P5",
            "prompt_summary": "在不新增数值的前提下优化段落表达",
            "ai_role": ["writing_assistance", "language_polishing"],
            "output_used": "modified",
            "human_verification": "checked against frozen claims",
            "human_modification": "按冻结结果修订措辞",
        },
    ]
    target = root / "output" / "ai" / "raw_usage.jsonl"
    target.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in events), encoding="utf-8")


def test_aggregate_groups_ai_usage_into_four_submission_stages(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    root = workspace / "project"
    make_project(root)
    policy = write_policy(workspace)
    write_events(root)

    summary = aggregate_ai_usage.aggregate(root, policy, "used")

    assert summary["unclassified_events"] == []
    assert summary["tools"] == [{"tool": "ChatGPT", "model_version": "GPT-X"}]
    assert all(summary["stages"][key]["used"] for key in summary["stages"])
    assert summary["stages"]["modeling_implementation"]["event_count"] == 1
    assert len(summary["stages"]["paper_writing"]["prompt_themes"]) <= 2


def test_prepare_creates_concise_statement_and_stage_level_details(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    root = workspace / "project"
    make_project(root)
    policy = write_policy(workspace)
    write_events(root)

    result = prepare_ai_disclosure.prepare(root, policy, compile_pdf=False)

    assert result["status"] == "READY"
    statement = (root / "paper" / "generated" / "ai_usage_statement.tex").read_text(encoding="utf-8")
    details = (root / "output" / "ai" / "generated" / "AI工具使用详情.tex").read_text(encoding="utf-8")
    assert "本参赛队在竞赛过程中使用了AI工具" in statement
    assert "详细使用情况见支撑材料" in statement
    assert "问题分析与思路拓展" in details
    assert "模型与算法实现辅助" in details
    assert "实验检查与结果分析" in details
    assert "论文表达辅助" in details
    assert "人工审核与验证" in details
    assert "event_count" not in details
    assert "AI-1" not in details


def test_not_used_mode_generates_statement_without_details(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    root = workspace / "project"
    make_project(root, mode="not_used")
    policy = write_policy(workspace)

    result = prepare_ai_disclosure.prepare(root, policy, compile_pdf=False)

    assert result["mode"] == "not_used"
    statement = (root / "paper" / "generated" / "ai_usage_statement.tex").read_text(encoding="utf-8")
    assert "未使用任何AI工具" in statement
    assert not (root / "output" / "ai" / "generated" / "AI工具使用详情.tex").exists()
