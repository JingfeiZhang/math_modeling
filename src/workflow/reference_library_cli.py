"""Strict CLI boundary for the competition reference library.

The underlying :mod:`reference_library` module contains the mature validation,
lookup, status, card/module and algorithm-source logic.  This adapter changes
only playbook discovery: the L3 layer is an explicit, reviewable set of P1-P3
cross-module playbooks.  Cross-stage quality guides may coexist in the
repository but are never interpreted as routable L3 assets.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from src.workflow import reference_library as lib
except ModuleNotFoundError:  # Direct execution from scripts/reference-library.ps1.
    import reference_library as lib


ROUTABLE_PLAYBOOK_FILENAMES = (
    "constraint-modeling-quality.md",
    "data-to-decision-modeling.md",
    "mechanism-fit-and-scenario.md",
    "predict-then-optimize.md",
    "resource-allocation-under-uncertainty.md",
)


def routable_playbook_records(
    workspace_root: Path,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return only schema-governed L3 playbooks.

    This intentionally reuses ``lib.validate_playbook`` and the validated L2
    module records.  A missing declared L3 asset is an issue; unrelated Markdown
    files in ``playbooks/`` are compatibility documentation and are ignored by
    the routable layer.
    """

    modules, module_issues = lib.module_records(workspace_root)
    modules_by_id = {str(item["module_id"]): item for item in modules}
    playbook_dir = (
        lib.library_root(workspace_root)
        / "references"
        / "competition-knowledge"
        / "playbooks"
    )

    records: list[dict[str, Any]] = []
    issues = list(module_issues)
    seen_ids: set[str] = set()

    for filename in ROUTABLE_PLAYBOOK_FILENAMES:
        path = playbook_dir / filename
        if not path.is_file():
            issues.append(f"declared routable playbook is missing: {filename}")
            continue

        playbook_issues = lib.validate_playbook(path, modules_by_id)
        try:
            front, body = lib._frontmatter(path)
        except (OSError, ValueError, lib.yaml.YAMLError):
            issues.extend(playbook_issues)
            continue

        playbook_id = str(front.get("playbook_id", path.stem))
        if playbook_id in seen_ids:
            playbook_issues.append(f"duplicate playbook_id: {playbook_id}")
        seen_ids.add(playbook_id)
        issues.extend(playbook_issues)
        records.append(
            {
                "path": path,
                "playbook_id": playbook_id,
                "tags": [
                    str(item).lower()
                    for item in front.get("tags", [])
                    if isinstance(item, str)
                ],
                "modules": [str(item) for item in front.get("modules", [])],
                "stage_scope": list(front.get("stage_scope", [])),
                "body": body,
                "valid": not playbook_issues,
            }
        )

    return records, issues


def install_strict_playbook_boundary() -> None:
    """Install the L3 discovery boundary for all existing library operations."""

    lib.playbook_records = routable_playbook_records


def main() -> int:
    install_strict_playbook_boundary()
    return lib.main()


if __name__ == "__main__":
    raise SystemExit(main())
