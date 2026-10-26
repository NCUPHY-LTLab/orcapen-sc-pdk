"""Build the authored Traditional Chinese edition beside the English output.

English source stays in docs/, Chinese prose in docs/zh-TW/. The theme and
generated API reference are shared build inputs, not a second editable copy.
"""

from __future__ import annotations

import copy
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

import yaml

LABELS = {
    "Get Started": "入門",
    "Simulation": "模擬",
    "Research": "研究",
    "Development": "開發",
    "API overview": "API 概覽",
    "Function index": "函式索引",
    "Package": "套件",
    "Cells": "元件",
    "Overview": "概覽",
    "Components": "元件指南",
    "All components": "所有元件",
    "Function references": "函式參考",
    "Materials & Interfaces": "材料與介面",
}


def localize_labels(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"text", "title", "section"} and isinstance(item, str):
                value[key] = LABELS.get(item, item)
            else:
                localize_labels(item)
    elif isinstance(value, list):
        for item in value:
            localize_labels(item)


def english_links(text: str, page: Path, authored: Path, base_path: str) -> str:
    """Send untranslated documentation links to the actual English edition."""

    def replace(match: re.Match[str], *, download: bool = False) -> str:
        target = match.group(2)
        parsed = urlsplit(target)
        if target.startswith("/orcapen-sc-pdk/") and base_path == "/":
            return match.group(1) + target.removeprefix("/orcapen-sc-pdk") + match.group(3)
        if parsed.scheme or parsed.netloc or target.startswith(("/", "#")):
            return match.group(0)
        relative = parsed.path
        if Path(relative).suffix not in {".md", ".qmd", ".ipynb", ".html", ".json"}:
            return match.group(0)
        destination = (page.parent / relative).resolve()
        equivalents = [destination]
        if destination.suffix == ".html":
            equivalents.extend(destination.with_suffix(suffix) for suffix in (".qmd", ".md"))
        if any(candidate.exists() for candidate in equivalents):
            return match.group(0)
        try:
            normalized = destination.relative_to(authored.resolve()).as_posix()
        except ValueError:
            return match.group(0)
        output = normalized if download else str(Path(normalized).with_suffix(".html"))
        if parsed.query:
            output += "?" + parsed.query
        if parsed.fragment:
            output += "#" + parsed.fragment
        return match.group(1) + base_path + "en/" + output + match.group(3)

    # Leave code fences untouched; only reader-facing Markdown links are routed.
    chunks = re.split(r"(^```[^\n]*\n.*?^```\s*$)", text, flags=re.M | re.S)
    for index in range(0, len(chunks), 2):
        chunks[index] = re.sub(r"(\]\()([^\s)]+)(\))", replace, chunks[index])
        chunks[index] = re.sub(
            r"""(href=["'])([^"']+)(["'])""",
            lambda match: replace(match, download=True),
            chunks[index],
        )
    return "".join(chunks)


def main() -> None:
    if os.environ.get("QUARTO_PROJECT_RENDER_ALL") != "1":
        return
    docs = Path(__file__).resolve().parents[1] / "docs"
    authored = docs / "zh-TW"
    config = yaml.safe_load((docs / "_quarto.yml").read_text())
    preview = "preview" in os.environ.get("QUARTO_PROFILE", "").split(",")
    base_path = "/" if preview else "/orcapen-sc-pdk/"
    english_output = docs / os.environ.get("QUARTO_PROJECT_OUTPUT_DIR", "_site/en")
    output = english_output.resolve().parent
    if english_output.resolve().name != "en":
        raise ValueError("English output must be the en/ directory of the bilingual site")
    if not (authored / "index.qmd").is_file():
        raise FileNotFoundError("The authored Traditional Chinese homepage is required")

    with tempfile.TemporaryDirectory(prefix="orcapen-zh-tw-") as temporary:
        staged = Path(temporary)
        shutil.copytree(authored, staged, dirs_exist_ok=True)
        for name in (
            "_extensions",
            "assets",
            "_static",
            "reference",
            "public-pdk-examples/cross-sections",
        ):
            source = docs / name
            if source.exists():
                shutil.copytree(source, staged / name, dirs_exist_ok=True)
        for name in ("styles.css", "askr-versions.json", "public-pdk-examples/cross-sections.svg"):
            shutil.copyfile(docs / name, staged / name)

        child = copy.deepcopy(config)
        child.pop("quartodoc", None)
        child.pop("profile", None)
        child["lang"] = "zh-TW"
        child["project"] = {
            "type": "website",
            "output-dir": "_site",
            "render": ["**/*.qmd", "**/*.md", "!_extensions/"],
            "resources": [
                "assets",
                "_static",
                "public-pdk-examples/cross-sections",
                "public-pdk-examples/cross-sections.svg",
                "askr-versions.json",
            ],
        }
        child["website"]["site-url"] = (
            "http://127.0.0.1:42635/"
            if preview
            else "https://ncuphy-ltlab.github.io/orcapen-sc-pdk/"
        )
        child["website"]["navbar"]["tools"][0].update(
            {"text": "GitHub 原始碼", "aria-label": "GitHub 原始碼"}
        )
        localize_labels(child["website"])
        child["askr"]["languages"] = {
            "current": "zh-TW",
            "items": [
                {"code": "zh-TW", "label": "繁體中文", "href": base_path},
                {"code": "en", "label": "English", "href": base_path + "en/"},
            ],
        }
        child["format"]["askr-html"]["toc-title"] = "本頁章節"
        for page in staged.rglob("*"):
            if page.suffix in {".qmd", ".md"} and "_extensions" not in page.parts:
                original = authored / page.relative_to(staged)
                page.write_text(english_links(page.read_text(), original, authored, base_path))
        (staged / "_quarto.yml").write_text(
            yaml.safe_dump(child, allow_unicode=True, sort_keys=False)
        )
        # The existing English output must survive the child project's render.
        subprocess.run(
            ["quarto", "render", str(staged), "--no-execute", "--no-clean"],
            check=True,
            env={
                key: value
                for key, value in os.environ.items()
                if key not in {"QUARTO_PROFILE", "QUARTO_PROJECT_OUTPUT_DIR"}
            },
        )
        shutil.copytree(staged / "_site", output, dirs_exist_ok=True)


if __name__ == "__main__":
    main()
