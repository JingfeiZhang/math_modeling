from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from src.corpus.miner import (
    SourceSpec,
    build_paper_card,
    classify_authenticity,
    deduplicate_records,
    git_blob_sha1,
    index_matlab_manifest,
    is_award_verified_deep_read,
    load_source_config,
    scan_matlab_text,
    scan_matlab_tree,
    sync_git_tree,
    validate_paper_card,
)


ROOT = Path(__file__).resolve().parents[1]


def git_entry(path: str, content: bytes) -> dict:
    return {"path": path, "type": "blob", "sha": git_blob_sha1(content), "size": len(content)}


def test_pinned_sources_and_metadata_only_tree_sync(tmp_path: Path) -> None:
    config, specs = load_source_config(ROOT / "config" / "corpus_sources.yaml")
    assert config["policy"]["default_download"] == "metadata_only"
    assert {item.commit for item in specs} == {
        "cd5be91735ebf11d5ee52eb170e86a6d07131977",
        "8783d0d822f89f98aa6182dd933cc2e9f3e2ddce",
    }
    content = b"x = linprog(f,A,b);\n"
    tree = {"sha": "a" * 40, "truncated": False, "tree": [git_entry("code/model.m", content), git_entry("paper/a.pdf", b"pdf")]}

    def no_network(_: str) -> bytes:
        raise AssertionError("metadata fixture sync must not fetch blob content")

    manifest = sync_git_tree(specs[0], tmp_path, tree_payload=tree, fetch_bytes=no_network)
    assert manifest["commit"] == specs[0].commit
    assert manifest["entry_count"] == 2
    assert manifest["cached_count"] == 0
    assert manifest["download_policy"] == "metadata_only"
    persisted = json.loads((tmp_path / "sources" / specs[0].source_id / specs[0].commit / "manifest.json").read_text(encoding="utf-8"))
    assert persisted["extension_counts"] == {".m": 1, ".pdf": 1}


def test_source_config_keeps_gmcm_mirror_out_of_cumcm_target() -> None:
    config = yaml.safe_load((ROOT / "config" / "corpus_sources.yaml").read_text(encoding="utf-8"))
    repositories = {item["id"]: item for item in config["repositories"]}
    zhanwen = repositories["zhanwen-mathmodel"]
    assert "gmcm-paper-index" in zhanwen["adopted"]
    assert "cumcm-paper-index" not in zhanwen["adopted"]
    assert "not CUMCM" in zhanwen["identity_warning"]

    groups = config["deep_read_program"]["groups"]
    assert groups["cumcm_historical_2012_2020"] == 18
    assert groups["cumcm_official_2024"] == 6
    assert "cumcm_2012_2023" not in groups


def test_explicit_small_download_is_git_verified_and_content_addressed(tmp_path: Path) -> None:
    spec = SourceSpec("fixture", "https://github.com/example/repo", "1" * 40)
    script = b"result = fmincon(fun,x0,A,b);\n"
    pdf = b"large-pdf"
    tree = {"sha": "2" * 40, "truncated": False, "tree": [git_entry("src/run.m", script), git_entry("papers/a.pdf", pdf)]}

    def fetch(url: str) -> bytes:
        assert url.endswith("/src/run.m")
        return script

    manifest = sync_git_tree(
        spec,
        tmp_path,
        tree_payload=tree,
        fetch_bytes=fetch,
        download_small=True,
        allowed_extensions=[".m"],
    )
    assert manifest["cached_count"] == 1
    cached = manifest["cached"][0]
    object_path = tmp_path / cached["object"]
    assert object_path.read_bytes() == script
    assert cached["sha256"] == hashlib.sha256(script).hexdigest()


def official_record(**overrides: object) -> dict:
    value = {
        "paper_id": "cumcm-2023-a-001",
        "identity": {"contest": "CUMCM", "year": 2023, "problem": "A", "team_id": "20230001", "title": "某模型"},
        "source": {"url": "https://official.example/paper", "publisher": "official", "accessible": True, "fulltext": True},
        "award_evidence": {"official_url": "https://official.example/results", "verified": True, "contest": "CUMCM", "year": 2023, "problem": "A", "team_id": "20230001"},
    }
    value.update(overrides)
    return value


def test_authenticity_never_uses_filename_claim() -> None:
    unverified = {
        "filename_claim": "2023_O奖_优秀论文.pdf",
        "identity": {"contest": "MCM", "year": 2023, "problem": "A"},
        "source": {"url": "https://community.example/file", "publisher": "community", "accessible": True, "fulltext": True},
    }
    result = classify_authenticity(unverified)
    assert result["level"] == "C"
    assert "filename claims were ignored" in result["reasons"]
    assert classify_authenticity(official_record())["level"] == "A"

    mirror = official_record(
        source={"url": "https://mirror.example/paper", "publisher": "mirror", "accessible": True, "fulltext": True}
    )
    assert classify_authenticity(mirror)["level"] == "B"
    mirror["award_evidence"]["team_id"] = "mismatch"
    assert classify_authenticity(mirror)["level"] == "C"


def test_paper_card_v3_requires_real_page_evidence_for_deep_read(tmp_path: Path) -> None:
    base = official_record()
    base.update(
        {
            "pdf": {"sha256": "a" * 64, "pages": 20},
            "review_status": "evidence_deep_read",
            "page_evidence": [{"page": 1, "observation": "摘要按四问逐项给出量化结果", "locator": "PDF p.1", "render": "pages/01.png", "derivation": "visual"}],
            "abstract_structure": [{"page": 1, "role": "result", "detail": "给出误差与提升率"}],
            "model_chain": [{"page": 4, "question": "Q1", "model": "MILP", "reason": "离散资源约束"}],
            "validation_chain": [{"type": "baseline", "locator": "p.12 Table 4"}],
            "figures": [{"page": 8, "type": "sensitivity", "role": "robustness", "lesson": "展示参数扰动后的结论稳定性"}],
            "code_links": [{"path": "code/q1.m", "blob_sha": "b" * 40}],
            "transferable_rules": ["摘要中的每个数字都能定位到正文表格"],
            "risks": ["旧版格式不能作为 2026 规则依据"],
        }
    )
    card = build_paper_card(base, require_deep_read=True)
    assert card["schema_version"] == "3.0"
    assert card["authenticity"]["level"] == "A"
    assert is_award_verified_deep_read(card)
    assert validate_paper_card(card, require_deep_read=True) == []
    card_path = tmp_path / "paper-card.json"
    card_path.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
    skill_validator = ROOT / "skill_staging" / "modeling-paper-miner" / "scripts" / "validate_paper_card.py"
    result = subprocess.run(
        [sys.executable, str(skill_validator), str(card_path), "--require-deep-read"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    base["page_evidence"] = []
    with pytest.raises(ValueError, match="page_evidence"):
        build_paper_card(base, require_deep_read=True)


def test_content_deep_read_allows_level_c_without_award_claim() -> None:
    record = official_record(
        source={"url": "https://mirror.example/paper", "publisher": "mirror", "accessible": True, "fulltext": True},
        award_evidence={"verified": False, "official_url": "", "contest": "", "year": None, "problem": "", "award": ""},
    )
    record.update(
        {
            "pdf": {"sha256": "d" * 64, "pages": 18},
            "review_status": "evidence_deep_read",
            "page_evidence": [{"page": 1, "observation": "摘要结构清楚", "locator": "PDF p.1", "render": "pages/01.png", "derivation": "mixed"}],
            "abstract_structure": [{"page": 1, "role": "summary"}],
            "model_chain": [{"page": 5, "model": "regression"}],
            "validation_chain": [{"locator": "PDF p.12", "type": "residual"}],
            "figures": [{"page": 8, "type": "residual", "role": "diagnostic", "lesson": "把假设检查与主结果分开"}],
            "code_links": [],
            "transferable_rules": ["摘要方法与结果一一对应"],
            "risks": ["奖项未获独立官方证据核验"],
        }
    )
    card = build_paper_card(record, require_deep_read=True)
    assert card["authenticity"]["level"] == "C"
    assert validate_paper_card(card, require_deep_read=True) == []
    assert not is_award_verified_deep_read(card)

    official_without_award = dict(record)
    official_without_award["source"] = {
        "url": "https://official.example/paper",
        "publisher": "official",
        "accessible": True,
        "fulltext": True,
    }
    official_card = build_paper_card(official_without_award, require_deep_read=True)
    assert official_card["authenticity"]["level"] == "A"
    assert not is_award_verified_deep_read(official_card)


def test_exact_and_probable_deduplication_have_different_actions() -> None:
    digest = "a" * 64
    common = "摘要建立混合整数规划模型并通过基线比较和参数扰动验证结论稳健。" * 8
    records = [
        {"id": "a", "sha256": digest, "first_page_phash": "0000000000000000", "text": common},
        {"id": "b", "sha256": digest, "first_page_phash": "0000000000000000", "text": common},
        {"id": "c", "sha256": "b" * 64, "first_page_phash": "0000000000000001", "text": "水印" + common},
        {"id": "d", "sha256": "c" * 64, "first_page_phash": "ffffffffffffffff", "text": "完全不同的内容"},
    ]
    report = deduplicate_records(records)
    assert report["exact_groups"][0]["duplicate_ids"] == ["b"]
    probable_pairs = {(item["left_id"], item["right_id"]) for item in report["probable_duplicates"]}
    assert ("a", "c") in probable_pairs
    assert all(item["action"] == "review_keep_separate" for item in report["probable_duplicates"])
    assert ("a", "d") not in probable_pairs


def test_matlab_scan_finds_dangerous_patterns_and_toolboxes(tmp_path: Path) -> None:
    source = """
% system('comment only')
data = readtable('C:\\Users\\name\\data.csv');
x = intlinprog(f,intcon,A,b,Aeq,beq,lb,ub);
y = eval(user_expression);
payload = webread('https://example.com/data');
uifigure();
delete('result.mat');
"""
    result = scan_matlab_text(source, path="unsafe.m")
    categories = {item["category"] for item in result["risks"]}
    assert {"absolute_path", "network", "interactive_gui", "dynamic_execution", "delete_or_overwrite"} <= categories
    assert "Optimization Toolbox" in {item["toolbox"] for item in result["toolboxes"]}
    assert result["execution_policy"] == "manual_review_required"

    (tmp_path / "safe.m").write_text("x = 1:10; y = x.^2; plot(x,y);\n", encoding="utf-8")
    (tmp_path / "unsafe.m").write_text(source, encoding="utf-8")
    index = scan_matlab_tree(tmp_path)
    assert index["file_count"] == 2
    assert index["execution_policy"] == "static_index_only_no_bulk_execution"


def test_matlab_tree_manifest_indexes_without_claiming_a_scan() -> None:
    manifest = {
        "entries": [
            {"path": "a.m", "blob_sha": "a" * 40, "bytes": 10},
            {"path": "paper.pdf", "blob_sha": "b" * 40, "bytes": 20},
        ]
    }
    index = index_matlab_manifest(manifest)
    assert index["file_count"] == 1
    assert index["files"][0]["scan_status"] == "content_not_cached"


def test_truncated_git_tree_is_rejected(tmp_path: Path) -> None:
    spec = SourceSpec("fixture", "https://github.com/example/repo", "1" * 40)
    with pytest.raises(ValueError, match="truncated"):
        sync_git_tree(spec, tmp_path, tree_payload={"truncated": True, "tree": []})
