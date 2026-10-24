---
title: "Contributing"
sidebar: development
---

Contribute reusable cells, process records, examples, or documentation through
the [public repository](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk).
Start with the part of the PDK your change affects.

## Set up a development checkout

```bash
git clone https://github.com/NCUPHY-LTLab/orcapen-sc-pdk.git
cd orcapen-sc-pdk
uv sync -p 3.12 --extra dev
```

Check: `uv run python --version` reports a supported Python version.
For documentation dependencies and preview, use
[Documentation & Website](docs-publishing.md).

## Keep changes focused

- Put reusable layout and process definitions in OrcaPen.
- Reuse GDSFactory for component composition and routing.
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
