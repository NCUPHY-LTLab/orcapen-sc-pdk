---
title: "Construction checks"
sidebar: development
page-navigation: true
---

"It looks right" is not evidence: a 1 nm gap, a 1 nm edge or a notch of a
few square micrometres is invisible at the scale you view a cell at. The
construction checks read the built cell and say whether the code drew the
polygons it meant. They live in `tests/geometry_checks.py`, and a cell's test
calls `construction_report`.

Run this page's examples with
`uv run pytest tests/test_docs_construction_examples.py -k construction-checks`. They
run in order and share this setup. The test puts `tests/` on the import path, where
`geometry_checks` lives.

```python
import gdsfactory as gf
from orcapen_sc_pdk import activate
from orcapen_sc_pdk.helpers.layout.geometry import polar_point

from geometry_checks import MIN_EDGE_DBU, construction_report  # tests/geometry_checks.py

activate()
LAYER = (1, 0)


def box(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def merged(component):
    return component.get_region(LAYER, merge=True)
```

## R18. Run `construction_report` on every build the cell supports {#r18}

**Rule.** In the cell's test, assert that `construction_report` finds no
defect on every build the cell supports.

- Build the cell at its defaults, at the boundary values of its supported range
  and their combinations, and at both curve samplings.
- Assert no defect: every conductor one valid polygon, no edge shorter than
  2 DBU, only the holes you meant, and the shape you meant where you can
  state it.

The 2 DBU floor matters beyond tidiness. SCGSim builds the outline it is given
and does not remove short edges, so the mesher has to resolve a 1 nm edge with
elements that small: with the 1 nm edges of the zero-width slits in the
disk-qubit claw present, one measured run of the disk qubit ended without a
usable mesh, and a 0.136 µm edge left at a claw corner forced small mesh
elements (SCGSim
[Known Geometry Problems](https://github.com/NCUPHY-LTLab/scgsim/blob/develop/docs/known-geometry-problems.qmd),
C2 to C4; [#47](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/47)).

`construction_report(component)` flattens the cell and reports, per layer:

- every drawn polygon and every polygon of the merged layer that intersects or
  touches itself, repeats a vertex, has an edge shorter than `MIN_EDGE_DBU`
  (2 DBU, 2 nm here), or runs out and back to form a spike or a zero-width slit;
- the holes of the merged layer, as a region, to compare with the cut-outs you
  drew on purpose;
- the smallest interior angle, which is reported and has no threshold yet;
- with `conductors={layer: n}`, a defect when the merged layer does not hold
  exactly `n` polygons, so a conductor that fell apart is found;
- with `intended={layer: region}`, a defect where the merged layer differs from
  the shape you meant (the XOR). Differences no wider than 2 DBU are grid
  rounding and are left out; a gap that narrow is found by the polygon count.

DBU (database unit) is the integer grid GDS stores; 1 DBU is 1 nm in this PDK.

![**Problem.** A conductor rounded part by part, so it has notches where its
parts meet. It is one polygon, with no hole and no short edge, so a check of
holes and edge lengths alone passes it.](../_static/images/contributing/en/r18-problem.svg)

![**Result.** The same conductor checked against its intended shape. Red marks
the difference `construction_report` reports: the notches.](../_static/images/contributing/en/r18-result.svg)

The two defects below pass a check of holes and edge lengths alone. The first
is a conductor split in two by a 1 nm gap
([R1](grid-and-polygons.md#r1)); the second is the notched conductor of
[R5](one-outline.md#r5).

```python
def split_conductor():
    """Two parts that share an off-grid edge at x = 9.3643 µm, each rotated by 315° and moved."""
    c = gf.Component()
    for x0, x1, height in [(0, 9.3643, 3.3), (9.3643, 16.7689, 6.1)]:
        part = gf.Component()
        part.add_polygon(box(0, 0, x1 - x0, height), layer=LAYER)
        ref = c << part
        ref.drotate(315)
        ref.dmove(polar_point(x0, 315))
    return c


def rounded(*boxes):
    c = gf.Component()
    for corners in boxes:
        c.add_polygon(box(*corners), layer=LAYER)
    radius = gf.kcl.to_dbu(3)
    return merged(c).rounded_corners(radius, radius, 64)


notched = gf.Component()
notched.add_polygon((rounded((0, 0, 20, 10)) + rounded((20, 0, 30, 10))).merged(), layer=LAYER)
meant = rounded((0, 0, 20, 10), (20, 0, 30, 10))


def holes_and_edges_pass(component):  # too weak on its own
    report = construction_report(component)[LAYER]
    return report.holes.is_empty() and report.min_edge_dbu >= MIN_EDGE_DBU


assert holes_and_edges_pass(split_conductor())
assert holes_and_edges_pass(notched)
```

With the polygon count and the intended shape, the report finds both:

```python
split = construction_report(split_conductor(), conductors={LAYER: 1})[LAYER]
assert split.defects == ("merged: 2 polygons for 1 conductor(s)",)

notches = construction_report(notched, intended={LAYER: meant})[LAYER]
assert len(notches.defects) == 1 and "differs from the intended shape" in notches.defects[0]
assert round(notches.difference.area() * gf.kcl.dbu**2, 3) == 7.702  # µm²
```

### Name every hole you meant

When a cell has holes on purpose, compare the merged holes with the cut-outs
you drew, not only their number: a cut-out moved sideways keeps the same
count.

```python
def plate_with_cutout(x0):
    """A 10 µm plate with one 1 µm square cut-out at x0…x0 + 1, y 2…3."""
    c = gf.Component()
    for corners in [(0, 0, 10, 2), (0, 3, 10, 10), (0, 2, x0, 3), (x0 + 1, 2, 10, 3)]:
        c.add_polygon(box(*corners), layer=LAYER)
    return c


cutout = gf.kdb.Region(gf.kdb.DBox(2, 2, 3, 3).to_itype(gf.kcl.dbu))  # the cut-out you meant
assert (construction_report(plate_with_cutout(2))[LAYER].holes ^ cutout).is_empty()
moved = construction_report(plate_with_cutout(6))[LAYER].holes
assert moved.count() == 1 and not (moved ^ cutout).is_empty()  # same count, wrong place
```

### In a cell's test

`tests/test_disk_qubit.py::test_every_polygon_is_drawn_as_meant` is the
pattern: it builds `disk_flip_chip_qubit` at its defaults and at the
boundary values named in its Issue, with both curve samplings, and for every
layer asserts no defect, no edge below 2 DBU, and holes equal to the
ground openings it names. It prints the smallest interior angle for the PR.

**How to check.** The test fails when a defect appears. A cell without such a
test has no construction evidence; add one when you add or change the cell.
