---
title: "OrcaPen and SCGSim integration"
sidebar: development
---

Pass the selected component's geometry, stack, materials, and source annotations
to the SCGSim version used by its tutorial. SCGSim handles backend preparation
and returned results; OrcaPen supplies the public model inputs.

## Preserve the source model

Keep physical layer identities, die faces, original thicknesses, holes,
placements, and conductor ownership with the geometry. Nonmetal locator sheets
identify interfaces rather than adding metal or assigning solver terminals.

The technology source exposes physical declarations through
`LayerLevel.info["physical_layer"]`. Selected component getters add source-owned
records without changing the global material or stack definitions.
Read the [technology source](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/blob/aee7f8b848895f2d107f6b086310e866e8381f73/orcapen_sc_pdk/tech.py)
and the selected tutorial's getter for exact record fields.

## Use one runtime for the selected calculation

Follow a tutorial from [Choose a Simulation](../notebooks.qmd).
For generic backend APIs, use the
[SCGSim documentation](https://github.com/OrPenStrike/scgsim/tree/develop/docs)
at the version selected by that tutorial.

Keep source preparation, native execution, and returned-run analysis as
separate operations. A source preview shows geometry; inspect the backend's
actual bodies, assignments, and returned quantities for a simulation result.
