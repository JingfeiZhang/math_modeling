from __future__ import annotations

import ast
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
QUALITY_PLAYBOOKS = {
    "references/competition-knowledge/playbooks/data-and-feature-quality.md",
    "references/competition-knowledge/playbooks/algorithm-routing-quality.md",
    "references/competition-knowledge/playbooks/experiment-design-quality.md",
}
AWARD_PLAYBOOK = "references/competition-knowledge/playbooks/award-oriented-modeling.md"
PAPER_PLAYBOOK = "references/cumcm-paper-quality-playbook.md"
VISUAL_PLAYBOOK = "references/competition-knowledge/playbooks/visual-evidence-quality.md"
RENDERING_HELPER = "templates/figures/python/publication_helpers.py"
FIGURE_SOURCE_NOTE = "references/figure-sources/figures4papers-integration.md"
NEW_RECIPES = {
    "observed-vs-predicted",
    "error-by-group",
    "distribution-ecdf",
    "rank-stability",
    "schedule-gantt",
    "resource-profile",
}


def _load_yaml(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_quality_playbooks_are_wired_into_prompt_policy() -> None:
    policy = _load_yaml(ROOT / "config" / "prompt_policy.yaml")
    roles = policy["roles"]

    solver_scope = set(roles["solver"]["read_scope"])
    assert QUALITY_PLAYBOOKS <= solver_scope
    assert AWARD_PLAYBOOK in solver_scope

    visualization_scope = set(roles["visualization"]["read_scope"])
    assert VISUAL_PLAYBOOK in visualization_scope
    assert "templates/figures/recipe_catalog.yaml" in visualization_scope

    paper_scope = set(roles["paper"]["read_scope"])
    reviewer_scope = set(roles["reviewer"]["read_scope"])
    assert VISUAL_PLAYBOOK in paper_scope
    assert PAPER_PLAYBOOK in paper_scope
    assert QUALITY_PLAYBOOKS | {AWARD_PLAYBOOK, VISUAL_PLAYBOOK} <= reviewer_scope
    assert PAPER_PLAYBOOK in reviewer_scope

    for relative in QUALITY_PLAYBOOKS | {AWARD_PLAYBOOK, PAPER_PLAYBOOK, VISUAL_PLAYBOOK}:
        assert (ROOT / relative).is_file(), relative


def test_generalized_training_principles_live_in_existing_mainline_guidance() -> None:
    data_text = (ROOT / "references/competition-knowledge/playbooks/data-and-feature-quality.md").read_text(encoding="utf-8")
    routing_text = (ROOT / "references/competition-knowledge/playbooks/algorithm-routing-quality.md").read_text(encoding="utf-8")
    experiment_text = (ROOT / "references/competition-knowledge/playbooks/experiment-design-quality.md").read_text(encoding="utf-8")
    award_text = (ROOT / AWARD_PLAYBOOK).read_text(encoding="utf-8")
    paper_text = (ROOT / PAPER_PLAYBOOK).read_text(encoding="utf-8")

    # General principles must be background-independent and attached to the existing execution path.
    assert "特殊数值先解释“生成语义”" in data_text
    assert "fit(reference/train)" in data_text
    assert "外部数据只在能改变决策时优先接入" in data_text

    assert "Formulation-first" in routing_text
    assert "Estimate → Decide" in routing_text
    assert "Feasibility first" in routing_text
    assert "确定性模型先闭合" in routing_text

    assert "先验证 formulation" in experiment_text
    assert "端到端实验" in experiment_text
    assert "跨问接口验证" in experiment_text

    assert "Formulation 五联检" in award_text
    assert "Model\n↔ Code\n↔ Result\n↔ Paper" in award_text
    assert "误差如何传播" in award_text

    assert "Model ↔ Code ↔ Result ↔ Paper 一致性" in paper_text
    assert "评委视角九问" in paper_text

    # Specific historical problem nouns must not become routing rules in the integrated mainline.
    forbidden_case_terms = ["蔬菜", "农作物", "地块", "轮作", "2023C", "2024C"]
    integrated_text = "\n".join([data_text, routing_text, experiment_text, award_text, paper_text])
    for term in forbidden_case_terms:
        assert term not in integrated_text, f"Historical-case term leaked into mainline guidance: {term}"


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


def test_publication_rendering_patterns_remain_internal_and_parseable() -> None:
    helper = ROOT / RENDERING_HELPER
    source_note = ROOT / FIGURE_SOURCE_NOTE
    visual_playbook = (ROOT / VISUAL_PLAYBOOK).read_text(encoding="utf-8")
    multipanel = ROOT / "templates/figures/python/plot_multipanel_main_result.py"

    assert helper.is_file()
    assert source_note.is_file()
    ast.parse(helper.read_text(encoding="utf-8"), filename=str(helper))
    ast.parse(multipanel.read_text(encoding="utf-8"), filename=str(multipanel))

    assert "publication_helpers.new_panel_figure()" in visual_playbook
    assert "config/figure_style.yaml" in visual_playbook
    assert "figures4papers-integration.md" in visual_playbook

    multipanel_text = multipanel.read_text(encoding="utf-8")
    assert "allow_multiple_primary_axes=True" in multipanel_text
    assert "shared_legend" in multipanel_text

    source_text = source_note.read_text(encoding="utf-8")
    assert "config/figure_style.yaml" in source_text
    assert "明确不吸收" in source_text
