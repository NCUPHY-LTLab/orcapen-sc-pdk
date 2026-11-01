"""Publish byte-identical raw downloads beside the rendered SurfaceBands pages."""

import os
import shutil
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


def _attribute_value_span(tag_text: str, wanted: str) -> tuple[int, int] | None:
    """Return the raw value span for a real attribute token in a start tag."""
    length = len(tag_text)
    index = 1  # opening '<'
    while index < length and not tag_text[index].isspace() and tag_text[index] not in "/>":
        index += 1  # tag name
    while index < length:
        while index < length and (tag_text[index].isspace() or tag_text[index] == "/"):
            index += 1
        if index >= length or tag_text[index] == ">":
            return None
        name_start = index
        while index < length and not tag_text[index].isspace() and tag_text[index] not in "=/>":
            index += 1
        name = tag_text[name_start:index].lower()
        while index < length and tag_text[index].isspace():
            index += 1
        if index >= length or tag_text[index] != "=":
            continue
        index += 1
        while index < length and tag_text[index].isspace():
            index += 1
        if index >= length:
            return None
        if tag_text[index] in "\"'":
            quote = tag_text[index]
            start = index + 1
            end = tag_text.find(quote, start)
            if end < 0:
                return None
            index = end + 1
        else:
            start = index
            while index < length and not tag_text[index].isspace() and tag_text[index] != ">":
                index += 1
            end = index
        if name == wanted.lower():
            return start, end
    return None


class _SiblingQmdLinkRewriter(HTMLParser):
    def __init__(self, html_path: Path, text: str) -> None:
        super().__init__(convert_charrefs=False)
        self.html_path = html_path
        self.text = text
        self.line_offsets = [0]
        self.line_offsets.extend(index + 1 for index, char in enumerate(text) if char == "\n")
        self.replacements: list[tuple[int, int, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attribute_names = {name.lower() for name, _ in attrs}
        if "download" in attribute_names or "data-noresolveinput" in attribute_names:
            return
        href = next((value for name, value in attrs if name.lower() == "href"), None)
        if not href:
            return
        parsed = urlsplit(href)
        if parsed.scheme or parsed.netloc or not parsed.path.endswith(".qmd") or "/" in parsed.path:
            return
        peer = self.html_path.parent / Path(parsed.path).with_suffix(".html")
        if not peer.is_file():
            return
        tag_text = self.get_starttag_text()
        if not tag_text:
            return
        value_span = _attribute_value_span(tag_text, "href")
        if not value_span:
            return
        value_start, value_end = value_span
        raw_value = tag_text[value_start:value_end]
        raw_path_end = min(
            (position for position in (raw_value.find("?"), raw_value.find("#")) if position >= 0),
            default=len(raw_value),
        )
        raw_path = raw_value[:raw_path_end]
        if not raw_path.endswith(".qmd"):
            return
        replacement_value = raw_path[:-4] + ".html" + raw_value[raw_path_end:]
        start_line, start_column = self.getpos()
        tag_offset = self.line_offsets[start_line - 1] + start_column
        value_offset = tag_offset + value_start
        self.replacements.append((value_offset, value_offset + len(raw_value), replacement_value))


def rewrite_sibling_qmd_links(output_dir: Path) -> None:
    """Point rendered anchors at rendered same-directory pages, preserving URL suffixes."""
    for html_path in output_dir.rglob("*.html"):
        original = html_path.read_text(encoding="utf-8")
        parser = _SiblingQmdLinkRewriter(html_path, original)
        parser.feed(original)
        updated = original
        for start, end, replacement in reversed(parser.replacements):
            updated = updated[:start] + replacement + updated[end:]
        if updated != original:
            html_path.write_text(updated, encoding="utf-8")


def main() -> None:
    docs_dir = Path(__file__).resolve().parents[1] / "docs"
    # Quarto output paths are relative to its project directory, not the caller.
    output_dir = docs_dir / os.environ["QUARTO_PROJECT_OUTPUT_DIR"]
    source_paths = (
        "notebooks/src/SCGSimExamples/SurfaceBands/SimplePad/aedt_q2d_interfaces.qmd",
        "notebooks/src/SCGSimExamples/SurfaceBands/SimplePad/palace_eigenmode_bands.qmd",
    )
    for relative in source_paths:
        destination = output_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(docs_dir / relative, destination)
    rewrite_sibling_qmd_links(output_dir)


if __name__ == "__main__":
    main()
