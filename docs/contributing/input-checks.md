---
title: "Input checks"
sidebar: development
---

An input check makes a cell refuse a parameter value instead of drawing it.
It is the right tool only for a value the geometry cannot support, and only
after the construction has been made as robust as it can be. R7 has four
parts.

The examples on this page run on their own, in order. They share this setup.

```python
import gdsfactory as gf
import pytest
from orcapen_sc_pdk import activate
from orcapen_sc_pdk.helpers.layout.geometry import polar_point
from orcapen_sc_pdk.pdk import PDK

activate()
LAYER = (1, 0)
```

## R7a. Fix the construction before you limit an input {#r7a}

**Rule.** When a parameter value gives a bad shape, find the construction
cause first; limit the parameter only when no construction can draw the value.

A limit hides the cause for the values it allows. In `disk_flip_chip_qubit`,
limiting the claw's landing angle to 42.51° at the defaults did not remove the
claw spike or its 16–93 nm jogs, which came from rounding the claw before the
taper was added ([#53](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/53),
cause 2; [R6](one-outline.md#r6)). Neither does a finer sampling or a smaller
database unit (DBU, the grid GDS stores; 1 nm here) cure a construction cause: with eight times the points the curve join of
[R5](curves.md#r5) has more holes, not fewer.

**How to check.** The construction rules on the other pages each say how to
check their defect; run those checks over the whole range before you add a
limit.

## R7b. Reject a value the construction cannot draw; never clamp it {#r7b}

**Rule.** Raise a `ValueError` that names the parameter and the supported
range, test that error, and state the range in the cell's docstring. Do not
replace the value with the nearest supported one.

A clamped value draws a different design from the one that was asked for, and
nothing tells the caller.

![**Problem.** A claw asked for with a 90° span (dashed) and drawn with 60°,
because the code clamps the span silently.](../_static/images/contributing/r7b-problem.svg)

![**Result.** The checked claw draws exactly the 60° that was asked for, and a
90° request raises an error instead.](../_static/images/contributing/r7b-result.svg)

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

## R7c. Reject off-grid inputs {#r7c}

**Rule.** A length or position parameter that sets geometry directly must be a
whole number of nanometres; an off-grid value raises a `ValueError` that names
the parameter.

An off-grid value is rounded where it is used, so two parts meant to meet can
miss each other by 1 nm ([R9](grid-and-polygons.md#r9)). The check applies to
the values a caller passes, not to values that come out of trigonometry or
curve sampling, which are off the grid by nature
([#62](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/62)). The Purcell
readout cell rejects the IDC finger length that left its 1 nm slits
([#58](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/58), A1):

```python
PURCELL = "capacitive_coupling_intrinsic_individual_purcell_filter_readout_resonators"
with pytest.raises(ValueError, match="idc_finger_length must be aligned to the active manufacturing grid"):
    PDK.get_component(PURCELL, idc_finger_length=59.92476)
```

**How to check.** `gf.snap.is_on_grid(value)` decides it; the cell's test
asserts the error for one off-grid value of each checked parameter.

## R7d. Do not hide a symptom {#r7d}

**Rule.** Do not cover a construction defect afterwards: no overlap added to
close a gap, no global snapping, no simplifying or repairing the geometry
after it is built.

A repair hides the cause from every check and from the next reader, and it
changes the shape in places nobody meant. Overlap that is part of the design
is different: the 1 nm sheet overlap that SCGSim reported in #58 is deliberate
and supported ([#58](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/issues/58),
A7 withdrawn). The test is the reason: an overlap is a defect when it exists
to hide a gap.

**How to check.** Review the diff: a fix changes the construction that caused
the defect, and the construction check that found it then passes without any
added overlap, snap or repair step.
