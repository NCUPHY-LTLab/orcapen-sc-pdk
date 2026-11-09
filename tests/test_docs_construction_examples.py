"""Run the construction-rule examples in the developer guide and keep both editions identical."""

import re
from pathlib import Path

DOCS = Path(__file__).parent.parent / "docs"
CODE_BLOCK = re.compile(r"^```python\n(.*?)^```", re.MULTILINE | re.DOTALL)


def python_blocks(page, heading):
    """Python blocks between ``## <heading>`` and the next ``## `` heading."""
    text = (DOCS / page).read_text(encoding="utf-8")
    section = re.search(
        rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL
    )
    assert section, f"{page} has no '## {heading}' section"
    blocks = CODE_BLOCK.findall(section.group(1))
    assert blocks, f"'## {heading}' in {page} has no Python examples"
    return blocks


ENGLISH = ("developing-features.md", "Build cell geometry")
TRADITIONAL_CHINESE = ("zh-TW/developing-features.md", "建構 cell 幾何")


def test_construction_examples_run_in_order():
    namespace = {}  # the examples build on each other
    for block in python_blocks(*ENGLISH):
        exec(block, namespace)


def test_traditional_chinese_page_has_the_same_examples():
    assert python_blocks(*TRADITIONAL_CHINESE) == python_blocks(*ENGLISH)
