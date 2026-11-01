import unittest
from pathlib import Path
import yaml


ROOT = Path(__file__).parents[1]


class DocsVersioningTests(unittest.TestCase):
    def test_case_downloads_have_one_reader_page_per_language(self):
        docs = ROOT / "docs"
        config = yaml.safe_load((docs / "_quarto.yml").read_text())
        menus = str(config["website"]["sidebar"])
        self.assertEqual(menus.count("simulation/recorded-cases.qmd"), 1)
        self.assertNotIn("simulation/reproducibility.qmd", menus)
        for language in ("", "zh-TW"):
            page = docs / language / "simulation/recorded-cases.qmd"
            text = page.read_text()
            metadata = yaml.safe_load(text.split("---", 2)[1])
            self.assertIn("reproducibility.html", metadata["aliases"])
            self.assertFalse((page.parent / "reproducibility.qmd").exists())
            rows = [line for line in text.splitlines() if line.startswith("| ")]
            case_rows = [line for line in rows if "⏳" in line]
            self.assertEqual(len(case_rows), 19)
            self.assertEqual(sum("✅" in row for row in case_rows), 11)
            self.assertEqual(sum("⚠️" in row for row in case_rows), 8)
            self.assertTrue(all("Run ID" not in row and "執行識別碼" not in row for row in rows))
            self.assertTrue(all("⏳" in row.split("|")[-2] for row in case_rows))
            self.assertNotIn("/blob/v1.0.0/", text)
            self.assertNotIn("/releases/tag/v1.0.0", text)
            self.assertEqual(text.count("/evidence/run_set.json)"), 3)

    def test_authored_area_pages_are_in_their_page_lists(self):
        docs = ROOT / "docs"
        config = yaml.safe_load((docs / "_quarto.yml").read_text())

        def entries(items):
            for item in items:
                if isinstance(item, str):
                    yield item
                else:
                    if "href" in item:
                        yield item["href"]
                    yield from entries(item.get("contents", []))

        menus = {
            menu["id"]: set(entries(menu["contents"])) for menu in config["website"]["sidebar"]
        }
        for source in docs.rglob("*"):
            relative = source.relative_to(docs).as_posix()
            if source.suffix not in {".md", ".qmd"} or relative.startswith(
                ("_", "zh-TW/", "reference/")
            ):
                continue
            text = source.read_text()
            if not text.startswith("---\n"):
                continue
            metadata = yaml.safe_load(text.split("---", 2)[1]) or {}
            area = metadata.get("sidebar")
            if isinstance(area, str) and area in menus:
                with self.subTest(page=relative, area=area):
                    self.assertIn(relative, menus[area])

    def test_primary_simulation_guides_share_collapsed_tutorial_section(self):
        docs = ROOT / "docs"
        config = yaml.safe_load((docs / "_quarto.yml").read_text())
        simulation = next(
            menu for menu in config["website"]["sidebar"] if menu["id"] == "simulation"
        )
        expected = [
            "simulation/requirements/electrostatic-capacitance.qmd",
            "simulation/requirements/eigenmode.qmd",
            "simulation/requirements/driven-terminal.qmd",
            "simulation/requirements/q2d-cross-section.qmd",
            "simulation/requirements/epr-loss.qmd",
        ]
        section = next(
            item
            for item in simulation["contents"]
            if isinstance(item, dict) and item.get("section") == "Simulation tutorials"
        )
        self.assertEqual(
            (section["contents"], [item for item in simulation["contents"] if item in expected]),
            (expected, []),
        )

    def test_pages_workflow_keeps_strict_notebook_check_and_render(self):
        workflow = (ROOT / ".github/workflows/pages.yml").read_text()
        self.assertIn("uv sync -p 3.12 --locked --group docs --extra dev", workflow)
        self.assertIn("scripts/sync_qmd_notebooks.py notebooks/src notebooks", workflow)
        self.assertIn("uv run --group docs quarto render docs --no-execute", workflow)
        self.assertNotIn("--check", workflow)
        self.assertNotIn("just docs", workflow)
        self.assertIn("draft", workflow)
        self.assertIn("refs/heads/main", workflow)

    def test_release_reuses_exact_sha_pages_artifact(self):
        workflow = (ROOT / ".github/workflows/release.yml").read_text()
        self.assertIn("r.head_sha === context.sha", workflow)
        self.assertIn('workflow_id: "pages.yml"', workflow)
        self.assertIn("name: docs-site", workflow)
        self.assertNotIn("quarto render", workflow)
        self.assertNotIn("uv sync", workflow)


if __name__ == "__main__":
    unittest.main()
