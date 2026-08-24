from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_environment_contract_includes_workflow_runtime_dependencies() -> None:
    requirements = json.loads((ROOT / "config" / "environment_requirements.json").read_text(encoding="utf-8"))
    core_imports = {item["import"] for item in requirements["core"]["python"]}
    assert {"jsonschema", "pytest", "ruff", "yaml"} <= core_imports


def test_local_first_environment_report() -> None:
    report = json.loads((ROOT / "output" / "environment.json").read_text(encoding="utf-8"))
    assert report["schema_version"] == 2
    assert report["policy"] == "existing_first"
    assert set(report["selection"]) == {"core", "full"}
    assert set(report["tiers"]) == {"core", "full"}

    selected = report["selection"]["core"]
    core = report["tiers"]["core"]
    assert selected["prefix"] == core["environment_prefix"]
    assert core["requested_tier"] == "core"
    assert core["provenance_policy"] == "environment-prefix-plus-external-local"
    assert core["status"] == ("PASS" if not core["core_missing"] else "FAIL")
    assert core["checks"] and isinstance(core["checks"][0], dict)

    full = report["tiers"]["full"]
    assert full["requested_tier"] == "full"
    assert isinstance(full["extended_missing"], list)

    base = next(item for item in report["candidates"] if item["name"] == "base")
    assert base["core_missing"] == []
    base_audit = json.loads((ROOT / "output" / "environment-base.json").read_text(encoding="utf-8"))
    assert "pypdf" in base_audit["core_prefix_missing"]
    assert base_audit["core_missing"] == []
    assert "pypdf" in base_audit["core_external_local"]
    pypdf = next(item for item in base_audit["checks"] if item["name"] == "pypdf")
    assert pypdf["available"] is False
    assert pypdf["user_site_available"] is True
    assert "AppData\\Roaming\\Python" in pypdf["user_site_location"]
    assert base_audit["warnings"]


def test_conda_temp_directories_are_unique_for_sequential_and_parallel_calls() -> None:
    command = (
        ". '.\\scripts\\_environment.ps1'; "
        "$a=New-CondaTemporaryDirectory; $b=New-CondaTemporaryDirectory; "
        "$payload=[ordered]@{paths=@($a.Path,$b.Path); cleaned=@("
        "(Remove-CondaTemporaryDirectory $a),(Remove-CondaTemporaryDirectory $b))}; "
        "$payload | ConvertTo-Json -Compress"
    )

    def probe() -> dict:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        return json.loads(completed.stdout.strip().splitlines()[-1])

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: probe(), range(2)))
    paths = [path for result in results for path in result["paths"]]
    assert len(paths) == len(set(path.lower() for path in paths))
    assert all(cleaned for result in results for cleaned in result["cleaned"])
    assert all(not Path(path).exists() for path in paths)


def test_extended_setup_report_never_claims_an_unverified_environment() -> None:
    report = json.loads((ROOT / "output" / "setup-extended.json").read_text(encoding="utf-8"))
    assert report["schema_version"] == 3
    assert report["base"]["modified"] is False
    assert report["base"]["fingerprint_before"] == report["base"]["fingerprint_after"]
    if report["status"] == "PASS":
        assert report["promotion_completed"] is True
        assert report["python_version"].startswith("3.13.")
    else:
        assert report["promotion_completed"] is False
        assert report["stage"] != "promoted"
    script = (ROOT / "scripts" / "setup.ps1").read_text(encoding="utf-8")
    assert "Build-CleanPython313Candidate" in script
    assert "Build-Python312Candidate" not in script
    assert "clean-local-python" in script
    assert "ExpectedPython '3.13'" in script
    assert "--only-binary" in script
    assert "Get-DefaultEnvironmentPrefix -Name $Environment" in script
    assert "python=3.13.*" in (ROOT / "environment.yml").read_text(encoding="utf-8")
    verify_script = (ROOT / "scripts" / "verify_env.ps1").read_text(encoding="utf-8")
    assert "'python', '-E', '-s'" in verify_script
    assert script.index("if ($reuseExit -eq 0)") < script.index("Write-SetupReport -Status 'PASS' -Stage 'reuse-existing'")
    assert "transaction_scope = $true" in script
    assert "TimeoutSeconds 600" in script


def test_experiment_artifacts_have_stable_provenance() -> None:
    result_path = ROOT / "experiments" / "demo" / "results" / "experiment_result.json"
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["random_seed"] == 20260801
    assert payload["metrics"]["regression"]["r2"] > 0.9
    for artifact in payload["artifacts"]:
        path = ROOT / artifact["path"]
        assert path.is_file(), artifact["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]


def test_submission_outputs_and_audits_pass() -> None:
    assert (ROOT / "output" / "submission.pdf").read_bytes().startswith(b"%PDF")
    assert (ROOT / "output" / "supporting.zip").is_file()
    for name in ("paper_audit.json", "figure_audit.json", "audit.json"):
        report = json.loads((ROOT / "output" / name).read_text(encoding="utf-8"))
        if "passed" in report:
            assert report["passed"] is True, name
        if "status" in report:
            assert report["status"] == "PASS", name
    assert (ROOT / "output" / "_verification" / "pdf" / "rendered-pages" / "page-1.png").is_file()


def test_pipeline_entrypoints_are_present() -> None:
    for name in (
        "setup.ps1",
        "verify_env.ps1",
        "run_experiment.ps1",
        "build_paper.ps1",
        "audit_submission.ps1",
        "package_submission.ps1",
        "workflow.ps1",
    ):
        assert (ROOT / "scripts" / name).is_file(), name


def test_same_seed_reproduces_metrics_data_and_figures() -> None:
    with tempfile.TemporaryDirectory(dir=ROOT / "output") as temp_dir:
        temp = Path(temp_dir)
        payloads = []
        for label in ("first", "second"):
            output_root = temp / label
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "src" / "modeling" / "run_demo.py"),
                    "--experiment-id",
                    "repro",
                    "--seed",
                    "20260801",
                    "--output-root",
                    str(output_root),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            assert completed.returncode == 0, completed.stdout + completed.stderr
            payloads.append(json.loads((output_root / "repro" / "results" / "experiment_result.json").read_text(encoding="utf-8")))
        assert payloads[0]["metrics"] == payloads[1]["metrics"]
        first_hashes = {Path(item["path"]).name: item["sha256"] for item in payloads[0]["artifacts"]}
        second_hashes = {Path(item["path"]).name: item["sha256"] for item in payloads[1]["artifacts"]}
        assert first_hashes == second_hashes
