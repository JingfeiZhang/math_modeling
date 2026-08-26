from __future__ import annotations

import ast
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
ACADEMIC_STANDARD = "references/competition-knowledge/playbooks/academic-quality-standard.md"
END_TO_END_STANDARD = "references/competition-knowledge/playbooks/end-to-end-quality-standard.md"
ALGORITHM_STANDARD = "references/algorithm-sources/QUALITY_STANDARD.md"
QUALITY_PLAYBOOKS = {
    "references/competition-knowledge/playbooks/data-and-feature-quality.md",
    "references/competition-knowledge/playbooks/algorithm-routing-quality.md",
    "references/competition-knowledge/playbooks/experiment-design-quality.md",
}
VISUAL_PLAYBOOK = "references/competition-knowledge/playbooks/visual-evidence-quality.md"
PAPER_PLAYBOOK = "references/cumcm-paper-quality-playbook.md"
NEW_RECIPES = {
    "observed-vs-predicted",
    "error-by-group",
    "distribution-ecdf",
    "rank-stability",
    "schedule-gantt",
    "resource-profile",
}
CODE_LIBRARY_READMES = {
    "代码库/README.md",
    "代码库/01_数据预处理与可视化/README.md",
    "代码库/02_评价类模型/README.md",
    "代码库/03_预测类模型/README.md",
    "代码库/04_分类与聚类/README.md",
    "代码库/05_规划与优化/README.md",
    "代码库/06_智能优化算法/README.md",
    "代码库/07_统计分析/README.md",
    "代码库/08_图论与网络模型/README.md",
    "代码库/09_机理建模/README.md",
    "代码库/10_模型检验/README.md",
    "代码库/11_组合模型（创新加分）/README.md",
}
DEPRECATED_GUIDANCE = {
    "C题几乎必考",
    "改参数即用",
    "三大必备检验",
    "三大必做检验",
    "随机森林首选基线",
    "精度常高于随机森林",
}


def _load_yaml(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_academic_quality_is_wired_into_prompt_policy() -> None:
    policy = _load_yaml(ROOT / "config" / "prompt_policy.yaml")
    roles = policy["roles"]

    academic = policy["academic_quality"]
    assert academic["profile"] == ACADEMIC_STANDARD
    assert set(academic["roles"]) >= {"solver", "literature", "visualization", "paper", "reviewer"}

    solver_scope = set(roles["solver"]["read_scope"])
    assert QUALITY_PLAYBOOKS <= solver_scope
    assert ACADEMIC_STANDARD in solver_scope
    assert ALGORITHM_STANDARD in solver_scope

    literature_scope = set(roles["literature"]["read_scope"])
    visualization_scope = set(roles["visualization"]["read_scope"])
    paper_scope = set(roles["paper"]["read_scope"])
    reviewer_scope = set(roles["reviewer"]["read_scope"])

    assert ACADEMIC_STANDARD in literature_scope
    assert ACADEMIC_STANDARD in visualization_scope
    assert ACADEMIC_STANDARD in paper_scope
    assert ACADEMIC_STANDARD in reviewer_scope
    assert VISUAL_PLAYBOOK in visualization_scope
    assert VISUAL_PLAYBOOK in paper_scope
    assert QUALITY_PLAYBOOKS | {VISUAL_PLAYBOOK} <= reviewer_scope
    assert PAPER_PLAYBOOK in paper_scope
    assert PAPER_PLAYBOOK in reviewer_scope

    for relative in QUALITY_PLAYBOOKS | {
        ACADEMIC_STANDARD,
        END_TO_END_STANDARD,
        ALGORITHM_STANDARD,
        VISUAL_PLAYBOOK,
        PAPER_PLAYBOOK,
    }:
        assert (ROOT / relative).is_file(), relative


def test_reference_algorithm_library_uses_quality_contracts() -> None:
    for relative in CODE_LIBRARY_READMES:
        path = ROOT / relative
        assert path.is_file(), relative
        text = path.read_text(encoding="utf-8")
        for phrase in DEPRECATED_GUIDANCE:
            assert phrase not in text, f"Deprecated guidance {phrase!r} found in {relative}"

    template_standard = (ROOT / "代码库" / "_模板编写规范.md").read_text(encoding="utf-8")
    assert "study" in template_standard.lower() or "参考" in template_standard
    assert "Formal" in template_standard

    algorithm_index = (ROOT / "references" / "algorithm-sources" / "index.md").read_text(encoding="utf-8")
    assert "QUALITY_STANDARD.md" in algorithm_index
    assert "study" in algorithm_index.lower()


def test_figure_recipe_catalog_points_to_existing_parseable_scripts() -> None:
    catalog = _load_yaml(ROOT / "templates" / "figures" / "recipe_catalog.yaml")
    recipes = catalog["recipes"]
    by_id = {entry["id"]: entry for entry in recipes}
    assert NEW_RECIPES <= set(by_id)

    for entry in recipes + catalog.get("compatibility_recipes", []):
        script = ROOT / "templates" / "figures" / entry["script"]
        assert script.is_file(), f"Missing recipe script: {entry['id']} -> {script}"
        if script.suffix == ".py":
            ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
        assert entry["required_columns"], f"Recipe has no evidence-column contract: {entry['id']}"
