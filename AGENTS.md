# OrcaPen SC PDK Agent Instructions

This is the public `NCUPHY-LTLab/orcapen-sc-pdk` repository. The OrcaPen Repo
Lead owns product source, documentation and the documentation Preview. Private
layouts, parameters, notebooks and evidence stay private. QPDK is reference
material; SCGSim owns reusable solver, runtime and result behavior.

## Task-Scoped Reading

Read only the sources relevant to the task:

- `README.md` for repository orientation.
- `pyproject.toml` for packaging or dependencies.
- `orcapen_sc_pdk/pdk.py` for registries or factories.
- `orcapen_sc_pdk/tech.py` for layers or stack definitions.
- `docs/home/pdk-responsibilities.md` for package boundaries.
- `docs/features/scgsim-integration.md` for SCGSim integration or notebook work.

Package usage starts at `docs/usage/index.md`.

## Implementation and Documentation

The Repo Lead handles small, tightly coupled changes directly. Delegate larger
implementation, documentation-site or noisy work as needed within the existing
two-worker limit. Use a team `docs_writer` for substantial writing; there is no
separate Documentation Lead or recurring prose-approval handoff.

Keep one writer per overlapping path or hunk. Preserve existing work, valid
results and the running Preview. A change includes its directly related
documentation and tests under the Human-authorized scope; removing a feature
also includes its obsolete dedicated tests. Keep real failures visible rather
than skipping checks or weakening assertions or coverage.

## Shared Policy and Delivery

Use `$v1-lifecycle` for lifecycle and Human research decisions,
`$scq-collaboration-roles` for relevant ownership and Git routing, and
`$model-routing` when assigning work. Use `$scq-gdsfactory-layout` for layout,
component or geometry work. These shared Skills remain the policy authority;
do not duplicate their forms or checklists here.

The original Git owner serializes ordinary commit, push and remote readback,
preserving unrelated WIP. Integration retains its assigned CI and protected
delivery work. Publication, merge, release, deployment and consumer pin changes
follow their separate Human authority.
