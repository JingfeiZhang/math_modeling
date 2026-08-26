from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import yaml
from pypdf import PdfWriter


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from src.utils import audit_ai_usage  # noqa: E402


def write_policy(workspace: Path) -> Path:
    snapshot = workspace / "config" / "rules" / "cumcm_ai_2026.yaml"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text("status: verified\nrule: cumcm-2026-ai\n", encoding="utf-8")
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
                "state": {
                    "path": "output/ai_usage_state.yaml",
                    "required_in_formal_project": True,
                    "allowed_modes": ["used", "not_used"],
                },
                "log": {
                    "path": "output/ai_usage_log.jsonl",
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
                "disclosure": {
                    "required": True,
                    "generated_statement_locator": "paper/generated/ai_usage_statement.tex",
                    "no_ai_text": "本参赛队在竞赛过程中未使用任何AI工具。",
                    "used_ai_required_markers": ["本参赛队在竞赛过程中使用了AI工具", "支撑材料"],
                },
                "details": {
                    "required_when_used": True,
                    "filename": "AI工具使用详情.pdf",
                    "generated_tex": "output/ai/generated/AI工具使用详情.tex",
                    "support_archive": "output/supporting.zip",
                    "package_member": "manifest/AI工具使用详情.pdf",
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return policy


def make_formal_project(root: Path) -> None:
    (root / "output").mkdir(parents=True, exist_ok=True)
    (root / "paper" / "generated").mkdir(parents=True, exist_ok=True)
    (root / "contest.yaml").write_text("problem: C\n", encoding="utf-8")


def write_details_source(root: Path) -> None:
    target = root / "output" / "ai" / "generated" / "AI工具使用详情.tex"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("AI工具使用详情\n使用工具及模型\n人工审核与验证\n", encoding="utf-8")


def make_pdf_bytes(tmp_path: Path) -> bytes:
    path = tmp_path / "details.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    with path.open("wb") as handle:
        writer.write(handle)
    return path.read_bytes()


def test_formal_not_used_declaration_passes(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    root = workspace / "project"
    make_formal_project(root)
    policy = write_policy(workspace)
    (root / "output" / "ai_usage_state.yaml").write_text("mode: not_used\n", encoding="utf-8")
    (root / "paper" / "generated" / "ai_usage_statement.tex").write_text(
        "本参赛队在竞赛过程中未使用任何AI工具。\n", encoding="utf-8"
    )

    result = audit_ai_usage.audit(root, policy)

    assert result["passed"] is True
    assert result["errors"] == []
    assert result["declared_ai_mode"] == "not_used"


def test_formal_used_requires_log_statement_and_valid_details_pdf(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    root = workspace / "project"
    make_formal_project(root)
    policy = write_policy(workspace)
    (root / "output" / "ai_usage_state.yaml").write_text("mode: used\n", encoding="utf-8")
    (root / "paper" / "generated" / "ai_usage_statement.tex").write_text(
        "本参赛队在竞赛过程中使用了AI工具，主要用于代码调试，详细使用情况见支撑材料。\n",
        encoding="utf-8",
    )
    entry = {
        "timestamp": "2026-09-10T20:00:00+08:00",
        "tool": "example-ai",
        "model_version": "model-x",
        "purpose": "代码调试",
        "stage": "求解实现",
        "prompt_summary": "检查数组越界并解释修复原因",
        "output_used": "partially",
        "human_verification": "reran tests and checked outputs",
    }
    (root / "output" / "ai_usage_log.jsonl").write_text(json.dumps(entry, ensure_ascii=False) + "\n", encoding="utf-8")
    write_details_source(root)
    pdf_bytes = make_pdf_bytes(tmp_path)
    with zipfile.ZipFile(root / "output" / "supporting.zip", "w") as archive:
        archive.writestr("manifest/AI工具使用详情.pdf", pdf_bytes)

    result = audit_ai_usage.audit(root, policy)

    assert result["passed"] is True
    assert result["errors"] == []
    assert result["metrics"]["details_pdf_present"] is True
    assert result["metrics"]["details_pdf_valid"] is True


def test_formal_used_with_placeholder_pdf_blocks_release(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    root = workspace / "project"
    make_formal_project(root)
    policy = write_policy(workspace)
    (root / "output" / "ai_usage_state.yaml").write_text("mode: used\n", encoding="utf-8")
    (root / "paper" / "generated" / "ai_usage_statement.tex").write_text(
        "本参赛队在竞赛过程中使用了AI工具，详细使用情况见支撑材料。\n", encoding="utf-8"
    )
    entry = {
        "timestamp": "2026-09-10T20:00:00+08:00",
        "tool": "example-ai",
        "model_version": "model-x",
        "purpose": "代码调试",
        "stage": "求解实现",
        "prompt_summary": "检查错误",
        "output_used": "yes",
        "human_verification": "verified manually",
    }
    (root / "output" / "ai_usage_log.jsonl").write_text(json.dumps(entry, ensure_ascii=False) + "\n", encoding="utf-8")
    write_details_source(root)
    with zipfile.ZipFile(root / "output" / "supporting.zip", "w") as archive:
        archive.writestr("manifest/AI工具使用详情.pdf", b"%PDF-1.4 placeholder")

    result = audit_ai_usage.audit(root, policy)

    assert result["passed"] is False
    assert any(item["code"] == "AI_DETAILS_PDF_INVALID" for item in result["errors"])


def test_formal_used_without_details_pdf_blocks_release(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    root = workspace / "project"
    make_formal_project(root)
    policy = write_policy(workspace)
    (root / "output" / "ai_usage_state.yaml").write_text("mode: used\n", encoding="utf-8")
    (root / "paper" / "generated" / "ai_usage_statement.tex").write_text(
        "本参赛队在竞赛过程中使用了AI工具，详细使用情况见支撑材料。\n", encoding="utf-8"
    )
    entry = {
        "timestamp": "2026-09-10T20:00:00+08:00",
        "tool": "example-ai",
        "model_version": "model-x",
        "purpose": "代码调试",
        "stage": "求解实现",
        "prompt_summary": "检查错误",
        "output_used": "no",
        "human_verification": "verified manually",
    }
    (root / "output" / "ai_usage_log.jsonl").write_text(json.dumps(entry, ensure_ascii=False) + "\n", encoding="utf-8")
    write_details_source(root)

    result = audit_ai_usage.audit(root, policy)

    assert result["passed"] is False
    assert any(item["code"] == "AI_DETAILS_PDF_MISSING" for item in result["errors"])
