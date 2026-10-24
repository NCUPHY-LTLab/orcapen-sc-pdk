# OrcaPen SC PDK Agent Instructions

This is the public `OrPenStrike/orcapen-sc-pdk` repository. The registered OrcaPen
SC PDK Repo Lead owns its tracked production source. Private layout, parameters,
notebooks, and evidence stay private; QPDK is reference/example material only;
SCGSim owns reusable solver/runtime/result behavior.

## Task-Scoped Reading

Read only the sources relevant to the task:

- `README.md` when repository orientation is needed.
- `pyproject.toml` for packaging or dependencies.
- `orcapen_sc_pdk/pdk.py` for registries or factories.
- `orcapen_sc_pdk/tech.py` for layers or stack definitions.
- `docs/home/pdk-responsibilities.md` for ownership boundaries.
- `docs/features/scgsim-integration.md` for SCGSim integration or notebook work.

## Routing

`$v1-lifecycle` remains authoritative. Use `$scq-collaboration-roles` for
relevant ownership, cross-owner, or Git questions; resolve the exact scope's
route and delivery profile only when needed. Use `$scq-gdsfactory-layout`
only for layout, component, or geometry work.
Package usage starts at `docs/usage/index.md`.
The canonical Skills own the full collaboration and Git policy; do
not duplicate it here.
