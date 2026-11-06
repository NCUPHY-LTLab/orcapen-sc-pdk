---
title: "Contributing"
sidebar: development
---

Contribute reusable cells, process records, examples, or documentation through
the [public repository](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk).
Start with the part of the PDK your change affects.

## Set up a development checkout

GDSFactory+ is optional and needs a paid subscription. Pick one setup.

**Without GDSFactory+** (KLayout for viewing):

```bash
git clone https://github.com/NCUPHY-LTLab/orcapen-sc-pdk.git
cd orcapen-sc-pdk
uv sync -p 3.12
```

This installs the PDK plus the development tools, pytest and Ruff. To view
layouts, install [KLayout](https://www.klayout.de/) and its klive plugin.

**With GDSFactory+** (the VS Code extension):

```bash
git clone https://github.com/NCUPHY-LTLab/orcapen-sc-pdk.git
cd orcapen-sc-pdk
uv sync -p 3.12 --all-extras
```

`--all-extras` adds the `gdsfactoryplus` extra, which holds the packages
GDSFactory+ Worker Health requires, including the SPICE packages InSpice and
vacask. It is the same command the extension's **Setup Automatically** runs.
Keep using `--all-extras` afterwards: a plain `uv sync` removes these packages,
and the extension then shows no components. GDSFactory+ requires Python 3.12.

Check: `uv run python --version` reports a supported Python version.
For documentation dependencies and preview, use
[Documentation & Website](docs-publishing.md).

## Preview a component

Every cell module ends with a preview block. Run the file directly, for example
with **Run Python File** in VS Code:

```bash
uv run python orcapen_sc_pdk/cells/layout/resonator.py
```

To preview any registered cell by name:

```bash
uv run python -m orcapen_sc_pdk.preview resonator
```

Both write `build/gds/<cell>.gds` and open it. Inside a VS Code terminal with
GDSFactory+ installed, the file opens in the GDSFactory+ Layout Viewer.
Otherwise it is sent to KLayout through klive. Pass `--viewer klayout` or
`--viewer gdsfactoryplus` to choose explicitly. In a new cell module, end with
the same block:

```python
if __name__ == "__main__":
    # Imported here because orcapen_sc_pdk.pdk imports this module.
    from orcapen_sc_pdk.preview import show

    show(my_cell)
```

## Keep changes focused

- Put reusable layout and process definitions in OrcaPen.
- Reuse GDSFactory for component composition and routing.
- Decorate cells with plain `@gf.cell`, the only form GDSFactory+ discovers. A
  cell with curves takes `curve_sampling: CurveSampling = FABRICATION` and passes it
  to nested cells and curve helpers; see [Curve sampling](usage/curve-sampling.md).
- Use SCGSim for simulation preparation, solver integration, and returned results.
- Keep private layouts, parameters, and run directories in the consuming project.

Inspect the relevant existing source and examples before introducing a new
interface. Keep the related documentation next to the public behavior it describes.

## Submit a change

Describe the behavior changed, the affected public interfaces, and the checks
you ran in a pull request. Keep saved scientific results associated with their
original model and runtime; editing a tutorial does not rerun it.

See [Workspace & Related Packages](home/ecosystem-workspace.md) for package roles,
[SCGSim integration](features/scgsim-integration.md) for the source/runtime boundary,
and [Documentation & Website](docs-publishing.md) for notebook pairing and deployment.
