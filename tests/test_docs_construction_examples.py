"""Run each contributor-guide page's examples on their own, and keep both editions identical.

Every page under ``docs/contributing/`` that holds Python examples runs them in
order in a fresh namespace, so a page never depends on another. The examples
assert what their page claims, so a claim that stops holding fails here. The
sweeps that a page states in one sentence run here, on the page's own code.
The Traditional Chinese page must carry exactly the same code, and each edition
shows the same figures in its own language.

Run one page with ``uv run pytest tests/test_docs_construction_examples.py -k <page>``.
"""

import re
from functools import cache
from pathlib import Path

import pytest

DOCS = Path(__file__).parent.parent / "docs"
GUIDE = DOCS / "contributing"
CHINESE_GUIDE = DOCS / "zh-TW/contributing"
CODE_BLOCK = re.compile(r"^```python\n(.*?)^```", re.MULTILINE | re.DOTALL)
FIGURE = re.compile(r"!\[[^\]]*\]\(\.\./_static/images/contributing/([^/]+)/([^)\s]+)\)")

PAGES = sorted(path.stem for path in GUIDE.glob("*.md") if CODE_BLOCK.search(path.read_text()))
ANGLES = [step * 0.3 for step in range(1200)]  # 0° to 359.7° in 0.3° steps


def python_blocks(page: Path) -> list[str]:
    return CODE_BLOCK.findall(page.read_text(encoding="utf-8"))


@cache
def page_namespace(page: str) -> dict:
    """Run a page's examples once, in order, in a fresh namespace."""
    namespace = {"__name__": f"docs_{page}"}
    for block in python_blocks(GUIDE / f"{page}.md"):
        exec(block, namespace)
    return namespace


@pytest.mark.parametrize("page", PAGES)
def test_page_examples_run_on_their_own(page):
    page_namespace(page)


@pytest.mark.parametrize("page", PAGES)
def test_traditional_chinese_page_has_the_same_examples(page):
    assert python_blocks(CHINESE_GUIDE / f"{page}.md") == python_blocks(GUIDE / f"{page}.md")


@pytest.mark.parametrize("page", sorted(path.stem for path in GUIDE.glob("*.md")))
def test_both_editions_show_the_same_figures_in_their_language(page):
    english = FIGURE.findall((GUIDE / f"{page}.md").read_text(encoding="utf-8"))
    chinese = FIGURE.findall((CHINESE_GUIDE / f"{page}.md").read_text(encoding="utf-8"))
    assert {language for language, _ in english} <= {"en"}
    assert {language for language, _ in chinese} <= {"zh-TW"}
    assert [name for _, name in chinese] == [name for _, name in english]
    for language, name in english + chinese:
        assert (DOCS / "_static/images/contributing" / language / name).is_file(), name


def test_rotating_a_merged_outline_leaves_no_short_edge():
    """One outline (R4): the counts the page states for 1200 angles."""
    page = page_namespace("one-outline")
    short = page["short_edges"]
    assert sum(short(page["rotated_parts"](angle)) > 0 for angle in ANGLES) == 12
    assert sum(short(page["rotated_one_by_one"](angle)) > 0 for angle in ANGLES) == 28
    assert sum(short(page["rotated_outline"](angle)) > 0 for angle in ANGLES) == 0


def test_connecting_in_the_local_frame_then_rotating_never_splits():
    """Placement (R10): the counts the page states for 1200 angles."""
    page = page_namespace("placement")
    polygons = page["polygons"]
    assert sum(polygons(page["connected_at"](angle)) > 1 for angle in ANGLES) == 312
    for angle in ANGLES:
        outline = page["connected_then_rotated"](angle).get_region(page["LAYER"], merge=True)
        assert outline.count() == 1, angle
        assert outline.edges().with_length(0, 2, False).is_empty(), angle


def test_shared_vertices_add_no_short_edge_at_any_width():
    """Curves (R12): the 500 on-grid half widths the page states."""
    page = page_namespace("curves")
    for half_width in (round(0.04 * step, 3) for step in range(1, 501)):
        assert page["short_edges"](page["strip_on_shared_vertices"](half_width)).is_empty()
