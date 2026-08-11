"""Audit and fingerprint the isolated Huashu Cup input package.

This script only reads the project input files and writes reproducible audit
artifacts. It does not create experiment state, claims, or figure contracts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_safe(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return value


def file_manifest(project: Path, roots: list[Path]) -> list[dict[str, Any]]:
    records = []
    for root in roots:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                records.append(
                    {
                        "path": path.relative_to(project).as_posix(),
                        "size_bytes": path.stat().st_size,
                        "sha256": sha256(path),
                    }
                )
    return records


def workbook_audit(path: Path) -> dict[str, Any]:
    book = pd.ExcelFile(path)
    sheets: dict[str, Any] = {}
    for sheet in book.sheet_names:
        frame = pd.read_excel(path, sheet_name=sheet)
        sheets[sheet] = {
            "rows": int(len(frame)),
            "columns": [str(c) for c in frame.columns],
            "missing_cells": int(frame.isna().sum().sum()),
            "duplicate_rows": int(frame.duplicated().sum()),
        }
    return {"path": path.name, "sha256": sha256(path), "sheets": sheets}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()
    project = args.project_root.resolve()
    data = project / "problems" / "C" / "data"
    source = project / "problems" / "C" / "source"
    output = project / "output"
    output.mkdir(parents=True, exist_ok=True)

    workloads = pd.read_excel(data / "workload_trace.xlsx", sheet_name="Sheet1")
    region_time = pd.read_excel(data / "region_time_data.xlsx", sheet_name="region_time_data")
    gpu = pd.read_excel(data / "GPU_information.xlsx", sheet_name="GPU中心基础情况")
    source_records = file_manifest(
        project,
        [project / "problems" / "_official", source, data],
    )

    gpu_util = region_time["GPU_Utilization_Percent"]
    input_audit = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "project_id": "huashu-cup-2026",
        "problem": "C",
        "scope": "read-only input audit; no formal claims or experiments created",
        "workload": {
            "rows": int(len(workloads)),
            "task_id_unique": bool(workloads["TaskID"].is_unique),
            "task_types": {str(k): int(v) for k, v in workloads["TaskType"].value_counts().sort_index().items()},
            "source_regions": sorted(workloads["SourceRegion"].dropna().astype(str).unique().tolist()),
            "arrival_hour_min": int(workloads["ArrivalHour"].min()),
            "arrival_hour_max": int(workloads["ArrivalHour"].max()),
            "latest_finish_min": json_safe(workloads["LatestFinishHour"].min()),
            "latest_finish_max": json_safe(workloads["LatestFinishHour"].max()),
            "missing_cells": int(workloads.isna().sum().sum()),
            "duplicate_rows": int(workloads.duplicated().sum()),
        },
        "region_time": {
            "rows": int(len(region_time)),
            "regions": sorted(region_time["Region"].dropna().astype(str).unique().tolist()),
            "hour_min": int(region_time["Hour"].min()),
            "hour_max": int(region_time["Hour"].max()),
            "expected_region_hour_rows": int(len(gpu) * 2407),
            "key_unique": bool(~region_time.duplicated(["Hour", "Region"]).any()),
            "missing_cells": int(region_time.isna().sum().sum()),
            "duplicate_rows": int(region_time.duplicated().sum()),
            "gpu_utilization_percent": {
                "min": float(gpu_util.min()),
                "max": float(gpu_util.max()),
                "rows_over_100": int((gpu_util > 100).sum()),
                "warning": "Baseline field exceeds 100 in some rows; verify definition before using as an optimization result.",
            },
        },
        "workbooks": [workbook_audit(path) for path in sorted(data.glob("*.xlsx"))],
        "source_files": source_records,
    }
    (output / "input_audit.json").write_text(json.dumps(input_audit, ensure_ascii=False, indent=2), encoding="utf-8")
    (project / "problems" / "C" / "source_manifest.json").write_text(
        json.dumps({"schema_version": 1, "project_id": "huashu-cup-2026", "problem": "C", "files": source_records}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"status": "PASS", "input_audit": str(output / "input_audit.json"), "source_manifest": str(project / "problems" / "C" / "source_manifest.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
