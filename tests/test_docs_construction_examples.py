"""Run the construction-rule examples in the developer guide and keep both editions identical."""

import re
from pathlib import Path

DOCS = Path(__file__).parent.parent / "docs"
SECTION_POSITION = 3  # "Build cell geometry" is the fourth "## " heading on both pages
CODE_BLOCK = re.compile(r"^```python\n(.*?)^```", re.MULTILINE | re.DOTALL)


def python_blocks(page):
    sections = re.split(r"^## ", (DOCS / page).read_text(encoding="utf-8"), flags=re.MULTILINE)
    return CODE_BLOCK.findall(sections[SECTION_POSITION + 1])


def test_construction_examples_run_in_order():
    namespace = {}  # the examples build on each other
    for block in python_blocks("developing-features.md"):
        exec(block, namespace)


def test_traditional_chinese_page_has_the_same_examples():
    assert python_blocks("zh-TW/developing-features.md") == python_blocks("developing-features.md")
