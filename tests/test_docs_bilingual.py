"""Keep language routing separate from source code and raw downloads."""

import tempfile
import unittest
from pathlib import Path

from scripts.build_bilingual_docs import (
    english_links,
    localize_labels,
    route_untranslated_navigation,
)


class BilingualDocsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.authored = Path(self.temporary.name)
        self.page = self.authored / "simulation" / "guide.qmd"
        self.page.parent.mkdir()
        self.page.touch()

    def route(self, text, prefix="/orcapen-sc-pdk/"):
        return english_links(text, self.page, self.authored, prefix)

    def test_translated_page_and_anchor_stay_in_current_language(self):
        (self.authored / "start.qmd").touch()
        text = "[Start](../start.qmd#setup) and [Start HTML](../start.html#setup)"
        self.assertEqual(self.route(text), text)

    def test_english_tutorial_view_and_raw_download_are_distinct(self):
        text = (
            "[View](../notebooks/run.ipynb#results) "
            '<a href="../notebooks/run.ipynb" download>IPYNB</a>'
        )
        result = self.route(text)
        self.assertIn("[View](../en/notebooks/run.html#results)", result)
        self.assertIn('href="../en/notebooks/run.ipynb"', result)

    def test_preview_prefix_and_model_download(self):
        text = (
            "[API](/orcapen-sc-pdk/en/reference/api.html) "
            '<a href="../notebooks/model.json" download>JSON</a>'
        )
        result = self.route(text, "/")
        self.assertIn("[API](../en/reference/api.html)", result)
        self.assertIn('href="../en/notebooks/model.json"', result)

    def test_nested_root_and_english_links_work_below_any_mount(self):
        self.page = self.authored / "simulation/requirements/guide.qmd"
        text = "[API](/orcapen-sc-pdk/en/reference/api.html#signature)"
        expected = "[API](../../en/reference/api.html#signature)"
        self.assertEqual(self.route(text), expected)
        self.assertEqual(self.route(text, "/"), expected)

    def test_code_and_external_links_are_unchanged(self):
        text = (
            '```python\nurl = "[Run](../notebooks/run.ipynb)"\n```\n[Quarto](https://quarto.org/)'
        )
        self.assertEqual(self.route(text), text)

    def test_only_navigation_labels_are_localized(self):
        navigation = {
            "text": "Get Started",
            "href": "Get Started",
            "contents": [{"section": "Cells"}],
        }
        localize_labels(navigation)
        self.assertEqual(
            navigation, {"text": "入門", "href": "Get Started", "contents": [{"section": "元件"}]}
        )

    def test_missing_translation_uses_the_existing_english_page(self):
        english = self.authored / "english"
        (english / "usage").mkdir(parents=True)
        (english / "usage/index.md").write_text("# Package usage\n")
        (english / "start.qmd").write_text("---\ntitle: Start\n---\n")
        (self.authored / "start.qmd").touch()
        navigation = ["usage/index.md", "start.qmd", {"href": "usage/index.md#setup"}]
        route_untranslated_navigation(navigation, self.authored, english)
        self.assertEqual(
            navigation[0], {"text": "Package usage（英文）", "href": "en/usage/index.html"}
        )
        self.assertEqual(navigation[1], "start.qmd")
        self.assertEqual(navigation[2]["href"], "en/usage/index.html#setup")


if __name__ == "__main__":
    unittest.main()
