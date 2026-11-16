---
title: "Three kinds of check, and process rules"
sidebar: development
---

Three kinds of check apply to a layout. They answer different questions, have
different owners and reach different users, so a pass on one says nothing
about the others.

| Kind | Asks | Owner | Where it runs today |
|---|---|---|---|
| [Construction checks](construction-checks.md) | Did the code draw what it meant? Valid polygons, no edge shorter than 2 DBU (2 nm), only intended holes, one polygon per conductor, the intended shape; the smallest interior angle is reported | This PDK, in its tests | `tests/test_disk_qubit.py` for `disk_flip_chip_qubit`. Other cells gain them as their tests are written. A consumer may call `construction_report` on its own layouts |
| Process design rules (DRC) | Can the process make it? Width, spacing and enclosure per layer | This PDK | None yet: no process rule has been adopted. Once rules exist, consumers may adopt, change or ignore them |
| Simulation checks | Can the solver model it? | [SCGSim](https://github.com/NCUPHY-LTLab/scgsim) | Defined and run by SCGSim. Its [Supported Geometry](https://github.com/NCUPHY-LTLab/scgsim/blob/develop/docs/supported-geometry.qmd) page lists what it accepts, and [Known Geometry Problems](https://github.com/NCUPHY-LTLab/scgsim/blob/develop/docs/known-geometry-problems.qmd) shows the drawing defects it does not work around |

Consumers of the PDK are not required to follow its process rules.

## Record a process rule

A process rule states a limit of the fabrication process, such as a minimum
width on a layer. No process rule is invented: each one comes with a source
the PDK maintainers supply.

To propose one, open an Issue in this repository that records:

- **Source**: where the number comes from.
- **Layer**: the layer or layer pair it applies to.
- **Value**: the number and its unit.
- **Status**: `proposed` until the PDK maintainers adopt it, then `adopted`.

The PDK maintainers decide whether a rule is adopted. The first adopted rule
adds a page that lists the process rules, and the code that checks them, to
this guide.

The 2 DBU limit of the construction checks is not a process rule: it is the
smallest edge a drawing can mean, whatever the process.
