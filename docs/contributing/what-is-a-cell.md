---
title: "What is a cell"
sidebar: development
---

A cell is a function decorated with `@gf.cell` that builds one component from
its parameters. GDSFactory caches it, GDSFactory+ lists it, and other cells
place it by reference: a placement of the shared cell with its own position,
rotation and mirror. These four rules say what becomes a cell, what you
build it from, and how its code is laid out. The PDK maintainers set them;
reviewers check a new cell against them before the
[construction rules](rules.md).

## H1. Reuse before you write {#h1}

**Rule.** Build with what already exists, in this order, and name in the PR any
existing function that did not fit and why.

1. **The PDK's cells and primitives**: the registered cells and
   `orcapen_sc_pdk/cells/layout/primitives.py` (`bend_euler`,
   `rounded_rectangle`, `wire_corner` and others); see
   [Shared layout primitives](../public-pdk-examples/shared-primitives.md).
2. **The GDSFactory public API**: `gf.components`, `gf.path`,
   `gf.cross_section`, `Component.get_region`, `gf.boolean` and `connect`.
   Use `gf.kdb` for KLayout's geometry types and `gf.kcl.dbu` and
   `gf.kcl.to_dbu` for the grid, rather than importing KLayout or kfactory
   yourself.
3. **The PDK helpers**: `orcapen_sc_pdk.helpers.layout` and
   `orcapen_sc_pdk.curve_sampling`. For example, `polar_point` and
   `rotate_point` replace an inline `cos` and `sin`.

These imports work as written:

```python
import gdsfactory as gf
import pytest
from orcapen_sc_pdk.curve_sampling import FABRICATION, circle_segments
from orcapen_sc_pdk.helpers.layout import add_etch_for_component, merge_component_layers
from orcapen_sc_pdk.helpers.layout.geometry import polar_point, rotate_point

assert polar_point(10, 90) == pytest.approx((0, 10))  # radius, angle in degrees
assert rotate_point((10, 0), 90) == pytest.approx((0, 10))  # about the origin
assert gf.kcl.to_dbu(1.5) == 1500  # 1 DBU is 1 nm
assert circle_segments(50, FABRICATION) > 0  # points per circle for this radius and sampling
```

## H2. List new helper functions on the Issue for one approval {#h2}

**Rule.** Every new function that is not a `@gf.cell` is listed once on the
Issue, and the PDK maintainers approve the list once before you write them.

The list says, for each function, what it does and why no existing one fits
(H1). This holds whether the function stays private to one cell file or is
shared under `orcapen_sc_pdk/helpers/`. Two kinds need no approval:

- a small file-local wrapper of one expression;
- a test helper.

Existing private functions are reviewed when their cell is next rewritten.

## H3. A part is a cell when it is a component in its own right {#h3}

**Rule.** Make a part a `@gf.cell` when it is a component in its own right;
make it a helper function applied to a host component when its shape or
position derives from that host.

A part is a component in its own right when:

- its shape comes from its own parameters, not from a component it is
  attached to;
- it has ports where other parts connect;
- it can be fabricated and simulated as that element, for example a bend, a
  launcher, an interdigital capacitor or a resonator.

Routing pieces such as bends are therefore cells: they stand alone and carry
ports.

A part derives from a host when it changes the host at one of the host's ports
or along its outline, for example the open-end termination at a CPW port or
the etch drawn around a conductor. Such a part is a helper function that takes
the host, as `add_etch_for_component` does.

Do not wrap a GDSFactory component in a PDK cell unless the PDK adds geometry
or meaning to it (H1).

## H4. Structure matters more than length {#h4}

**Rule.** Write the cell body in the order of its physical parts, each under a
short comment heading; a long cell file is acceptable.

A reader follows a cell by its parts, so the order of the code is the order
of the parts in the layout. A part that becomes a cell (H3) moves into its own
module when another cell uses it, so one fix reaches every cell that shares
it.
