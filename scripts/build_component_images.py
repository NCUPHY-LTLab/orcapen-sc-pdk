"""Redraw the default-layout images in docs/_static/images/components/.

Each image is drawn from the registered cell at its default parameters, as XY
polygons of the fabrication layers (metal DRAW/ETCH, junction, airbridge and
indium layers). Ground masks, simulation boundaries and other helper layers are
not drawn. Output is deterministic, so re-running leaves no diff.

    uv run python scripts/build_component_images.py [CELL ...]
"""

from __future__ import annotations

import sys
from pathlib import Path

import gdsfactory as gf
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, PathPatch
from matplotlib.path import Path as MplPath

from orcapen_sc_pdk.pdk import PDK, activate
from orcapen_sc_pdk.tech import LAYER

plt.switch_backend("Agg")

OUTPUT = Path(__file__).resolve().parents[1] / "docs/_static/images/components"

CELLS = (
    "disk_flip_chip_qubit",
    "kosen2024_flip_chip_xmon_qubit",
    "manhattan_style_junction",
    "resonator",
    "resonator_hanger",
    "resonator_meander",
    "capacitive_coupling_intrinsic_individual_purcell_filter_readout_resonators",
    "interdigital_capacitor",
    "martinis2022_differential_ribbon_capacitor",
    "launcher",
    "taper",
    "cpw_t_junction",
    "airbridge",
    "n_trace_mtl_section",
    "mtl_bend_coupling_section",
    "mtl_straight_bend_coupling_section",
    "mtl_straight_bend_transition",
    "mtl_bend_bend_transition",
    "indium_bump",
    "indium_ground",
    "dicing_edge",
)

# Fabrication layers only: (fill colour, fill opacity, edge colour, draw order).
# Lower order is drawn first, so etched areas sit below the metal they surround.
METAL_DRAW = ("#0f766e", 1.0, "none", 2)
METAL_ETCH = ("#b2dfd9", 0.65, "none", 1)
AIRBRIDGE_DRAW = ("#7a4fa3", 1.0, "none", 3)
AIRBRIDGE_VIA = ("#d6c8e6", 0.65, "none", 1)
JUNCTION = ("#c0262d", 1.0, "none", 4)
INDIUM_BUMP = ("#888888", 1.0, "#555555", 3)
UNDER_BUMP = ("#c9d3dc", 0.65, "#555555", 2)

STYLES = {
    "D0_TOP_M1_DRAW": METAL_DRAW,
    "D0_TOP_M1_ETCH": METAL_ETCH,
    "D1_BOTTOM_M1_DRAW": METAL_DRAW,
    "D1_BOTTOM_M1_ETCH": METAL_ETCH,
    "D0_TOP_AB_DRAW": AIRBRIDGE_DRAW,
    "D0_TOP_AB_VIA": AIRBRIDGE_VIA,
    "D1_BOTTOM_JJ_DRAW": JUNCTION,
    "D0_TOP_JJ_DRAW": JUNCTION,
    "D0_D1_INDIUM_BUMP": INDIUM_BUMP,
    "D0_D1_UNDER_BUMP": UNDER_BUMP,
}

# Cells whose layers sit on two dies are drawn as one panel per die.
PANELS = {
    "disk_flip_chip_qubit": (
        ("Qubit die, D1_BOTTOM", ("D1_BOTTOM_M1_DRAW", "D1_BOTTOM_JJ_DRAW")),
        ("Control die, D0_TOP", ("D0_TOP_M1_DRAW", "D0_D1_UNDER_BUMP", "D0_D1_INDIUM_BUMP")),
    ),
}


def layer_names() -> dict[tuple[int, int], str]:
    return {tuple(gf.get_layer_tuple(member)): member.name for member in LAYER}


def legend_label(name: str, layer: tuple[int, int]) -> str:
    # The metal layers keep the short DRAW/ETCH names of the first images.
    shown = name.rsplit("_", 1)[1] if "_M1_" in name else name.replace("_", " ")
    return f"{shown} {layer[0]}/{layer[1]}"


def to_path(polygon, dbu: float) -> MplPath:
    """One polygon, hull first and holes after, in micrometres."""
    dpolygon = polygon.to_dtype(dbu)
    rings = [list(dpolygon.each_point_hull())]
    rings += [list(dpolygon.each_point_hole(i)) for i in range(dpolygon.holes())]
    vertices, codes = [], []
    for ring in rings:
        points = [(point.x, point.y) for point in ring]
        vertices += points + [points[0]]
        codes += [MplPath.MOVETO] + [MplPath.LINETO] * (len(points) - 1) + [MplPath.CLOSEPOLY]
    return MplPath(vertices, codes)


def layers_to_draw(component, names, wanted=None):
    """Fabrication layers present in the cell, ordered bottom to top."""
    polygons = component.get_polygons(by="tuple")
    found = []
    for layer, shapes in polygons.items():
        name = names.get(layer)
        if name in STYLES and (wanted is None or name in wanted):
            found.append((STYLES[name][3], layer, name, shapes))
    return sorted(found, key=lambda item: (item[0], item[1]))


def draw_panel(axes, component, names, title, wanted=None):
    handles = []
    for _, layer, name, shapes in layers_to_draw(component, names, wanted):
        fill, opacity, edge, _ = STYLES[name]
        compound = MplPath.make_compound_path(
            *(to_path(shape, component.kcl.dbu) for shape in shapes)
        )
        face = matplotlib.colors.to_rgba(fill, opacity)
        axes.add_patch(PathPatch(compound, facecolor=face, edgecolor=edge, linewidth=0.4))
        handles.append(Patch(facecolor=face, edgecolor=edge, label=legend_label(name, layer)))
    axes.autoscale_view()
    axes.set_aspect("equal")
    axes.set_title(title, fontsize=10)
    axes.set_xlabel("X (µm)")
    axes.set_ylabel("Y (µm)")
    axes.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.14),
        ncol=min(len(handles), 2),
        frameon=False,
    )


def draw_cell(cell_name: str, names) -> Path:
    component = PDK.get_component(cell_name)
    panels = PANELS.get(cell_name, ((cell_name, None),))
    figure, axes_list = plt.subplots(1, len(panels), figsize=(6 * len(panels), 6), squeeze=False)
    for axes, (title, wanted) in zip(axes_list[0], panels, strict=True):
        draw_panel(axes, component, names, title, wanted)
    figure.tight_layout()
    path = OUTPUT / f"{cell_name}.svg"
    figure.savefig(
        path,
        format="svg",
        metadata={
            "Date": None,
            "Description": f"{cell_name} default public source XY polygons. "
            "Not native simulation evidence.",
        },
    )
    plt.close(figure)
    return path


def main(cell_names: list[str]) -> None:
    activate()
    # Fonts stay text and element ids stay stable between runs.
    plt.rcParams.update({"svg.fonttype": "none", "svg.hashsalt": "orcapen-sc-pdk"})
    names = layer_names()
    for cell_name in cell_names or CELLS:
        print(draw_cell(cell_name, names))


if __name__ == "__main__":
    main(sys.argv[1:])
