from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

import src.workflow.competition_workflow as workflow


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "config" / "schemas"
TEMPLATE_ROOT = ROOT / "templates" / "workflow"
LITERATURE_SCHEMA_CASES = (
    ("literature_search_plan.schema.json", "literature_search_plan.yaml"),
    ("literature_search_receipt.schema.json", "literature_search_receipt.yaml"),
    ("academic_reference_card.schema.json", "literature_reference_card.yaml"),
    ("model_evidence_brief.schema.json", "literature_model_evidence_brief.yaml"),
)


def dump_yaml(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")


def load_yaml(path: Path) -> dict:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scaffold_workspace(root: Path, question_count: int = 1) -> Path:
    dump_yaml(
        root / "contest.yaml",
        {
            "competition": "CUMCM",
            "year": 2026,
            "problem": "TBD",
            "deadline": "2026-09-13T20:00:00+08:00",
        },
    )
    dump_yaml(root / "project.yaml", {"project_id": "fixture-v6", "workflow_contract_version": 6})
    for relative in (
        "config/workflow.yaml",
        "skills.lock.yaml",
        "templates/figures/figure_contract_v2.schema.json",
        "templates/figures/figure_contract_v2.template.yaml",
        "templates/workflow/question.yaml",
        "templates/workflow/literature_search_plan.yaml",
        "templates/workflow/literature_search_receipt.yaml",
        "templates/workflow/literature_reference_card.yaml",
        "templates/workflow/literature_model_evidence_brief.yaml",
        "config/schemas/literature_search_plan.schema.json",
        "config/schemas/literature_search_receipt.schema.json",
        "config/schemas/academic_reference_card.schema.json",
        "config/schemas/model_evidence_brief.schema.json",
        "skill_staging/handsomeZR-mathmodel-skill/templates/shared/decision_log.json",
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)

    markers = ["一", "二", "三", "四"][:question_count]
    problem_file = root / "problems" / "problem.txt"
    problem_file.parent.mkdir(parents=True, exist_ok=True)
    problem_file.write_text(
        "\n".join(f"问题{marker} 建立模型并给出第{index}项结果。" for index, marker in enumerate(markers, start=1)),
        encoding="utf-8",
    )
    workflow.initialize(root, "C", problem_file)
    return root / "problems" / "C" / "questions" / "Q1" / "question.yaml"


def prepare_question_interface(root: Path) -> Path:
    question_path = scaffold_workspace(root)
    question = load_yaml(question_path)
    question["problem"].update(
        {
            "target": "在小样本需求数据上给出带不确定性的库存预测。",
            "type": "prediction",
            "inputs": ["历史需求", "库存容量"],
            "outputs": ["需求预测", "预测区间"],
            "constraints": ["small sample", "capacity limit"],
            "evaluation_metrics": ["MAE", "interval coverage"],
            "dependencies": [],
            "key_conflicts": ["accuracy versus interval width"],
        }
    )
    dump_yaml(question_path, question)
    return question_path


def literature_record(
    canonical_id: str,
    title: str,
    author: str,
    year: int,
    doi: str | None,
) -> dict:
    return {
        "canonical_id": canonical_id,
        "title": title,
        "authors": [author],
        "year": year,
        "publication_type": "journal-article",
        "doi": doi,
        "arxiv_id": None,
        "url": f"https://example.org/{canonical_id}",
        "abstract_available": True,
        "selected_for_screening": True,
        "exclusion_reason": None,
    }


def write_search_config(
    root: Path,
    receipt_id: str,
    provider: str,
    records: list[dict],
) -> Path:
    plan_path = root / "problems" / "C" / "questions" / "Q1" / "literature" / "search_plan.yaml"
    raw_path = root / "work" / "cache" / "literature" / "C" / "Q1" / f"{receipt_id}.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps({"results": records}, ensure_ascii=False), encoding="utf-8")
    config = load_yaml(TEMPLATE_ROOT / "literature_search_receipt.yaml")
    config.update(
        {
            "receipt_id": receipt_id,
            "problem_id": "C",
            "question_id": "Q1",
            "search_plan": plan_path.relative_to(root).as_posix(),
            "search_plan_sha256": sha256(plan_path),
            "query_id": "query-method-constraint-en",
            "query_text": "probabilistic demand forecasting small sample",
            "provider": provider,
            "raw_results": {
                "path": raw_path.relative_to(root).as_posix(),
                "sha256": sha256(raw_path),
                "content_type": "application/json",
            },
            "results": records,
            "deduplication": {
                "input_count": len(records),
                "unique_count": len(records),
                "key_order": ["doi", "normalized-title-first-author-year"],
                "merged_records": [],
            },
            "academic_sources_only": True,
            "status": "DISCOVERED",
        }
    )
    config_path = root / "work" / "literature-configs" / f"{receipt_id}.yaml"
    dump_yaml(config_path, config)
    return config_path


def write_card_config(
    root: Path,
    receipt_path: Path,
    *,
    card_id: str = "litcard-q1-forecast",
    depth: str = "TARGETED_READ",
) -> Path:
    cache = root / "work" / "cache" / "literature" / "C" / "Q1"
    cache.mkdir(parents=True, exist_ok=True)
    metadata_path = cache / f"{card_id}-metadata.json"
    metadata_path.write_text(
        json.dumps({"title": "Probabilistic Forecasting for Small Samples", "doi": "10.1234/forecast.1"}),
        encoding="utf-8",
    )
    document_path = cache / f"{card_id}.pdf"
    document_path.write_bytes(b"%PDF-1.4\nfixture\n")

    config = load_yaml(TEMPLATE_ROOT / "literature_reference_card.yaml")
    config.update(
        {
            "card_id": card_id,
            "problem_id": "C",
            "question_id": "Q1",
            "source_search_receipts": [
                {"path": receipt_path.relative_to(root).as_posix(), "sha256": sha256(receipt_path)}
            ],
            "review_depth": depth,
            "metadata": {
                "title": "Probabilistic Forecasting for Small Samples",
                "authors": [{"full_name": "Ada Lovelace", "orcid": None}],
                "year": 2025,
                "publication_type": "journal-article",
                "venue": "Journal of Forecasting",
                "doi": "10.1234/forecast.1",
                "arxiv_id": None,
                "url": "https://doi.org/10.1234/forecast.1",
                "bibtex_key": "Lovelace2025Forecast",
            },
            "metadata_sources": [
                {
                    "provider": "crossref",
                    "locator": "https://api.crossref.org/works/10.1234/forecast.1",
                    "checked_at_utc": "2026-08-11T00:02:00Z",
                }
            ],
            "metadata_snapshot": {
                "path": metadata_path.relative_to(root).as_posix(),
                "sha256": sha256(metadata_path),
            },
            "source_document": {
                "available": True,
                "kind": "pdf",
                "path": document_path.relative_to(root).as_posix(),
                "url": "https://example.org/forecast.pdf",
                "sha256": sha256(document_path),
            },
            "external_results": [
                {
                    "metric": "MAE",
                    "value_text": "1.23 items",
                    "context": "the paper's own benchmark",
                    "source_locator": "Table 2, page 8",
                    "not_project_evidence": True,
                }
            ],
            "paper_handoff": {
                "bibtex_key": "Lovelace2025Forecast",
                "eligible_sections": ["model-selection", "parameter-basis", "model-validation"],
                "citation_note": "Cite the method and parameter basis, not the reported score.",
            },
            "status": "CARD_READY",
        }
    )
    if depth in {"METADATA_ONLY", "ABSTRACT_SCREENED"}:
        config["source_document"] = {
            "available": False,
            "kind": "none",
            "path": None,
            "url": config["metadata"]["url"],
            "sha256": None,
        }
        config["locators"] = []
        config["precision_evidence"] = []
        config["substantive_citation_eligible"] = False
        config["status"] = "SOURCES_VERIFIED"
    else:
        config["substantive_citation_eligible"] = True

    config_path = root / "work" / "literature-configs" / f"{card_id}.yaml"
    dump_yaml(config_path, config)
    return config_path


def write_synthesis_config(root: Path, card_path: Path) -> Path:
    question_path = root / "problems" / "C" / "questions" / "Q1" / "question.yaml"
    config = load_yaml(TEMPLATE_ROOT / "literature_model_evidence_brief.yaml")
    config.update(
        {
            "brief_id": "litevidence-q1-forecast",
            "problem_id": "C",
            "question_id": "Q1",
            "source_question_manifest": question_path.relative_to(root).as_posix(),
            "source_question_manifest_sha256": workflow.question_interface_sha256(load_yaml(question_path)),
            "source_cards": [
                {
                    "path": card_path.relative_to(root).as_posix(),
                    "sha256": sha256(card_path),
                }
            ],
            "candidates": [
                {
                    "candidate_id": "model-probabilistic-forecast",
                    "model_name": "Probabilistic forecast",
                    "evidence_roles": {
                        "model_family": ["litcard-q1-forecast"],
                        "mechanism": [],
                        "parameter": ["litcard-q1-forecast"],
                        "validation": ["litcard-q1-forecast"],
                    },
                    "fit_to_current_problem": {
                        "matched_conditions": ["small sample and probabilistic output"],
                        "mismatched_conditions": ["different inventory horizon"],
                    },
                    "implementation": {"expected_runtime": "under one hour", "dependencies": ["numpy"]},
                    "baseline": "historical mean with empirical interval",
                    "risk_probes": ["coverage under demand spikes"],
                    "rejected_when": ["interval coverage is below baseline"],
                    "decision": "retain",
                }
            ],
            "recommendation": {
                "primary_candidate": "model-probabilistic-forecast",
                "rationale": "The model produces the required point and interval outputs under small samples.",
                "baseline": "historical mean with empirical interval",
                "fallback": None,
                "rejected_alternatives": [],
            },
            "citation_handoff": {
                "bibtex_keys": ["Lovelace2025Forecast"],
                "paper_targets": [
                    {
                        "bibtex_key": "Lovelace2025Forecast",
                        "section": "model-selection",
                        "purpose": "Support the model family and its transfer conditions.",
                        "minimum_review_depth": "TARGETED_READ",
                    }
                ],
                "differences_from_literature": ["The contest instance has a shorter inventory horizon."],
            },
            "status": "CITATION_READY",
        }
    )
    config_path = root / "work" / "literature-configs" / "synthesis.yaml"
    dump_yaml(config_path, config)
    return config_path


def test_v6_literature_schemas_and_templates_are_valid() -> None:
    for schema_name, template_name in LITERATURE_SCHEMA_CASES:
        schema = json.loads((SCHEMA_ROOT / schema_name).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(load_yaml(TEMPLATE_ROOT / template_name))


def test_initialize_creates_question_v3_and_search_plan(tmp_path: Path) -> None:
    question_path = scaffold_workspace(tmp_path, question_count=2)
    question = load_yaml(question_path)

    assert question["schema_version"] == 3
    assert question["literature"] == {
        "search_plan": {
            "path": "problems/C/questions/Q1/literature/search_plan.yaml",
            "sha256": question["literature"]["search_plan"]["sha256"],
        },
        "search_receipts": [],
        "evidence_cards": [],
        "model_evidence_brief": None,
        "bib_keys": [],
        "status": "PLAN_READY",
    }
    plan_path = tmp_path / question["literature"]["search_plan"]["path"]
    plan = load_yaml(plan_path)
    assert question["literature"]["search_plan"]["sha256"] == sha256(plan_path)
    assert plan["source_question_manifest"] == "problems/C/questions/Q1/question.yaml"
    assert plan["source_question_manifest_sha256"] == workflow.question_interface_sha256(question)
    assert plan["screening"]["contest_papers_allowed"] is False
    assert plan["time_budget"] == {
        "per_question_minutes": 20,
        "project_total_minutes": 90,
        "stop_when_budget_exhausted": True,
    }
    q2 = load_yaml(tmp_path / "problems" / "C" / "questions" / "Q2" / "question.yaml")
    assert q2["schema_version"] == 3
    assert q2["literature"]["status"] == "PLAN_READY"
    assert (tmp_path / q2["literature"]["search_plan"]["path"]).is_file()


def test_literature_schemas_reject_absolute_paths_and_external_results_as_claims() -> None:
    plan = load_yaml(TEMPLATE_ROOT / "literature_search_plan.yaml")
    plan["source_question_manifest"] = r"D:\\other-project\\question.yaml"
    plan_schema = json.loads((SCHEMA_ROOT / "literature_search_plan.schema.json").read_text(encoding="utf-8"))
    assert list(Draft202012Validator(plan_schema).iter_errors(plan))

    card = load_yaml(TEMPLATE_ROOT / "literature_reference_card.yaml")
    card["external_results"] = [
        {
            "metric": "MAE",
            "value_text": "1.23 items",
            "context": "reported on the paper's own benchmark",
            "source_locator": "Table 2, page 8",
            "not_project_evidence": False,
        }
    ]
    card_schema = json.loads((SCHEMA_ROOT / "academic_reference_card.schema.json").read_text(encoding="utf-8"))
    assert list(Draft202012Validator(card_schema).iter_errors(card))


def test_gitignore_excludes_literature_caches_but_not_cards_or_briefs() -> None:
    patterns = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "work/cache/literature" in patterns
    assert "projects/**/work/cache/literature" in patterns
    assert "literature/cards" not in patterns
    assert "model_evidence_brief.yaml" not in patterns


def test_literature_deduplicates_by_doi_then_title_first_author_and_year() -> None:
    records = [
        {
            "canonical_id": "crossref-1",
            "title": "Probabilistic Forecasting for Small Samples",
            "authors": ["Ada Lovelace", "Grace Hopper"],
            "year": 2025,
            "publication_type": "journal-article",
            "doi": "https://doi.org/10.1234/Forecast.1",
            "url": "https://example.org/paper-1",
        },
        {
            "canonical_id": "openalex-1",
            "title": "Probabilistic Forecasting for Small Samples",
            "authors": ["Ada Lovelace"],
            "year": 2025,
            "publication_type": "journal-article",
            "doi": "10.1234/forecast.1",
            "url": None,
        },
        {
            "canonical_id": "arxiv-2",
            "title": "Robust inventory optimization under uncertain demand",
            "authors": ["Turing, Alan"],
            "year": 2024,
            "publication_type": "preprint",
            "doi": None,
            "url": "https://arxiv.org/abs/2401.00001",
        },
        {
            "canonical_id": "manual-2",
            "title": "Robust Inventory Optimization Under Uncertain Demand!",
            "authors": ["Alan Turing"],
            "year": 2024,
            "publication_type": "preprint",
            "doi": None,
            "url": None,
        },
    ]

    unique, merged = workflow.deduplicate_literature_records(records)

    assert len(unique) == 2
    assert {workflow.normalize_doi(item.get("doi")) for item in unique} == {"10.1234/forecast.1", None}
    assert sum(len(item["merged"]) for item in merged) == 2


def test_powershell_exposes_all_v6_literature_actions() -> None:
    script = (ROOT / "scripts" / "workflow.ps1").read_text(encoding="utf-8")
    for action in (
        "literature-plan",
        "literature-search",
        "literature-register",
        "literature-read",
        "literature-synthesize",
        "literature-audit",
    ):
        assert f"'{action}'" in script


def test_literature_plan_search_register_read_synthesize_and_audit(tmp_path: Path) -> None:
    question_path = prepare_question_interface(tmp_path)
    question = load_yaml(question_path)
    question["model_selection"] = {
        "primary": "Probabilistic forecast",
        "rationale": "Produces point and interval outputs for the stated task.",
        "baseline": "historical mean with empirical interval",
        "rejected_alternatives": ["unconstrained point forecast"],
    }
    dump_yaml(question_path, question)

    plan_result = workflow.literature_plan(tmp_path, "C", "Q1", None)
    assert plan_result["status"] == "PLAN_READY"
    plan_path = tmp_path / "problems" / "C" / "questions" / "Q1" / "literature" / "search_plan.yaml"
    assert load_yaml(plan_path)["source_question_manifest_sha256"] == workflow.question_interface_sha256(
        load_yaml(question_path)
    )

    doi_records = [
        literature_record(
            "crossref-forecast",
            "Probabilistic Forecasting for Small Samples",
            "Ada Lovelace",
            2025,
            "10.1234/Forecast.1",
        ),
        literature_record(
            "openalex-forecast",
            "Probabilistic Forecasting for Small Samples",
            "Ada Lovelace",
            2025,
            "10.1234/forecast.1",
        ),
    ]
    workflow.literature_search(
        tmp_path,
        "C",
        "Q1",
        write_search_config(tmp_path, "litsearch-q1-crossref", "crossref", doi_records),
    )
    receipt_paths = sorted(
        (tmp_path / "problems" / "C" / "questions" / "Q1" / "literature" / "searches").glob(
            "*/search_receipt.json"
        )
    )
    assert len(receipt_paths) == 1
    receipt = json.loads(receipt_paths[0].read_text(encoding="utf-8"))
    assert receipt["deduplication"]["input_count"] == 2
    assert receipt["deduplication"]["unique_count"] == 1

    title_records = [
        literature_record(
            "manual-inventory-a",
            "Robust inventory optimization under uncertain demand",
            "Alan Turing",
            2024,
            None,
        ),
        literature_record(
            "manual-inventory-b",
            "Robust Inventory Optimization Under Uncertain Demand!",
            "Turing, Alan",
            2024,
            None,
        ),
    ]
    workflow.literature_register(
        tmp_path,
        "C",
        "Q1",
        write_search_config(tmp_path, "litsearch-q1-user", "user-supplied", title_records),
    )
    question = load_yaml(question_path)
    assert len(question["literature"]["search_receipts"]) == 2

    card_config = write_card_config(tmp_path, receipt_paths[0])
    workflow.literature_read(tmp_path, "C", "Q1", card_config)
    card_path = tmp_path / "problems" / "C" / "questions" / "Q1" / "literature" / "cards" / "litcard-q1-forecast.yaml"
    assert card_path.is_file()
    assert load_yaml(card_path)["substantive_citation_eligible"] is True

    workflow.literature_synthesize(tmp_path, "C", "Q1", write_synthesis_config(tmp_path, card_path))
    question = load_yaml(question_path)
    assert question["literature"]["status"] == "SYNTHESIS_READY"
    assert question["literature"]["bib_keys"] == ["Lovelace2025Forecast"]

    paper = tmp_path / "paper"
    (paper / "sections").mkdir(parents=True, exist_ok=True)
    (paper / "sections" / "question_1.tex").write_text(
        "模型族及其迁移条件参见\\UpCite{Lovelace2025Forecast}。\n",
        encoding="utf-8",
    )
    (paper / "references.bib").write_text(
        "@article{Lovelace2025Forecast,\n"
        "  author={Ada Lovelace},\n"
        "  title={Probabilistic Forecasting for Small Samples},\n"
        "  journal={Journal of Forecasting},\n"
        "  year={2025},\n"
        "  doi={10.1234/forecast.1}\n"
        "}\n",
        encoding="utf-8",
    )
    audit = workflow.literature_audit(tmp_path, "C", "Q1", strict=True)
    assert audit["passed"] is True
    assert load_yaml(question_path)["literature"]["status"] == "CITATION_READY"

    claims = json.loads((tmp_path / "results" / "C" / "claims.json").read_text(encoding="utf-8"))
    assert claims["claims"] == []


def test_literature_is_nonblocking_through_g4_but_blocks_strict_g5(tmp_path: Path) -> None:
    question_path = prepare_question_interface(tmp_path)
    workflow.literature_plan(tmp_path, "C", "Q1", None)

    for gate in ("G0", "G1", "G2", "G3", "G4"):
        report = workflow.validate(tmp_path, "C", gate, "Q1", write=False, strict=True)
        checks = [item for item in report["checks"] if "literature" in item["name"].lower()]
        assert checks, gate
        assert all(item["passed"] for item in checks), (gate, checks)
        assert any("LITERATURE_INCOMPLETE" in item["detail"] for item in checks), (gate, checks)

    g5 = workflow.validate(tmp_path, "C", "G5", "Q1", write=False, strict=True)
    checks = [item for item in g5["checks"] if "literature" in item["name"].lower()]
    assert checks
    assert any(not item["passed"] for item in checks)
    assert load_yaml(question_path)["literature"]["status"] == "PLAN_READY"


def test_abstract_screened_card_cannot_support_formula_parameter_or_synthesis(tmp_path: Path) -> None:
    prepare_question_interface(tmp_path)
    workflow.literature_plan(tmp_path, "C", "Q1", None)
    workflow.literature_search(
        tmp_path,
        "C",
        "Q1",
        write_search_config(
            tmp_path,
            "litsearch-q1-abstract",
            "crossref",
            [
                literature_record(
                    "crossref-abstract",
                    "Probabilistic Forecasting for Small Samples",
                    "Ada Lovelace",
                    2025,
                    "10.1234/forecast.1",
                )
            ],
        ),
    )
    receipt_path = next(
        (tmp_path / "problems" / "C" / "questions" / "Q1" / "literature" / "searches").glob(
            "*/search_receipt.json"
        )
    )
    workflow.literature_read(
        tmp_path,
        "C",
        "Q1",
        write_card_config(tmp_path, receipt_path, depth="ABSTRACT_SCREENED"),
    )
    card_path = tmp_path / "problems" / "C" / "questions" / "Q1" / "literature" / "cards" / "litcard-q1-forecast.yaml"
    card = load_yaml(card_path)
    assert card["precision_evidence"] == []
    assert card["substantive_citation_eligible"] is False

    synthesis = workflow.literature_synthesize(
        tmp_path,
        "C",
        "Q1",
        write_synthesis_config(tmp_path, card_path),
    )
    assert synthesis["status"] == "SYNTHESIS_READY"
    assert synthesis["bib_keys"] == []
    audit = workflow.literature_audit(tmp_path, "C", "Q1", strict=True)
    assert audit["passed"] is False
    failed = [item for item in audit["checks"] if not item["passed"]]
    assert any(item["name"] in {"literature_cards_current", "literature_citation_handoff"} for item in failed)


def test_literature_rejects_cross_project_configs_and_detects_card_hash_drift(tmp_path: Path) -> None:
    question_path = prepare_question_interface(tmp_path)
    workflow.literature_plan(tmp_path, "C", "Q1", None)

    with pytest.raises(ValueError, match="project|workspace|outside|absolute"):
        workflow.literature_search(
            tmp_path,
            "C",
            "Q1",
            TEMPLATE_ROOT / "literature_search_receipt.yaml",
        )

    workflow.literature_search(
        tmp_path,
        "C",
        "Q1",
        write_search_config(
            tmp_path,
            "litsearch-q1-drift",
            "crossref",
            [
                literature_record(
                    "crossref-drift",
                    "Probabilistic Forecasting for Small Samples",
                    "Ada Lovelace",
                    2025,
                    "10.1234/forecast.1",
                )
            ],
        ),
    )
    receipt_path = next(
        (tmp_path / "problems" / "C" / "questions" / "Q1" / "literature" / "searches").glob(
            "*/search_receipt.json"
        )
    )
    workflow.literature_read(tmp_path, "C", "Q1", write_card_config(tmp_path, receipt_path))
    card_path = tmp_path / "problems" / "C" / "questions" / "Q1" / "literature" / "cards" / "litcard-q1-forecast.yaml"
    card_path.write_text(card_path.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")

    audit = workflow.literature_audit(tmp_path, "C", "Q1", strict=True)
    assert audit["passed"] is False
    assert any("SHA-256" in item["detail"] or "STALE" in item["detail"] for item in audit["checks"])
    assert load_yaml(question_path)["literature"]["status"] == "STALE"


def test_search_rejects_invalid_doi_and_read_rejects_metadata_conflict(tmp_path: Path) -> None:
    prepare_question_interface(tmp_path)
    workflow.literature_plan(tmp_path, "C", "Q1", None)

    invalid = literature_record(
        "bad-doi",
        "Probabilistic Forecasting for Small Samples",
        "Ada Lovelace",
        2025,
        "doi-is-not-valid",
    )
    with pytest.raises(ValueError, match="invalid DOI"):
        workflow.literature_search(
            tmp_path,
            "C",
            "Q1",
            write_search_config(tmp_path, "litsearch-q1-invalid", "crossref", [invalid]),
        )

    workflow.literature_search(
        tmp_path,
        "C",
        "Q1",
        write_search_config(
            tmp_path,
            "litsearch-q1-conflict",
            "crossref",
            [
                literature_record(
                    "valid-doi",
                    "Probabilistic Forecasting for Small Samples",
                    "Ada Lovelace",
                    2025,
                    "10.1234/forecast.1",
                )
            ],
        ),
    )
    receipt_path = next(
        (tmp_path / "problems" / "C" / "questions" / "Q1" / "literature" / "searches").glob(
            "*/search_receipt.json"
        )
    )
    card_config = write_card_config(tmp_path, receipt_path)
    card = load_yaml(card_config)
    card["metadata"]["doi"] = "10.9999/conflicting-source"
    dump_yaml(card_config, card)
    with pytest.raises(ValueError, match="conflict|metadata|receipt"):
        workflow.literature_read(tmp_path, "C", "Q1", card_config)


def test_literature_audit_detects_source_document_hash_drift(tmp_path: Path) -> None:
    question_path = prepare_question_interface(tmp_path)
    workflow.literature_plan(tmp_path, "C", "Q1", None)
    workflow.literature_search(
        tmp_path,
        "C",
        "Q1",
        write_search_config(
            tmp_path,
            "litsearch-q1-document-drift",
            "crossref",
            [
                literature_record(
                    "source-document",
                    "Probabilistic Forecasting for Small Samples",
                    "Ada Lovelace",
                    2025,
                    "10.1234/forecast.1",
                )
            ],
        ),
    )
    receipt_path = next(
        (tmp_path / "problems" / "C" / "questions" / "Q1" / "literature" / "searches").glob(
            "*/search_receipt.json"
        )
    )
    workflow.literature_read(tmp_path, "C", "Q1", write_card_config(tmp_path, receipt_path))
    card_path = tmp_path / "problems" / "C" / "questions" / "Q1" / "literature" / "cards" / "litcard-q1-forecast.yaml"
    card = load_yaml(card_path)
    document_path = tmp_path / card["source_document"]["path"]
    document_path.write_bytes(document_path.read_bytes() + b"drift")

    audit = workflow.literature_audit(tmp_path, "C", "Q1", strict=True)
    assert audit["passed"] is False
    assert any("source document" in item["detail"] and "SHA-256" in item["detail"] for item in audit["checks"])
    assert load_yaml(question_path)["literature"]["status"] == "STALE"
