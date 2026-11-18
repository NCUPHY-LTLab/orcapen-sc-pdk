---
title: "Companion layers from one source"
sidebar: development
page-navigation: true
---

A conductor in this PDK is described by up to three layers: the metal you draw
(`DRAW`), the ground mask that clears the ground plane around it
(`GROUND_MASK`), and the etch (`ETCH`), where metal is removed. The fabrication
stack derives the metal from the etch, as the domain minus `ETCH − DRAW`.
SCGSim derives it from the mask, as the ground plane minus `GROUND_MASK`, plus
the drawn traces. The two derivations must give the same metal. See
[Layers](../start/layers.qmd) for the layer list.

Run this page's examples with
`uv run pytest tests/test_docs_construction_examples.py -k companion-layers`. They
run in order and share this setup.

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

## R13. Derive the etch from a mask drawn with the metal {#r13}

**Rule.** Derive the etch with `add_etch_for_component`, which sets
`ETCH = GROUND_MASK − DRAW`, from a mask drawn with the metal.

- Draw the ground mask from the same anchors as the metal: the named points,
  such as a port centre or a corner, that both shapes are measured from, with
  the same dimensions.
- Put every cleared area, such as a dicing street, on the mask.

An etch drawn by hand is a third, independent description, and nothing keeps
it in step with the mask. `sample_small_airbridge_chip` had a 2300 × 1000 µm
dicing frame on the etch layer but not on the ground mask, so the two
derivations differed by about 320,000 µm²
([#58](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/58), A6, fixed in
[#61](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/pull/61)). For a routed
line, a GDSFactory cross-section draws the metal and its mask from one path; see
[Cross-sections](../public-pdk-examples/cross-sections.qmd).

![**Problem.** One panel per layer: the pad on `DRAW`, its clearance on
`GROUND_MASK`, and a hand-drawn `ETCH` that also holds a dicing frame the mask
lacks. The last panel marks in red where the etch-derived and the mask-derived
metal disagree: the whole frame.](../_static/images/contributing/en/r13-problem.svg)

![**Result.** The same panels with the frame drawn on `GROUND_MASK` and the
etch derived from the mask and the metal: the two derivations agree
everywhere.](../_static/images/contributing/en/r13-result.svg)

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
