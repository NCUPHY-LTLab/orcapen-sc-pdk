# OrcaPen package usage knowledge

OrcaPen supplies public PDK facts, reusable components and layout authoring,
semantic inspection, and public Component Simulation notebook sources. These
guides describe the package shipped with them. Use the installed distribution
version and resource digests when recording which instructions were consumed;
the current website or a neighboring checkout may describe different bytes.

## Canonical resource inventory

| Resource | Editable source | Scope and status |
| --- | --- | --- |
| Component authoring | `docs/public-pdk-examples/component-authoring.md` | Available: activation, discovery, public geometry, ports, units and preview |
| Semantic inspection | `docs/usage/semantic-inspection.md` | Available: concept versus artifact inspection and reproducible inspection plates |
| Component Simulation notebooks | `docs/usage/component-simulation-notebooks.md` | Available examples; run results retain their individual diagnostic or historical status |
| Publication pairing | `docs/docs-publishing.md` | Available: canonical QMD inputs, derived IPYNB, output-preserving checks |
| Process and material APIs | `orcapen_sc_pdk/tech.py`, `orcapen_sc_pdk/materials.py`, `orcapen_sc_pdk/materials.json` | Canonical source: structured PDK records; see the authoring guide |
| Public examples | `notebooks/src/ComponentSimulation/`, `notebooks/src/CrossSectionSimulation/`, `notebooks/src/Tools/` | Canonical example inputs; never evidence that a new run has succeeded |

The guides and examples are the editable authorities. Offline packaging must
copy or derive resources from these sources, not maintain another editable
instruction set. Raw run folders, executed outputs, credentials and local
environment configuration are not usage resources.

## Prerequisites and boundaries

The public core needs the Python and GDSFactory versions declared by this
distribution. GDSFactory+ is an optional design/editing/viewer integration;
core PDK use does not require the commercial extra. A live viewer and a solver
installation are not prerequisites for reading installed knowledge.

The source-authority chain is:

```text
OrcaPen material/layer/stack facts + canonical component semantics
-> generic scgsim.sgb
-> SCGSim solver runtime, returned results and reports
```

For simulation API signatures, backend prerequisites, failure behavior and
supported runtime capabilities, read the knowledge bundle belonging to the
installed `scgsim` distribution. If that bundle is unavailable, report that
fact and consult its matching version documentation; do not import a solver
to discover documentation or infer support from an OrcaPen example. OrcaPen's
examples show consumer placement, not a second SCGSim API specification.

The offline bundle is available independently of MCP. Discovery of the renamed
`orcapen-sc-pdk` distribution through the existing MCP supported-name table has
not been observed; do not assume support from bundle availability. OrcaPen has
no MCP runtime dependency. Knowledge availability does not imply license availability,
numerical convergence, fabrication qualification or scientific acceptance.

## Installed offline bundle

The renamed `0.1.0.dev2` distribution is currently a local candidate only. Its
packaged resources describe available source behavior, not Human acceptance,
registry publication or newly executed notebook evidence. See
[Distribution and handoff](../distribution.md).

Ordinary wheels and source distributions contain
`orcapen_sc_pdk/_agent_knowledge/manifest.json` and the UTF-8 sources declared by
`docs/usage/resources.toml`. That file owns resource IDs and descriptions;
content remains in its listed canonical source. Build with `uv build`.
The build hook generates resource copies and hashes before invoking `uv_build`;
it imports neither OrcaPen nor a numerical runtime. Generated resources are
ignored in the checkout and must not be edited. The sdist contains both the
generated bundle and its generation inputs, allowing offline wheel rebuilds
with the declared build backend already installed.

This distribution consumes Agent Knowledge Bundle transport `1.0`, whose
canonical contract belongs to `OrPenStrike/scq-mcp` at
`docs/agent-knowledge-bundle.md`. OrcaPen defines content, not another transport
schema. The manifest binds the distribution version, sorted resource IDs,
source paths/hashes, exact content hashes and canonical bundle digest. Wheel
`RECORD` binds those installed bytes independently. Stable resource IDs survive
documentation moves; a changed guide changes its content identity.

Install an ordinary wheel into the environment used by the consumer and its
optional MCP reader. Editable installs are not supported for bundle discovery.
The following locates the manifest without importing `orcapen_sc_pdk`:

```python
from importlib.metadata import distribution

dist = distribution("orcapen-sc-pdk")
manifest_entry = next(
    entry for entry in dist.files or ()
    if str(entry) == "orcapen_sc_pdk/_agent_knowledge/manifest.json"
)
manifest_text = dist.locate_file(manifest_entry).read_text(encoding="utf-8")
```

This is a metadata lookup example, not a replacement integrity validator.
For distributions it supports, the MCP reader verifies distribution version, declared paths, bundle/content
digests and wheel `RECORD` hashes/sizes before returning text. Missing or
modified resources, unavailable distributions and version mismatches must be
reported explicitly; there is no implicit workspace or network fallback.
Bundled example source is read as text. Executing a notebook remains a separate
action governed by its consumer environment, selected workflow and artifacts.
