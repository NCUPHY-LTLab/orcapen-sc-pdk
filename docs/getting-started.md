---
title: "Install & Get Started"
sidebar: get-started
---

Install the public source preview, activate its GDSFactory process design kit
(PDK), and build a registered resonator. The preview's package metadata reports
`1.0.0`; this is not a published `v1.0.0` release. Layout creation does not
require a solver.

## Install

Use Python 3.12 or 3.13 with uv. For a new Python 3.12 project:

{{< include _includes/_readme-install.md >}}

For an existing project, run:

```bash
uv add "orcapen-sc-pdk @ git+https://github.com/NCUPHY-LTLab/orcapen-sc-pdk.git@947a216d295d3ceadd1dc06bcd34e8aebf61ff0c"
uv run python -c "import importlib.metadata as m; print(m.version('orcapen-sc-pdk'))"
```

The version command reports `1.0.0`, the package metadata in this preview source.

## Activate and build {#activate-and-see-a-cell}

```python
import gdsfactory as gf
from orcapen_sc_pdk import activate

activate()
component = gf.get_component("resonator")
print(component.name, component.dbbox())
component.plot()
```

The output includes the resonator name and bounding box, and a 2D layout
appears. Physical dimensions are in micrometres.

## Continue

Explore [common cells](start/common-cells.qmd), [layers and stack](start/layers.qmd),
[materials and interfaces](start/materials.qmd), or [simulation guides](notebooks.qmd).
Each simulation guide identifies its own SCGSim version and solver requirements.
