from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PAPER_TEMPLATES = ROOT / "templates" / "paper"
FIGURE_TEMPLATES = ROOT / "templates" / "figures"
SECTION_TEMPLATES = ROOT / "templates" / "sections"
MINER_SKILL = ROOT / "skill_staging" / "modeling-paper-miner"


class PaperTemplateFamilyTests(unittest.TestCase):
    families = ("cumcm-2026", "mcm-current", "gmcm-reference")

    def test_family_contracts(self) -> None:
        for family in self.families:
            with self.subTest(family=family):
                root = PAPER_TEMPLATES / family
                self.assertTrue((root / "main.tex").is_file())
                self.assertTrue((root / "preamble.tex").is_file())
                self.assertTrue((root / "metadata.tex").is_file())
                config = yaml.safe_load((root / "template.yaml").read_text(encoding="utf-8"))
                self.assertEqual(config["engine"], "xelatex")
                self.assertFalse(config["automatic_toc"])
                tex = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.tex"))
                self.assertNotIn("\\tableofcontents", tex)
                self.assertIn("\\FrozenClaim", tex)

    def test_chinese_templates_exclude_personal_identity_fields(self) -> None:
        forbidden = ("姓名", "学校", "学号", "指导教师", "参赛队员")
        for family in ("cumcm-2026", "gmcm-reference"):
            tex = "\n".join(path.read_text(encoding="utf-8") for path in (PAPER_TEMPLATES / family).rglob("*.tex"))
            for token in forbidden:
                self.assertNotIn(token, tex, f"{family} contains identity token {token}")

    @unittest.skipUnless(shutil.which("latexmk") and shutil.which("xelatex"), "XeLaTeX toolchain is unavailable")
    def test_all_families_compile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target_root = Path(tmp)
            for family in self.families:
                with self.subTest(family=family):
                    target = target_root / family
                    shutil.copytree(PAPER_TEMPLATES / family, target)
                    result = subprocess.run(
                        ["latexmk", "-xelatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                        cwd=target,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=180,
                    )
                    self.assertEqual(result.returncode, 0, result.stdout[-4000:] + result.stderr[-2000:])
                    self.assertGreater((target / "main.pdf").stat().st_size, 1_000)


class SectionSkeletonTests(unittest.TestCase):
    expected = {
        "optimization.tex",
        "prediction.tex",
        "comprehensive-evaluation.tex",
        "statistical-inference.tex",
        "dynamic-simulation.tex",
        "network-spatial.tex",
    }

    def test_six_evidence_first_skeletons(self) -> None:
        actual = {path.name for path in SECTION_TEMPLATES.glob("*.tex")}
        self.assertEqual(actual, self.expected)
        for path in SECTION_TEMPLATES.glob("*.tex"):
            text = path.read_text(encoding="utf-8")
            self.assertIn("基线", text)
            self.assertIn("稳健", text)
            self.assertIn("边界", text)
            self.assertIn("\\TemplatePrompt", text)


class FigureRecipeTests(unittest.TestCase):
    def test_catalog_declares_single_backend_recipes_and_legacy_compatibility(self) -> None:
        catalog = yaml.safe_load((FIGURE_TEMPLATES / "recipe_catalog.yaml").read_text(encoding="utf-8"))
        recipes = catalog["recipes"]
        self.assertEqual(len(recipes), 14)
        self.assertEqual(len({recipe["id"] for recipe in recipes}), 14)
        self.assertIn("model-comparison", {recipe["id"] for recipe in recipes})
        self.assertTrue(catalog["policy"]["one_backend_per_figure"])
        self.assertEqual(catalog["policy"]["input"], "real_experiment_artifacts_only")
        for recipe in recipes:
            self.assertIn(recipe["backend"], {"python", "matlab"})
            self.assertTrue((FIGURE_TEMPLATES / recipe["script"]).is_file(), recipe["id"])
            self.assertGreaterEqual(len(recipe["required_columns"]), 2)
        compatibility = catalog["compatibility_recipes"]
        self.assertEqual({recipe["id"] for recipe in compatibility}, {"residual-calibration", "roc-pr", "multipanel-main-result"})
        for recipe in compatibility:
            self.assertTrue((FIGURE_TEMPLATES / recipe["script"]).is_file(), recipe["id"])

    def test_figure_contract_v2_required_fields(self) -> None:
        schema = json.loads((FIGURE_TEMPLATES / "figure_contract_v2.schema.json").read_text(encoding="utf-8"))
        required = set(schema["required"])
        expected = {
            "core_conclusion",
            "evidence_chain",
            "archetype",
            "panel_map",
            "review_risks",
            "final_width_mm",
            "min_font_pt",
            "source_data",
            "statistics",
        }
        self.assertTrue(expected <= required)
        template = yaml.safe_load((FIGURE_TEMPLATES / "figure_contract_v2.template.yaml").read_text(encoding="utf-8"))
        self.assertEqual(template["contract_version"], "2.0")
        self.assertEqual(template["outputs"]["png_dpi"], 400)
        self.assertEqual(set(template["outputs"]), {"pdf", "svg", "png", "png_dpi"})
        self.assertTrue(template["panel_map"])
        self.assertTrue(expected <= set(template))
        workspace_schema = json.loads((ROOT / "config" / "schemas" / "figure_contract.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(workspace_schema["$ref"], "../../templates/figures/figure_contract_v2.schema.json")

    def test_recipes_have_no_random_data_fallback(self) -> None:
        for path in list((FIGURE_TEMPLATES / "python").glob("plot_*.py")) + list((FIGURE_TEMPLATES / "matlab").glob("plot_*.m")):
            text = path.read_text(encoding="utf-8").lower()
            self.assertNotIn("np.random", text, path.name)
            self.assertNotIn("default_rng", text, path.name)
            self.assertNotIn("rand(", text, path.name)
            self.assertNotIn("randn(", text, path.name)

    def test_matlab_recipes_use_explicit_axes_and_exportgraphics(self) -> None:
        for path in (FIGURE_TEMPLATES / "matlab").glob("plot_*.m"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("subplot(", text)
            self.assertNotIn("gca", text)
            self.assertNotIn("gcf", text)
            self.assertNotIn("saveas(", text)
            self.assertIn("mm_export_triplet", text)

    def test_python_prediction_recipe_exports_triplet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "evidence.csv"
            evidence.write_text(
                "x,observed,predicted,lower,upper,baseline\n"
                "1,2.1,2.0,1.7,2.3,1.8\n"
                "2,2.9,3.0,2.6,3.4,2.5\n"
                "3,4.2,4.0,3.5,4.5,3.4\n",
                encoding="utf-8",
            )
            output = root / "figures"
            script = FIGURE_TEMPLATES / "python" / "plot_prediction_interval.py"
            result = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--input",
                    str(evidence),
                    "--output-dir",
                    str(output),
                    "--stem",
                    "fixture",
                    "--x-label",
                    "Time",
                    "--x-unit",
                    "day",
                    "--y-label",
                    "Response",
                    "--y-unit",
                    "unit",
                ],
                capture_output=True,
                text=True,
                timeout=90,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for extension in ("pdf", "svg", "png"):
                self.assertGreater((output / f"fixture.{extension}").stat().st_size, 500)


class PaperMinerSkillTests(unittest.TestCase):
    def test_skill_metadata_and_card_template_validate(self) -> None:
        metadata = yaml.safe_load((MINER_SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8"))
        self.assertIn("$modeling-paper-miner", metadata["interface"]["default_prompt"])
        result = subprocess.run(
            [sys.executable, str(MINER_SKILL / "scripts" / "validate_paper_card.py"), str(MINER_SKILL / "assets" / "paper_card.template.json")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        schema = json.loads((MINER_SKILL / "assets" / "paper_card.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema_version"]["const"], "3.0")


if __name__ == "__main__":
    unittest.main()
