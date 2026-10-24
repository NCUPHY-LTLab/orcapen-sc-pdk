---
title: "Install & Activate"
sidebar: get-started
---

Install the public source revision below, activate OrcaPen, and build a registered
cell. Layout use needs neither Palace nor an AEDT installation.

## Install

Use Python 3.12 or 3.13 in your project environment. Install this public revision:

```bash
python -m pip install "orcapen-sc-pdk @ git+https://github.com/NCUPHY-LTLab/orcapen-sc-pdk.git@aee7f8b848895f2d107f6b086310e866e8381f73"
```

Check: `python -m pip show orcapen-sc-pdk` reports version `0.1.0.dev2`.
The package selects GDSFactory `~=9.48.0` and its other layout dependencies.

## Activate and see a cell

In a Jupyter notebook, run:

```python
import gdsfactory as gf
from orcapen_sc_pdk import activate

activate()
component = gf.get_component("resonator")
print(component.name)
print(component.dbbox())
component.plot()
```

Check: the cell name and physical bounding box are printed, and a 2D layout
appears below the cell. Lengths and physical port dimensions use micrometres.

![OrcaPen resonator layout.](_static/images/components/resonator.svg){width=80%}

## Choose your next step

| Task | Guide |
| --- | --- |
| Pick a capacitor, resonator, launcher, or primitive | [Cells](public-pdk-examples/index.md) |
| Select geometry layers and physical heights | [Layers & Stack](start/layers.qmd) |
| Choose bulk materials or surface-interface assumptions | [Materials & Interfaces](start/materials.qmd) |
| Select a CPW section and inspect layout interfaces | [Cross-sections](public-pdk-examples/cross-sections.qmd) |
| Place, connect, route, or export a layout | [GDSFactory and OrcaPen](public-pdk-examples/component-authoring.md) |
| Calculate an electrical quantity | [Choose a Simulation](notebooks.qmd) |

Simulation examples have their own SCGSim and solver prerequisites. Read the
selected tutorial's setup before installing optional simulation dependencies.
