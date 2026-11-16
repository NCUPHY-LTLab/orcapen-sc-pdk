"""Construction checks for a built cell: did the code draw the polygons it meant?

These are the checks of the contributor guide's "Construction checks" page
(``docs/contributing/construction-checks.md``, rule R8). They read the
flattened cell in database units (DBU, the integer grid GDS stores; 1 DBU is
1 nm in this PDK) and answer, per layer:

- each drawn polygon, and each polygon of the merged layer, has no
  self-intersection or self-contact, no repeated vertex, no edge shorter than
  ``MIN_EDGE_DBU`` and no spike or zero-width slit (a vertex whose two edges
  run out and back closer than ``MIN_EDGE_DBU``);
- the holes of the merged layer, which GDS can only store as cut lines;
- the smallest interior angle, which is reported and has no threshold yet;
- when the caller says how many conductors a layer holds, that the merged
  layer has exactly that many polygons, so no conductor has fallen apart;
- when the caller gives the intended shape of a layer, where the merged layer
  differs from it (the XOR). Differences no wider than ``MIN_EDGE_DBU`` are
  grid rounding and are left out; a split or a slit that narrow is caught by
  the polygon count and the checks above.

The 2 DBU limit is a construction check, not a process or simulation rule.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import gdsfactory as gf
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.validation import explain_validity

MIN_EDGE_DBU = 2

Layer = tuple[int, int]


@dataclass(frozen=True)
class LayerReport:
    """What one layer of a flattened cell holds after merging.

    ``difference`` is where the merged layer differs from its intended shape,
    in DBU, without grid rounding; it is empty when no intended shape is given.
    """

    layer: Layer
    polygons: int
    holes: gf.kdb.Region
    min_edge_dbu: float
    min_angle_deg: float
    defects: tuple[str, ...] = field(default=())
    difference: gf.kdb.Region = field(default_factory=gf.kdb.Region)


def construction_report(
    component: gf.Component,
    *,
    conductors: dict[Layer, int] | None = None,
    intended: dict[Layer, gf.kdb.Region] | None = None,
) -> dict[Layer, LayerReport]:
    """One report per layer of the flattened cell.

    Args:
        component: the built cell.
        conductors: for each listed layer, how many separate conductors it
            holds. Each conductor must be one polygon, so a merged layer with
            another polygon count is a defect.
        intended: for each listed layer, the shape it should have, as a region
            in DBU. Where the merged layer differs from it is a defect.
    """
    conductors = conductors or {}
    intended = intended or {}
    return {
        layer: layer_report(layer, polygons, conductors.get(layer), intended.get(layer))
        for layer, polygons in sorted(flat_layers(component).items())
    }


def flat_layers(component: gf.Component) -> dict[Layer, list[gf.kdb.Polygon]]:
    """Every drawn polygon of the flattened cell, by layer, in DBU."""
    flat = component.copy()
    flat.flatten()
    layers = {}
    for index in flat.kcl.layer_indexes():
        info = flat.kcl.get_info(index)
        polygons = [shape.polygon for shape in flat.shapes(index).each() if shape.is_polygon()]
        polygons += [
            gf.kdb.Polygon(shape.box) for shape in flat.shapes(index).each() if shape.is_box()
        ]
        if polygons:
            layers[(info.layer, info.datatype)] = polygons
    return layers


def layer_report(
    layer: Layer,
    polygons: list[gf.kdb.Polygon],
    conductors: int | None = None,
    intended: gf.kdb.Region | None = None,
) -> LayerReport:
    """Check each drawn polygon of one layer, the merged layer, and its intent."""
    defects = []
    for polygon in polygons:
        defects.extend(f"drawn: {defect}" for defect in polygon_defects(polygon))
    merged = gf.kdb.Region(polygons).merged()
    edges, angles = [], []
    for polygon in merged.each():
        defects.extend(f"merged: {defect}" for defect in polygon_defects(polygon))
        for points in _contours(polygon):
            edges.extend(_contour_defects(points)[1])
            angles.extend(interior_angles(points))
    if conductors is not None and merged.count() != conductors:
        defects.append(f"merged: {merged.count()} polygons for {conductors} conductor(s)")
    difference = gf.kdb.Region()
    if intended is not None:
        difference = shape_difference(merged, intended)
        if not difference.is_empty():
            defects.append(f"merged: differs from the intended shape within {difference.bbox()}")
    return LayerReport(
        layer=layer,
        polygons=merged.count(),
        holes=merged.holes(),
        min_edge_dbu=round(min(edges), 2),
        min_angle_deg=round(min(angles), 2),
        defects=tuple(defects),
        difference=difference,
    )


def shape_difference(merged: gf.kdb.Region, intended: gf.kdb.Region) -> gf.kdb.Region:
    """Where two shapes differ, leaving out differences no wider than MIN_EDGE_DBU.

    Shrinking the XOR by half the limit removes every sliver up to the limit
    wide; growing it back restores the size of what remains.
    """
    half = MIN_EDGE_DBU // 2
    return (merged ^ intended).sized(-half).sized(half) & (merged ^ intended)


def polygon_defects(polygon: gf.kdb.Polygon) -> list[str]:
    """Every validity defect of one polygon (holes are not defects here)."""
    contours = _contours(polygon)
    defects = []
    for points in contours:
        defects.extend(_contour_defects(points)[0])
    shape = ShapelyPolygon(
        [(p.x, p.y) for p in contours[0]], [[(p.x, p.y) for p in hole] for hole in contours[1:]]
    )
    if not shape.is_valid:
        defects.append(explain_validity(shape))
    return defects


def interior_angles(points: list[gf.kdb.Point]) -> list[float]:
    """Interior angle at each vertex of a closed contour, in degrees.

    KLayout keeps the material on the right of the contour.
    """
    return [
        180 + math.degrees(math.atan2(a[0] * b[1] - a[1] * b[0], a[0] * b[0] + a[1] * b[1]))
        for _, a, b in _corners(points)
    ]


def _contours(polygon: gf.kdb.Polygon) -> list[list[gf.kdb.Point]]:
    """Hull first, then each hole, as drawn (KLayout keeps material on the right)."""
    return [list(polygon.each_point_hull())] + [
        list(polygon.each_point_hole(i)) for i in range(polygon.holes())
    ]


def _corners(points: list[gf.kdb.Point]):
    """Each vertex of a closed contour with its incoming and outgoing edge vectors."""
    count = len(points)
    for index, here in enumerate(points):
        before, after = points[index - 1], points[(index + 1) % count]
        yield here, (here.x - before.x, here.y - before.y), (after.x - here.x, after.y - here.y)


def _contour_defects(points: list[gf.kdb.Point]) -> tuple[list[str], list[float]]:
    """Repeated vertices, short edges and spikes of one closed contour, and its edge lengths."""
    defects, edges = [], []
    if len(set((p.x, p.y) for p in points)) != len(points):
        defects.append("repeated vertex")
    for here, incoming, outgoing in _corners(points):
        length = math.hypot(*outgoing)
        edges.append(length)
        if 0 < length < MIN_EDGE_DBU:
            defects.append(f"edge of {length:.2f} DBU at ({here.x}, {here.y})")
        cross = incoming[0] * outgoing[1] - incoming[1] * outgoing[0]
        dot = incoming[0] * outgoing[0] + incoming[1] * outgoing[1]
        longest = max(math.hypot(*incoming), length)
        # Out and back: the edges turn by more than 90 degrees and the nearer
        # end lies within MIN_EDGE_DBU of the other edge's line.
        if dot < 0 and longest and abs(cross) / longest < MIN_EDGE_DBU:
            defects.append(f"spike or slit at ({here.x}, {here.y})")
    return defects, edges
