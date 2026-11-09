---
title: "Install & Get Started"
sidebar: get-started
---

Install the public source preview, activate its GDSFactory process design kit
(PDK), and build a registered resonator. Layout creation does not require a
solver.

With a GDSFactory+ license, you can preview layouts from a local or remote
OrcaPen project. Without a license, use KLayout with a local project.
See [Preview Cells](start/preview-cells.qmd) for setup.

## Install

Use Python 3.12 or 3.13 with uv. For a new Python 3.12 project:

{{< include _includes/_readme-install.md >}}

For an existing project, run:

```bash
uv add "orcapen-sc-pdk @ git+https://github.com/NCUPHY-LTLab/orcapen-sc-pdk.git@947a216d295d3ceadd1dc06bcd34e8aebf61ff0c"
uv run python -c "import importlib.metadata as m; print(m.version('orcapen-sc-pdk'))"
```

::: {.callout-note title="Package metadata is not a published release"}
The version command reports `1.0.0`, the package metadata in this preview
source. This does not mean `v1.0.0` has been published.
:::

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

Choose a layout in [Common Cells](start/common-cells.qmd), then set up
GDSFactory+ or local KLayout with [Preview Cells](start/preview-cells.qmd).
Continue to [Layers & Stack](start/layers.qmd) and
[Materials & Interfaces](start/materials.qmd). Each [simulation guide](notebooks.qmd)
identifies its SCGSim version and solver requirements.
