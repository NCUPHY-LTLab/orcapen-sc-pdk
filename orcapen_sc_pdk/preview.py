"""Show an OrcaPen component in GDSFactory+ when available, otherwise in KLayout.

This module owns the developer preview entry point used by each cell module's
`if __name__ == "__main__":` block and by `python -m orcapen_sc_pdk.preview`.
It does not own component geometry or the GDSFactory+ project discovery, which
the extension performs on its own from `[tool.gdsfactoryplus]`.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path
from typing import Literal

from gdsfactory.typings import ComponentSpec

from orcapen_sc_pdk.pdk import PDK

Viewer = Literal["auto", "gdsfactoryplus", "klayout"]

GDSFACTORYPLUS_EXTENSION_ID = "gdsfactory.gdsfactoryplus"
PREVIEW_GDS_DIRECTORY = Path("build/gds")


def show(component: ComponentSpec, viewer: Viewer = "auto") -> Path:
    """Build a component with the OrcaPen PDK, write its GDS and open it.

    `viewer="auto"` opens the GDS in the GDSFactory+ Layout Viewer when this runs
    in a VS Code terminal that has the extension, and streams it to KLayout
    otherwise. KLayout needs the klive plugin running to receive it.
    """

    PDK.activate()
    built = PDK.get_component(component)
    # One file per factory, so a rebuilt preview replaces the open viewer tab.
    gds_path = built.write_gds(PREVIEW_GDS_DIRECTORY / f"{built.function_name or built.name}.gds")
    print(f"Wrote {gds_path}", flush=True)

    if viewer == "auto":
        viewer = "gdsfactoryplus" if gdsfactoryplus_is_available() else "klayout"
    if viewer == "gdsfactoryplus":
        subprocess.run(["code", "--reuse-window", str(gds_path)], check=True)
    else:
        # kfactory only logs a warning when nothing listens on the klive port.
        print("Sent to KLayout through klive; open the GDS file if no window appears.")
        built.show()
    return gds_path


def gdsfactoryplus_is_available() -> bool:
    """Return whether a VS Code window with GDSFactory+ can open the GDS file."""

    # VS Code sets TERM_PROGRAM in its integrated terminal, where `code` reaches
    # the current window, including over Remote SSH.
    if os.environ.get("TERM_PROGRAM") != "vscode" or shutil.which("code") is None:
        return False
    extensions = subprocess.run(
        ["code", "--list-extensions"], capture_output=True, text=True, check=False
    ).stdout.split()
    return GDSFACTORYPLUS_EXTENSION_ID in (name.lower() for name in extensions)


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("cell", help="registered PDK cell name, for example `resonator`")
    parser.add_argument("--viewer", choices=["auto", "gdsfactoryplus", "klayout"], default="auto")
    arguments = parser.parse_args()
    show(arguments.cell, viewer=arguments.viewer)


if __name__ == "__main__":
    _main()
