"""Check that rendered content pages can be reached from the site homepages."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit


class PageLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.has_main = False
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "main":
            self.has_main = True
        if tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"])


def unreachable_pages(site: Path, prefix: str = "/orcapen-sc-pdk/") -> list[str]:
    prefix = "/" + prefix.strip("/") + "/" if prefix.strip("/") else "/"
    graph: dict[str, set[str]] = {}
    for path in site.rglob("*.html"):
        relative = path.relative_to(site).as_posix()
        parser = PageLinks()
        parser.feed(path.read_text(encoding="utf-8"))
        if not parser.has_main:
            continue
        targets = set()
        for href in parser.links:
            target = urlsplit(urljoin("https://docs.invalid" + prefix + relative, href))
            if target.netloc != "docs.invalid" or not target.path.startswith(prefix):
                continue
            destination = unquote(target.path[len(prefix) :])
            if destination.endswith("/") or not destination:
                destination += "index.html"
            targets.add(destination)
        graph[relative] = targets
    if "index.html" not in graph:
        raise ValueError(f"missing rendered homepage: {site / 'index.html'}")
    pending = [name for name in ("index.html", "en/index.html") if name in graph]
    visited: set[str] = set()
    while pending:
        page = pending.pop()
        if page not in visited:
            visited.add(page)
            pending.extend(graph.get(page, set()) - visited)
    return sorted(set(graph) - visited)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    parser.add_argument("--prefix", default="/orcapen-sc-pdk/")
    args = parser.parse_args()
    missing = unreachable_pages(args.site, args.prefix)
    if missing:
        print("Content pages without a navigation path from the homepages:")
        print("\n".join(missing))
        return 1
    print("PASS: every rendered content page is reachable from a homepage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
