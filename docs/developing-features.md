---
title: "Contributing"
sidebar: development
---

Contribute reusable cells, process records, examples, or documentation through
the [public repository](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk).
Start with the part of the PDK your change affects.

## Set up a development checkout

```bash
git clone https://github.com/NCUPHY-LTLab/orcapen-sc-pdk.git
cd orcapen-sc-pdk
uv sync -p 3.12
```

This installs the PDK plus the development tools, pytest and Ruff. Then set up
the viewer you use. GDSFactory+ is optional and needs a paid subscription.

**Without GDSFactory+**: install [KLayout](https://www.klayout.de/) and its
klive plugin. Previews then open in KLayout.

**With GDSFactory+**: open the checkout in VS Code with the GDSFactory+
extension (version 2.3 or later) and choose **Setup Automatically** in
**GF+ Settings → Status**. The extension installs its SDK and the packages its
worker needs, including the SPICE packages InSpice and vacask, into `.venv`.
GDSFactory+ requires Python 3.12.

- These packages are not in `uv.lock`, so a later `uv sync` removes them.
  Choose **Setup Automatically** again to reinstall them.
- The extension also adds a `[tool.uv]` block marked "Managed by GDSFactory+"
  to `pyproject.toml` and updates `uv.lock`. Keep those edits local and leave
  them out of commits: they limit the lock file to Linux x86-64 for everyone.

Check: `uv run python --version` reports a supported Python version.
For documentation dependencies and preview, use
[Documentation & Website](docs-publishing.md).

## Preview a component

Every cell module ends with a preview block. Run the file directly, for example
with **Run Python File** in VS Code:

```bash
uv run python orcapen_sc_pdk/cells/layout/resonator.py
```

To preview any registered cell by name:

```bash
uv run python -m orcapen_sc_pdk.preview resonator
```

Both write `build/gds/<cell>.gds` and open it. Inside a VS Code terminal with
GDSFactory+ installed, the file opens in the GDSFactory+ Layout Viewer.
Otherwise it is sent to KLayout through klive. Pass `--viewer klayout` or
`--viewer gdsfactoryplus` to choose explicitly. In a new cell module, end with
the same block:

```python
if __name__ == "__main__":
    # Imported here because orcapen_sc_pdk.pdk imports this module.
    from orcapen_sc_pdk.preview import show

    show(my_cell)
```

## Keep changes focused

- Put reusable layout and process definitions in OrcaPen.
- Reuse GDSFactory for component composition and routing.
- Decorate cells with plain `@gf.cell`, the only form GDSFactory+ discovers. A
  cell with curves takes `curve_sampling: CurveSampling = FABRICATION` and passes it
  to nested cells and curve helpers; see [Curve sampling](usage/curve-sampling.md).
- Use SCGSim for simulation preparation, solver integration, and returned results.
- Keep private layouts, parameters, and run directories in the consuming project.

Inspect the relevant existing source and examples before introducing a new
interface. Keep the related documentation next to the public behavior it describes.

## Build cell geometry

A cell is correct when its polygons are the shapes you meant to draw. These
rules say how to build geometry so that it is, how to check it, and where a
cell may live before it joins the Library. Each construction rule comes
from a measured failure. Reviewers check a cell against them.

The examples below run against the installed GDSFactory. They share this
helper, which merges a layer the way a mask writer would and reports what is
left. GDS stores no holes, so a hole in the merged region is drawn as a cut
line.

```python
import math

import gdsfactory as gf
from kfactory import kdb
from orcapen_sc_pdk import activate

activate()
LAYER = (1, 0)


def report(component, layer=LAYER):
    """Polygons, holes, shortest edge (DBU) and smallest interior angle after merging."""
    index = component.kcl.layout.layer(*layer)
    region = kdb.Region(component.begin_shapes_rec(index)).merged()
    edges, angles = [], []
    for polygon in region.each():
        for i in range(-1, polygon.holes()):  # -1 is the outer contour
            points = list(polygon.each_point_hull() if i < 0 else polygon.each_point_hole(i))
            for before, here, after in zip(points[-1:] + points[:-1], points, points[1:] + points[:1]):
                incoming = (here.x - before.x, here.y - before.y)
                outgoing = (after.x - here.x, after.y - here.y)
                edges.append(math.hypot(*outgoing))
                turn = math.atan2(
                    incoming[0] * outgoing[1] - incoming[1] * outgoing[0],
                    incoming[0] * outgoing[0] + incoming[1] * outgoing[1],
                )
                angles.append(180 + math.degrees(turn))  # KLayout keeps material on the right
    return {
        "polygons": region.count(),
        "holes": sum(polygon.holes() for polygon in region.each()),
        "min_edge_dbu": round(min(edges), 1),
        "min_angle_deg": round(min(angles), 1),
    }
```

### Construction rules

**R1. Draw one rigid shape in one frame, then rotate, then move.** Draw every
part of a rigid shape in a single local frame, with shared edges on shared
coordinates. Then `ref.drotate(angle)`, then `ref.dmove(offset)`. Rotating and
moving the parts separately rounds each shared edge on its own, so a conductor
can fall apart. Depending on the dimensions, the shared edge splits the
conductor into two polygons (as at 315° and 17.3° below) or leaves an edge of 1 DBU.

```python
PARTS = [(0, 9.3643, 3.3), (9.3643, 16.7689, 6.1)]  # x0, x1, height; share x = 9.3643


def rect(x0, x1, height):
    return [(x0, 0), (x1, 0), (x1, height), (x0, height)]


def separately(angle):  # don't: each part gets its own rotation and move
    c, t = gf.Component(), math.radians(angle)
    for x0, x1, height in PARTS:
        part = gf.Component()
        part.add_polygon(rect(0, x1 - x0, height), layer=LAYER)
        ref = c << part
        ref.drotate(angle)
        ref.dmove((x0 * math.cos(t), x0 * math.sin(t)))
    return c


def together(angle):  # do: one frame, then rotate, then move
    shape = gf.Component()
    for part in PARTS:
        shape.add_polygon(rect(*part), layer=LAYER)
    c = gf.Component()
    ref = c << shape
    ref.drotate(angle)
    ref.dmove((5, 5))
    return c


for angle in (315, 17.3):
    print(angle, "separately", report(separately(angle)))
    print(angle, "together  ", report(together(angle)))
```

Parts that are one straight conductor of one width are the exception to
"several parts": a same-width route and its extensions are one outline, not
rectangles joined along a side that is meant to be common. A metal and the
mask around it (for example a CPW mask) share the path and cross-section
dimensions, the local anchors and the endpoint definitions. Where the mask runs
past the metal, author the mask's whole side from those anchors, and keep the
metal endpoint and its port where they were.

**R2. Move then rotate only to place something on a circle.** `drotate` turns
about the parent origin, not about the part. Move and then rotate when you mean
polar placement, and say so in a comment. To turn a part where it stands, pass
its centre.

```python
rect_cell = gf.components.rectangle(size=(4, 2), layer=LAYER)
c = gf.Component()
ref = c << rect_cell
ref.dmove((10, 0))
ref.drotate(90)  # polar placement: the part swings to x=-2..0, y=10..14
print(ref.dbbox())

c = gf.Component()
ref = c << rect_cell
ref.dmove((10, 0))
ref.drotate(90, center=ref.dcenter)  # in place: the part stays around (12, 1)
print(ref.dbbox())
```

**R3. Rotate and mirror references, never a shared cell.** A cell built by a
`@gf.cell` factory is cached and shared by every caller. Transform the
reference you got from `c << cell`. GDSFactory refuses to modify the cached
cell itself, and a cell that does not refuse would change for every user.

```python
try:
    rect_cell.drotate(30)  # don't: rect_cell is the cached cell
except RuntimeError as error:
    print("refused:", error)
```

**R4. Mirror, then rotate, and verify one marker port.** Mirror and rotation do
not commute: at 30° the two orders end 60° apart. Pick the order on purpose,
name the mirror axis in a comment, and after composing check the orientation of
one marker port.

```python
marker = gf.Component()
marker.add_polygon([(0, 0), (4, 0), (0, 2)], layer=LAYER)
marker.add_port("m", center=(4, 0), width=1, orientation=0, layer=LAYER)

c = gf.Component()
ref = c << marker
ref.dmirror_y()  # mirror across the x axis
ref.drotate(30)
print("mirror, rotate:", ref.ports["m"].orientation)  # 30

c = gf.Component()
ref = c << marker
ref.drotate(30)
ref.dmirror_y()
print("rotate, mirror:", ref.ports["m"].orientation)  # 330, not 30
```

**R5. Where an edge meets a curve, run the edge into the body.** Extend the
straight sides into the body, or reuse the body's own vertices. Do not sample a
second arc on the same radius to "meet" the first, and do not nudge it by a
few nanometres: two samples of one ideal curve do not coincide on the grid, and
the slivers between them become holes. Joins that must share an arc use the
same sampling angles and the same anchors.

```python
def arc(radius, n, start=0.0, stop=360.0, closed=False):
    step = (stop - start) / n
    angles = [math.radians(start + i * step) for i in range(n + closed)]
    return [(radius * math.cos(a), radius * math.sin(a)) for a in angles]


def lead_on_disk(disk_points, lead_ends_on_arc_points=None):
    c = gf.Component()
    c.add_polygon(arc(50, disk_points), layer=LAYER)
    if lead_ends_on_arc_points:  # don't: a second sampling of the same circle
        landing = arc(50, lead_ends_on_arc_points, -20, 20, closed=True)
        c.add_polygon([(80, -8), (80, 8)] + landing[::-1], layer=LAYER)
    else:  # do: the lead's sides run straight into the disk
        c.add_polygon([(80, -8), (80, 8), (40, 8), (40, -8)], layer=LAYER)
    return c


print("separate arc:", report(lead_on_disk(128, 100)))
print("into the body:", report(lead_on_disk(128)))
```

**R6. Union first, round once, keep square ends by extending and clipping.**
Round a conductor after all of its parts are unioned. Rounding a part and then
adding more geometry leaves dents where the rounded corner meets the new part.
To keep a square end, extend the outline past the end and clip it back. Do not
limit rounding with circular windows. The disk-qubit claw spike came from
rounding the claw and then unioning a taper onto it.

```python
dbu = 1000  # DBU per micrometre in this PDK


def box(x0, y0, x1, y1):
    return kdb.Region(kdb.Box(x0 * dbu, y0 * dbu, x1 * dbu, y1 * dbu))


def rounded(region, radius=3):
    return region.rounded_corners(radius * dbu, radius * dbu, 64)


left, right = box(0, 0, 20, 10), box(20, 0, 30, 10)
dont = (rounded(left) + rounded(right)).merged()  # round, then add
do = rounded((left + right).merged())             # union, then round once
print("area that differs, um2:", (dont ^ do).area() / dbu**2)  # dents at x = 20
```

**R7. Add an input check only when the construction cannot be made robust.**
First try to fix the construction. Add a check only for an input the geometry
cannot support, give it an error test, and state the supported range in the
cell's documentation. Do not hide a fixable construction behind a parameter
limit: limiting an angle alone left 16–93 nm jogs in the claw. Do not hide a
symptom by quietly adding overlap, snapping globally, simplifying or repairing
the geometry afterwards. A smaller DBU or more points on the circle does not
cure a construction cause either: the R5 join above still fails with eight
times the points.

```python
def span_deg_checked(span_deg):
    if not 0 < span_deg <= 60:  # do: reject what the construction cannot make
        raise ValueError(f"span_deg must be in (0, 60], got {span_deg}")
    return span_deg  # don't: min(span_deg, 40), which changes the design silently


try:
    span_deg_checked(61)
except ValueError as error:  # a test asserts this error with pytest.raises
    print("rejected:", error)

print("1024 points:", report(lead_on_disk(1024, 800)))  # holes remain
```

**R8. Run the construction checks after each build.** "It looks right" is not
evidence. In a test, build the cell at its defaults and at the corners of the
supported range, then assert that no hole is unintended, that no edge is
shorter than 2 DBU, and print the smallest interior angle. The angle has no
threshold yet, so it is reported and not asserted. Name every hole that is
meant to be there. The check takes about 0.02 s on the default disk qubit and
found both defects above.

```python
component = together(315)
result = report(component)
intended_holes = 0  # name each cut-out you drew on purpose, per layer
assert result["holes"] == intended_holes
assert result["min_edge_dbu"] >= 2
print("min interior angle (reported only):", result["min_angle_deg"])
```

### Helpers and structure

PDK maintainers decided these rules. They keep cell files short to review and
let one fix reach every cell that shares a part.

**H1. Reuse before you write.** Draw with what exists, in this order:

1. `orcapen_sc_pdk.helpers`, for example `polar_point` and `rotate_point`
   instead of inline `cos` and `sin`, `merge_component_layers` and
   `add_etch_for_component`.
2. The PDK's cells and primitives in `orcapen_sc_pdk/cells/layout/primitives.py`
   (`bend_euler`, `rounded_rectangle`, `wire_corner` and others); see
   [Shared layout primitives](public-pdk-examples/shared-primitives.md).
3. The public GDSFactory API.

When an existing function does not fit, name it and say why in the PR.

**H2. A new function needs approval first.** Any new function that is not a
`@gf.cell` component needs the PDK maintainers' approval on the Issue or PR
before you write it. This holds whether the function is private to a cell file
or shared under `helpers/`. The PR lists each new function and why the existing
ones do not fit. Existing private functions are reviewed when their cell is
next rewritten.

**H3. Structure matters more than length.** A long cell file is acceptable. A
part that is reusable, previewable or simulated on its own becomes its own
`@gf.cell`, in its own module when another cell uses it. Write the cell body in
the order of its physical parts, with a short comment heading for each part.

### Three kinds of check

The checks answer different questions, have different owners and reach different
users. Keep them apart: a pass on one says nothing about the others.

| Kind | Asks | Owner | Reach |
|---|---|---|---|
| Construction checks | Did the code draw what it meant? No unintended holes, no edge shorter than 2 DBU, minimum interior angle reported | This PDK, in its tests | Run in each PDK cell's tests, starting with the disk flip-chip qubit; other cells gain them as their tests are added. Opt-in for other layouts |
| Process design rules (DRC) | Can the process make it? Width, spacing and enclosure per layer | This PDK | Opt-in. Consumers may adopt, change or ignore them |
| Simulation checks | Can the solver model it? | [SCGSim](https://github.com/NCUPHY-LTLab/scgsim) | Defined and run by SCGSim, not by this PDK |

Consumers of the PDK are not required to follow the process rules.

### Record a process rule

No process rule is invented. A rule enters only with a source supplied by the
PDK maintainers, and each rule records:

- **Source**: where the number comes from.
- **Layer**: the layer or layer pair it applies to.
- **Value**: the number and its unit.
- **Status**: `proposed` or `adopted`.

The page that lists process rules, and the code that checks them, are added
together with the first sourced rule.

### Candidate cells

This repository's `develop` branch holds no candidate cells. It is what
consumers pin and what GDSFactory+ lists, so a candidate there becomes
something others can depend on. A candidate lives on its Issue branch. The
PDK maintainers may merge it into a personal branch to preview it. Personal branches
here are public, so a candidate that carries a private design starts in the
private layout repository instead.

## Submit a change

Describe the behavior changed, the affected public interfaces, and the checks
you ran in a pull request. Keep saved scientific results associated with their
original model and runtime; editing a tutorial does not rerun it.

See [Workspace & Related Packages](home/ecosystem-workspace.md) for package roles,
[SCGSim integration](features/scgsim-integration.md) for the source/runtime boundary,
and [Documentation & Website](docs-publishing.md) for notebook pairing and deployment.
