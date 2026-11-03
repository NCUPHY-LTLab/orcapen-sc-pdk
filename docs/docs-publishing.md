---
title: "Documentation & Website"
sidebar: development
---

Build the documentation site from `docs/` and the paired notebook sources with
the pinned docs environment. The build does not execute notebooks or launch a solver.

## Build locally

Generate the README and layer snippets first; Quarto scans those included files
before pre-render hooks run.

```bash
uv sync -p 3.12 --locked --group docs --extra dev
uv run --group docs python scripts/sync_qmd_notebooks.py notebooks/src notebooks
uv run --group docs python scripts/build_overview_snippets.py
uv run --group docs quarto render docs --no-execute
uv run python scripts/check_docs_navigation.py docs/_site
```

Run the notebook synchronization command as a check; it must report no drift.
The rendered site is in `docs/_site/`. For a local static preview, serve that
built directory on loopback with `python -m http.server --directory docs/_site
8000 --bind 127.0.0.1`.

## Edit notebook guides

Canonical tutorial sources live in `notebooks/src/`; distributed notebooks live
in `notebooks/`. Generate a changed pair only with the synchronization tool's
explicit `--generate` option. Review the matching SCGSim version and usage
instructions before changing executable examples.

## Pages and publication

Ready pull requests build the site for review. A successful build on `main`
publishes to [GitHub Pages](https://ncuphy-ltlab.github.io/orcapen-sc-pdk/).
The site uses native Quarto navigation and the Askr theme; see
[theme and toolchain](features/docs-theme.md).

Keep the older topic URLs available for existing references without restoring
them to the core References route.

::: {.callout-note title="Older topic URLs" collapse="true"}
- [CPW Resonator References](papers/cpw-resonator-references.md)
- [Transmon Reference Designs](papers/transmon-reference-designs.md)
- [Flip-Chip and 3D Integration](papers/flip-chip-3d-integration.md)
:::

## Preserve released documentation

Before preparing a later release, add each earlier release's `docs-site.tar.gz`
to `docs/releases-history.json` with its version, tag and SHA-256 from that
release's `SHA256SUMS`. Pages downloads only these named archives and retains
them under `vVERSION/`; Askr lists the real editions in its version menu.
The history list is empty for the first release.
