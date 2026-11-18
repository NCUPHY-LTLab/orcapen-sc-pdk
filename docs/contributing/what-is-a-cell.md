---
title: "What is a cell"
sidebar: development
page-navigation: true
---

A cell is a function decorated with `@gf.cell` that builds one component from
its parameters. GDSFactory caches it, GDSFactory+ lists it, and other cells
place it by reference: a placement of the shared cell with its own position,
rotation and mirror. These four rules say what becomes a cell, what you build
it from, and how its code is laid out. Reviewers check a new cell against them
before the [construction rules](rules.md).

H1, H2 and H4 are rules about code and approval, not about geometry, so they
come with a table or a code example instead of a pair of figures. H3 decides
what a part is, and its figures show the two kinds side by side.

Run this page's example with
`uv run pytest tests/test_docs_construction_examples.py -k what-is-a-cell`.

## H1. Reuse before you write {#h1}

**Rule.** Build with what already exists, in the order of this table, and name
in the PR any existing function that did not fit and why.

| Order | Source | For example |
|---|---|---|
| 1 | The PDK's cells and primitives: the registered cells and `orcapen_sc_pdk/cells/layout/primitives.py`; see [Shared layout primitives](../public-pdk-examples/shared-primitives.md) | `bend_euler`, `rounded_rectangle`, `wire_corner` |
| 2 | The GDSFactory public API | `gf.components`, `gf.path`, `gf.cross_section`, `Component.get_region`, `gf.boolean`, `connect`; `gf.kdb` for KLayout's geometry types, `gf.kcl.dbu` and `gf.kcl.to_dbu` for the grid |
| 3 | The PDK helpers: `orcapen_sc_pdk.helpers.layout` and `orcapen_sc_pdk.curve_sampling` | `polar_point` and `rotate_point` instead of an inline `cos` and `sin`; `add_etch_for_component` |

Import KLayout's types through `gf.kdb` rather than importing KLayout or
kfactory yourself. These imports work as written:

```python
import gdsfactory as gf
import pytest
from orcapen_sc_pdk.curve_sampling import FABRICATION, circle_segments
from orcapen_sc_pdk.helpers.layout import add_etch_for_component, merge_component_layers
from orcapen_sc_pdk.helpers.layout.geometry import polar_point, rotate_point
from orcapen_sc_pdk.pdk import PDK
from orcapen_sc_pdk.tech import LAYER

PDK.activate()
assert polar_point(10, 90) == pytest.approx((0, 10))  # radius, angle in degrees
assert rotate_point((10, 0), 90) == pytest.approx((0, 10))  # about the origin
assert gf.kcl.to_dbu(1.5) == 1500  # 1 DBU is 1 nm
assert circle_segments(50, FABRICATION) > 0  # points per circle for this radius and sampling
```

## H2. List new helper functions on the Issue for one approval by the repository owner {#h2}

**Rule.** List every new function that is not a `@gf.cell` once on the Issue,
and wait until the repository owner approves the list.

The list says, for each function, what it does and why no existing one fits
(H1). The repository owner approves the whole list once.

| Needs the repository owner's approval | Needs none |
|---|---|
| A new function private to one cell file | A small file-local wrapper of one expression |
| A new shared function under `orcapen_sc_pdk/helpers/` | A test helper |

Existing private functions are reviewed when their cell is next rewritten.

## H3. A part is a cell when it is a component in its own right {#h3}

**Rule.** Make a part a `@gf.cell` when it is a component in its own right, and
a helper function applied to a host component when its shape or position comes
from that host.

A part is a component in its own right when:

- its shape comes from its own parameters, not from a component it is
  attached to;
- it has ports, named connection points with a width and a direction, where
  other parts connect;
- it can be fabricated and simulated as that element, for example a bend, a
  launcher, an interdigital capacitor or a resonator.

Routing pieces such as bends are therefore cells: they stand alone and carry
ports. A part comes from a host when it changes the host at one of the host's
ports or along its outline, for example the open end at a CPW port or the etch
drawn around a conductor. Such a part is a helper function that takes the
host, as `add_etch_for_component` does.

![**A cell.** The PDK's `bend_euler`: its shape comes from its own radius and
cross-section, and its two ports (arrows) are where other parts connect.](../_static/images/contributing/en/h3-cell.svg)

![**A helper on a host.** A 40 µm CPW straight with an open end added at its
port `o2` (arrow): the ground clearance runs 6 µm past the port, as wide as the
host's port plus its gaps.](../_static/images/contributing/en/h3-helper.svg)

```python
bend = PDK.get_component("bend_euler")  # a cell: its own parameters, its own ports
host = PDK.get_component("straight", length=40)


def add_open_end(host, port_name, gap=6.0):
    """Clear the ground `gap` µm past one of the host's ports; the cap's size comes from that port."""
    c = host.copy()
    port = host.ports[port_name]
    cap = gf.components.rectangle(
        size=(gap, port.dwidth + 2 * gap),
        layer=LAYER.D0_TOP_GROUND_MASK,
        centered=True,
        port_type="optical",
        port_orientations=(0, 180),
    )
    (c << cap).connect("o1", port, allow_width_mismatch=True, allow_layer_mismatch=True)
    return add_etch_for_component(c)  # ETCH = GROUND_MASK − DRAW, as R13 asks


assert [port.name for port in bend.ports] == ["o1", "o2"]
open_ended = add_open_end(host, "o2")
assert open_ended.dbbox().right == pytest.approx(46)  # the 40 µm host plus the 6 µm cap
```

Do not wrap a GDSFactory component in a PDK cell unless the PDK adds geometry
or meaning to it (H1).

## H4. Write the cell body in the order of its physical parts {#h4}

**Rule.** Write the cell body in the order of its physical parts, each under a
short comment heading; a long cell file is acceptable.

A reader follows a cell by its parts, so the order of the code is the order of
the parts in the layout. A part that becomes a cell (H3) moves into its own
module when another cell uses it, so one fix reaches every cell that shares
it. The shape of such a body:

```python
@gf.cell
def pad_with_lead(pad_size: float = 20.0, lead_length: float = 30.0) -> gf.Component:
    c = gf.Component()

    # Pad
    c << gf.components.rectangle(size=(pad_size, pad_size), layer=LAYER.D0_TOP_M1_DRAW)

    # Lead, from the pad's right edge
    lead = c << gf.components.rectangle(size=(lead_length, 4), layer=LAYER.D0_TOP_M1_DRAW)
    lead.dmove((pad_size, pad_size / 2 - 2))

    # Port at the lead's end
    c.add_port("o1", center=(pad_size + lead_length, pad_size / 2), width=4, orientation=0,
               layer=LAYER.D0_TOP_M1_DRAW)
    return c


assert pad_with_lead().ports["o1"].dcenter[0] == pytest.approx(50)
```
