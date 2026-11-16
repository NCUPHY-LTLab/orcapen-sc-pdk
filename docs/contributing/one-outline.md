---
title: "One outline, transformed and rounded once"
sidebar: development
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

The examples on this page run on their own, in order, from the repository root
with `PYTHONPATH=tests` (for `geometry_checks`). They share this setup.

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
    """Edges of the merged layer shorter than 2 DBU.

    Pass all three arguments: KLayout reads ``with_length(0, 2)`` as
    "length is not 0" (a length and an ``inverse`` flag).
    """
    return merged(component).edges().with_length(0, 2, False).count()
```

## R1. Merge the parts of a rigid shape in its local frame, then rotate and move it once {#r1}

**Rule.** Draw every part of a rigid shape in one local frame, merge them into
one outline there, and only then rotate and move that outline.

A part's corner that lies on another part's edge (a T-junction) is a vertex of
one polygon but not of the other. After a rotation each polygon's vertices are
rounded on their own, so that corner no longer lies on the other edge, and the
merge leaves an edge of 1 DBU next to it. Merging in the local frame, where
every coordinate is exact, removes the T-junction before anything is rounded.

![**Problem.** Two parts in one frame, rotated by 76.5° as two polygons. The
right panel zooms on the T-junction, where the merged outline has an edge of 1 DBU
(marked).](../_static/images/contributing/r1-problem.svg)

![**Result.** The same parts merged in the local frame, then rotated by 76.5°.
The right panel shows the same place, with no short edge.](../_static/images/contributing/r1-result.svg)

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
returns the point at that radius and angle in degrees. Sweeping the rotation
over 1200 angles counts the short edges each construction leaves:

```python
ANGLES = [step * 0.3 for step in range(1200)]  # 0° to 359.7° in 0.3° steps
assert short_edges(rotated_parts(76.5)) == 1
assert short_edges(rotated_outline(76.5)) == 0
assert sum(short_edges(rotated_parts(angle)) > 0 for angle in ANGLES) == 12
assert sum(short_edges(rotated_one_by_one(angle)) > 0 for angle in ANGLES) == 28
assert sum(short_edges(rotated_outline(angle)) > 0 for angle in ANGLES) == 0
```

Over 1200 angles, the two polygons rotated together leave a 1 DBU edge at 12
angles and the parts rotated one by one at 28. The merged outline leaves none.
Rotating the parts one by one with an off-grid shared coordinate also splits
the conductor ([R9](grid-and-polygons.md#r9)).

**How to check.** Sweep the rotation and count the short edges, as above. In a
cell's test, `construction_report` reports every edge shorter than 2 DBU
([R8](construction-checks.md)).

## R6. Union the parts first, round once, and keep a square end by extending and clipping {#r6}

**Rule.** Round a conductor's corners after all of its parts are joined. To
keep one end square, extend the outline past that end, round, and clip the
extension off.

Rounding a part and then adding another part leaves notches where the rounded
corner meets the new part: the corner was rounded although it is no longer a
corner. In `disk_flip_chip_qubit`, rounding the claw and then adding the taper
left a 58–65° spike and 16–93 nm jogs
([#53](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/53), cause 2).

Do not limit the rounding with circular windows either: cutting rounded
pieces apart and splicing them back leaves cut points that round 1 DBU apart.
That left zero-width slits 1.3 µm and 2.3 µm long in the same claw
([#47](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/47), C2 and C3).

![**Problem.** A 20 µm claw and a 10 µm taper, each rounded with a 3 µm radius
and then joined. The right panel zooms on the notch at x = 20 µm, where two
rounded corners meet.](../_static/images/contributing/r6-problem.svg)

![**Result.** The parts joined first and rounded once. The right end is kept
square by rounding an outline extended by 6 µm and clipping it back to
x = 30 µm.](../_static/images/contributing/r6-result.svg)

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
joined conductor.

**How to check.** A notch is not a hole, a short edge or a self-intersection,
so only a comparison with the shape you meant finds it. Pass the intended shape
to `construction_report`; it reports where the layer differs from it
([R8](construction-checks.md)).

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

## R12. Combine shapes with Booleans, not by joining their point lists {#r12}

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
the intended clearance; the stored polygon has none.](../_static/images/contributing/r12-problem.svg)

![**Result.** The same ground built as the square minus the clearance circle
with `gf.boolean`.](../_static/images/contributing/r12-result.svg)

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
