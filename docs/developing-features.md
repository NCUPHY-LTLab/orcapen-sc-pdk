---
title: "Start contributing"
sidebar: development
---

Contribute reusable cells, process records, examples, or documentation through
the [public repository](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk). This
page sets up a checkout and takes a change from an Issue to a merged pull
request. To write a cell, continue with [What is a cell](contributing/what-is-a-cell.md)
and the [construction rules](contributing/rules.md).

## Set up a development checkout

```bash
git clone https://github.com/NCUPHY-LTLab/orcapen-sc-pdk.git
cd orcapen-sc-pdk
uv sync -p 3.12
```

This installs the PDK plus pytest and Ruff. Run `uv run python --version` to
check your interpreter. For viewer setup, see [Preview Cells](start/preview-cells.qmd).
For documentation dependencies and preview, see
[Documentation & Website](docs-publishing.md).

If the GDSFactory+ extension adds machine-specific settings to `pyproject.toml`
or `uv.lock`, keep those edits in your local checkout.

## How a change flows

1. **Issue.** Describe the goal and what done looks like. Larger work, a new
   cell or a change to a public interface starts here; a small, clear fix may
   go straight to a pull request.
2. **Issue branch.** Work on a branch made for that Issue, from `develop`.
3. **Pull request into `develop`.** Name the Issue, say what changed, and give
   the evidence for each acceptance item (see [Submit a change](#submit-a-change)).
4. **Review.** A reviewer checks the change against the Issue and, for a cell,
   against the [construction rules](contributing/rules.md). The PDK maintainers
   merge it.

## Add a preview to a new cell {#preview-a-component}

See [Preview Cells](start/preview-cells.qmd) for viewer setup and usage. End new
cell modules with the following block so users can run the file directly and
preview the selected cell.

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

## Submit a change {#submit-a-change}

Describe the behavior changed, the affected public interfaces, and the checks
you ran in a pull request. Keep saved scientific results associated with their
original model and runtime; editing a tutorial does not rerun it.

See [Workspace & Related Packages](home/ecosystem-workspace.md) for package roles,
[SCGSim integration](features/scgsim-integration.md) for the source/runtime boundary,
and [Documentation & Website](docs-publishing.md) for notebook pairing and deployment.

### Candidate cells

A candidate cell is a new cell that is not yet part of the Library, the set of
registered cells that this repository's `develop` branch carries. `develop` is
what consumers pin and what GDSFactory+ lists, so it holds no candidates: a
candidate there would become something others can depend on.

A candidate lives on its Issue branch, the branch made for the Issue that
proposes it. The repository owner may merge it into a personal branch, a
branch of their own used to preview work, to try it out. Personal branches
here are public, so a candidate that carries a private design starts in the
private layout repository instead.
