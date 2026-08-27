from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / "config" / "prompt_policy.yaml"
ACADEMIC = ROOT / "references" / "competition-knowledge" / "playbooks" / "academic-quality-standard.md"
ALGORITHM_STANDARD = ROOT / "references" / "algorithm-sources" / "QUALITY_STANDARD.md"
TEMPLATE_STANDARD = ROOT / "代码库" / "_模板编写规范.md"


def _load_policy() -> dict:
    return yaml.safe_load(POLICY.read_text(encoding="utf-8"))


def test_academic_quality_profile_is_connected_to_prompt_roles() -> None:
    policy = _load_policy()
    quality = policy["academic_quality"]

    assert quality["profile"] == "references/competition-knowledge/playbooks/academic-quality-standard.md"
    assert quality["corpus_report"] == "corpus/reports/cumcm-c-writing-template-2021-2025.md"

    required_roles = {"solver", "literature", "visualization", "paper", "reviewer"}
    assert required_roles.issubset(set(quality["roles"]))

    for role in required_roles:
        scope = set(policy["roles"][role]["read_scope"])
        assert quality["profile"] in scope


def test_academic_quality_documents_exist_and_cover_core_reasoning() -> None:
    academic = ACADEMIC.read_text(encoding="utf-8")
    algorithm = ALGORITHM_STANDARD.read_text(encoding="utf-8")

    for marker in [
        "优秀论文的最小闭环",
        "Baseline 与模型选择质量",
        "自我反驳",
        "停止规则",
        "最终评委视角七问",
    ]:
        assert marker in academic

    for marker in [
        "Trigger",
        "Non-trigger",
        "Baseline",
        "Validation",
        "禁止 silent fallback",
        "验证模板必须“按风险选”",
    ]:
        assert marker.lower() in algorithm.lower()


def test_study_template_standard_does_not_encourage_copy_and_run() -> None:
    text = TEMPLATE_STANDARD.read_text(encoding="utf-8")

    assert "study-only" in text
    assert "禁止 silent fallback" in text
    assert "Known-answer" in text
    assert "把示例数据换成附件即可" in text  # must appear only as a prohibited phrase
    assert "不得再写" in text


def test_high_risk_algorithm_readmes_use_quality_first_language() -> None:
    paths = [
        ROOT / "代码库" / "03_预测类模型" / "README.md",
        ROOT / "代码库" / "05_规划与优化" / "README.md",
        ROOT / "代码库" / "10_模型检验" / "README.md",
        ROOT / "代码库" / "11_组合模型（创新加分）" / "README.md",
    ]
    texts = [p.read_text(encoding="utf-8") for p in paths]

    assert "随机森林不是通用 baseline" in texts[0]
    assert "能精确建模和求解时" in texts[1]
    assert "没有任何规则要求每个模型固定完成" in texts[2]
    assert "不代表组合模型天然更高级或更容易得分" in texts[3]
