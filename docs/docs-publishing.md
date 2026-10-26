---
title: "Documentation & Website"
sidebar: development
---

Edit English reader pages in `docs/`, their Traditional Chinese translations in
`docs/zh-TW/`, and canonical tutorial sources in `notebooks/src/`. Build with
Quarto 1.10.19; the site keeps notebook execution disabled.

## Build locally

```bash
uv sync -p 3.12 --locked --group docs --extra dev
just docs
```

Check: generated notebook inputs match their QMD sources, and the site appears
in `docs/_site/`. Traditional Chinese is the default homepage; English is in
`docs/_site/en/`. The pre-render step generates the API reference with quartodoc.

For a local preview:

```bash
just serve-docs
```

Check: open `http://127.0.0.1:8000`. Inspect the desktop navigation and the
collapsed menu at narrow widths.
The command builds both editions with local language links before starting the
static server. Rebuild with `quarto render docs --profile preview --no-execute`
after editing; refresh the browser to see the new pages.

## Edit notebooks without changing their results

QMD files own the tutorial text, executable cells, settings, and stable code-cell IDs.
Their IPYNB counterparts are generated downloads. After editing a QMD, regenerate
the corresponding notebook with the existing pairing tool; use
`just convert-notebooks` for the repository-wide conversion.

`just check-notebooks` compares source structure without running cells.
Keep simulation execution separate from site generation.

## Pages and downloads

Ready pull requests build the site for review; Draft builds are skipped. A successful build on `main`
deploys to [GitHub Pages](https://ncuphy-ltlab.github.io/orcapen-sc-pdk/).

The SurfaceBands examples render from their canonical QMD paths so sibling
HTML links and the model JSON stay together. Their IPYNBs remain separate
downloads. The existing post-render helper copies the two raw QMD sources
byte-for-byte into site output; raw download anchors use `data-noresolveinput`.

## Theme and site structure

The site uses the unchanged Askr extension and native Quarto navigation.
See [theme and toolchain](features/docs-theme.md) for its selected versions.
Place pages in one of Get Started, Simulation, API, Research, or Development;
the logo returns to the home page.

Use [public package source](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk) for API
definitions and [Research](paper-review.md) for literature notes.
