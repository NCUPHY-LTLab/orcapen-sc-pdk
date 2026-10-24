---
title: "Workspace & Related Packages"
sidebar: development
---

Use OrcaPen for PDK facts and source layouts, GDSFactory for layout composition,
and SCGSim for simulation. Keep each package's version with the project that uses it.

| Package or project | What it supplies |
| --- | --- |
| [OrcaPen](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk) | Public cells, cross-sections, layers, stacks, materials, and component simulation examples |
| [GDSFactory](https://gdsfactory.github.io/gdsfactory/) | Component construction, placement, connections, routing, and GDS export |
| [SCGSim](https://github.com/OrPenStrike/scgsim) | Geometry interpretation, Palace/AEDT preparation, handoff, and returned-result analysis |
| Your layout project | Device parameters, chip assemblies, final Nets and excitations, and private results |

## Select the environment by task

The core installation supports layout use. A simulation tutorial may require
a different SCGSim revision or solver installation from the repository's
ordinary dependency groups; use that tutorial's stated setup.

[Install & Activate](../getting-started.md) covers the public source installation.
[Choose a Simulation](../notebooks.qmd) routes to electrical calculations.
[SCGSim integration](../features/scgsim-integration.md) explains which records travel between packages.

## Share only public inputs

Use public layouts and parameters in examples committed to OrcaPen.
Retain private designs and their outputs in the private project, so a public
documentation build needs no private files.
