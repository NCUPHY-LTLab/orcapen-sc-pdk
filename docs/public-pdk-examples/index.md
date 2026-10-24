---
title: "Cells"
sidebar: get-started
---

Choose a registered OrcaPen factory for the geometry you need. Activate the
PDK first, then use its [component guide](components/index.qmd) to inspect the
defaults, ports, and layers before changing dimensions.

For path-based cells, choose the widths, gaps, and layer recipe in
[Cross-sections](cross-sections.qmd), including CPW, coupled traces, and strips.

| Family | Component guides |
| --- | --- |
| CPW and resonators | [straight](components/straight.qmd), [taper](components/taper.qmd), [resonator](components/resonator.qmd), [resonator_hanger](components/resonator_hanger.qmd), [resonator_meander](components/resonator_meander.qmd) |
| Capacitors | [interdigital_capacitor](components/interdigital_capacitor.qmd), [martinis2022_differential_ribbon_capacitor](components/martinis2022_differential_ribbon_capacitor.qmd) |
| Connections | [launcher](components/launcher.qmd), [cpw_t_junction](components/cpw_t_junction.qmd), [airbridge](components/airbridge.qmd), [indium_bump](components/indium_bump.qmd), [indium_ground](components/indium_ground.qmd) |
| Primitives | [cpw_handoff](components/cpw_handoff.qmd), [rounded_end_metal_segment](components/rounded_end_metal_segment.qmd), [rounded_rectangle](components/rounded_rectangle.qmd), [wire_corner](components/wire_corner.qmd) |
| Simulation layouts | Square/circular pads, finite CPW, strips, flip-chip, airbridge, and TSV models in the [Model Gallery](test-components.md) |

Use the [generated cell API](../reference/index.qmd#cells) for signatures,
[shared primitives](shared-primitives.md) for connection roles, and
[GDSFactory guides](component-authoring.md) for placement, connection, and routing.

## Choose a cell with flat tags

Factories use flat metadata tags for purpose (`layout` or `simulation`),
object (`capacitor`, `resonator`, `cpw`), and features such as `airbridge`
or `flip_chip`. Tags help you find source geometry; choose a separate
[simulation tutorial](../notebooks.qmd) for electrical behavior.

## Components Layout

Default layout previews show DRAW in deep teal and ETCH in light teal.
Use **+ / −**, drag, **Fit**, or **Expand** to inspect the existing images.

### Resonator

[Factory source: `resonator`](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/blob/aee7f8b848895f2d107f6b086310e866e8381f73/orcapen_sc_pdk/cells/layout/resonator.py)
builds a CPW resonator from hanger and meander sections.

![Default resonator: actual DRAW and ETCH.](../_static/images/components/resonator.svg){#fig-layout-resonator}

{{< askr-image-view target="fig-layout-resonator" mode="inline" >}}

### Interdigital capacitor

[Component guide](components/interdigital_capacitor.qmd) covers the factory
settings and corner-radius behavior. The image below shows the sharp default.

![Default interdigital capacitor: actual DRAW and ETCH.](../_static/images/components/interdigital_capacitor.svg){#fig-layout-idc}

{{< askr-image-view target="fig-layout-idc" mode="inline" >}}

### Martinis ribbon capacitor

[Factory source: `martinis2022_differential_ribbon_capacitor`](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/blob/aee7f8b848895f2d107f6b086310e866e8381f73/orcapen_sc_pdk/cells/layout/martinis.py)
provides the differential ribbon capacitor layout.

![Default Martinis ribbon capacitor: actual DRAW only; the source has no ETCH.](../_static/images/components/martinis2022_differential_ribbon_capacitor.svg){#fig-layout-martinis}

{{< askr-image-view target="fig-layout-martinis" mode="inline" >}}

### Launcher

[Factory source: `launcher`](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/blob/aee7f8b848895f2d107f6b086310e866e8381f73/orcapen_sc_pdk/cells/layout/cpw.py)
provides the CPW launcher layout.

![Default CPW launcher: actual DRAW and ETCH.](../_static/images/components/launcher.svg){#fig-layout-launcher}

{{< askr-image-view target="fig-layout-launcher" mode="inline" >}}

### Bump geometry

[Factory source: `indium_ground`](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/blob/aee7f8b848895f2d107f6b086310e866e8381f73/orcapen_sc_pdk/cells/layout/indium.py)
provides indium bump `40/0` and UBM `40/1` footprints, without M1 DRAW/ETCH.
See the [Test Set's flip-chip view](test-components.md#reading-the-multi-level-views)
for layer-separated bump geometry.
