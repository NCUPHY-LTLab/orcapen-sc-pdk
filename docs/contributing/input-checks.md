---
title: "Input checks"
sidebar: development
page-navigation: true
---

An input check makes a cell refuse a parameter value instead of drawing it.
It is the right tool only for a value the geometry cannot support, and only
after the construction has been made as robust as it can be. Four rules,
R14 to R17, cover input checks.

Run this page's examples with
`uv run pytest tests/test_docs_construction_examples.py -k input-checks`. They
run in order and share this setup.

```python
import gdsfactory as gf
import pytest
from orcapen_sc_pdk import activate
from orcapen_sc_pdk.helpers.layout.geometry import polar_point
from orcapen_sc_pdk.pdk import PDK

activate()
LAYER = (1, 0)


def merged(component):
    return component.get_region(LAYER, merge=True)
```

## R14. Fix the construction before you limit an input {#r14}

**Rule.** When a parameter value gives a bad shape, find and fix the
construction cause first; limit the parameter only when no construction can
draw the value.

A limit hides the cause for the values it allows. In `disk_flip_chip_qubit`,
limiting the landing span (`tc_landing_span`, the angle over which a claw's
taper meets the disk side; see the
[component page](../public-pdk-examples/components/disk_flip_chip_qubit.qmd))
to 42.51° at the defaults did not remove the claw spike or its 16–93 nm jogs.
They came from rounding the claw before the taper was added
([#53](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/53), cause 2;
[R5](one-outline.md#r5)). Neither does a finer sampling or a smaller database
unit (DBU, the grid GDS stores; 1 nm here) cure a construction cause: with
eight times the points, the curve join of [R11](curves.md#r11) has 112 holes
instead of 8.

![**Problem** (the figure of R11). A lead that ends on a second sampling of the
disk's circle leaves holes along the join; more points do not remove them.](../_static/images/contributing/en/r11-problem.svg)

![**Result** (the figure of R11). The construction fixed instead: the lead's
sides run on into the disk, with no holes and no limit on any input.](../_static/images/contributing/en/r11-result.svg)

**How to check.** The construction rules on the other pages each say how to
check their defect; run those checks over the whole range before you add a
limit.

## R15. Reject a value the construction cannot draw; never clamp it {#r15}

**Rule.** Raise a `ValueError` that names the parameter and the supported
range, rather than clamping the value, that is, replacing it with the nearest
supported one.

- Test that error.
- State the range in the cell's docstring.

A clamped value draws a different design from the one that was asked for, and
nothing tells the caller.

![**Problem.** A claw asked for with a 90° span (dashed) and drawn with 60°,
because the code clamps the span silently.](../_static/images/contributing/en/r15-problem.svg)

![**Result.** The checked claw draws exactly the 60° that was asked for, and a
90° request raises an error instead.](../_static/images/contributing/en/r15-result.svg)

```python
MAX_SPAN = 60  # degrees; adjacent claws would touch beyond this


def claw_points(span):
    """An arc band from radius 100 to 120 µm, centred on 0°, `span` degrees wide."""
    steps = 32
    angles = [-span / 2 + span * i / steps for i in range(steps + 1)]
    return [polar_point(120, a) for a in angles] + [polar_point(100, a) for a in reversed(angles)]


def claw_clamped(span):  # don't: draws 60° when asked for 90°
    c = gf.Component()
    c.add_polygon(claw_points(min(span, MAX_SPAN)), layer=LAYER)
    return c


def claw_checked(span):  # do: refuse what the construction cannot draw
    if not 0 < span <= MAX_SPAN:
        raise ValueError(f"span must be in (0, {MAX_SPAN}] degrees, got {span}")
    c = gf.Component()
    c.add_polygon(claw_points(span), layer=LAYER)
    return c


assert claw_clamped(90).dbbox() == claw_checked(60).dbbox()  # the 90° request drew the 60° claw
with pytest.raises(ValueError, match="span must be in"):
    claw_checked(90)
```

The real cells do the same. `disk_flip_chip_qubit` rejects junction angles
its claws cannot clear:

```python
with pytest.raises(ValueError, match="junction and open lead angles must be 45° \\+ k·90°"):
    PDK.get_component("disk_flip_chip_qubit", junction_angle=0.0)
```

**How to check.** The cell's test asserts the error with `pytest.raises` and
the message, as above, for a value just outside each end of the range.

## R16. Reject off-grid inputs {#r16}

**Rule.** Raise a `ValueError` that names the parameter when a length or
position parameter that sets geometry directly is not a whole number of
nanometres.

An off-grid value is rounded where it is used, so two parts meant to meet can
miss each other by 1 nm ([R1](grid-and-polygons.md#r1)). The check applies to
the values a caller passes, not to values that come out of trigonometry or
curve sampling, which are off the grid by nature
([#62](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/62)).

![**Problem** (the figure of R1). Off-grid lengths of 10.0004 µm and 5.0004 µm
leave a 1 nm gap, so the second pad is a separate polygon.](../_static/images/contributing/en/r1-problem.svg)

![**Result** (the figure of R1). With on-grid lengths the chain is one
polygon.](../_static/images/contributing/en/r1-result.svg)

The Purcell readout cell rejects the IDC finger length that left its 1 nm
slits ([#58](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/58), A1):

```python
PURCELL = "capacitive_coupling_intrinsic_individual_purcell_filter_readout_resonators"
with pytest.raises(ValueError, match="idc_finger_length must be aligned to the active manufacturing grid"):
    PDK.get_component(PURCELL, idc_finger_length=59.92476)
```

**How to check.** `gf.snap.is_on_grid(value)` decides it; the cell's test
asserts the error for one off-grid value of each checked parameter.

## R17. Fix the cause of a defect instead of patching over it {#r17}

**Rule.** Fix the construction that caused a defect rather than covering it
afterwards.

- Do not add overlap to close a gap.
- Do not snap the whole layout to the grid, simplify it, or repair it after it
  is built.

A patch hides the cause from every check and from the next reader, and the
cause stays: in the example the off-grid lengths that opened the gap still
shift the second pad by 1 nm. Overlap that is part of the design is different:
the 1 nm sheet overlap that SCGSim reported in #58 is deliberate and supported
([#58](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/58), A7
withdrawn). The test is the reason: an overlap is a defect when it exists to
hide a gap.

![**Problem.** The 1 nm gap of R1 closed with a 2 nm patch (red): one polygon
again, but the off-grid lengths are still there.](../_static/images/contributing/en/r17-problem.svg)

![**Result.** The construction fixed: on-grid lengths, no patch. The right
panel shows the same place.](../_static/images/contributing/en/r17-result.svg)

```python
def pad_lead_pad(pad_length, lead_length):
    """A 10 µm pad, a 4 µm lead and a second pad, each placed at the sum of the lengths before it."""
    c = gf.Component()
    pad = gf.components.rectangle(size=(pad_length, 10), layer=LAYER)
    lead = gf.components.rectangle(size=(lead_length, 4), layer=LAYER)
    c << pad
    (c << lead).dmove((pad_length, 3))
    (c << pad).dmove((pad_length + lead_length, 0))
    return c


PATCH = gf.kdb.Region(gf.kdb.DBox(14.999, 3, 15.001, 7).to_itype(gf.kcl.dbu))  # 2 nm across the gap


def patched():  # don't: the gap is covered, the cause stays
    c = pad_lead_pad(10.0004, 5.0004)
    c.add_polygon(PATCH, layer=LAYER)
    return c


fixed = pad_lead_pad(10.0, 5.0)  # do: lengths on the grid
assert merged(pad_lead_pad(10.0004, 5.0004)).count() == 2
assert merged(patched()).count() == 1  # looks fixed to a polygon count
assert merged(fixed).count() == 1
assert not (merged(patched()) ^ merged(fixed)).is_empty()  # but it is not the shape that was meant
```

**How to check.** Review the diff: a fix changes the construction that caused
the defect, and the construction check that found it then passes without any
added overlap, snap or repair step.
