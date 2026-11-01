---
title: "Install & Get Started"
sidebar: get-started
---

Install OrcaPen SC PDK 1.0.0, activate its GDSFactory process design kit (PDK),
and build a registered resonator. Layout creation does not require a solver.

## Install

Use Python 3.12 or 3.13 with uv. For a new Python 3.12 project:

{{< include _includes/_readme-install.md >}}

For an existing project, run:

```bash
uv add "orcapen-sc-pdk @ git+https://github.com/NCUPHY-LTLab/orcapen-sc-pdk.git@v1.0.0"
uv run python -c "import importlib.metadata as m; print(m.version('orcapen-sc-pdk'))"
```

Check: the version command reports `1.0.0` once the `v1.0.0` source tag is available.

## Activate and build

```python
import gdsfactory as gf
from orcapen_sc_pdk import activate

activate()
component = gf.get_component("resonator")
print(component.name, component.dbbox())
component.plot()
```

Check: the output includes the resonator name and bounding box, and a 2D layout
appears. Physical dimensions are in micrometres.

## Continue

Explore [common cells](start/common-cells.qmd), [layers and stack](start/layers.qmd),
[materials and interfaces](start/materials.qmd), or [simulation guides](notebooks.qmd).
Each simulation guide identifies its own SCGSim version and solver requirements.
