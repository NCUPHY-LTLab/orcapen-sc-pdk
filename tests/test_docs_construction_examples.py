"""Run each contributor-guide page's examples on their own, and keep both editions identical.

Every page under ``docs/contributing/`` that holds Python examples runs them in
order in a fresh namespace, so a page never depends on another. The examples
assert what their page claims, so a claim that stops holding fails here. The
Traditional Chinese page must carry exactly the same code.
"""

import re
from pathlib import Path

import pytest

DOCS = Path(__file__).parent.parent / "docs"
GUIDE = DOCS / "contributing"
CODE_BLOCK = re.compile(r"^```python\n(.*?)^```", re.MULTILINE | re.DOTALL)
FIGURE = re.compile(r"!\[[^\]]*\]\((\.\./_static/images/contributing/[^)\s]+)\)")

PAGES = sorted(path.name for path in GUIDE.glob("*.md") if CODE_BLOCK.search(path.read_text()))


def python_blocks(page: Path) -> list[str]:
    return CODE_BLOCK.findall(page.read_text(encoding="utf-8"))


def test_the_guide_has_example_pages():
    assert len(PAGES) == 8, PAGES


@pytest.mark.parametrize("page", PAGES)
def test_page_examples_run_on_their_own(page):
    namespace = {"__name__": f"docs_{page}"}
    for block in python_blocks(GUIDE / page):
        exec(block, namespace)


@pytest.mark.parametrize("page", PAGES)
def test_traditional_chinese_page_has_the_same_examples(page):
    assert python_blocks(DOCS / "zh-TW/contributing" / page) == python_blocks(GUIDE / page)


@pytest.mark.parametrize("page", sorted(path.name for path in GUIDE.glob("*.md")))
def test_both_editions_show_the_same_figures(page):
    english = FIGURE.findall((GUIDE / page).read_text(encoding="utf-8"))
    chinese = FIGURE.findall((DOCS / "zh-TW/contributing" / page).read_text(encoding="utf-8"))
    assert chinese == english
    for figure in english:
        assert (GUIDE / figure).resolve().is_file(), figure
