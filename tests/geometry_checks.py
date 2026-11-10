"""Construction checks for a built cell: did the code draw the polygons it meant?

These are the checks of "Build cell geometry" in ``docs/developing-features.md``
(R8). They read the flattened cell in database units (DBU) and answer, per
layer:

- each drawn polygon, and each polygon of the merged layer, has no
  self-intersection or self-contact, no repeated vertex, no edge shorter than
  ``MIN_EDGE_DBU`` and no spike or zero-width slit (a vertex whose two edges
  run out and back closer than ``MIN_EDGE_DBU``);
- the holes of the merged layer, which GDS can only store as cut lines;
- the smallest interior angle, which is reported and has no threshold yet.

The 2 DBU limit is a construction check, not a process or simulation rule.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import gdsfactory as gf
from kfactory import kdb
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.validation import explain_validity

MIN_EDGE_DBU = 2


@dataclass(frozen=True)
class LayerReport:
    """What one layer of a flattened cell holds after merging."""

    layer: tuple[int, int]
    polygons: int
    holes: kdb.Region
    min_edge_dbu: float
    min_angle_deg: float
    defects: tuple[str, ...] = field(default=())


def _contours(polygon: kdb.Polygon) -> list[list[kdb.Point]]:
    """Hull first, then each hole, as drawn (KLayout keeps material on the right)."""
    return [list(polygon.each_point_hull())] + [
        list(polygon.each_point_hole(i)) for i in range(polygon.holes())
    ]


def _corners(points: list[kdb.Point]):
    """Each vertex of a closed contour with its incoming and outgoing edge vectors."""
    count = len(points)
    for index, here in enumerate(points):
        before, after = points[index - 1], points[(index + 1) % count]
        yield here, (here.x - before.x, here.y - before.y), (after.x - here.x, after.y - here.y)


def interior_angles(points: list[kdb.Point]) -> list[float]:
    """Interior angle at each vertex of a closed contour, in degrees.

    KLayout keeps the material on the right of the contour.
    """
    return [
        180 + math.degrees(math.atan2(a[0] * b[1] - a[1] * b[0], a[0] * b[0] + a[1] * b[1]))
        for _, a, b in _corners(points)
    ]


def _contour_defects(points: list[kdb.Point]) -> tuple[list[str], list[float]]:
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


def polygon_defects(polygon: kdb.Polygon) -> list[str]:
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


def flat_layers(component: gf.Component) -> dict[tuple[int, int], list[kdb.Polygon]]:
    """Every drawn polygon of the flattened cell, by layer, in DBU."""
    flat = component.copy()
    flat.flatten()
    layers = {}
    for index in flat.kcl.layer_indexes():
        info = flat.kcl.get_info(index)
        polygons = [shape.polygon for shape in flat.shapes(index).each() if shape.is_polygon()]
        polygons += [
            kdb.Polygon(shape.box) for shape in flat.shapes(index).each() if shape.is_box()
        ]
        if polygons:
            layers[(info.layer, info.datatype)] = polygons
    return layers


def layer_report(layer: tuple[int, int], polygons: list[kdb.Polygon]) -> LayerReport:
    """Check each drawn polygon of one layer and the merged layer."""
    defects = []
    for polygon in polygons:
        defects.extend(f"drawn: {defect}" for defect in polygon_defects(polygon))
    merged = kdb.Region(polygons).merged()
    edges, angles = [], []
    holes = kdb.Region()
    for polygon in merged.each():
        defects.extend(f"merged: {defect}" for defect in polygon_defects(polygon))
        for points in _contours(polygon):
            edges.extend(_contour_defects(points)[1])
            angles.extend(interior_angles(points))
        for i in range(polygon.holes()):
            holes.insert(kdb.Polygon(list(polygon.each_point_hole(i))))
    return LayerReport(
        layer=layer,
        polygons=merged.count(),
        holes=holes,
        min_edge_dbu=round(min(edges), 2),
        min_angle_deg=round(min(angles), 2),
        defects=tuple(defects),
    )


def construction_report(component: gf.Component) -> dict[tuple[int, int], LayerReport]:
    """One report per layer of the flattened cell."""
    return {
        layer: layer_report(layer, polygons)
        for layer, polygons in sorted(flat_layers(component).items())
    }
