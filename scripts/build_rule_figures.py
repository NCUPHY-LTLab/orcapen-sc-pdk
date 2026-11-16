"""Redraw the construction-rule figures in docs/_static/images/contributing/.

Every figure is drawn from the code of its page in docs/contributing/: this
script runs a page's Python examples, in order, exactly as
tests/test_docs_construction_examples.py does, and draws the builds that the
figure names. Each rule gets a problem figure and a result figure. A drawing
shows the merged layer, one colour per merged polygon, with holes left open,
defects marked with red circles, and a panel on the right that zooms on the
defect. The result figure zooms on the same place as its problem figure.
Output is deterministic, so re-running leaves no diff.

    uv run python scripts/build_rule_figures.py [RULE ...]
"""

from __future__ import annotations

import math
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import gdsfactory as gf
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrow, PathPatch
from matplotlib.path import Path as MplPath
from matplotlib.ticker import MaxNLocator

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs/contributing"
OUTPUT = ROOT / "docs/_static/images/contributing"
CODE_BLOCK = re.compile(r"^```python\n(.*?)^```", re.MULTILINE | re.DOTALL)

POLYGON_COLOURS = ("#0f766e", "#d97706", "#7c3aed", "#2563eb", "#be185d")
DEFECT = "#dc2626"
INTENDED = "#334155"
TARGET_PORT = "#94a3b8"
LAYER_COLOURS = {"DRAW": "#0f766e", "GROUND_MASK": "#cbd5e1", "ETCH": "#f59e0b"}


@dataclass
class Scene:
    """What one figure draws, in DBU regions and micrometre points."""

    conductors: list[gf.kdb.Region] = field(default_factory=list)
    layers: list[tuple[str, gf.kdb.Region]] = field(default_factory=list)
    intended: list[gf.kdb.Region] = field(default_factory=list)
    difference: gf.kdb.Region | None = None
    markers: list[tuple[float, float]] = field(default_factory=list)
    ports: list[tuple[float, float, float, str]] = field(
        default_factory=list
    )  # x, y, angle, colour


@dataclass(frozen=True)
class RulePair:
    """A rule's problem and result builds, and the half width of the zoom on the defect."""

    rule: str
    page: str
    problem: Callable[[dict], Scene]
    result: Callable[[dict], Scene]
    zoom_half_width_um: float | None = None


def main(rules: list[str]) -> None:
    sys.path.insert(0, str(ROOT / "tests"))  # the pages import geometry_checks
    plt.rcParams.update({"svg.fonttype": "none", "svg.hashsalt": "orcapen-sc-pdk", "font.size": 9})
    OUTPUT.mkdir(parents=True, exist_ok=True)
    namespaces: dict[str, dict] = {}
    for pair in PAIRS:
        if rules and pair.rule not in rules:
            continue
        namespace = namespaces.setdefault(pair.page, run_page(GUIDE / pair.page))
        problem, result = pair.problem(namespace), pair.result(namespace)
        centre = problem.markers[0] if problem.markers and pair.zoom_half_width_um else None
        for kind, scene in (("problem", problem), ("result", result)):
            path = OUTPUT / f"{pair.rule}-{kind}.svg"
            draw(scene, centre, pair.zoom_half_width_um, path)
            print(path.relative_to(ROOT))


def run_page(page: Path) -> dict:
    """Run a page's examples in order in a fresh namespace, as its test does."""
    namespace: dict = {"__name__": f"docs_{page.name}"}
    for block in CODE_BLOCK.findall(page.read_text(encoding="utf-8")):
        exec(block, namespace)
    return namespace


# Finding what to mark --------------------------------------------------------


def merged(component: gf.Component, layer=(1, 0)) -> gf.kdb.Region:
    return component.get_region(layer, merge=True)


def to_um(point: gf.kdb.Point) -> tuple[float, float]:
    return point.x * gf.kcl.dbu, point.y * gf.kcl.dbu


def short_edge_points(region: gf.kdb.Region) -> list[tuple[float, float]]:
    """Midpoints of the edges shorter than 2 DBU."""
    edges = region.edges().with_length(0, 2, False)
    return [
        to_um(gf.kdb.Point((e.p1.x + e.p2.x) // 2, (e.p1.y + e.p2.y) // 2)) for e in edges.each()
    ]


def gap_points(region: gf.kdb.Region) -> list[tuple[float, float]]:
    """Where separate polygons come within 5 DBU of each other."""
    polygons = [gf.kdb.Region(polygon) for polygon in region.each()]
    points = []
    for index, first in enumerate(polygons):
        for second in polygons[index + 1 :]:
            for pair in first.separation_check(second, 5).each():
                edge = pair.first
                points.append(
                    to_um(gf.kdb.Point((edge.p1.x + edge.p2.x) // 2, (edge.p1.y + edge.p2.y) // 2))
                )
    return points


def hole_points(region: gf.kdb.Region) -> list[tuple[float, float]]:
    return [to_um(hole.bbox().center()) for hole in region.holes().each()]


def repeated_vertex_points(region: gf.kdb.Region) -> list[tuple[float, float]]:
    points = []
    for polygon in region.each():
        hull = [(p.x, p.y) for p in polygon.each_point_hull()]
        points += [
            to_um(gf.kdb.Point(*xy)) for xy in sorted(set(xy for xy in hull if hull.count(xy) > 1))
        ]
    return points


def area_centres(region: gf.kdb.Region) -> list[tuple[float, float]]:
    return [to_um(polygon.bbox().center()) for polygon in region.each()]


def conductor(component, find=None) -> Scene:
    region = merged(component)
    return Scene(conductors=[region], markers=find(region) if find else [])


# The figures, page by page ---------------------------------------------------


def r9(ns, on_grid):
    lengths = (10.0, 5.0) if on_grid else (10.0004, 5.0004)
    return conductor(ns["pad_lead_pad"](*lengths), gap_points)


def r10(ns, overlap):
    return conductor(ns["two_pads"](overlap), repeated_vertex_points)


def r11(ns, spine):
    return conductor(ns["comb"](spine))


def r1(ns, build):
    return conductor(ns[build](76.5), short_edge_points)


def r6(ns, kind):
    notches = ns["round_then_join"] ^ ns["join_then_round"]
    if kind == "problem":
        return Scene(conductors=[ns["round_then_join"]], markers=area_centres(notches)[:1])
    return Scene(conductors=[ns["square_end"]])


def r12(ns, kind):
    intended = merged(ns["ground_from_shapes"]())
    if kind == "problem":
        reversed_clearance = ns["CLEARANCE"][::-1]
        return Scene(
            conductors=[merged(ns["ground_from_points"](reversed_clearance))], intended=[intended]
        )
    return Scene(conductors=[intended])


def r2(ns, about_centre):
    placed, _ = ns["turned"](about_centre)
    meant, _ = ns["turned"](True)
    return Scene(conductors=[merged(placed)], intended=[] if about_centre else [merged(meant)])


def port_arrow(port, colour=INTENDED) -> tuple[float, float, float, str]:
    return port.dcenter[0], port.dcenter[1], port.orientation, colour


def r4(ns, kind):
    if kind == "problem":
        scenes = [ns["mirrored_and_rotated"](mirror_first) for mirror_first in (True, False)]
        return Scene(
            conductors=[merged(c) for c, _ in scenes],
            ports=[port_arrow(ref.ports["m"]) for _, ref in scenes],
        )
    component, ref = ns["connected_mirrored"]()
    target = next(inst for inst in component.insts if inst is not ref)
    return Scene(
        conductors=[merged(component)],
        ports=[port_arrow(ref.ports["m"]), port_arrow(target.ports["t"], TARGET_PORT)],
    )


def r13(ns, use_connect):
    return conductor(ns["comb_and_lead"](63.225, use_connect), gap_points)


def r5(ns, kind):
    if kind == "problem":
        return conductor(ns["lead_on_a_second_arc"](128, 100), hole_points)
    return conductor(ns["lead_into_the_body"](128))


def r14(ns, shared):
    build = ns["strip_on_shared_vertices" if shared else "strip_across_disk"](7.336)
    return conductor(build, short_edge_points)


def r15(ns, kind):
    component = ns["chip_with_derived_etch" if kind == "result" else "chip_with_hand_drawn_etch"]()
    layers = [
        (name, component.get_region(layer, merge=True))
        for name, layer in (("GROUND_MASK", ns["MASK"]), ("ETCH", ns["ETCH"]), ("DRAW", ns["DRAW"]))
    ]
    return Scene(layers=layers, difference=ns["metal_mismatch"](component))


def r7b(ns, kind):
    span = 90 if kind == "problem" else 60
    drawn = ns["claw_clamped"](span) if kind == "problem" else ns["claw_checked"](span)
    asked = gf.Component()
    asked.add_polygon(ns["claw_points"](span), layer=(1, 0))
    return Scene(conductors=[merged(drawn)], intended=[merged(asked)])


def r8(ns, kind):
    notched = merged(ns["notched"])
    if kind == "problem":
        return Scene(conductors=[notched])
    report = ns["notches"]
    return Scene(conductors=[notched], difference=report.difference)


def pair(rule, page, build, problem_arg, result_arg, zoom=None) -> RulePair:
    return RulePair(
        rule, page, lambda ns: build(ns, problem_arg), lambda ns: build(ns, result_arg), zoom
    )


PAIRS = (
    pair("r9", "grid-and-polygons.md", r9, False, True, zoom=0.006),
    pair("r10", "grid-and-polygons.md", r10, 0, 1, zoom=1.5),
    pair("r11", "grid-and-polygons.md", r11, False, True),
    pair("r1", "one-outline.md", r1, "rotated_parts", "rotated_outline", zoom=0.006),
    pair("r6", "one-outline.md", r6, "problem", "result", zoom=2.0),
    pair("r12", "one-outline.md", r12, "problem", "result"),
    pair("r2", "placement.md", r2, False, True),
    pair("r4", "placement.md", r4, "problem", "result"),
    pair("r13", "placement.md", r13, False, True, zoom=0.006),
    pair("r5", "curves.md", r5, "problem", "result", zoom=0.6),
    pair("r14", "curves.md", r14, False, True, zoom=0.006),
    pair("r15", "companion-layers.md", r15, "problem", "result"),
    pair("r7b", "input-checks.md", r7b, "problem", "result"),
    pair("r8", "construction-checks.md", r8, "problem", "result"),
)


# Drawing ---------------------------------------------------------------------


def draw(scene: Scene, centre, half_width: float | None, path: Path) -> None:
    """One main panel and, when a defect is located, a zoomed panel to its right."""
    zoomed = centre is not None
    figure, panels = plt.subplots(1, 2 if zoomed else 1, figsize=(7.2 if zoomed else 3.8, 3.4))
    main_panel = panels[0] if zoomed else panels
    limits = scene_limits(scene)
    main_panel.set_xlim(limits[0], limits[1])
    main_panel.set_ylim(limits[2], limits[3])
    draw_scene(main_panel, scene, limits, marker_size=9)
    style_axes(main_panel)
    if zoomed:
        zoom = panels[1]
        x, y = centre
        zoom.set_xlim(x - half_width, x + half_width)
        zoom.set_ylim(y - half_width, y + half_width)
        draw_scene(zoom, scene, limits, marker_size=40)
        style_axes(zoom)
        zoom.xaxis.set_major_locator(MaxNLocator(3))
        zoom.yaxis.set_major_locator(MaxNLocator(3))
        bounds = (x - half_width, y - half_width, 2 * half_width, 2 * half_width)
        main_panel.indicate_inset(bounds, inset_ax=zoom, edgecolor=INTENDED, alpha=0.8)
    figure.tight_layout()
    figure.savefig(
        path,
        bbox_inches="tight",  # fit the canvas to every label and the zoomed panel
        pad_inches=0.1,
        metadata={
            "Date": None,
            "Description": f"{path.stem}: drawn from docs/contributing examples",
        },
    )
    plt.close(figure)


def scene_limits(scene: Scene) -> tuple[float, float, float, float]:
    """Square-ish limits around everything drawn, with a margin."""
    box = gf.kdb.Box()
    for region in scene.conductors + scene.intended + [region for _, region in scene.layers]:
        box += region.bbox()
    left, bottom, right, top = (
        value * gf.kcl.dbu for value in (box.left, box.bottom, box.right, box.top)
    )
    for x, y, _, _ in scene.ports:
        left, right, bottom, top = min(left, x), max(right, x), min(bottom, y), max(top, y)
    margin = 0.12 * max(right - left, top - bottom)
    return left - margin, right + margin, bottom - margin, top + margin


def style_axes(axes) -> None:
    axes.set_aspect("equal", adjustable="box")
    axes.set_xlabel("x (µm)")
    axes.set_ylabel("y (µm)")
    axes.ticklabel_format(useOffset=False)


def region_path(region: gf.kdb.Region) -> MplPath:
    """Every polygon of a region, hull first and holes after, in micrometres."""
    vertices, codes = [], []
    for polygon in region.each():
        dpolygon = polygon.to_dtype(gf.kcl.dbu)
        rings = [list(dpolygon.each_point_hull())]
        rings += [list(dpolygon.each_point_hole(i)) for i in range(dpolygon.holes())]
        for ring in rings:
            points = [(point.x, point.y) for point in ring]
            vertices += points + [points[0]]
            codes += [MplPath.MOVETO] + [MplPath.LINETO] * (len(points) - 1) + [MplPath.CLOSEPOLY]
    return MplPath(vertices, codes)


def draw_scene(axes, scene: Scene, limits, marker_size: float) -> None:
    """Layers, then conductors (one colour per merged polygon), then outlines and marks."""
    for name, region in scene.layers:
        axes.add_patch(
            PathPatch(region_path(region), facecolor=LAYER_COLOURS[name], edgecolor="none")
        )
    colours = iter(POLYGON_COLOURS * 4)
    for region in scene.conductors:
        for polygon in region.each():
            fill = next(colours)
            outline = region_path(gf.kdb.Region(polygon))
            axes.add_patch(
                PathPatch(outline, facecolor=fill, edgecolor=fill, linewidth=0.3, alpha=0.85)
            )
    for region in scene.intended:
        outline = region_path(region)
        axes.add_patch(
            PathPatch(outline, facecolor="none", edgecolor=INTENDED, linewidth=1.0, linestyle="--")
        )
    if scene.difference is not None and not scene.difference.is_empty():
        axes.add_patch(PathPatch(region_path(scene.difference), facecolor=DEFECT, edgecolor=DEFECT))
    span = max(limits[1] - limits[0], limits[3] - limits[2])
    for x, y, orientation, colour in scene.ports:
        dx, dy = math.cos(math.radians(orientation)), math.sin(math.radians(orientation))
        axes.add_patch(
            FancyArrow(
                x,
                y,
                0.1 * span * dx,
                0.1 * span * dy,
                width=0.008 * span,
                head_width=0.03 * span,
                color=colour,
                length_includes_head=True,
            )
        )
    for x, y in scene.markers:
        axes.plot(
            x,
            y,
            "o",
            markersize=marker_size,
            markerfacecolor="none",
            markeredgecolor=DEFECT,
            markeredgewidth=1.5,
        )


if __name__ == "__main__":
    main(sys.argv[1:])
