---
title: "Companion layers from one source"
sidebar: development
---

A conductor in this PDK is described by up to three layers: the metal you draw
(`DRAW`), the ground mask that clears the ground plane around it
(`GROUND_MASK`), and the etch (`ETCH`), where metal is removed. The fabrication
stack derives the metal from the etch, as the domain minus `ETCH − DRAW`.
SCGSim derives it from the mask, as the ground plane minus `GROUND_MASK`, plus
the drawn traces. The two derivations must give the same metal. See
[Layers](../start/layers.qmd) for the layer list.

The examples on this page run on their own, in order. They share this setup.

```python
import gdsfactory as gf
from orcapen_sc_pdk import activate
from orcapen_sc_pdk.helpers.layout import add_etch_for_component
from orcapen_sc_pdk.tech import LAYER

activate()
DRAW, MASK, ETCH = LAYER.D0_TOP_M1_DRAW, LAYER.D0_TOP_GROUND_MASK, LAYER.D0_TOP_M1_ETCH


def box(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def metal_mismatch(component):
    """Where the etch-derived metal and the mask-derived metal disagree, in DBU."""
    draw = component.get_region(DRAW, merge=True)
    etch = component.get_region(ETCH, merge=True)
    mask = component.get_region(MASK, merge=True)
    plane = gf.kdb.Region(component.dbbox().to_itype(component.kcl.dbu))
    metal_from_etch = plane - (etch - draw)  # fabrication stack: domain − (ETCH − DRAW)
    metal_from_mask = (plane - mask) + draw  # SCGSim: plane − GROUND_MASK, plus the drawn traces
    return metal_from_etch ^ metal_from_mask
```

## R15. Draw the mask from the metal's source and derive the etch from both {#r15}

**Rule.** Draw the ground mask from the same anchors and dimensions as the
metal, put every cleared area (such as a dicing street) on the mask, and derive
the etch with `add_etch_for_component`, which sets `ETCH = GROUND_MASK − DRAW`.

An etch drawn by hand is a third, independent description, and nothing keeps
it in step with the mask. `sample_small_airbridge_chip` had a 2300 × 1000 µm
dicing frame on the etch layer but not on the ground mask, so the two
derivations differed by about 320,000 µm²
([#58](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/58), A6, fixed in
[#61](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/pull/61)). For a routed
line, a GDSFactory cross-section draws the metal and its mask from one path; see
[Cross-sections](../public-pdk-examples/cross-sections.qmd).

![**Problem.** A pad (teal, `DRAW`) with its ground clearance (`GROUND_MASK`,
grey, here under the amber `ETCH`), and a dicing frame drawn on the etch layer
only, with the etch drawn by hand. Red marks where the
etch-derived and the mask-derived metal disagree: the whole frame.](../_static/images/contributing/r15-problem.svg)

![**Result.** The frame drawn on the mask and the etch derived from the mask
and the metal: the two derivations agree everywhere.](../_static/images/contributing/r15-result.svg)

```python
PAD, CLEARANCE = (-50, -10, 50, 10), (-70, -30, 70, 30)


def frame():
    """A 10 µm dicing street around a 200 × 100 µm chip, as one region."""
    c = gf.Component()
    c.add_polygon(box(-100, -50, 100, 50), layer=MASK)
    outer = c.get_region(MASK)
    return outer - outer.sized(-gf.kcl.to_dbu(10))


def chip_with_hand_drawn_etch():  # don't: the frame is only on the etch
    c = gf.Component()
    c.add_polygon(box(*PAD), layer=DRAW)
    c.add_polygon(box(*CLEARANCE), layer=MASK)
    clearance_etch = gf.kdb.Region(gf.kdb.DBox(*CLEARANCE).to_itype(gf.kcl.dbu))
    c.add_polygon(clearance_etch - c.get_region(DRAW), layer=ETCH)
    c.add_polygon(frame(), layer=ETCH)
    return c


def chip_with_derived_etch():  # do: the frame is on the mask, the etch is derived
    c = gf.Component()
    c.add_polygon(box(*PAD), layer=DRAW)
    c.add_polygon(box(*CLEARANCE), layer=MASK)
    c.add_polygon(frame(), layer=MASK)
    return add_etch_for_component(c, draw_layer=DRAW, mask_layer=MASK, etch_layer=ETCH)


assert round(metal_mismatch(chip_with_hand_drawn_etch()).area() * gf.kcl.dbu**2) == 5600  # the frame
assert metal_mismatch(chip_with_derived_etch()).is_empty()
```

**How to check.** In the cell's test, compute both derivations within the
cell's extent and assert that their XOR is empty, as `metal_mismatch` does
above and `tests/test_idc_airbridge_geometry.py` does for the airbridge chip.
