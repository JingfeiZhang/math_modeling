"""Run the installed modeling-paper-studio Figure Contract auditor.

The upstream auditor predates project-local ``paper/figures`` graphic paths and
scans archived TeX files under ``paper/staging``.  Adapt those two behaviours
here so the formal audit follows the same source set and search path as
``main.tex`` without modifying the installed skill.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = [
    ROOT / "skill_staging" / "modeling-paper-studio" / "scripts" / "audit_figures.py",
    Path.home() / ".codex" / "skills" / "modeling-paper-studio" / "scripts" / "audit_figures.py",
]
TARGET = next((path for path in CANDIDATES if path.is_file()), None)
if TARGET is None:
    raise SystemExit("modeling-paper-studio audit_figures.py was not found")


def _load_target():
    spec = importlib.util.spec_from_file_location("modeling_paper_studio_audit_figures", TARGET)
    if spec is None or spec.loader is None:
        raise SystemExit(f"could not load Figure Contract auditor: {TARGET}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _resolve_graphic(paper_dir: Path, raw: str) -> Path | None:
    roots = (paper_dir, paper_dir / "figures")
    for root in roots:
        candidate = (root / raw).resolve()
        paths = [candidate]
        if not candidate.suffix:
            paths.extend(candidate.with_suffix(ext) for ext in (".pdf", ".svg", ".png", ".jpg", ".jpeg"))
        match = next((path for path in paths if path.is_file()), None)
        if match is not None:
            return match
    return None


def main() -> int:
    module = _load_target()
    module.resolve_graphic = _resolve_graphic

    original_rglob = Path.rglob

    def formal_rglob(path: Path, pattern: str):
        matches = original_rglob(path, pattern)
        if pattern == "*.tex" and path.name == "paper":
            return (candidate for candidate in matches if "staging" not in candidate.relative_to(path).parts)
        return matches

    Path.rglob = formal_rglob
    try:
        sys.argv[0] = str(TARGET)
        return int(module.main())
    finally:
        Path.rglob = original_rglob


if __name__ == "__main__":
    raise SystemExit(main())
