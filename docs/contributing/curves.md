---
title: "Curves: joins and cuts"
sidebar: development
---

A curve in GDS is a polygon: its vertices are points sampled on the ideal
curve, joined by straight chords, each rounded to the 1 nm grid. Two samplings
of one curve are two different polygons. These rules say how to join a
straight edge to a curve, and how to cut across one, so that the samplings
never have to agree.

Terms used here:

- **DBU** (database unit): the integer grid GDS stores; 1 DBU is 1 nm here.
- **Sagitta**: the largest distance between a chord and the arc it stands for.
  For a chord spanning an angle θ on radius R it is R·(1 − cos(θ/2)): about
  15 nm for one step of a 128-point circle of radius 50 µm.
- **Hole**: an enclosed gap in a merged polygon. GDS cannot store holes, so a
  writer joins each hole to the outline with a cut line.

The examples on this page run on their own, in order, from the repository root
with `PYTHONPATH=tests` (for `geometry_checks`). They share this setup.

```python
import math

import gdsfactory as gf
from orcapen_sc_pdk import activate
from orcapen_sc_pdk.helpers.layout.geometry import polar_point

activate()
LAYER = (1, 0)
RADIUS = 50  # µm


def arc(radius, start, stop, segments):
    """Points on a circle from `start` to `stop` degrees, both ends included."""
    return [polar_point(radius, start + (stop - start) * i / segments) for i in range(segments + 1)]


def disk(segments):
    return arc(RADIUS, 0, 360, segments)[:-1]


def merged(component):
    return component.get_region(LAYER, merge=True)


def sagitta(radius, step_deg):
    return radius * (1 - math.cos(math.radians(step_deg) / 2))


assert round(sagitta(RADIUS, 360 / 128) * 1000) == 15  # nm
```

## R5. Where a straight edge meets a curve, run the edge into the body {#r5}

**Rule.** Extend a part's straight sides past the curve into the body, or
reuse the body's own vertices along the join. Never sample a second arc on the
same radius to meet the first.

Two samplings of one circle do not coincide on the grid: between their
vertices the chords cross back and forth within the sagitta, and the slivers
they enclose become holes after the merge. The `disk_flip_chip_qubit` lead fan
ended on its own arc at the disk radius, which left 14 holes on the qubit
metal; shrinking that arc by less than its sagitta did not remove them
([#53](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/53), cause 1).

![**Problem.** A lead that flares from 16 µm to ±20° and ends on its own arc,
100 steps over 40°, at the radius of a 128-point disk. The merged layer has 8 holes
(marked); the right panel zooms on one.](../_static/images/contributing/r5-problem.svg)

![**Result.** The same flare with its straight sides run on into the disk: no
holes. The right panel shows the same place.](../_static/images/contributing/r5-result.svg)

```python
def flared_lead(landing):
    """A lead from x = 80 µm, 16 µm wide, flaring out to the given landing points."""
    return [(80, -8), (80, 8)] + landing


def lead_on_a_second_arc(disk_segments, landing_segments):  # don't
    c = gf.Component()
    c.add_polygon(disk(disk_segments), layer=LAYER)
    landing = arc(RADIUS, -20, 20, landing_segments)
    c.add_polygon(flared_lead(landing[::-1]), layer=LAYER)
    return c


def lead_into_the_body(disk_segments):  # do: the flare's sides continue to x = 40 µm
    c = gf.Component()
    c.add_polygon(disk(disk_segments), layer=LAYER)
    top, bottom = polar_point(RADIUS, 20), polar_point(RADIUS, -20)

    def continued(outer, corner, x_end=40):
        t = (x_end - outer[0]) / (corner[0] - outer[0])
        return (x_end, outer[1] + t * (corner[1] - outer[1]))

    c.add_polygon(flared_lead([continued((80, 8), top), continued((80, -8), bottom)]), layer=LAYER)
    return c


def lead_on_the_body_vertices(disk_segments):  # do: land on the disk's own vertices
    c = gf.Component()
    points = disk(disk_segments)
    c.add_polygon(points, layer=LAYER)
    step = 360 / disk_segments
    landing = [polar_point(RADIUS, i * step) for i in range(-int(20 // step), int(20 // step) + 1)]
    c.add_polygon(flared_lead(landing[::-1]), layer=LAYER)
    return c


assert merged(lead_on_a_second_arc(128, 100)).holes().count() == 8
assert merged(lead_into_the_body(128)).holes().count() == 0
assert merged(lead_on_the_body_vertices(128)).holes().count() == 0
assert merged(lead_on_a_second_arc(1024, 800)).holes().count() == 112  # eight times the points: more holes
```

More points do not cure it: with eight times the points on both arcs the
merge leaves 112 holes. The fair comparison draws the same lead both ways. The two differ only by the
slivers between the two arcs, 0.34 µm² in all:

```python
differ = merged(lead_on_a_second_arc(128, 100)) ^ merged(lead_into_the_body(128))
assert round(differ.area() * gf.kcl.dbu**2, 2) == 0.34
```

**How to check.** Count the holes of the merged layer, and name every hole you
meant to draw ([R8](construction-checks.md)).

```python
from geometry_checks import construction_report  # tests/geometry_checks.py

assert construction_report(lead_on_a_second_arc(128, 100))[LAYER].holes.count() == 8
assert construction_report(lead_into_the_body(128))[LAYER].holes.is_empty()
```

## R14. Where a straight edge or cut crosses a sampled curve, give both one shared vertex {#r14}

**Rule.** Where a straight edge crosses a sampled curve, make the crossing a
vertex of both outlines: sample the curve so that a vertex sits at the
crossing, and end the straight edge on that vertex.

Left to the merge, the crossing point is computed and rounded to the grid.
When it falls within a nanometre of one of the curve's own vertices, the merged
outline keeps both, 1 DBU apart. In `disk_flip_chip_qubit`, the ground mask
had 1 DBU edges where a claw taper's mask strip crossed the 350 µm clearance
circle, at 3 of 60 landing spans
([#63](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/63)).

![**Problem.** A strip 14.672 µm wide (on the grid) run into a 128-point disk.
Its edges cross the disk's outline about 0.5 nm from a vertex. The right panel zooms on
the top crossing, where the merge leaves an edge of 1 DBU (marked).](../_static/images/contributing/r14-problem.svg)

![**Result.** The disk sampled from the crossing angle, with the strip ending on
that vertex. The right panel shows the same place, with no short edge.](../_static/images/contributing/r14-result.svg)

```python
def short_edges(component):
    """Edges of the merged layer shorter than 2 DBU (pass all three arguments to with_length)."""
    return merged(component).edges().with_length(0, 2, False)


def strip_across_disk(half_width):  # don't: the merge computes the crossing
    c = gf.Component()
    c.add_polygon(disk(128), layer=LAYER)
    c.add_polygon([(0, -half_width), (80, -half_width), (80, half_width), (0, half_width)], layer=LAYER)
    return c


def strip_on_shared_vertices(half_width):  # do: the crossing is a vertex of both
    c = gf.Component()
    crossing = math.degrees(math.asin(half_width / RADIUS))
    segments = math.ceil((360 - 2 * crossing) / (360 / 128))  # about the same step as before
    body = arc(RADIUS, crossing, 360 - crossing, segments)  # starts and ends on the crossings
    c.add_polygon(body, layer=LAYER)
    top, bottom = body[0], body[-1]
    c.add_polygon([bottom, (80, bottom[1]), (80, top[1]), top], layer=LAYER)
    return c


assert short_edges(strip_across_disk(7.336)).count() == 2  # at (49.459, ±7.336) µm
assert short_edges(strip_on_shared_vertices(7.336)).count() == 0
```

The shared-vertex build adds no short edge of its own at other widths: over
500 on-grid half widths from 0.04 µm to 20 µm it leaves none.

```python
HALF_WIDTHS = [round(0.04 * step, 3) for step in range(1, 501)]
assert all(short_edges(strip_on_shared_vertices(h)).count() == 0 for h in HALF_WIDTHS)
```

**How to check.** `construction_report` reports every edge shorter than 2 DBU
with its position ([R8](construction-checks.md)). Build the cell at the
parameter values where a cut crosses a curve near a vertex, as well as at the
defaults.

```python
report = construction_report(strip_across_disk(7.336))[LAYER]
assert report.min_edge_dbu < 2
assert construction_report(strip_on_shared_vertices(7.336))[LAYER].min_edge_dbu >= 2
```
