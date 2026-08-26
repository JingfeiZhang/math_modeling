from __future__ import annotations

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "paper" / "cumcm-2026"


class CumcmTemplateV3Tests(unittest.TestCase):
    def test_machine_readable_structure_contract(self) -> None:
        config = yaml.safe_load((TEMPLATE / "template.yaml").read_text(encoding="utf-8"))
        self.assertEqual(config["contract_version"], "3.0")
        self.assertEqual(config["standard_paper_profile"], "cumcm-standard-v1")
        self.assertEqual(config["standard_paper_profile_source"], "templates/prompts/paper/cumcm-2026.yaml")
        self.assertEqual(
            config["contract_evidence"]["sha256"],
            "EB36D0D70F6DA29F21A13C4551F8C93997292E72C139DD9B2159E7878B8A5603",
        )
        contract = config["structure_contract"]
        self.assertFalse(contract["automatic_toc"])
        self.assertEqual(contract["notation_location"], "front_body")
        self.assertFalse(contract["appendix_symbol_table"])
        self.assertEqual(contract["generated_question_structure"], "paper/generated/question_structure.tex")
        self.assertEqual(contract["generated_build_mode"], "paper/generated/build_mode.tex")
        self.assertIn("MathModelPreviewfalse", contract["generated_build_mode_rule"])
        self.assertEqual(
            [item["id"] for item in contract["question_argument_contract"]["responsibilities"]],
            [
                "objective_interface",
                "data_mechanism",
                "model_choice",
                "formulation",
                "algorithm",
                "result",
                "validation",
                "conclusion",
            ],
        )
        self.assertFalse(contract["writing_boundaries"]["algorithm_name_fixed_by_template"])
        self.assertFalse(contract["writing_boundaries"]["question_heading_fixed_by_template"])
        self.assertEqual(contract["question_argument_contract"]["heading_strategy"]["mode"], "dynamic")
        self.assertEqual(contract["question_count"]["minimum"], 1)
        self.assertIsNone(contract["question_count"]["maximum"])
        self.assertIn("由真实题面解析得到", contract["question_count"]["rule"])
        self.assertEqual(
            contract["abstract_contract"]["per_question_required"],
            ["subject", "method", "result", "validation", "boundary"],
        )
        self.assertEqual(
            contract["figure_table_contract"]["explanation_required"],
            ["result", "cause_or_mechanism", "problem_meaning", "boundary"],
        )

    def test_main_uses_generated_question_structure_with_preview_fallback(self) -> None:
        main = (TEMPLATE / "main.tex").read_text(encoding="utf-8")
        self.assertIn("generated/question_structure.tex", main)
        self.assertIn("Missing generated/question_structure.tex", main)
        self.assertIn("\\ifMathModelPreview", main)
        self.assertIn("\\PackageError{cumcm-2026}{Missing generated/question_structure.tex for a formal project}", main)
        self.assertNotIn("\\tableofcontents", main)
        self.assertLess(main.index("sections/assumptions_notation.tex"), main.index("generated/question_structure.tex"))
        self.assertIn("\\ifRequireAIStatement", main)
        generated = (TEMPLATE / "generated" / "question_structure.tex").read_text(encoding="utf-8")
        metadata = (TEMPLATE / "metadata.tex").read_text(encoding="utf-8")
        self.assertIn("\\MathModelPreviewtrue", metadata)
        self.assertIn("Preview-only", generated)
        for number in range(1, 5):
            self.assertIn(f"sections/question_{number}.tex", generated)

    def test_each_question_uses_suggested_headings_and_dynamic_responsibility_contract(self) -> None:
        suggested_headings = (
            "问题目标与关键口径",
            "数据特征与机理依据",
            "模型建立与求解",
            "结果、检验与决策含义",
            "结论与适用边界",
        )
        forbidden_fixed_algorithms = ("XGBoost", "ARIMA", "LSTM", "遗传算法", "粒子群", "TOPSIS")
        for number in range(1, 5):
            with self.subTest(question=number):
                text = (TEMPLATE / "sections" / f"question_{number}.tex").read_text(encoding="utf-8")
                self.assertEqual(text.count("\\subsection{"), 5)
                for heading in suggested_headings:
                    self.assertIn(f"\\subsection{{{heading}}}", text)
                self.assertNotIn("\\WritingContract", text)
                self.assertNotIn("\\TemplatePrompt", text)
                for algorithm in forbidden_fixed_algorithms:
                    self.assertNotIn(algorithm, text)

    def test_authoring_prompts_are_external_to_formal_tex(self) -> None:
        required = (
            "abstract.tex",
            "problem_restatement.tex",
            "problem_analysis.tex",
            "assumptions_notation.tex",
            "data_processing.tex",
            "model_evaluation.tex",
            "references.tex",
            "appendix.tex",
        )
        for name in required:
            with self.subTest(section=name):
                text = (TEMPLATE / "sections" / name).read_text(encoding="utf-8")
                self.assertNotIn("\\WritingContract", text)
                self.assertNotIn("\\TemplatePrompt", text)
        preamble = (TEMPLATE / "preamble.tex").read_text(encoding="utf-8")
        self.assertNotIn("\\WritingContract", preamble)
        self.assertNotIn("\\TemplatePrompt", preamble)
        prompts = yaml.safe_load((ROOT / "templates" / "prompts" / "paper" / "cumcm-2026.yaml").read_text(encoding="utf-8"))
        assert set(prompts["sections"]) == {
            "abstract", "ai_statement", "problem_restatement", "problem_analysis", "assumptions_notation",
            "data_processing", "question", "model_evaluation", "references", "appendix",
        }
        assert prompts["sections"]["question"]["required_content"] == [
            "objective_interface", "data_mechanism", "model_choice", "formulation",
            "algorithm", "result", "validation", "conclusion",
        ]
        assert prompts["sections"]["question"]["heading_policy"]["mode"] == "dynamic"
        assert prompts["sections"]["question"]["heading_policy"]["default_titles_are"] == "suggestions_only"
        assert prompts["source_contract_count"] == 52
        assert set(prompts["sections"]["question"]["variants"]) == {"Q1", "Q2", "Q3", "Q4"}
        for question in prompts["sections"]["question"]["variants"].values():
            assert set(question["contracts"]) == set(prompts["sections"]["question"]["required_content"])
        standard = prompts["standard_profile"]
        assert standard["id"] == "cumcm-standard-v1"
        assert "current_official_rules" in standard["precedence"]
        assert set(standard["activation"]) == {"always", "conditional", "not_applicable"}
        triggers = prompts["quality_review"]["conditional_triggers"]
        assert "prediction_delivery" in triggers
        assert "multi_objective" in triggers
        assert "physical_state" in triggers
        assert "scenario_scope" in triggers
        assert not any(key.startswith("Q") for key in triggers)
        content_audit = prompts["quality_review"]["content_audit"]
        assert content_audit["review_order"][:3] == [
            "question_answerability",
            "variable_assumption_closure",
            "model_fit",
        ]
        assert content_audit["result_sentence_pattern"] == "结果—原因—意义—边界"
        assert len(content_audit["reviewer_test"]["questions"]) == 4
        count = 0
        for section in prompts["sections"].values():
            count += int("contract" in section)
            count += len(section.get("contracts", {}))
            count += sum(len(variant.get("contracts", {})) for variant in section.get("variants", {}).values())
        assert count == prompts["source_contract_count"]

    def test_bibtex_does_not_duplicate_the_explicit_reference_heading(self) -> None:
        references = (TEMPLATE / "sections" / "references.tex").read_text(encoding="utf-8")
        preamble = (TEMPLATE / "preamble.tex").read_text(encoding="utf-8")
        self.assertEqual(references.count("\\section*{参考文献}"), 1)
        self.assertIn("\\bibliographystyle{gbt7714-numerical}", references)
        self.assertIn("\\bibliography{references}", references)
        self.assertIn("\\patchcmd{\\thebibliography}{\\section*{\\refname}}{}{}", preamble)

    def test_appendix_does_not_define_a_second_symbol_table(self) -> None:
        appendix = (TEMPLATE / "sections" / "appendix.tex").read_text(encoding="utf-8")
        self.assertNotIn("\\subsection{符号", appendix)
        self.assertNotIn("\\section{符号", appendix)


if __name__ == "__main__":
    unittest.main()
