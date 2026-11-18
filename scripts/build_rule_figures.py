"""Redraw the contributor-guide figures in docs/_static/images/contributing/.

Every figure is drawn from the code of its page in docs/contributing/: this
script runs a page's Python examples, in order, exactly as
tests/test_docs_construction_examples.py does, and draws the builds that the
figure names. Each rule gets a problem figure and a result figure, in English
(en/) and in Traditional Chinese (zh-TW/); only the short in-figure labels
differ. The colour convention is stated once on docs/contributing/rules.md:
one colour per merged polygon, red for a defect, dashed outlines for
comparison, arrows for ports, and a panel on the right that zooms on the
defect, at the same place in the problem and the result figure. Output is
deterministic, so re-running leaves no diff.

    uv run python scripts/build_rule_figures.py [RULE ...]
"""

from __future__ import annotations

import logging
import math
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path

import gdsfactory as gf
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrow, Patch, PathPatch
from matplotlib.path import Path as MplPath
from matplotlib.ticker import MaxNLocator

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs/contributing"
OUTPUT = ROOT / "docs/_static/images/contributing"
CODE_BLOCK = re.compile(r"^```python\n(.*?)^```", re.MULTILINE | re.DOTALL)
LANGUAGES = ("en", "zh-TW")

POLYGON_COLOURS = ("#0f766e", "#d97706", "#7c3aed", "#2563eb", "#be185d")
DEFECT = "#dc2626"
OUTLINE = "#334155"
TARGET_PORT = "#94a3b8"
LAYER_COLOURS = {"DRAW": "#0f766e", "GROUND_MASK": "#cbd5e1", "ETCH": "#f59e0b"}

LABELS = {
    "en": {
        "polygons": "{n} polygon(s)",
        "gap": "1 nm gap",
        "slit": "1 nm slit",
        "touches_itself": "outline touches itself",
        "valid_outline": "one valid outline",
        "short_edge": "1 DBU edge",
        "no_short_edge": "no short edge",
        "notch": "notch",
        "rounded_once": "rounded once",
        "clearance_lost": "clearance lost",
        "square_minus_circle": "square − circle",
        "about_origin": "turned about the origin",
        "about_centre": "turned about its centre",
        "faces": "port m faces {angle}°",
        "faces_expected": "port m faces {angle}°, should be {expected}°",
        "holes": "{n} hole(s)",
        "shared_vertex": "shared vertex",
        "mismatch": "metal mismatch",
        "no_mismatch": "metal mismatch: none",
        "asked_drawn": "asked {asked}°, drawn {drawn}°",
        "patch": "patch",
        "on_grid": "on-grid lengths",
        "passes_simple_check": "1 polygon, 0 holes",
        "difference": "differs from the intended shape",
        "cell": "cell: bend_euler",
        "DRAW": "DRAW: metal",
        "GROUND_MASK": "GROUND_MASK: ground clearance",
        "ETCH": "ETCH: etch",
        "helper": "helper: open end at o2",
    },
    "zh-TW": {
        "polygons": "{n} 個多邊形",
        "gap": "1 nm 縫",
        "slit": "1 nm 縫",
        "touches_itself": "輪廓自我接觸",
        "valid_outline": "一個有效輪廓",
        "short_edge": "1 DBU 的邊",
        "no_short_edge": "沒有過短的邊",
        "notch": "缺口",
        "rounded_once": "只圓角一次",
        "clearance_lost": "淨空區消失",
        "square_minus_circle": "方塊 − 圓",
        "about_origin": "繞原點轉動",
        "about_centre": "繞自身中心轉動",
        "faces": "port m 朝向 {angle}°",
        "faces_expected": "port m 朝向 {angle}°，應為 {expected}°",
        "holes": "{n} 個孔洞",
        "shared_vertex": "共用頂點",
        "mismatch": "金屬不一致",
        "no_mismatch": "金屬不一致：無",
        "asked_drawn": "要求 {asked}°，畫出 {drawn}°",
        "patch": "補丁",
        "on_grid": "格點上的長度",
        "passes_simple_check": "1 個多邊形、0 個孔洞",
        "difference": "與預期形狀的差異",
        "cell": "cell：bend_euler",
        "DRAW": "DRAW：金屬",
        "GROUND_MASK": "GROUND_MASK：接地淨空區",
        "ETCH": "ETCH：蝕刻",
        "helper": "helper：o2 上的開路端",
    },
}


@dataclass
class Scene:
    """What one figure draws: DBU regions, micrometre points and short labels."""

    conductors: list[gf.kdb.Region] = field(default_factory=list)
    layers: list[tuple[str, gf.kdb.Region]] = field(default_factory=list)
    layer_panels: bool = False
    legend: list[tuple[str, str]] = field(default_factory=list)  # layer name, label
    outlines: list[gf.kdb.Region] = field(default_factory=list)
    difference: gf.kdb.Region | None = None
    markers: list[tuple[float, float]] = field(default_factory=list)
    ports: list[tuple[float, float, float, str]] = field(
        default_factory=list
    )  # x, y, angle, colour
    arcs: list[tuple[float, float, float, float, float]] = field(
        default_factory=list
    )  # centre, r, a0, a1
    origin: bool = False
    limits: tuple[float, float, float, float] | None = None
    note: str | None = None
    zoom_note: str | None = None


Say = Callable[..., str]


@dataclass(frozen=True)
class FigurePair:
    """Two figures of one rule, drawn from one page, and how they are framed."""

    rule: str
    page: str
    build: Callable[[dict, object, Say], Scene]
    arguments: tuple[object, object]
    names: tuple[str, str] = ("problem", "result")
    zoom_half_width_um: float | None = None
    shared_limits: bool = False


def main(rules: list[str]) -> None:
    # The CJK fallbacks missing on this machine are expected; the SVG still names them.
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    sys.path.insert(0, str(ROOT / "tests"))  # the pages import geometry_checks
    plt.rcParams.update(
        {
            "svg.fonttype": "none",
            "svg.hashsalt": "orcapen-sc-pdk",
            "font.size": 9,
            # The later families carry the Traditional Chinese labels. The SVG
            # keeps the whole list, so a browser on any platform finds one.
            "font.family": [
                "DejaVu Sans",
                "Heiti TC",
                "PingFang TC",
                "Noto Sans CJK TC",
                "Noto Sans TC",
                "Microsoft JhengHei",
            ],
        }
    )
    namespaces: dict[str, dict] = {}
    for pair in PAIRS:
        if rules and pair.rule not in rules:
            continue
        if pair.page not in namespaces:
            namespaces[pair.page] = run_page(GUIDE / pair.page)
        for language in LANGUAGES:
            draw_pair(pair, namespaces[pair.page], language)


def run_page(page: Path) -> dict:
    """Run a page's examples in order in a fresh namespace, as its test does."""
    namespace: dict = {"__name__": f"docs_{page.stem}"}
    for block in CODE_BLOCK.findall(page.read_text(encoding="utf-8")):
        exec(block, namespace)
    return namespace


def draw_pair(pair: FigurePair, namespace: dict, language: str) -> None:
    labels = LABELS[language]

    def say(key: str, **values) -> str:
        return labels[key].format(**values)

    scenes = [pair.build(namespace, argument, say) for argument in pair.arguments]
    if pair.shared_limits:
        limits = combined_limits(scenes)
        scenes = [replace(scene, limits=limits) for scene in scenes]
    first = scenes[0]
    centre = first.markers[0] if first.markers and pair.zoom_half_width_um else None
    folder = OUTPUT / language
    folder.mkdir(parents=True, exist_ok=True)
    for name, scene in zip(pair.names, scenes, strict=True):
        path = folder / f"{pair.rule}-{name}.svg"
        draw(scene, centre, pair.zoom_half_width_um, path)
        print(path.relative_to(ROOT))


# Finding what to mark --------------------------------------------------------


def merged(component: gf.Component, layer=(1, 0)) -> gf.kdb.Region:
    return component.get_region(layer, merge=True)


def to_um(point: gf.kdb.Point) -> tuple[float, float]:
    return point.x * gf.kcl.dbu, point.y * gf.kcl.dbu


def midpoint(edge: gf.kdb.Edge) -> tuple[float, float]:
    return to_um(gf.kdb.Point((edge.p1.x + edge.p2.x) // 2, (edge.p1.y + edge.p2.y) // 2))


def short_edge_points(region: gf.kdb.Region) -> list[tuple[float, float]]:
    """Midpoints of the edges shorter than 2 DBU."""
    return [midpoint(edge) for edge in region.edges().with_length(0, 2, False).each()]


def gap_points(region: gf.kdb.Region) -> list[tuple[float, float]]:
    """Where separate polygons come within 5 DBU of each other."""
    polygons = [gf.kdb.Region(polygon) for polygon in region.each()]
    points = []
    for index, first in enumerate(polygons):
        for second in polygons[index + 1 :]:
            points += [midpoint(pair.first) for pair in first.separation_check(second, 5).each()]
    return points


def widest_hole_point(region: gf.kdb.Region) -> list[tuple[float, float]]:
    """A point well inside the largest hole, near its middle.

    A hole between two samplings is a thin curved sliver, so its bounding-box
    centre can lie outside it. A vertex of the hole shrunk by 2 DBU lies inside.
    """
    holes = sorted(region.holes().each(), key=lambda hole: (-hole.area(), str(hole)))
    if not holes:
        return []
    middle = holes[0].bbox().center()
    inside = gf.kdb.Region(holes[0]).sized(-2)
    points = [point for polygon in inside.each() for point in polygon.each_point_hull()]
    return [to_um(min(points, key=lambda point: (point.distance(middle), point.x, point.y)))]


def repeated_vertex_points(region: gf.kdb.Region) -> list[tuple[float, float]]:
    points = []
    for polygon in region.each():
        hull = [(p.x, p.y) for p in polygon.each_point_hull()]
        repeated = sorted({xy for xy in hull if hull.count(xy) > 1})
        points += [to_um(gf.kdb.Point(*xy)) for xy in repeated]
    return points


def area_centres(region: gf.kdb.Region) -> list[tuple[float, float]]:
    return [to_um(polygon.bbox().center()) for polygon in region.each()]


def conductor(component, say: Say, find=None, zoom_note=None) -> Scene:
    region = merged(component)
    return Scene(
        conductors=[region],
        markers=find(region) if find else [],
        note=say("polygons", n=region.count()),
        zoom_note=zoom_note,
    )


def port_arrow(port, colour=OUTLINE) -> tuple[float, float, float, str]:
    return port.dcenter[0], port.dcenter[1], port.orientation, colour


def layer_regions(component, names_and_layers) -> list[tuple[str, gf.kdb.Region]]:
    return [(name, component.get_region(layer, merge=True)) for name, layer in names_and_layers]


# The figures, page by page ---------------------------------------------------


def r1(ns, on_grid, say):
    lengths = (10.0, 5.0) if on_grid else (10.0004, 5.0004)
    return conductor(ns["pad_lead_pad"](*lengths), say, gap_points, None if on_grid else say("gap"))


def r2(ns, overlap, say):
    region = merged(ns["two_pads"](overlap))
    return Scene(
        conductors=[region],
        markers=repeated_vertex_points(region),
        note=say("valid_outline" if overlap else "touches_itself"),
    )


def r3(ns, spine, say):
    return conductor(ns["comb"](spine), say)


def r4(ns, build, say):
    scene = conductor(ns[build](76.5), say, short_edge_points)
    return replace(scene, zoom_note=say("short_edge" if scene.markers else "no_short_edge"))


def r5(ns, kind, say):
    notches = ns["round_then_join"] ^ ns["join_then_round"]
    if kind == "problem":
        return Scene(
            conductors=[ns["round_then_join"]],
            markers=area_centres(notches)[:1],
            zoom_note=say("notch"),
        )
    return Scene(conductors=[ns["join_then_round"]], zoom_note=say("rounded_once"))


def r6(ns, kind, say):
    intended = merged(ns["ground_from_shapes"]())
    if kind == "problem":
        drawn = merged(ns["ground_from_points"](ns["CLEARANCE"][::-1]))
        return Scene(conductors=[drawn], outlines=[intended], note=say("clearance_lost"))
    return Scene(conductors=[intended], note=say("square_minus_circle"))


def r7(ns, about_centre, say):
    placed, _ = ns["turned"](about_centre)
    start = gf.Component()
    (start << ns["part"]).dmove((10, 0))
    if about_centre:
        arc = (12.0, 1.0, 2.5, 0.0, 90.0)
    else:
        arc = (
            0.0,
            0.0,
            math.hypot(12, 1),
            math.degrees(math.atan2(1, 12)),
            90 + math.degrees(math.atan2(1, 12)),
        )
    return Scene(
        conductors=[merged(placed)],
        outlines=[merged(start)],
        arcs=[arc],
        origin=True,
        note=say("about_centre" if about_centre else "about_origin"),
    )


def r9(ns, build, say):
    component, ref = ns[build]()
    target = next(inst for inst in component.insts if inst is not ref)
    angle = round(ref.ports["m"].orientation) % 360
    return Scene(
        conductors=[merged(component)],
        ports=[port_arrow(target.ports["t"], TARGET_PORT), port_arrow(ref.ports["m"])],
        # The target faces 210°, so a port that meets it must face 30°.
        note=say("faces", angle=angle)
        if angle == 30
        else say("faces_expected", angle=angle, expected=30),
    )


def r10(ns, use_connect, say):
    scene = conductor(ns["comb_and_lead"](63.225, use_connect), say, gap_points)
    return replace(scene, zoom_note=None if use_connect else say("slit"))


def r11(ns, kind, say):
    build = (
        ns["lead_on_a_second_arc"](128, 100) if kind == "problem" else ns["lead_into_the_body"](128)
    )
    region = merged(build)
    return Scene(
        conductors=[region],
        markers=widest_hole_point(region),
        note=say("holes", n=region.holes().count()),
    )


def r12(ns, shared, say):
    build = ns["strip_on_shared_vertices" if shared else "strip_across_disk"](7.336)
    scene = conductor(build, say, short_edge_points)
    return replace(scene, note=None, zoom_note=say("shared_vertex" if shared else "short_edge"))


def r13(ns, kind, say):
    component = ns["chip_with_derived_etch" if kind == "result" else "chip_with_hand_drawn_etch"]()
    names = (("DRAW", ns["DRAW"]), ("GROUND_MASK", ns["MASK"]), ("ETCH", ns["ETCH"]))
    return Scene(
        layers=layer_regions(component, names),
        layer_panels=True,
        difference=ns["metal_mismatch"](component),
        note=say("mismatch" if kind == "problem" else "no_mismatch"),
    )


def r15(ns, kind, say):
    asked = 90 if kind == "problem" else 60
    drawn = ns["claw_clamped"](asked) if kind == "problem" else ns["claw_checked"](asked)
    asked_shape = gf.Component()
    asked_shape.add_polygon(ns["claw_points"](asked), layer=(1, 0))
    return Scene(
        conductors=[merged(drawn)],
        outlines=[merged(asked_shape)],
        note=say("asked_drawn", asked=asked, drawn=60),
    )


def r17(ns, kind, say):
    if kind == "problem":
        return Scene(
            conductors=[merged(ns["patched"]())],
            difference=ns["PATCH"],
            markers=area_centres(ns["PATCH"]),
            note=say("polygons", n=1),
            zoom_note=say("patch"),
        )
    return Scene(conductors=[merged(ns["fixed"])], note=say("on_grid"))


def r18(ns, kind, say):
    notched = merged(ns["notched"])
    if kind == "problem":
        return Scene(conductors=[notched], note=say("passes_simple_check"))
    return Scene(conductors=[notched], difference=ns["notches"].difference, note=say("difference"))


def h3(ns, kind, say):
    component = ns["bend"] if kind == "cell" else ns["open_ended"]
    layer = ns["LAYER"]
    names = (
        ("GROUND_MASK", layer.D0_TOP_GROUND_MASK),
        ("ETCH", layer.D0_TOP_M1_ETCH),
        ("DRAW", layer.D0_TOP_M1_DRAW),
    )
    if kind == "cell":
        ports = [port_arrow(port) for port in component.ports]
        outlines = []
    else:
        ports = [port_arrow(ns["host"].ports["o2"])]
        host_mask = ns["host"].get_region(layer.D0_TOP_GROUND_MASK, merge=True)
        outlines = [component.get_region(layer.D0_TOP_GROUND_MASK, merge=True) - host_mask]
    return Scene(
        layers=layer_regions(component, names),
        ports=ports,
        outlines=outlines,
        legend=[(name, say(name)) for name in ("DRAW", "ETCH", "GROUND_MASK")],
        note=say(kind),
    )


PAIRS = (
    FigurePair("r1", "grid-and-polygons.md", r1, (False, True), zoom_half_width_um=0.006),
    FigurePair("r2", "grid-and-polygons.md", r2, (0, 1), zoom_half_width_um=1.5),
    FigurePair("r3", "grid-and-polygons.md", r3, (False, True)),
    FigurePair(
        "r4", "one-outline.md", r4, ("rotated_parts", "rotated_outline"), zoom_half_width_um=0.006
    ),
    FigurePair("r5", "one-outline.md", r5, ("problem", "result"), zoom_half_width_um=2.0),
    FigurePair("r6", "one-outline.md", r6, ("problem", "result")),
    FigurePair("r7", "placement.md", r7, (False, True), shared_limits=True),
    FigurePair(
        "r9", "placement.md", r9, ("placed_by_hand", "placed_by_connect"), shared_limits=True
    ),
    FigurePair("r10", "placement.md", r10, (False, True), zoom_half_width_um=0.006),
    FigurePair("r11", "curves.md", r11, ("problem", "result"), zoom_half_width_um=0.04),
    FigurePair("r12", "curves.md", r12, (False, True), zoom_half_width_um=0.006),
    FigurePair("r13", "companion-layers.md", r13, ("problem", "result")),
    FigurePair("r15", "input-checks.md", r15, ("problem", "result")),
    FigurePair("r17", "input-checks.md", r17, ("problem", "result"), zoom_half_width_um=0.006),
    FigurePair("r18", "construction-checks.md", r18, ("problem", "result")),
    FigurePair("h3", "what-is-a-cell.md", h3, ("cell", "helper"), names=("cell", "helper")),
)


# Drawing ---------------------------------------------------------------------


def draw(scene: Scene, centre, half_width: float | None, path: Path) -> None:
    """One panel per layer, or one main panel with a zoomed panel to its right."""
    if scene.layer_panels:
        figure = draw_layer_panels(scene)
    else:
        figure = draw_main_and_zoom(scene, centre, half_width)
    figure.tight_layout()
    figure.savefig(
        path,
        bbox_inches="tight",  # fit the canvas to every label and panel
        pad_inches=0.1,
        metadata={"Date": None, "Description": f"{path.stem}: drawn from docs/contributing"},
    )
    plt.close(figure)


def draw_main_and_zoom(scene: Scene, centre, half_width: float | None):
    zoomed = centre is not None
    figure, panels = plt.subplots(1, 2 if zoomed else 1, figsize=(7.2 if zoomed else 3.8, 3.4))
    main_panel = panels[0] if zoomed else panels
    limits = scene.limits or scene_limits(scene)
    set_limits(main_panel, limits)
    draw_scene(main_panel, scene, limits, marker_size=9)
    style_axes(main_panel)
    write_note(main_panel, scene.note)
    if scene.legend:
        handles = [
            Patch(facecolor=LAYER_COLOURS[name], label=label) for name, label in scene.legend
        ]
        main_panel.legend(
            handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=1, frameon=False
        )
    if zoomed:
        zoom = panels[1]
        x, y = centre
        set_limits(zoom, (x - half_width, x + half_width, y - half_width, y + half_width))
        draw_scene(zoom, scene, limits, marker_size=40)
        style_axes(zoom)
        zoom.xaxis.set_major_locator(MaxNLocator(3))
        zoom.yaxis.set_major_locator(MaxNLocator(3))
        write_note(zoom, scene.zoom_note)
        bounds = (x - half_width, y - half_width, 2 * half_width, 2 * half_width)
        main_panel.indicate_inset(bounds, inset_ax=zoom, edgecolor=OUTLINE, alpha=0.8)
    return figure


def draw_layer_panels(scene: Scene):
    """DRAW, GROUND_MASK and ETCH, then the defect area in red, two panels to a row."""
    count = len(scene.layers) + (scene.difference is not None)
    rows = math.ceil(count / 2)
    figure, grid = plt.subplots(rows, 2, figsize=(6.0, 2.2 * rows), squeeze=False)
    panels = list(grid.flat)
    limits = scene_limits(scene)
    for panel, (name, region) in zip(panels, scene.layers, strict=False):
        set_limits(panel, limits)
        panel.add_patch(
            PathPatch(region_path(region), facecolor=LAYER_COLOURS[name], edgecolor="none")
        )
        style_axes(panel)
        panel.set_title(name, fontsize=10, loc="left")
    if scene.difference is not None:
        panel = panels[count - 1]
        set_limits(panel, limits)
        if not scene.difference.is_empty():
            panel.add_patch(
                PathPatch(region_path(scene.difference), facecolor=DEFECT, edgecolor=DEFECT)
            )
        style_axes(panel)
        panel.set_title(scene.note, fontsize=10, loc="left")
    for panel in panels[count:]:
        panel.set_axis_off()
    return figure


def scene_limits(scene: Scene) -> tuple[float, float, float, float]:
    """Limits around everything drawn, with a margin."""
    box = gf.kdb.Box()
    regions = scene.conductors + scene.outlines + [region for _, region in scene.layers]
    for region in regions:
        box += region.bbox()
    left, bottom, right, top = (
        value * gf.kcl.dbu for value in (box.left, box.bottom, box.right, box.top)
    )
    for x, y, _, _ in scene.ports:
        left, right, bottom, top = min(left, x), max(right, x), min(bottom, y), max(top, y)
    if scene.origin:
        left, right, bottom, top = min(left, 0), max(right, 0), min(bottom, 0), max(top, 0)
    margin = 0.12 * max(right - left, top - bottom)
    return left - margin, right + margin, bottom - margin, top + margin


def combined_limits(scenes: list[Scene]) -> tuple[float, float, float, float]:
    limits = [scene_limits(scene) for scene in scenes]
    return (
        min(limit[0] for limit in limits),
        max(limit[1] for limit in limits),
        min(limit[2] for limit in limits),
        max(limit[3] for limit in limits),
    )


def set_limits(axes, limits) -> None:
    axes.set_xlim(limits[0], limits[1])
    axes.set_ylim(limits[2], limits[3])


def style_axes(axes) -> None:
    axes.set_aspect("equal", adjustable="box")
    axes.set_xlabel("x (µm)")
    axes.set_ylabel("y (µm)")
    axes.ticklabel_format(useOffset=False)


def write_note(axes, note: str | None) -> None:
    """A short label above the panel, where it never covers the drawing."""
    if note:
        axes.set_title(note, fontsize=9, loc="left")


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
    for region in scene.outlines:
        axes.add_patch(
            PathPatch(
                region_path(region),
                facecolor="none",
                edgecolor=OUTLINE,
                linewidth=1.0,
                linestyle="--",
            )
        )
    if scene.difference is not None and not scene.difference.is_empty():
        axes.add_patch(PathPatch(region_path(scene.difference), facecolor=DEFECT, edgecolor=DEFECT))
    span = max(limits[1] - limits[0], limits[3] - limits[2])
    for centre_x, centre_y, radius, start, stop in scene.arcs:
        draw_turn(axes, (centre_x, centre_y), radius, start, stop, span)
    if scene.origin:
        axes.plot(0, 0, "+", color=OUTLINE, markersize=10, markeredgewidth=1.5)
    for x, y, orientation, colour in scene.ports:
        dx, dy = math.cos(math.radians(orientation)), math.sin(math.radians(orientation))
        axes.add_patch(
            FancyArrow(
                x, y, 0.1 * span * dx, 0.1 * span * dy,
                width=0.008 * span, head_width=0.03 * span, color=colour, length_includes_head=True,
            )
        )  # fmt: skip
    for x, y in scene.markers:
        axes.plot(
            x, y, "o", markersize=marker_size, markerfacecolor="none",
            markeredgecolor=DEFECT, markeredgewidth=1.5,
        )  # fmt: skip


def draw_turn(axes, centre, radius, start, stop, span) -> None:
    """A rotation arc about `centre`, from `start` to `stop` degrees, with an arrowhead."""
    steps = [start + (stop - start) * i / 48 for i in range(49)]
    points = [
        (
            centre[0] + radius * math.cos(math.radians(a)),
            centre[1] + radius * math.sin(math.radians(a)),
        )
        for a in steps
    ]
    axes.plot(*zip(*points, strict=True), color=OUTLINE, linewidth=1.0)
    axes.annotate(
        "", xy=points[-1], xytext=points[-3],
        arrowprops={"arrowstyle": "-|>", "color": OUTLINE, "mutation_scale": 0.6 * span},
    )  # fmt: skip


if __name__ == "__main__":
    main(sys.argv[1:])
