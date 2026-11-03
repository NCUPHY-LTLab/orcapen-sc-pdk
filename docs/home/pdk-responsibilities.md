---
title: "PDK and simulation responsibilities"
sidebar: development
---

OrcaPen defines reusable public process inputs and source layouts. SCGSim
interprets those inputs for simulation; the consuming design supplies its
device-specific geometry and choices.

| OrcaPen | SCGSim | Consuming design |
| --- | --- | --- |
| Materials, layers, physical stacks, cross-sections, reusable cells, source annotations | Geometry interpretation, backend assignments, meshing, solver handoff, and results | Device dimensions, assemblies, final Nets, reference conductors, and excitation |

Read [Layers & Stack](../start/layers.qmd) and
[Materials & Interfaces](../start/materials.qmd) for PDK inputs. See
[Simulation](../notebooks.qmd) for tutorials and
[Workspace & Related Packages](ecosystem-workspace.md) for package relationships.

Keep private device geometry, parameters, layouts, and simulation records in
the consuming design repository. [QPDK](https://github.com/gdsfactory/quantum-rf-pdk)
is an external reference and example source, not the authority for OrcaPen
semantics or SCGSim runtime behavior.
