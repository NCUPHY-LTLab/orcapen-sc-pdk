from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "copy_surface_band_sources", ROOT / "scripts/copy_surface_band_sources.py"
)
LINKS = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(LINKS)


class NotebookSiteLinkTests(unittest.TestCase):
    def test_rewrites_only_existing_same_directory_qmd_anchor_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            page = site / "index.html"
            peer = site / "aedt_hfss_eigenmode_prepare.html"
            peer.write_text("rendered peer")
            (site / "nested").mkdir()
            (site / "nested/page.html").write_text("nested peer")
            page.write_text(
                '<a href="aedt_hfss_eigenmode_prepare.qmd?run=1&amp;mode=analyze#direct">view</a>\n'
                '<a href="aedt_hfss_eigenmode_prepare.qmd" download>raw notebook</a>\n'
                '<a data-noresolveinput href="aedt_hfss_eigenmode_prepare.qmd">literal source</a>\n'
                '<a href="https://example.test/aedt_hfss_eigenmode_prepare.qmd">external</a>\n'
                '<a href="nested/page.qmd">nested source</a>\n'
                '<a href="absent.qmd">missing peer</a>\n'
                '<img src="aedt_hfss_eigenmode_prepare.qmd">\n'
            )

            LINKS.rewrite_sibling_qmd_links(site)

            result = page.read_text()
            self.assertIn(
                'href="aedt_hfss_eigenmode_prepare.html?run=1&amp;mode=analyze#direct"', result
            )
            self.assertIn('href="aedt_hfss_eigenmode_prepare.qmd" download', result)
            self.assertIn('data-noresolveinput href="aedt_hfss_eigenmode_prepare.qmd"', result)
            self.assertIn('href="https://example.test/aedt_hfss_eigenmode_prepare.qmd"', result)
            self.assertIn('href="nested/page.qmd"', result)
            self.assertIn('href="absent.qmd"', result)
            self.assertIn('src="aedt_hfss_eigenmode_prepare.qmd"', result)

    def test_leaves_page_unchanged_when_no_peer_link_needs_rewriting(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            page = site / "index.html"
            original = '<a href="missing.qmd?x=1#cell">source</a>'
            page.write_text(original)
            LINKS.rewrite_sibling_qmd_links(site)
            self.assertEqual(page.read_text(), original)

    def test_ignores_href_text_inside_another_attribute(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            page = site / "index.html"
            (site / "fake.html").write_text("fake")
            (site / "real.html").write_text("real")
            page.write_text("<a title=\"literal href='fake.qmd'\" href='real.qmd'>link</a>")

            LINKS.rewrite_sibling_qmd_links(site)

            self.assertEqual(
                page.read_text(), "<a title=\"literal href='fake.qmd'\" href='real.html'>link</a>"
            )


if __name__ == "__main__":
    unittest.main()
