---
title: "PDK and simulation responsibilities"
sidebar: development
---

OrcaPen supplies reusable fabrication facts and public source layouts.
SCGSim supplies the simulation mechanics that consume those inputs.

| OrcaPen | SCGSim | Consuming design |
| --- | --- | --- |
| Material records, layer maps, physical stacks, cross-sections, reusable cells, and source annotations | Geometry interpretation, backend material/terminal assignment, meshing, configuration, solver handoff, and results | Device dimensions, assemblies, final Nets, reference conductors, and excitation |

Read [Layers & Stack](../start/layers.qmd) and
[Materials & Interfaces](../start/materials.qmd) for PDK inputs.
Use [Simulation](../notebooks.qmd) for the calculation and
[Workspace & Related Packages](ecosystem-workspace.md) for the package relationships.

Keep private devices and their run data in the consuming project.
