"""Extract README installation and actual LayerMap source for both doc editions."""

import ast
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    readme = (root / "README.md").read_text()
    begin = "<!-- overview-install:start -->"
    end = "<!-- overview-install:end -->"
    if readme.count(begin) != 1 or readme.count(end) != 1:
        raise ValueError("README must contain exactly one marked installation block")
    install = readme.split(begin)[1].split(end)[0].strip()
    if not install.startswith("```bash\n") or not install.endswith("```"):
        raise ValueError("README installation block must be a complete bash fence")
    source = (root / "orcapen_sc_pdk/tech.py").read_text()
    layer_map = next(
        node for node in ast.parse(source).body
        if isinstance(node, ast.ClassDef) and node.name == "LayerMapOrpenSCPDK"
    )
    fields = {
        node.target.id: node for node in layer_map.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }
    start = fields["D0_BOTTOM_M1_DRAW"].lineno - 1
    stop = fields["D0_D1_UNDER_BUMP"].end_lineno
    excerpt = "\n".join(source.splitlines()[start:stop]) + "\n"
    output = root / "docs/_includes"
    output.mkdir(parents=True, exist_ok=True)
    (output / "_readme-install.md").write_text(install + "\n")
    (output / "_layer-map.py").write_text(excerpt)


if __name__ == "__main__":
    main()
