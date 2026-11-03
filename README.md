# OrcaPen SC PDK

<p align="center">
  <img alt="Status: public PDK" src="https://img.shields.io/badge/status-public%20PDK-0f766e">
  <img alt="Python 3.12+" src="https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white">
  <img alt="GDSFactory 9.48.x" src="https://img.shields.io/badge/GDSFactory-9.48.x-4B8BBE">
  <img alt="Docs: GitHub Pages" src="https://img.shields.io/badge/docs-GitHub%20Pages-0f766e">
</p>

![OrcaPen superconducting layout and physical stack illustration.](docs/assets/orcapen-overview-banner-qubit.png)

OrcaPen SC PDK is a public superconducting quantum/RF process design kit for
[GDSFactory](https://gdsfactory.github.io/gdsfactory/). It provides
reusable process layers, stack semantics, layout cells and integration points
for [SCGSim](https://github.com/NCUPHY-LTLab/scgsim). Its 3D workflow keeps
source geometry and fabrication meaning available to downstream simulation,
with public examples that make handoff and inspection easier.

## Install & Get Started

Use Python 3.12 or 3.13 with [uv](https://docs.astral.sh/uv/).

The commands below install the public **1.0.0 source preview**, not a stable
release. The `v1.0.0` tag has not been published; this preview selects an exact
available source revision.

<!-- overview-install:start -->
```bash
uv init --python 3.12
uv add "orcapen-sc-pdk @ git+https://github.com/NCUPHY-LTLab/orcapen-sc-pdk.git@947a216d295d3ceadd1dc06bcd34e8aebf61ff0c"
uv run python -c "import importlib.metadata as m; print(m.version('orcapen-sc-pdk'))"
```
<!-- overview-install:end -->

In a Python script or notebook, activate OrcaPen and build a registered cell:

```python
import gdsfactory as gf
from orcapen_sc_pdk import activate

activate()
component = gf.get_component("resonator")
component.plot()
```

The version command reports the preview's package metadata, `1.0.0`; that
number does not indicate a published stable release. See [Get Started](docs/getting-started.md) for setup details. Contributors can
use [Documentation & Website](docs/docs-publishing.md) to build the docs.

## Documentation and downloads

- [Documentation site](https://ncuphy-ltlab.github.io/orcapen-sc-pdk/)
- [Simulation cases and downloads](https://ncuphy-ltlab.github.io/orcapen-sc-pdk/simulation/recorded-cases.html)
- [SimplePad simulation data](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/releases/tag/data-2026.11.01-r1)
- [GitHub repository](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk)

Simulation data uses independent `data-YYYY.MM.DD-rN` releases. Each case keeps
its recorded PDK, SCGSim and solver versions.

## Contributing and license

Contributions are welcome; see [Contributing](docs/developing-features.md).
Project-authored public software and components use the [MIT License](LICENSE).
See [license scope](LICENSING.md) and [third-party notices](THIRD_PARTY_NOTICES.md)
for attribution and exclusions.
