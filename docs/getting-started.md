---
title: "Get Started"
---

Use Python 3.12 or 3.13 and the GDSFactory version selected by this package.
Install the reviewed local OrcaPen `0.1.0.dev2` candidate wheel in your existing
Python environment, substituting the actual artifact path:

```bash
python -m pip install /path/to/orcapen_sc_pdk-0.1.0.dev2-py3-none-any.whl
```

The candidate is local only: it has not been uploaded to a registry or PyPI.
Record the exact version and wheel digest. See [Distribution and handoff](distribution.md)
for review, GDSFactory+ use and future organization-registry publication.

## Activate and build

```python
import gdsfactory as gf
from orcapen_sc_pdk import activate, get_pdk

activate()
component = gf.get_component("resonator", length=3500)
print(component.name, component.dbbox(), component.layers)
print(sorted(get_pdk().cells))
```

If a compatible local layout viewer is available, call `component.show()` to
open the cell. This is optional; the build above does not require a viewer.

Dimensions are in micrometres. Public factory defaults are preview settings,
not measured device specifications; choose your own process and design
parameters. Activate OrcaPen before resolving named cells or
cross-sections; do not silently substitute another PDK.

Choose the existing [Cells](public-pdk-examples/index.md) and read their typed
settings/source intent before composing a design. Use [Process](materials-and-technology.md)
for layers, materials and stack facts. The [build and compose guide](public-pdk-examples/component-authoring.md)
shows how to use existing cells and their ports in your own component.

## Add simulation only when needed

Layout use does not require an AEDT or Palace installation. Public simulation
notebooks consume SCGSim's reusable simulation runtime.
Select a [Simulation](notebooks.qmd) example and follow its exact runtime
prerequisites. The newer source-only examples require a separate SCGSim v2
environment; the ordinary project dependency groups do not select that cohort.
Saved outputs and source-only revisions are not interchangeable evidence.
