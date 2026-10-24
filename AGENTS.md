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

## Documentation Ownership

Resolve ownership and delivery through `$scq-collaboration-roles` and
`$v1-lifecycle`. After the one-time handoff of active edits, the OrcaPen
Documentation Lead owns reader-facing authoring, corrections, site presentation,
and documentation task closeout through its own existing Luna workers. This
includes information architecture, wording, navigation and anchors, cards,
CSS/theme adoption, and documentation-only rendering configuration or helpers.
Ordinary documentation work needs no recurring Development prose approval or
release. Transfer an existing Preview through its explicit custody handoff.

Documentation authors reader wording, including docstrings, in mixed product or
configuration files and coordinates only exact overlapping hunks with the
current writer. Development retains product behavior, APIs, schemas, scientific
meaning, generators, packaged knowledge behavior, executable notebook/tutorial
code, CI, build, and release. Consult Development for implementation defects
or unresolved product/scientific meaning; send each coherent candidate and
exact source identity for implementation consistency, not editorial approval.

The existing Git owner and Integration perform commit, push, remote readback,
and applicable protection and privacy steps for reviewed Documentation
candidates. Mechanical delivery does not transfer writing responsibility or
create an editorial approval step. This hunk grants no product change
authority and adds no test or validation workflow.
