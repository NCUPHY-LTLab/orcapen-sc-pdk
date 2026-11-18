---
title: "One outline, transformed and rounded once"
sidebar: development
page-navigation: true
---

A conductor drawn from several parts is safe only once its parts are one
outline. Every operation that recomputes coordinates (a rotation, a rounding, a
Boolean) rounds each vertex to the 1 nm grid again, and parts that are still
separate are rounded separately. These three rules say the same thing for
rotation, rounding and combining: make one outline first, then transform or
round it once.

Terms used here:

- **DBU** (database unit): the integer grid GDS stores. In this PDK 1 DBU is
  1 nm.
- **Local frame**: the coordinate system of the cell you draw a shape in,
  before any rotation or move places it in its parent.
- **Merge**: joining overlapping and touching polygons of a layer into the
  fewest polygons, as a mask writer does. `component.get_region(layer,
  merge=True)` returns the merged layer.

Run this page's examples with
`uv run pytest tests/test_docs_construction_examples.py -k one-outline`. They
run in order and share this setup. The test puts `tests/` on the import path, where
`geometry_checks` lives.

```python
import gdsfactory as gf
from orcapen_sc_pdk import activate
from orcapen_sc_pdk.helpers.layout.geometry import polar_point

activate()
LAYER = (1, 0)


def box(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def merged(component):
    return component.get_region(LAYER, merge=True)


def short_edges(component):
    """Edges of the merged layer shorter than 2 DBU."""
    return merged(component).edges().with_length(0, 2, False).count()
```

`with_length(0, 2, False)` counts the edges at least 0 and less than 2 DBU
long.[^with-length]

[^with-length]: Pass all three arguments. With two, KLayout reads
    `with_length(0, 2)` as a length and an `inverse` flag, that is "every edge
    whose length is not 0".

## R4. Merge the parts of a rigid shape in its local frame, then rotate and move it once {#r4}

**Rule.** Draw every part of a rigid shape in one local frame, merge them into
one outline there, and only then rotate and move that outline.

A part's corner that lies on another part's edge (a T-junction) is a vertex of
one polygon but not of the other. After a rotation each polygon's vertices are
rounded on their own, so that corner no longer lies on the other edge, and the
merge leaves an edge of 1 DBU next to it. Merging in the local frame, where
every coordinate is exact, removes the T-junction before anything is rounded.

![**Problem.** Two parts in one frame, rotated by 76.5° as two polygons. The
right panel zooms on the T-junction, where the merged outline has an edge of
1 DBU (marked). An edge that short forces the mesher to resolve it with
elements as small (see [R18](construction-checks.md)).](../_static/images/contributing/en/r4-problem.svg)

![**Result.** The same parts merged in the local frame, then rotated by 76.5°.
The right panel shows the same place, with no short edge.](../_static/images/contributing/en/r4-result.svg)

```python
PARTS = [(0, 9.364, 3.3), (9.364, 16.769, 6.1)]  # x0, x1, height in µm; the parts share x = 9.364


def parts_in_one_frame():
    local = gf.Component()
    for x0, x1, height in PARTS:
        local.add_polygon(box(x0, 0, x1, height), layer=LAYER)
    return local


def rotated_parts(angle):  # don't: the parts stay two polygons through the rotation
    c = gf.Component()
    ref = c << parts_in_one_frame()
    ref.drotate(angle)
    ref.dmove((5, 5))
    return c


def rotated_outline(angle):  # do: merge in the local frame, then rotate and move once
    outline = gf.Component()
    outline.add_polygon(merged(parts_in_one_frame()), layer=LAYER)
    c = gf.Component()
    ref = c << outline
    ref.drotate(angle)
    ref.dmove((5, 5))
    return c


def rotated_one_by_one(angle):  # don't either: each part rotated and moved on its own
    c = gf.Component()
    for x0, x1, height in PARTS:
        part = gf.Component()
        part.add_polygon(box(0, 0, x1 - x0, height), layer=LAYER)
        ref = c << part
        ref.drotate(angle)
        ref.dmove(polar_point(x0, angle))
    return c
```

`polar_point(radius, angle)`, from `orcapen_sc_pdk.helpers.layout.geometry`,
returns the point at that radius and angle in degrees.

```python
assert short_edges(rotated_parts(76.5)) == 1
assert short_edges(rotated_one_by_one(69.3)) > 0
assert short_edges(rotated_outline(76.5)) == 0
```

Swept over 1200 angles in 0.3° steps, the two polygons rotated together leave
a 1 DBU edge at 12 angles, the parts rotated one by one at 28, and the merged
outline at none; the sweep runs in the guide's test. Rotating the parts one by
one with an off-grid shared coordinate also splits the conductor
([R1](grid-and-polygons.md#r1)).

**How to check.** Build the shape at several angles and count the short edges,
as above. In a cell's test, `construction_report` reports every edge shorter
than 2 DBU ([R18](construction-checks.md)).

## R5. Round a conductor once, after all of its parts are joined {#r5}

**Rule.** Round a conductor's corners once, after all of its parts are joined.

- To keep one end square, extend the outline past that end, round, and clip
  the extension off.
- Do not round a part and then add another part to it.

Rounding a part and then adding another part leaves notches where the rounded
corner meets the new part: the corner was rounded although it is no longer a
corner. In `disk_flip_chip_qubit`, rounding a claw (one of the four arms around
the qubit disk; see the [component page](../public-pdk-examples/components/disk_flip_chip_qubit.qmd))
and then adding its taper left a 58–65° spike and 16–93 nm jogs
([#53](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/53), cause 2).

![**Problem.** A 20 µm claw and a 10 µm taper, each rounded with a 3 µm radius
and then joined. The right panel zooms on the notch at x = 20 µm, where two
rounded corners meet.](../_static/images/contributing/en/r5-problem.svg)

![**Result.** The same parts joined first and rounded once. The right panel
shows the same place, without a notch.](../_static/images/contributing/en/r5-result.svg)

```python
RADIUS = gf.kcl.to_dbu(3)  # the 3 µm corner radius in DBU; KLayout's rounding works in DBU
CLAW, TAPER = (0, 0, 20, 10), (20, 0, 30, 10)


def region(*boxes):
    """Boxes in µm as one merged region in DBU."""
    c = gf.Component()
    for corners in boxes:
        c.add_polygon(box(*corners), layer=LAYER)
    return merged(c)


def rounded(shape):
    return shape.rounded_corners(RADIUS, RADIUS, 64)  # inner radius, outer radius, points per circle


round_then_join = (rounded(region(CLAW)) + rounded(region(TAPER))).merged()  # don't
join_then_round = rounded(region(CLAW, TAPER))  # do
extended = rounded(region(CLAW, (20, 0, 30 + 2 * 3, 10)))  # run the outline 6 µm past the end
square_end = extended & region((-1, -1, 30, 11))  # and clip it back at x = 30


def area_um2(shape):
    return shape.area() * gf.kcl.dbu**2


assert round(area_um2(round_then_join ^ join_then_round), 3) == 7.702  # the notches at x = 20
corners = {(point.x, point.y) for point in next(square_end.each()).each_point_hull()}
assert {(30_000, 0), (30_000, 10_000)} <= corners  # the right end keeps its square corners
assert (0, 0) not in corners  # the left end is rounded
```

The two constructions differ by 7.702 µm²: the notches at the top and bottom
of x = 20 µm, where four corners were rounded that are not corners of the
joined conductor. `square_end` keeps the right end square: the outline runs
6 µm past x = 30 µm, is rounded, and is clipped back.

**How to check.** A notch is not a hole, a short edge or a self-intersection,
so only a comparison with the shape you meant finds it. Pass the intended shape
to `construction_report`; it reports where the layer differs from it
([R18](construction-checks.md)).

```python
from geometry_checks import construction_report  # tests/geometry_checks.py


def as_component(shape):
    c = gf.Component()
    c.add_polygon(shape, layer=LAYER)
    return c


notched = construction_report(as_component(round_then_join), intended={LAYER: join_then_round})
assert notched[LAYER].holes.is_empty() and notched[LAYER].min_edge_dbu >= 2
assert any("differs from the intended shape" in defect for defect in notched[LAYER].defects)
```

## R6. Combine shapes with Booleans, not by joining their point lists {#r6}

**Rule.** Build each part as a closed shape and combine the parts with a
Boolean operation (union, difference, intersection), never by concatenating
the parts' point lists into one polygon.

A joined point list is a valid polygon only if every piece runs in the right
direction and every join point lands exactly where the next piece starts.
When one does not, the polygon crosses or overlaps itself, and how it is
stored depends on KLayout's handling of that polygon, not on what you meant.
In the example, a ground square with a circular clearance is drawn as one
point list; when the arc runs the other way, the outline doubles back over
itself and the clearance disappears without any error. A Boolean gives the
same shape whichever way the arc runs. Splicing rounded claw pieces as point
lists is what left the zero-width slits of
[#47](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/47) C2 and C3, and
the rebuilt disk-qubit outlines use Booleans on shapes instead
([#53](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/53)).

![**Problem.** A 40 µm ground square with an 8 µm clearance arc spliced into
its top edge, with the arc listed in the wrong direction. The dashed line is
the intended clearance; the stored polygon has none.](../_static/images/contributing/en/r6-problem.svg)

![**Result.** The same ground built as the square minus the clearance circle
with `gf.boolean`.](../_static/images/contributing/en/r6-result.svg)

```python
def arc(center, radius, start, stop, segments):
    return [polar_point(radius, start + (stop - start) * i / segments, center) for i in range(segments + 1)]


CLEARANCE = arc((0, 20), 8, 0, -180, 32)  # from (8, 20) down and round to (-8, 20)


def ground_from_points(clearance):  # don't: one polygon spliced from point lists
    c = gf.Component()
    c.add_polygon([(-20, -20), (20, -20), (20, 20)] + clearance + [(-20, 20)], layer=LAYER)
    return c


def ground_from_shapes():  # do: a square minus a circle
    square = gf.Component()
    square.add_polygon(box(-20, -20, 20, 20), layer=LAYER)
    circle = gf.Component()
    circle.add_polygon(arc((0, 20), 8, 0, 360, 64)[:-1], layer=LAYER)
    return gf.boolean(square, circle, "not", layer=LAYER)


intended = merged(ground_from_shapes())
assert (merged(ground_from_points(CLEARANCE)) ^ intended).is_empty()  # right direction: same shape
assert round(area_um2(merged(ground_from_points(CLEARANCE[::-1]))), 3) == 1600  # the clearance is gone
assert round(area_um2(intended), 3) == 1499.632
```

**How to check.** The wrong-direction polygon has no defect a validity check
can see; only the comparison with the intended shape finds it.

```python
reversed_report = construction_report(ground_from_points(CLEARANCE[::-1]), intended={LAYER: intended})
assert any("differs from the intended shape" in defect for defect in reversed_report[LAYER].defects)
```
