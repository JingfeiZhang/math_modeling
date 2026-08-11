from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from src.utils import audit_package  # noqa: E402


def write_zip(path: Path, members: dict[str, bytes | str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)


def valid_members() -> dict[str, str]:
    return {
        "README.md": "# Reproduction guide\n",
        "requirements.txt": "numpy==2.0.0\n",
        "run.py": "print('run')\n",
        "code/q1/model.py": "print('q1')\n",
        "input/README.md": "Derived inputs only.\n",
        "results/q1/summary.json": "{\"status\": \"ok\"}\n",
        "manifest/files.sha256": "0  code/q1/model.py\n",
    }


def test_strict_accepts_curated_zip_root_structure(tmp_path: Path) -> None:
    support = tmp_path / "supporting.zip"
    write_zip(support, valid_members())

    result = audit_package.audit(support, strict=True)

    assert result["passed"] is True
    assert result["errors"] == []
    assert result["metrics"]["entries"] == len(valid_members())


def test_strict_accepts_same_curated_directory_structure(tmp_path: Path) -> None:
    for name, payload in valid_members().items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")

    result = audit_package.audit(tmp_path, strict=True)

    assert result["passed"] is True
    assert result["errors"] == []


def test_strict_rejects_legacy_project_roots_and_extra_root_files(tmp_path: Path) -> None:
    support = tmp_path / "supporting.zip"
    write_zip(
        support,
        {
            **valid_members(),
            "paper/main.tex": "% must not ship\n",
            "experiments/C/Q1/run.json": "{}\n",
            "contest.yaml": "problem: C\n",
        },
    )

    result = audit_package.audit(support, strict=True)

    rejected = {
        item["message"].rsplit(": ", 1)[-1]
        for item in result["errors"]
        if item["code"] == "OUTSIDE_WHITELIST"
    }
    assert result["passed"] is False
    assert rejected == {"paper/main.tex", "experiments/C/Q1/run.json", "contest.yaml"}


def test_strict_rejects_hidden_cache_member(tmp_path: Path) -> None:
    support = tmp_path / "supporting.zip"
    write_zip(support, {**valid_members(), "code/__pycache__/model.pyc": b"cache"})

    result = audit_package.audit(support, strict=True)

    assert result["passed"] is False
    assert any(item["code"] == "OUTSIDE_WHITELIST" for item in result["errors"])


def test_zip_path_traversal_and_absolute_paths_remain_blocking(tmp_path: Path) -> None:
    support = tmp_path / "supporting.zip"
    write_zip(
        support,
        {
            **valid_members(),
            "../escape.py": "print('escape')\n",
            "C:/Users/contestant/model.py": "print('absolute')\n",
        },
    )

    result = audit_package.audit(support, strict=True)

    path_errors = [item for item in result["errors"] if item["code"] == "ZIP_PATH_TRAVERSAL"]
    assert result["passed"] is False
    assert len(path_errors) == 2
    assert any("path traversal" in item["message"] for item in path_errors)
    assert any("absolute path" in item["message"] for item in path_errors)


def test_nested_archive_remains_blocking(tmp_path: Path) -> None:
    nested_buffer = io.BytesIO()
    with zipfile.ZipFile(nested_buffer, "w") as nested:
        nested.writestr("code/hidden.py", "print('hidden')\n")
    support = tmp_path / "supporting.zip"
    write_zip(support, {**valid_members(), "results/archive.zip": nested_buffer.getvalue()})

    result = audit_package.audit(support, strict=True)

    assert result["passed"] is False
    assert any(item["code"] == "NESTED_ARCHIVE" for item in result["errors"])


def test_identity_scan_remains_blocking(tmp_path: Path) -> None:
    support = tmp_path / "supporting.zip"
    members = valid_members()
    members["README.md"] = "Contact: contestant@example.com\n"
    write_zip(support, members)

    result = audit_package.audit(support, strict=True)

    assert result["passed"] is False
    assert any(item["code"] == "IDENTITY_STRING" for item in result["errors"])
