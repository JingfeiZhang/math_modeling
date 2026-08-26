from __future__ import annotations

import json
import hashlib
import zipfile
from pathlib import Path

import yaml

from src.utils import audit_ai_usage, audit_code_parity, audit_package, audit_submission, release_submission


def test_ai_audit_is_always_advisory_for_formal_problem(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir()
    (tmp_path / "contest.yaml").write_text(
        yaml.safe_dump({"problem": "C"}, allow_unicode=True), encoding="utf-8"
    )
    policy = {
        "source": {"status": "pending", "url": None, "sha256": None},
        "log": {"path": "output/ai_usage_log.jsonl", "required_fields": ["tool"]},
        "disclosure": {"required": True, "paper_locator": "paper/main.tex"},
    }
    policy_path = tmp_path / "config" / "ai_usage_policy.yaml"
    policy_path.write_text(yaml.safe_dump(policy), encoding="utf-8")

    result = audit_ai_usage.audit(tmp_path, policy_path)

    assert result["formal"] is True
    assert result["passed"] is True
    assert result["blocking"] is False
    assert result["errors"] == []
    assert {item["code"] for item in result["warnings"]} >= {
        "AI_POLICY_SOURCE_PENDING",
        "AI_LOG_MISSING",
        "AI_DISCLOSURE_MISSING",
    }


def _submission_fixture(tmp_path: Path, policy: str) -> None:
    (tmp_path / "output").mkdir()
    (tmp_path / "paper").mkdir()
    (tmp_path / "output" / "submission.pdf").write_bytes(b"pdf-fixture")
    (tmp_path / "paper" / "main.log").write_text("MATHMODEL:CUMCM_BODY_PAGES=3\n", encoding="utf-8")
    (tmp_path / "contest.yaml").write_text(
        yaml.safe_dump(
            {
                "problem": "TBD",
                "format": {
                    "paper_body_max_pages": 30,
                    "paper_max_mb": 20,
                    "searchable_pdf_min_chars_per_page": 20,
                    "searchable_pdf_min_page_ratio": 0.8,
                },
                "submission": {"searchable_pdf_policy": policy},
                "paths": {"paper_pdf": "output/submission.pdf", "audit_json": "output/audit.json"},
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    for name in (
        "paper_audit.json",
        "figure_audit.json",
        "figure_style_audit.json",
        "pdf_visual_audit.json",
        "code_parity_audit.json",
        "ai_usage_audit.json",
    ):
        (tmp_path / "output" / name).write_text(json.dumps({"passed": True}), encoding="utf-8")


def test_recommended_searchable_pdf_is_warning_under_strict(tmp_path: Path, monkeypatch) -> None:
    _submission_fixture(tmp_path, "recommended")
    monkeypatch.setattr(audit_submission, "pdf_pages", lambda _: ["", "x" * 40, "y" * 40])
    monkeypatch.setattr(audit_submission, "pdf_metadata", lambda _: ([], None))

    result = audit_submission.audit(tmp_path, strict=True, skip_package=True)

    assert result["status"] == "PASS"
    assert result["searchable_pdf"]["policy"] == "recommended"
    assert {item["name"] for item in result["warnings"]} >= {"searchable_pdf", "abstract_on_first_page"}


def test_required_searchable_pdf_still_blocks_low_ratio(tmp_path: Path, monkeypatch) -> None:
    _submission_fixture(tmp_path, "required")
    monkeypatch.setattr(audit_submission, "pdf_pages", lambda _: ["", "x" * 40, "y" * 40])
    monkeypatch.setattr(audit_submission, "pdf_metadata", lambda _: ([], None))

    result = audit_submission.audit(tmp_path, strict=True, skip_package=True)

    assert result["status"] == "FAIL"
    assert any(item["name"] == "searchable_pdf" and not item["passed"] for item in result["checks"])


def test_zero_searchable_pages_always_blocks(tmp_path: Path, monkeypatch) -> None:
    _submission_fixture(tmp_path, "recommended")
    monkeypatch.setattr(audit_submission, "pdf_pages", lambda _: ["", "", ""])
    monkeypatch.setattr(audit_submission, "pdf_metadata", lambda _: ([], None))

    result = audit_submission.audit(tmp_path, strict=True, skip_package=True)

    assert result["status"] == "FAIL"
    assert any(item["name"] == "searchable_pdf" and not item["passed"] for item in result["checks"])


def test_release_verify_detects_md5_and_sha256_changes(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    paper = output / "submission.pdf"
    support = output / "supporting.zip"
    paper.write_bytes(b"paper-v1")
    support.write_bytes(b"support-v1")
    manifest = output / "release_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "artifacts": [
                    release_submission.relative_digest(tmp_path, paper),
                    release_submission.relative_digest(tmp_path, support),
                ],
                "audit_evidence": [],
            }
        ),
        encoding="utf-8",
    )

    assert release_submission.verify(tmp_path, manifest)["passed"] is True
    paper.write_bytes(b"paper-v2")
    result = release_submission.verify(tmp_path, manifest)
    assert result["passed"] is False
    assert any("changed after sealing" in error for error in result["errors"])


def test_release_seal_refuses_precontest_tbd(tmp_path: Path) -> None:
    (tmp_path / "contest.yaml").write_text(yaml.safe_dump({"problem": "TBD"}), encoding="utf-8")

    try:
        release_submission.seal(tmp_path)
    except ValueError as exc:
        assert "forbidden before a real problem" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("precontest release sealing unexpectedly succeeded")


def test_release_seal_publishes_only_upload_artifacts(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    (output / "submission.pdf").write_bytes(b"paper")
    (output / "supporting.zip").write_bytes(b"support")
    for name in release_submission.AUDIT_REPORTS:
        (output / name).write_text(json.dumps({"passed": True}), encoding="utf-8")
    (tmp_path / "contest.yaml").write_text(
        yaml.safe_dump(
            {
                "competition": "CUMCM",
                "year": 2026,
                "problem": "C",
                "submission": {
                    "paper_filename": "C123.pdf",
                    "support_filename": "C123附件.zip",
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = release_submission.seal(tmp_path)

    assert result["passed"] is True
    assert sorted(path.name for path in (tmp_path / "submission").iterdir()) == ["C123.pdf", "C123附件.zip"]
    manifest = json.loads((tmp_path / "output" / "release" / "release_manifest.json").read_text(encoding="utf-8"))
    assert manifest["publish_dir"] == "submission"
    assert {item["path"] for item in manifest["artifacts"]} == {"submission/C123.pdf", "submission/C123附件.zip"}


def test_strict_package_audit_rejects_outside_whitelist(tmp_path: Path) -> None:
    (tmp_path / "paper").mkdir()
    (tmp_path / "paper" / "main.tex").write_text("% fixture\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("must not ship\n", encoding="utf-8")

    result = audit_package.audit(tmp_path, strict=True)

    assert result["passed"] is False
    assert any(item["code"] == "OUTSIDE_WHITELIST" for item in result["errors"])


def test_submission_packager_reads_only_curated_source_tree() -> None:
    script = (Path(__file__).resolve().parents[1] / "scripts" / "package_submission.ps1").read_text(encoding="utf-8")
    assert "$submissionSource = Join-Path $root 'src\\submission'" in script
    assert "Get-ChildItem -LiteralPath $root" not in script
    assert "Get-ChildItem -LiteralPath $sharedRoot" not in script
    assert "Copy-Item -LiteralPath $root" not in script
    assert "scratch" not in script.lower()
    assert "prompts" not in script.lower()
    assert "literature" not in script.lower()
    assert "_verification" not in script.lower()


def test_strict_package_audit_requires_exact_embedded_manifest(tmp_path: Path) -> None:
    support = tmp_path / "support"
    (support / "manifest").mkdir(parents=True)
    members = {
        "README.md": b"reproducible supporting package\n",
        "requirements.txt": b"pyyaml\n",
        "run.py": b"print('verify')\n",
    }
    for name, data in members.items():
        (support / name).write_bytes(data)
    lines = [f"{hashlib.sha256(data).hexdigest()}  {name}" for name, data in sorted(members.items())]
    (support / "manifest" / "package_manifest.sha256").write_text("\n".join(lines) + "\n", encoding="ascii")

    result = audit_package.audit(support, strict=True)
    assert result["passed"] is True

    (support / "results").mkdir()
    (support / "results" / "unlisted.json").write_text("{}\n", encoding="utf-8")
    result = audit_package.audit(support, strict=True)
    assert result["passed"] is False
    assert any(item["code"] == "PACKAGE_MEMBER_UNLISTED" for item in result["errors"])


def test_code_parity_detects_support_hash_mismatch(tmp_path: Path) -> None:
    (tmp_path / "paper").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "output").mkdir()
    (tmp_path / "contest.yaml").write_text(yaml.safe_dump({"problem": "TBD"}), encoding="utf-8")
    (tmp_path / "paper" / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\n\\lstinputlisting{src/model.py}\n\\end{document}\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "model.py").write_text("print('paper')\n", encoding="utf-8")
    support = tmp_path / "output" / "supporting.zip"
    with zipfile.ZipFile(support, "w") as archive:
        archive.writestr("src/model.py", "print('support')\n")

    result = audit_code_parity.audit(tmp_path, tmp_path / "paper", support)

    assert result["passed"] is False
    assert any(item["code"] == "CODE_HASH_MISMATCH" for item in result["errors"])


def test_release_and_audit_scripts_pin_independent_prefix() -> None:
    root = Path(__file__).resolve().parents[1]
    release_script = (root / "scripts" / "release_submission.ps1").read_text(encoding="utf-8")
    audit_script = (root / "scripts" / "audit_submission.ps1").read_text(encoding="utf-8")
    assert "-DisableUserSite" in release_script
    assert "-DisableUserSite" in audit_script
    assert "Tier full" in release_script
    assert "pypdf" in (root / "environment-extended.yml").read_text(encoding="utf-8")
