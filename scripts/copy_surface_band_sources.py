"""Publish byte-identical raw downloads beside the rendered SurfaceBands pages."""

import os
import shutil
from pathlib import Path


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


if __name__ == "__main__":
    main()
