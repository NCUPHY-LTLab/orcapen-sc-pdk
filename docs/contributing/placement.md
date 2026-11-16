---
title: "Placement and transform order"
sidebar: development
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

The examples on this page run on their own, in order. They share this setup.

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

## R2. Turn a part in place about its centre; place it on a circle on purpose {#r2}

**Rule.** To turn a part where it stands, pass its centre:
`ref.drotate(angle, center=ref.dcenter)`. To place a part on a circle, turn it
first and then move it to `polar_point(radius, angle)`.

`ref.drotate(angle)` without a centre turns the part about the origin of the
cell it is placed in, so a part that was moved there first swings around that
origin. That is right only when you mean to put the part on a circle about
the origin, and then the code should say so.

![**Problem.** A 4 × 2 µm part moved to x = 10 µm and then turned by 90° about
the origin: it swings to x = −2…0 µm, y = 10…14 µm. The dashed outline is
where it was meant to turn.](../_static/images/contributing/r2-problem.svg)

![**Result.** The same part turned by 90° about its own centre stays around
(12, 1) µm.](../_static/images/contributing/r2-result.svg)

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

## R3. Transform references, never a shared cell {#r3}

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

## R4. Mirror and rotate do not commute: connect a mirrored part to its port {#r4}

**Rule.** A mirror followed by a rotation is not the same as the rotation
followed by the mirror. Place a mirrored part with
`ref.connect(port, target, mirror=True)`, which sets both from the port it must
meet, and check one port's orientation.

At 30° the two orders end 60° apart. Writing them by hand invites the wrong
one, and an asymmetric part shows it only on close inspection.

![**Problem.** An L-shaped marker mirrored across the x axis and rotated by
30°, in the two orders: teal mirrors first, amber rotates first. The arrows are
its port `m`: 30° in the first order, 330° in the second.](../_static/images/contributing/r4-problem.svg)

![**Result.** The marker connected with `mirror=True` to a target port (grey
arrow) that faces 210°: its port `m` (dark arrow) sits on the target and faces
30°, opposite it.](../_static/images/contributing/r4-result.svg)

```python
marker = gf.Component()
marker.add_polygon([(0, 0), (4, 0), (4, 1), (1, 1), (1, 3), (0, 3)], layer=LAYER)  # an L, so a mirror shows
marker.add_port("m", center=(4, 0.5), width=1, orientation=0, layer=LAYER)


def mirrored_and_rotated(mirror_first):
    c = gf.Component()
    ref = c << marker
    if mirror_first:
        ref.dmirror_y()  # across the x axis
        ref.drotate(30)
    else:
        ref.drotate(30)
        ref.dmirror_y()
    return c, ref


assert mirrored_and_rotated(mirror_first=True)[1].ports["m"].orientation == pytest.approx(30)
assert mirrored_and_rotated(mirror_first=False)[1].ports["m"].orientation == pytest.approx(330)

target = gf.Component()
target.add_port("t", center=(10, 10), width=1, orientation=210, layer=LAYER)


def connected_mirrored():
    c = gf.Component()
    anchor = c << target
    ref = c << marker
    ref.connect("m", anchor.ports["t"], mirror=True)
    return c, ref


connected = connected_mirrored()[1]
assert connected.ports["m"].orientation == pytest.approx(30)
# connect rounds the placement to the grid, so the port lands within 1 nm of the target (R13)
assert tuple(connected.ports["m"].dcenter) == pytest.approx((10, 10), abs=0.001)
```

**How to check.** After composing, assert the orientation and position of one
port of the mirrored part with `pytest.approx`, since a rotation by 30° gives
29.999999999999993, not 30.

## R13. Join parts at their ports with `connect`, in the local frame {#r13}

**Rule.** Join two parts by connecting their ports, `ref.connect(port,
other.ports[name])`, rather than by moving each part to a position you
computed. Connect parts whose ports face 0°, 90°, 180° or 270°, and rotate the
merged result once ([R1](one-outline.md#r1)).

A position you compute, such as a centre at half an odd number of nanometres,
is rounded when the part is placed, and the parts can miss each other by
1 nm. `connect` puts one port exactly on the other. The Purcell IDC combs and
tapers were placed by separately rounded centre moves; a comb 63.225 µm wide
(an odd number of DBU) left a 1 nm slit on one side
([#58](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/58), A1, fixed in
[#61](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/pull/61)).

![**Problem.** A 63.225 µm comb moved by half its width and a lead moved to the
comb's computed edge: two polygons. The right panel shows the 1 nm slit.](../_static/images/contributing/r13-problem.svg)

![**Result.** The same lead connected to the comb's port: one polygon. The
right panel shows the same place.](../_static/images/contributing/r13-result.svg)

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
the port that you connect to is off the grid, and the rounded part can miss it
by 1 nm. A bar 9.364 µm long and 3.3 µm wide, rotated in steps of 0.3°, with a
6.1 µm wide bar connected to its end, falls into two polygons at 312 of 1200
angles.

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


ANGLES = [step * 0.3 for step in range(1200)]
assert sum(polygons(connected_at(angle)) > 1 for angle in ANGLES) == 312
```

**How to check.** Count the merged polygons of each conductor in the cell's
test ([R8](construction-checks.md)): a 1 nm slit splits a conductor in two.
