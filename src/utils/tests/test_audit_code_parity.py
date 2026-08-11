from __future__ import annotations

import sys
import zipfile
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from src.utils import audit_code_parity  # noqa: E402


def make_project(tmp_path: Path) -> tuple[Path, Path, bytes]:
    paper = tmp_path / "paper"
    code = tmp_path / "src" / "submission" / "code"
    output = tmp_path / "output"
    paper.mkdir(parents=True)
    code.mkdir(parents=True)
    output.mkdir()
    payload = b"print('verified')\n"
    (tmp_path / "contest.yaml").write_text("problem: C\n", encoding="utf-8")
    (paper / "main.tex").write_text(
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\\lstinputlisting{../src/submission/code/model.py}\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    (paper / "code_manifest.yaml").write_text(
        "schema_version: 2\n"
        "files:\n"
        "  - path: src/submission/code/model.py\n"
        "    support_path: code/model.py\n",
        encoding="utf-8",
    )
    (code / "model.py").write_bytes(payload)
    return paper, output / "supporting.zip", payload


def test_exact_manifest_listing_and_zip_match(tmp_path: Path) -> None:
    paper, support, payload = make_project(tmp_path)
    with zipfile.ZipFile(support, "w") as archive:
        archive.writestr("code/model.py", payload)

    result = audit_code_parity.audit(tmp_path, paper, support)

    assert result["passed"] is True
    assert result["support_checked"] is True
    assert result["metrics"]["manifest_code_entries"] == 1
    assert result["metrics"]["latex_code_listings"] == 1
    assert result["metrics"]["paper_code_entries"] == 1
    assert result["entries"][0]["path"] == "src/submission/code/model.py"
    assert result["entries"][0]["support_path"] == "code/model.py"


def test_missing_support_archive_is_not_marked_checked(tmp_path: Path) -> None:
    paper, support, _ = make_project(tmp_path)

    result = audit_code_parity.audit(tmp_path, paper, support)

    assert result["passed"] is False
    assert result["support_checked"] is False
    assert any(item["code"] == "SUPPORT_ARCHIVE_MISSING" for item in result["errors"])


def test_support_hash_mismatch_fails_after_real_zip_read(tmp_path: Path) -> None:
    paper, support, _ = make_project(tmp_path)
    with zipfile.ZipFile(support, "w") as archive:
        archive.writestr("code/model.py", b"print('changed')\n")

    result = audit_code_parity.audit(tmp_path, paper, support)

    assert result["passed"] is False
    assert result["support_checked"] is True
    assert any(item["code"] == "CODE_HASH_MISMATCH" for item in result["errors"])


def test_package_script_uses_only_curated_submission_tree() -> None:
    script = (WORKSPACE_ROOT / "scripts" / "package_submission.ps1").read_text(encoding="utf-8")

    assert "src\\submission" in script
    assert "no legacy fallback is enabled" in script
    assert "Join-Path $stage 'src\\submission'" not in script
    assert "$destination = Join-Path $stage ($relative.Replace('/', '\\'))" in script
    assert "foreach ($dir in @('paper','src','experiments'" not in script
