---
title: "Theme and toolchain"
sidebar: development
---

This site uses the public `askr-html` format from
[Askr v0.12.0 released source](https://github.com/arfiligol/askr/tree/v0.12.0).
The unchanged extension is
vendored at `docs/_extensions/arfiligol/askr`, including its MIT license,
third-party notices and local font/icon assets. The extension manifest
`_extension.yml` declares version `0.12.0` and Quarto `>=1.9.38 <1.11`.
The [released extension metadata](https://github.com/arfiligol/askr/blob/v0.12.0/_extensions/askr/_extension.yml)
records the format and compatibility requirements.

The root `_extensions` symlink points to `docs/_extensions`. It lets relative
extension includes resolve through the existing `docs/notebooks` symlink when
rendering saved notebooks. There is one vendored extension, not a second copy;
canonical notebook source, pairing and outputs are unchanged.

Use Quarto **1.10.19**, the selected stable consumer/CI toolchain. Install that
version from the [official release](https://github.com/quarto-dev/quarto-cli/releases/tag/v1.10.19),
then check `quarto --version`. To reproduce the extension installation:

```bash
cd docs
quarto add arfiligol/askr@v0.12.0 --no-prompt
```

Commit reviewed extension updates as consumer bytes; do not edit the installed
copy or track a moving branch. `_quarto.yml` selects `askr-html` without
replacing its themes, reading measure, fonts, colors or native controls.
`styles.css` retains only local table overflow and diagram popout behavior.
Its consumer-only color aliases follow Askr's `--qdk-border` and `--qdk-canvas`
tokens. The [Cells gallery](../public-pdk-examples/index.md#components-layout)
uses the stock inline Image Viewer; the previous custom iframe viewer is retired.
See the [released viewer usage](https://github.com/arfiligol/askr/blob/v0.12.0/usage/image-viewer.qmd).

## Languages and repository link

The published homepage is Traditional Chinese; English is at `en/`. Each edition
has its own navigation and search, connected by Askr's documented
[`askr.languages` selector](https://arfiligol.github.io/askr/usage/languages.html).
The GitHub button uses native `website.navbar.tools`, not a local widget.

English sources remain in `docs/`; their Traditional Chinese translations live
in `docs/zh-TW/`. A full render writes English to `_site/en/`, then
`scripts/build_bilingual_docs.py` stages the shared theme, assets and API
reference to render Chinese at `_site/`. Generated references and executable
notebooks remain English and are linked from the Chinese guides. Update the
corresponding translation when reader content changes; keep code identifiers
and examples consistent between editions.

For the existing local Preview, render with `--profile preview`; the language
links then use `/` and `/en/` instead of the deployed project prefix.

Documentation rendering keeps `execute.enabled: false`. For build commands,
notebook pairing, and Pages deployment, use [Documentation & Website](../docs-publishing.md).
