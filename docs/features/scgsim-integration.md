---
title: "Use OrcaPen source with SCGSim"
---

OrcaPen supplies geometry, layers/stack, materials and source annotations.
SCGSim is the reusable runtime for native geometry, backend preparation,
meshes, solver handoff and result resolution/reporting.

## Choose the notebook and its runtime

Start from [Simulation](../notebooks.qmd), select the component/backend and
follow that canonical source's declared runtime environment. The ordinary
project cohort and revised source-only v2 notebooks are distinct; installing
an optional backend group does not turn one into the other. Saved output may
belong to an earlier source/stack and is not evidence of executing a revision.
Canonical `.qmd`/`.py` sources and saved `.ipynb` pairs remain the example
authority; this guide does not define a parallel workflow.

## Preserve geometry and problem intent

- Keep conductor regions, material IDs and stack choices intact.
- Carry real port/locator sheets; nonmetal locators are not positive metal or
  native terminal assignments.
- Assign final Nets, reference conductors and excitation in the consuming
  design, using the selected runtime's supported contract.
- Export the geometry required by that example; a source GDS file or image
  does not prove native import or contacts.

[Process](../materials-and-technology.md) explains DRAW/masks/holes, stack
selection and materials. Follow the selected notebook's version-bound links
for backend APIs and prerequisites. The [SCGSim development documentation](https://github.com/OrPenStrike/scgsim/tree/develop/docs)
is the current moving development branch, not a fixed notebook runtime.

## Physical source declarations

Occupied process levels expose one plain `LayerLevel.info["physical_layer"]`
payload matching SCGSim's `PhysicalLayerDeclaration` fields. OrcaPen emits it
without importing SCGSim. It retains the authored level identity, GDS pair,
physical Z interval and material. `stack_film` and `local_film` include original
normal thickness and an explicit attachment face; finite posts, bumps, TSV walls
and substrate/domain volumes use `finite_volume`. Nonmetal locator sheets and
excluded under-bump footprints are not declared physical bodies.

This fresh carrier replaces `aedt_modeling`; it is not a compatibility alias.
Feature kind does not select retention, sheet projection, collapse, effective Z
or any backend. Consumers choose the explicit runtime approximation profile.
Each selected input occupies one original LayerStack frame; children sharing a
physical process identity do not create independent film-collapse events.

Generic levels have `actual_entity_contact_graph=None`. Selected source getters
can attach one consistent source-owned graph to their detached declarations,
without mutating the global catalogue. The graph separates existing contacts
and nonmetal supports from newly authored `source_owner_incidence`. Such
incidence is source intent, not native continuity or calculator field-side proof.

The Pair17 getter leaves its original 63 body records, holes and affines intact.
It provides `entity_aliases` and `physical_layer_bindings`, keyed by original
qualified record ID. A binding contains `source_level_id`, `physical_layer_id`,
`source_occurrence_path`, `source_local_entity_id` and `entity_selector`.
The selected Level payload remains under `source_levels[name].info.physical_layer`,
including the explicit Si identity. Original placed rings are not transformed
again; local supports retain their recorded occurrence transform. Only the
selected M1 film is supplied, not unused catalogue films or an invented upper die.

The TSV detached getter preserves its original wall/landing contact records and
actual body intervals. Its shared wall declaration adds radial wall thickness
from the selected source parameters, separately from axial span. Existing
sampled rings, perforated Si and empty-bore intent are not repaired or relabelled;
source recipe correspondence is not exact/native hole or contact readback.
These declaration/getter changes remain a CONVERGING source candidate; saved
exports and earlier runtime cohorts retain their original interpretation.

## Preparation is not execution

The sequence is source intent → runtime preparation → native handoff/execution
→ returned-run resolution → reports. Inspect actual native readback when
required by your example, then retain its returned outputs and provenance.
Palace and AEDT have separate prerequisites; source availability does not
establish an implemented branch. No runnable native branch is added here for
the source-only spline, flip-chip or airbridge Test Set views.
