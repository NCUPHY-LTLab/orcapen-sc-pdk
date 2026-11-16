---
title: "Placement and transform order"
sidebar: development
page-navigation: true
---

A cell places its parts as references: `ref = c << part` puts the cell `part`
into `c` without copying it, and `ref.drotate`, `ref.dmirror_y`, `ref.dmove`
and `ref.connect` set where it goes. These rules say which transform to use and
in which order, because the order changes the result.

Terms used here:

- **Reference**: one placement of a cell inside another, with its own rotation,
  mirror and position. The cell itself is shared.
- **Port**: a named point on a cell's edge, with a width and an orientation in
  degrees, where another part connects.
- **DBU** (database unit): the integer grid GDS stores; 1 DBU is 1 nm here.

Run this page's examples with
`uv run pytest tests/test_docs_construction_examples.py -k placement`. They
run in order and share this setup.

```python
import gdsfactory as gf
import pytest
from orcapen_sc_pdk import activate
from orcapen_sc_pdk.helpers.layout.geometry import polar_point

activate()
LAYER = (1, 0)


def box(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def bounds(ref):
    return ref.dxmin, ref.dxmax, ref.dymin, ref.dymax
```


## R7. Turn a part about its own centre; to place it on a circle, turn it at the origin and move it out {#r7}

**Rule.** Turn a part where it stands with `ref.drotate(angle, center=ref.dcenter)`;
to place a part on a circle, turn it while it is centred on the origin, then
move it to `polar_point(radius, angle)`.

`ref.drotate(angle)` without a centre turns the part about the origin of the
cell it is placed in, so a part that was moved away from the origin first
swings around it.

![**Problem.** A 4 × 2 µm part (dashed: where it starts) moved to x = 10 µm
and then turned by 90° without a centre: it swings about the origin (the cross)
along the arc to x = −2…0 µm, y = 10…14 µm.](../_static/images/contributing/en/r7-problem.svg)

![**Result.** The same part turned by 90° about its own centre: it stays
around (12, 1) µm. Both figures use the same axes.](../_static/images/contributing/en/r7-result.svg)

```python
part = gf.components.rectangle(size=(4, 2), layer=LAYER)


def turned(about_centre):
    c = gf.Component()
    ref = c << part
    ref.dmove((10, 0))
    if about_centre:
        ref.drotate(90, center=ref.dcenter)  # do: turns in place
    else:
        ref.drotate(90)  # turns about the parent's origin
    return c, ref


assert bounds(turned(about_centre=False)[1]) == pytest.approx((-2, 0, 10, 14))
assert bounds(turned(about_centre=True)[1]) == pytest.approx((11, 13, -1, 3))
```

Placing on a circle reads as two steps: turn a part that is centred on the
origin, then move it out along the angle.

```python
spoke = gf.components.rectangle(size=(4, 2), centered=True, layer=LAYER)


def on_a_circle(radius, angles):
    c = gf.Component()
    for angle in angles:
        ref = c << spoke
        ref.drotate(angle)  # centred on the origin, so this turns it in place
        ref.dmove(polar_point(radius, angle))
    return c


ring = on_a_circle(20, (0, 90, 180, 270))
centres = [tuple(ref.dcenter) for ref in ring.insts]
assert centres == pytest.approx([(20, 0), (0, 20), (-20, 0), (0, -20)])
```

**How to check.** Assert the placed part's bounds with `ref.dxmin`, `ref.dxmax`,
`ref.dymin` and `ref.dymax`, or its port positions, in the cell's test.

## R8. Transform references, never a shared cell {#r8}

**Note.** A cell built by a `@gf.cell` factory is cached: every caller with the
same arguments gets the same cell. GDSFactory locks it, so changing it
raises an error instead of changing it for every user. Transform the reference
you placed. To change the shape itself, work on a copy:
`editable = cell.copy()`.

```python
with pytest.raises(RuntimeError, match="locked"):
    part.drotate(30)  # part is the cached rectangle cell

editable = part.copy()
editable.add_polygon(box(0, 0, 1, 1), layer=LAYER)  # a copy is not locked
```

This is a note, not a construction rule with a figure: GDSFactory already
enforces it.

## R9. Place a mirrored part with `connect(..., mirror=True)` {#r9}

**Rule.** Place a mirrored part with `ref.connect(port, target, mirror=True)`,
which sets the mirror and the rotation from the port it must meet, rather than
writing the mirror and the rotation by hand.

A mirror followed by a rotation is not the same as the rotation followed by
the mirror: at 30° the two orders end 60° apart. Written by hand, the wrong
order still puts the part at the right place, and an asymmetric part shows the
mistake only on close inspection.

![**Problem.** An L-shaped marker that must meet the target port (grey arrow,
facing 210°). Written by hand as "rotate by 30°, mirror across the x axis,
move", its port `m` (dark arrow) lands on the target but faces 330° instead of
30°.](../_static/images/contributing/en/r9-problem.svg)

![**Result.** The same marker placed with `connect(..., mirror=True)`: its port
lands on the same target and faces 30°, opposite it.](../_static/images/contributing/en/r9-result.svg)

```python
marker = gf.Component()
marker.add_polygon([(0, 0), (4, 0), (4, 1), (1, 1), (1, 3), (0, 3)], layer=LAYER)  # an L, so a mirror shows
marker.add_port("m", center=(4, 0.5), width=1, orientation=0, layer=LAYER)

target = gf.Component()
target.add_port("t", center=(10, 10), width=1, orientation=210, layer=LAYER)


def placed_by_hand():  # don't: meant "mirror, then rotate", written the other way round
    c = gf.Component()
    anchor = c << target
    ref = c << marker
    ref.drotate(30)
    ref.dmirror_y()  # across the x axis
    ref.dmove(tuple(ref.ports["m"].dcenter), tuple(anchor.ports["t"].dcenter))
    return c, ref


def placed_by_connect():  # do: the target port sets the mirror and the rotation
    c = gf.Component()
    anchor = c << target
    ref = c << marker
    ref.connect("m", anchor.ports["t"], mirror=True)
    return c, ref


by_hand, by_connect = placed_by_hand()[1], placed_by_connect()[1]
assert by_hand.ports["m"].orientation == pytest.approx(330)  # should face 30°
assert by_connect.ports["m"].orientation == pytest.approx(30)
# connect rounds the placement to the grid, so the port lands within 1 nm of the target (R10)
assert tuple(by_connect.ports["m"].dcenter) == pytest.approx((10, 10), abs=0.001)
```

**How to check.** After composing, assert the orientation and position of one
port of the mirrored part with `pytest.approx`, since a rotation by 30° can give
29.999999999999993 rather than 30.

## R10. Join parts with `connect` at 0°, 90°, 180° or 270°, then rotate the merged result {#r10}

**Rule.** Join two parts by connecting their ports, `ref.connect(port,
other.ports[name])`, while the ports face 0°, 90°, 180° or 270°; merge the
result and rotate it once ([R4](one-outline.md#r4)).

A position you compute, such as a centre at half an odd number of nanometres,
is rounded when the part is placed, and the parts can miss each other by
1 nm. `connect` puts one port exactly on the other. The Purcell IDC combs and
tapers were placed by separately rounded centre moves; a comb 63.225 µm wide
(an odd number of DBU) left a 1 nm slit on one side
([#58](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/58), A1, fixed in
[#61](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/pull/61)).

![**Problem.** A 63.225 µm comb moved by half its width and a lead moved to the
comb's computed edge: two polygons. The right panel shows the 1 nm slit.](../_static/images/contributing/en/r10-problem.svg)

![**Result.** The same lead connected to the comb's port: one polygon. The
right panel shows the same place.](../_static/images/contributing/en/r10-result.svg)

```python
def comb(width):
    c = gf.Component()
    c.add_polygon(box(0, 0, width, 10), layer=LAYER)
    c.add_port("e", center=(width, 5), width=10, orientation=0, layer=LAYER)
    return c


lead = gf.Component()
lead.add_polygon(box(0, -5, 20, 5), layer=LAYER)
lead.add_port("w", center=(0, 0), width=10, orientation=180, layer=LAYER)


def comb_and_lead(width, use_connect):
    c = gf.Component()
    body = c << comb(width)
    body.dmove((-width / 2, 0))  # centred on x = 0
    tail = c << lead
    if use_connect:
        tail.connect("w", body.ports["e"])  # do
    else:
        tail.dmove((width / 2, 5))  # don't: a second, separately rounded position
    return c


def polygons(component):
    return component.get_region(LAYER, merge=True).count()


assert polygons(comb_and_lead(63.225, use_connect=False)) == 2
assert polygons(comb_and_lead(63.225, use_connect=True)) == 1
```

`connect` rounds the joined part's position to the grid. At 0°, 90°, 180° and
270° the ports are on the grid and the parts meet exactly. At any other angle
the port you connect to is off the grid, and the rounded part can miss it by
1 nm. So connect in the local frame, merge, and rotate the outline once:

```python
def bar(length, width):
    c = gf.Component()
    c.add_polygon(box(0, -width / 2, length, width / 2), layer=LAYER)
    c.add_port("w", center=(0, 0), width=width, orientation=180, layer=LAYER)
    c.add_port("e", center=(length, 0), width=width, orientation=0, layer=LAYER)
    return c


def connected_at(angle):  # don't: connect to a port that faces an arbitrary angle
    c = gf.Component()
    first = c << bar(9.364, 3.3)
    first.drotate(angle)
    second = c << bar(7.405, 6.1)
    second.connect("w", first.ports["e"], allow_width_mismatch=True)
    return c


def connected_then_rotated(angle):  # do: connect at 0°, merge, then rotate once
    local = gf.Component()
    first = local << bar(9.364, 3.3)
    second = local << bar(7.405, 6.1)
    second.connect("w", first.ports["e"], allow_width_mismatch=True)
    outline = gf.Component()
    outline.add_polygon(local.get_region(LAYER, merge=True), layer=LAYER)
    c = gf.Component()
    (c << outline).drotate(angle)
    return c


assert polygons(connected_at(2.1)) == 2
assert polygons(connected_then_rotated(2.1)) == 1
```

Swept over 1200 angles in 0.3° steps, `connected_at` falls into two polygons
at 312 angles; `connected_then_rotated` stays one polygon with no edge
shorter than 2 DBU at all 1200. The sweep runs in the guide's test.

**How to check.** Count the merged polygons of each conductor in the cell's
test ([R18](construction-checks.md)): a 1 nm slit splits a conductor in two.
