from __future__ import annotations

import shutil
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from src.workflow import reference_library


ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "references" / "competition-knowledge"
ALGORITHM_LIBRARY = ROOT / "references" / "algorithm-sources"


def _copy_library(tmp_path: Path) -> Path:
    shutil.copytree(LIBRARY, tmp_path / "references" / "competition-knowledge")
    return tmp_path


def _copy_algorithm_library(tmp_path: Path) -> Path:
    shutil.copytree(ALGORITHM_LIBRARY, tmp_path / "references" / "algorithm-sources")
    return tmp_path


def _source_payload(root: Path) -> dict:
    return yaml.safe_load((root / "references" / "competition-knowledge" / "sources.yaml").read_text(encoding="utf-8"))


def _write_source_payload(root: Path, payload: dict) -> None:
    path = root / "references" / "competition-knowledge" / "sources.yaml"
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def test_sources_schema_and_all_cards_are_valid() -> None:
    sources = reference_library.load_sources(ROOT)
    schema = yaml.safe_load((LIBRARY / "sources.schema.json").read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(sources)) == []
    records, issues = reference_library.card_records(ROOT)
    assert len(sources["sources"]) == 12
    assert len(records) == 29
    assert issues == []
    assert all(record["valid"] for record in records)


def test_algorithm_sources_schema_and_cards_are_valid() -> None:
    sources = reference_library.load_algorithm_sources(ROOT)
    schema = yaml.safe_load((ALGORITHM_LIBRARY / "sources.schema.json").read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(sources)) == []
    records, issues = reference_library.algorithm_records(ROOT)
    assert len(sources["sources"]) == 1
    assert set(sources["sources"][0]["source_paths"]) >= {
        "04_分类与聚类", "07_统计分析", "08_图论与网络模型",
        "09_机理建模", "11_组合模型（创新加分）",
    }
    assert len(records) == 11
    assert issues == []
    assert all(record["valid"] for record in records)
    assert all(record["license_status"] == "NO_LICENSE" for record in records)
    assert {record["algorithm_card_id"] for record in records} >= {
        "classification-clustering", "statistics-inference", "graph-network",
        "mechanistic-ode", "hybrid-models",
    }
    assert all((ROOT / record["skeleton_path"]).is_file() for record in records)


def test_algorithm_lookup_covers_new_high_frequency_families() -> None:
    expected = {
        "classification": "classification-clustering",
        "statistics": "statistics-inference",
        "graph": "graph-network",
        "mechanism": "mechanistic-ode",
        "hybrid": "hybrid-models",
    }
    for tag, card_id in expected.items():
        result = reference_library.lookup(ROOT, [tag], limit=20, layer="code")
        assert any(item["algorithm_card_id"] == card_id for item in result["results"])


def test_algorithm_cards_point_to_existing_local_skeletons() -> None:
    records, issues = reference_library.algorithm_records(ROOT)
    assert issues == []
    for record in records:
        skeleton = ROOT / record["skeleton_path"]
        assert skeleton.is_file(), record["skeleton_path"]
        assert skeleton.is_relative_to(ROOT / "references" / "algorithm-sources" / "skeletons")


def test_algorithm_code_lookup_returns_pinned_non_evidence_metadata() -> None:
    result = reference_library.lookup(ROOT, ["forecasting", "time-series"], limit=10, layer="code")
    assert result["results"]
    row = result["results"][0]
    assert row["kind"] == "code"
    assert row["algorithm_card_id"] == "forecasting-time-series"
    assert row["source_commit"] == "8abaef8c9262017925099d1463ebc78c1ab6a956"
    assert row["contest_evidence_eligible"] is False
    assert row["license_status"] == "NO_LICENSE"


def test_algorithm_card_rejects_commit_drift_and_absolute_source_path(tmp_path: Path) -> None:
    root = _copy_algorithm_library(tmp_path)
    card = root / "references" / "algorithm-sources" / "cards" / "forecasting-time-series.md"
    original = card.read_text(encoding="utf-8")
    card.write_text(original.replace("source_commit: 8abaef8c9262017925099d1463ebc78c1ab6a956", "source_commit: " + "a" * 40), encoding="utf-8")
    _, issues = reference_library.algorithm_records(root)
    assert any("source_commit" in issue for issue in issues)
    card.write_text(original.replace('source_path: "03_预测类模型"', 'source_path: "D:/outside"'), encoding="utf-8")
    _, issues = reference_library.algorithm_records(root)
    assert any("source_path" in issue for issue in issues)

    card.write_text(original.replace(
        'skeleton_path: "references/algorithm-sources/skeletons/forecasting/forecast_contract.py"',
        'skeleton_path: "D:/outside.py"',
    ), encoding="utf-8")
    _, issues = reference_library.algorithm_records(root)
    assert any("skeleton_path" in issue for issue in issues)

    card.write_text(original.replace(
        'skeleton_path: "references/algorithm-sources/skeletons/forecasting/forecast_contract.py"',
        'skeleton_path: "references/algorithm-sources/cards/forecast_contract.py"',
    ), encoding="utf-8")
    _, issues = reference_library.algorithm_records(root)
    assert any("skeleton_path" in issue for issue in issues)

    card.write_text(original.replace(
        'skeleton_path: "references/algorithm-sources/skeletons/forecasting/forecast_contract.py"',
        'skeleton_path: "references/algorithm-sources/skeletons/../cards/forecast_contract.py"',
    ), encoding="utf-8")
    _, issues = reference_library.algorithm_records(root)
    assert any("skeleton_path" in issue for issue in issues)


def test_local_algorithm_mirror_hash_drift_is_stale(tmp_path: Path) -> None:
    root = _copy_library(tmp_path)
    shutil.copytree(ALGORITHM_LIBRARY, root / "references" / "algorithm-sources")
    mirror = root / "代码库"
    mirror.mkdir(parents=True)
    source_file = mirror / "03_预测类模型" / "02_ARIMA时间序列.py"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("def arima_forecast(x):\n    return x\n", encoding="utf-8")

    synced = reference_library.sync_algorithm_source(root, "github-jingfeizhang-1")
    assert synced["passed"] is True
    report = reference_library.status(root)
    mirror_report = report["algorithm_mirrors"][0]
    assert mirror_report["status"] == "READY"

    source_file.write_text("def arima_forecast(x):\n    return list(reversed(x))\n", encoding="utf-8")
    drifted = reference_library.status(root)
    mirror_report = drifted["algorithm_mirrors"][0]
    assert mirror_report["status"] == "STALE"
    lookup = reference_library.lookup(root, ["forecasting", "time-series"], layer="code")
    assert lookup["results"][0]["mirror_status"] == "STALE"


def test_algorithm_layer_is_optional_for_legacy_library_copies(tmp_path: Path) -> None:
    root = _copy_library(tmp_path)
    result = reference_library.lookup(root, ["optimization"], layer="code")
    assert result["results"] == []
    assert any("algorithm source manifest" in warning for warning in result["warnings"])


def test_all_modules_and_playbooks_are_valid_and_non_evidence() -> None:
    modules, module_issues = reference_library.module_records(ROOT)
    playbooks, playbook_issues = reference_library.playbook_records(ROOT)
    assert len(modules) == 6
    assert len(playbooks) == 3
    assert module_issues == []
    assert playbook_issues == []
    assert all(item["valid"] for item in modules)
    assert all(item["valid"] for item in playbooks)
    assert all(set(item["stage_scope"]) <= {"P1", "P2", "P3a", "P3b"} for item in [*modules, *playbooks])
    runtime_paths = {item["path"].name for item in playbooks}
    assert runtime_paths == {
        "mechanism-fit-and-scenario.md",
        "predict-then-optimize.md",
        "resource-allocation-under-uncertainty.md",
    }
    assert "academic-quality-standard.md" not in runtime_paths
    assert "visual-evidence-quality.md" not in runtime_paths


def test_sources_and_cards_reject_absolute_paths_wrong_hash_and_missing_fields(tmp_path: Path) -> None:
    root = _copy_library(tmp_path)
    payload = _source_payload(root)
    payload["sources"][0]["filename"] = r"D:\outside.pdf"
    _write_source_payload(root, payload)
    assert any("basename" in issue for issue in reference_library.validate_sources(payload))

    root = _copy_library(tmp_path / "missing")
    card = next((root / "references" / "competition-knowledge" / "cards").glob("*.md"))
    text = card.read_text(encoding="utf-8").replace("source_sha256: ", "source_sha256: deadbeef", 1)
    card.write_text(text, encoding="utf-8")
    records, issues = reference_library.card_records(root)
    assert records
    assert any("source_sha256" in issue for issue in issues)

    root = _copy_library(tmp_path / "fields")
    payload = _source_payload(root)
    del payload["sources"][0]["pages"]
    _write_source_payload(root, payload)
    assert any("missing" in issue for issue in reference_library.validate_sources(payload))


def test_lookup_returns_expected_core_topics_without_local_pdf_mapping(monkeypatch) -> None:
    monkeypatch.delenv("MATHMODEL_REFERENCE_LIBRARY_ROOT", raising=False)
    expected = {
        "optimization": "optimization-lp-milp",
        "uncertainty": "uncertainty-fuzzy",
        "statistics": "statistics-anova",
        "numerical": "numerical-integration",
        "machine-learning": "ml-small-sample",
        "dynamics": "dynamics-difference",
        "mechanism": "mechanism-ode",
    }
    for tag, card_id in expected.items():
        result = reference_library.lookup(ROOT, [tag], limit=50)
        assert any(item.get("card_id") == card_id for item in result["results"])
    verification = reference_library.verify(ROOT)
    assert verification["passed"] is True
    assert verification["warning"]
    assert {item["status"] for item in verification["sources"]} == {"MISSING"}


def test_layered_lookup_returns_modules_and_playbooks() -> None:
    modules = reference_library.lookup(ROOT, ["optimization", "milp"], limit=10, layer="module")
    assert modules["layer"] == "module"
    assert any(item["module_id"] == "optimization-lp-milp" for item in modules["results"])
    assert {item["kind"] for item in modules["results"]} == {"module"}

    playbooks = reference_library.lookup(ROOT, ["forecasting", "optimization"], limit=10, layer="playbook")
    assert any(item["playbook_id"] == "predict-then-optimize" for item in playbooks["results"])
    assert all(item["contest_evidence_eligible"] is False for item in playbooks["results"])

    combined = reference_library.lookup(ROOT, ["mechanism", "uncertainty"], limit=20)
    assert {"card", "module", "playbook"} <= {item["kind"] for item in combined["results"]}


def test_module_contract_rejects_bad_scope_source_and_evidence_flag(tmp_path: Path) -> None:
    root = _copy_library(tmp_path)
    module = root / "references" / "competition-knowledge" / "modules" / "optimization" / "lp-milp.md"
    original = module.read_text(encoding="utf-8")

    module.write_text(original.replace("stage_scope: [P1, P2, P3a, P3b]", "stage_scope: [P4]"), encoding="utf-8")
    _, issues = reference_library.module_records(root)
    assert any("stage_scope" in issue for issue in issues)

    module.write_text(original.replace("optimization-inventory]", "unknown-card]"), encoding="utf-8")
    _, issues = reference_library.module_records(root)
    assert any("unknown source card" in issue for issue in issues)

    module.write_text(original.replace("contest_evidence_eligible: false", "contest_evidence_eligible: true"), encoding="utf-8")
    _, issues = reference_library.module_records(root)
    assert any("never be contest evidence" in issue for issue in issues)


def test_playbook_contract_rejects_unknown_module_absolute_path_and_missing_section(tmp_path: Path) -> None:
    root = _copy_library(tmp_path)
    playbook = root / "references" / "competition-knowledge" / "playbooks" / "predict-then-optimize.md"
    original = playbook.read_text(encoding="utf-8")

    playbook.write_text(original.replace("optimization-uncertainty-planning]", "unknown-module]"), encoding="utf-8")
    _, issues = reference_library.playbook_records(root)
    assert any("unknown module" in issue for issue in issues)

    playbook.write_text(original.replace("## 禁止事项", "## D:/outside/禁止事项"), encoding="utf-8")
    _, issues = reference_library.playbook_records(root)
    assert any("absolute path" in issue for issue in issues)
    assert any("missing section" in issue for issue in issues)


def test_hash_drift_marks_only_related_cards_stale(tmp_path: Path, monkeypatch) -> None:
    root = _copy_library(tmp_path)
    payload = _source_payload(root)
    records, _ = reference_library.card_records(root)
    referenced_source_id = next(
        record["source_id"] for record in records if record["card_id"] == "optimization-lp-milp"
    )
    source = next(item for item in payload["sources"] if item["source_id"] == referenced_source_id)
    original_sha256 = source["sha256"]
    expected = "a" * 64
    source["sha256"] = expected
    _write_source_payload(root, payload)

    card_dir = root / "references" / "competition-knowledge" / "cards"
    related = []
    for card in card_dir.glob("*.md"):
        content = card.read_text(encoding="utf-8")
        if f"source_id: {source['source_id']}" in content:
            card.write_text(content.replace("source_sha256: " + original_sha256, "source_sha256: " + expected), encoding="utf-8")
            related.append(card.stem)
    assert related
    local_pdf = tmp_path / "local.pdf"
    local_pdf.write_bytes(b"different local PDF")
    mapping = root / "work" / "reference-library" / "sources.local.yaml"
    mapping.parent.mkdir(parents=True)
    mapping.write_text(yaml.safe_dump({"sources": {source["source_id"]: str(local_pdf)}}), encoding="utf-8")
    monkeypatch.delenv("MATHMODEL_REFERENCE_LIBRARY_ROOT", raising=False)

    report = reference_library.status(root)
    statuses = {item["card_id"]: item["status"] for item in report["cards"]}
    assert all(statuses[card_id] == "STALE" for card_id in related)
    assert all(statuses[card_id] == "READY" for card_id in statuses if card_id not in related)
    module_statuses = {item["module_id"]: item["status"] for item in report["modules"]}
    playbook_statuses = {item["playbook_id"]: item["status"] for item in report["playbooks"]}
    assert module_statuses["optimization-lp-milp"] == "STALE"
    assert playbook_statuses["resource-allocation-under-uncertainty"] == "STALE"


def test_lookup_is_read_only_and_cannot_create_project_evidence(tmp_path: Path) -> None:
    root = _copy_library(tmp_path)
    before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())
    result = reference_library.lookup(root, ["optimization", "milp"], layer="all")
    after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())
    assert result["results"]
    assert before == after
    for prohibited in ("state/decision_log.json", "results/C/claims.json", "paper/figure_contracts.yaml", "submission", "output/release"):
        assert not (root / prohibited).exists()


def test_library_source_manifest_declares_non_evidence_policy() -> None:
    payload = _source_payload(ROOT)
    policy = payload["evidence_policy"]
    assert policy["contest_evidence_eligible"] is False
    forbidden = set(policy["forbidden_use"])
    assert {"formal_claim", "paper_number", "figure_contract", "submission", "release"} <= forbidden


def test_status_reports_all_three_layers() -> None:
    report = reference_library.status(ROOT)
    assert report["card_count"] == report["valid_card_count"] == 29
    assert report["module_count"] == report["valid_module_count"] == 6
    assert report["playbook_count"] == report["valid_playbook_count"] == 3
    assert report["module_issues"] == []
    assert report["playbook_issues"] == []
    assert report["coverage"]["statistics"]["modules"] == 3


def test_repository_library_contains_no_binary_or_cached_source_material() -> None:
    forbidden_suffixes = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".ocr"}
    assert not [path for path in LIBRARY.rglob("*") if path.is_file() and path.suffix.lower() in forbidden_suffixes]
    assert not [path for path in LIBRARY.rglob("*") if path.is_dir() and path.name.lower() in {"cache", "ocr", "rendered"}]


def test_local_mapping_rejects_relative_paths_and_unknown_sources(tmp_path: Path) -> None:
    sources = reference_library.load_sources(ROOT)
    by_id = {item["source_id"]: item for item in sources["sources"]}
    assert any("absolute path" in issue for issue in reference_library.validate_local_mapping({"root": "relative"}, by_id))
    assert any("unknown source_id" in issue for issue in reference_library.validate_local_mapping({"sources": {"unknown": str(tmp_path / "x.pdf")}}, by_id))
