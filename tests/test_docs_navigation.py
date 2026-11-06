import tempfile
import unittest
from pathlib import Path

from scripts.check_docs_navigation import unreachable_pages


class DocsNavigationTests(unittest.TestCase):
    def test_unlinked_page_and_disconnected_cycle_are_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "index.html").write_text('<main><a href="guide.html">Guide</a></main>')
            (root / "guide.html").write_text('<main><a href="index.html">Home</a></main>')
            (root / "orphan.html").write_text("<main>Orphan</main>")
            (root / "a.html").write_text('<main><a href="b.html">B</a></main>')
            (root / "b.html").write_text('<main><a href="a.html">A</a></main>')
            self.assertEqual(unreachable_pages(root), ["a.html", "b.html", "orphan.html"])

    def test_menu_download_and_language_routes_are_distinct(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "en").mkdir()
            (root / "simulation").mkdir()
            (root / "index.html").write_text(
                '<main><a href="/orcapen-sc-pdk/simulation/cases.html#cases">Cases</a></main>'
            )
            (root / "simulation/cases.html").write_text(
                '<main><a href="../en/guide.html">English guide</a>'
                '<a href="data.tar.gz" download>Data</a></main>'
            )
            (root / "en/index.html").write_text("<main>English</main>")
            (root / "en/guide.html").write_text("<main>Guide</main>")
            (root / "redirect.html").write_text(
                '<meta http-equiv="refresh" content="0;url=index.html">'
            )
            self.assertEqual(unreachable_pages(root), [])

    def test_missing_homepage_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "homepage"):
                unreachable_pages(Path(temporary))


if __name__ == "__main__":
    unittest.main()
