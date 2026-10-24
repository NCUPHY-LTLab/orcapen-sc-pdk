---
title: "Surface Loss and Participation Studies"
sidebar: research
---

Read these references when selecting surface-interface assumptions or
interpreting participation calculations. Match the paper's geometry,
materials, and extraction method to your model.

| Reference | Reading focus |
| --- | --- |
| Wenner et al., “Surface loss simulations of superconducting coplanar waveguide resonators,” APL 99, 113513 (2011), [DOI](https://doi.org/10.1063/1.3637047) | MA/MS/SA interface taxonomy and surface-loss scaling |
| Woods et al., “Determining Interface Dielectric Losses in Superconducting Coplanar-Waveguide Resonators,” PRApplied 12, 014012 (2019), [DOI](https://doi.org/10.1103/PhysRevApplied.12.014012) | Interface-loss extraction and material/process assumptions |
| Wang et al., “Surface participation and dielectric loss in superconducting qubits,” APL 107, 162601 (2015), [DOI](https://doi.org/10.1063/1.4934486) | Transmon surface participation and geometry dependence |
| Lahtinen and Möttönen, “Effects of device geometry and material properties on dielectric losses in superconducting coplanar-waveguide resonators,” JPCM 32, 405702 (2020), [DOI](https://doi.org/10.1088/1361-648X/ab98c8) | Geometry, material-property uncertainty, and inverse interpretation |

## Select assumptions for a calculation

Record the interface role, thickness, permittivity, and loss tangent together
with whether each value was measured, fitted, or assumed in the source.
Include the metal, substrate, surface treatment, temperature, and frequency
when comparing processes.

The current public records are in
[materials.json](https://github.com/NCUPHY-LTLab/orcapen-sc-pdk/blob/aee7f8b848895f2d107f6b086310e866e8381f73/orcapen_sc_pdk/materials.json)
and returned by `get_interface_preset_records()`.
Use [Materials & Interfaces](../start/materials.qmd) to select records;
literature conventions are not automatic defaults for an unmatched process.

Continue with [Participation & Surface Loss](../simulation/requirements/epr-loss.qmd)
for available tutorials.
