"""Common path, validation, and module-loading utilities."""

# 本程序及代码是在 AI 工具辅助下完成的。
# AI 工具名称：OpenAI Codex，版本/型号：GPT-5，开发机构/公司：OpenAI，版本发布日期：2025-08-07。

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
import platform
import shutil
import sys
from pathlib import Path

REQUIRED_INPUTS = {
    "Q1": (
        "workload_trace.xlsx",
        "GPU_information.xlsx",
        "network_latency.xlsx",
        "region_time_data.xlsx",
        "power_mapping.xlsx",
    ),
    "Q2": (
        "workload_trace.xlsx",
        "GPU_information.xlsx",
        "network_latency.xlsx",
        "region_time_data.xlsx",
        "power_mapping.xlsx",
    ),
    "Q3": (
        "region_time_data.xlsx",
        "storage_information.xlsx",
        "power_mapping.xlsx",
    ),
    "Q4": (
        "workload_trace.xlsx",
        "GPU_information.xlsx",
        "network_latency.xlsx",
        "region_time_data.xlsx",
        "power_mapping.xlsx",
        "storage_information.xlsx",
    ),
}

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
INPUT_MANIFEST = PACKAGE_ROOT / "input" / "input_manifest.sha256"
REQUIRED_MODULES = {
    "Q1": ("numpy", "pandas", "scipy", "sklearn", "ortools", "openpyxl"),
    "Q2": ("numpy", "pandas", "openpyxl"),
    "Q3": ("numpy", "pandas", "scipy", "openpyxl"),
    "Q4": ("numpy", "pandas", "scipy", "openpyxl"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def ensure_inputs(question: str, input_dir: Path) -> list[dict[str, object]]:
    question = question.upper()
    if question not in REQUIRED_INPUTS:
        raise ValueError(f"unsupported question: {question}")
    records: list[dict[str, object]] = []
    missing: list[str] = []
    for name in REQUIRED_INPUTS[question]:
        path = input_dir / name
        if not path.is_file():
            missing.append(name)
        else:
            records.append(
                {"name": name, "bytes": path.stat().st_size, "sha256": sha256(path)}
            )
    if missing:
        raise FileNotFoundError(
            f"{question} input directory lacks: {', '.join(missing)}"
        )
    return records


def load_expected_hashes() -> dict[str, str]:
    if not INPUT_MANIFEST.is_file():
        raise FileNotFoundError(f"missing packaged input manifest: {INPUT_MANIFEST}")
    expected: dict[str, str] = {}
    for raw_line in INPUT_MANIFEST.read_text(encoding="ascii").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        digest, name = line.split(None, 1)
        expected[name.strip()] = digest.lower()
    return expected


def verify_input_hashes(records: list[dict[str, object]]) -> None:
    expected = load_expected_hashes()
    mismatches = []
    for record in records:
        name = str(record["name"])
        observed = str(record["sha256"]).lower()
        if expected.get(name) != observed:
            mismatches.append(
                {"name": name, "expected": expected.get(name), "observed": observed}
            )
    if mismatches:
        raise RuntimeError(f"official input hash mismatch: {mismatches}")


def dependency_versions(question: str) -> dict[str, str]:
    versions: dict[str, str] = {}
    failures: list[str] = []
    for module_name in REQUIRED_MODULES[question.upper()]:
        try:
            importlib.import_module(module_name)
            distribution = "scikit-learn" if module_name == "sklearn" else module_name
            versions[module_name] = importlib.metadata.version(distribution)
        except Exception as exc:  # pragma: no cover - reported to the user verbatim
            failures.append(f"{module_name}: {type(exc).__name__}: {exc}")
    if failures:
        raise RuntimeError("dependency verification failed: " + "; ".join(failures))
    return versions


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def verification_payload(question: str, input_dir: Path) -> dict[str, object]:
    records = ensure_inputs(question, input_dir)
    verify_input_hashes(records)
    return {
        "question": question.upper(),
        "status": "PASS",
        "mode": "verify-only",
        "input_dir": str(input_dir.resolve()),
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": Path(sys.executable).name,
        },
        "dependencies": dependency_versions(question),
        "matlab": {
            "required_for_models": False,
            "executable_available": shutil.which("matlab") is not None,
            "declared_release": "R2026a",
        },
        "inputs": records,
    }
