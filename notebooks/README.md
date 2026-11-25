# Notebooks

The current authoring sources import `orcapen_sc_pdk`. The rename was source-only:
retained outputs were not rerun and remain attributed to their original OrPen
package, inputs and run identities. Changed imports are not evidence of execution
with the OrcaPen candidate.

## SCGSim examples

`SCGSimExamples/` contains the component and cross-section examples maintained
by OrcaPen for SCGSim use. Their single editable sources are under
`src/SCGSimExamples/`; matching IPYNBs are generated execution/download files.
The corresponding layouts live in `orcapen_sc_pdk/cells/simulation/scgsim/` and
remain available through the unified `orcapen_sc_pdk.cells` entry point and PDK.

Pages explain the physical problem, model and expected outputs. Notebooks own
the concrete dimensions, settings and public API calls. Solver examples use a
complete preparation, solve and returned-result workflow; preparation-only and
existing-run analysis are explicit alternatives where the backend provides them.
Geometry observations have no solver. Opening or rendering documentation does
not execute cells or establish native geometry, convergence or solved results.
The TSV examples currently retain their model-inspection stages while their
solve controls are being selected; the Modal entry is an authoring note, not a
complete solver example. Neither is presented as a finished full workflow.

```text
notebooks/
  SCGSimExamples/
    ComponentSimulation/
      SimplePad/
      CircularPad/
      CpwFiniteGround/
      CpwMeanderAirbridge/
      GeometrySemantics/
      TSV/
    CrossSectionSimulation/
      CpwFiniteGround/
  src/SCGSimExamples/          # canonical QMD sources, same case structure
  ComponentSimulation/        # separately retained historical examples/evidence
  Public_Docs/                # layout catalog
  Tools/                      # general inspection tools
```

Source layout families do not define a solver matrix: one layout can serve
several questions, and not every layout needs a solve. Keep OrcaPen's materials,
physical layers, source occurrences, holes, contact intent and explicit Net
meaning intact. SCGSim owns reusable lowering, meshes, handoff, execution,
Resolve and Report; notebooks do not implement a second solver runtime.

## Edit and generate

The canonical `.qmd` owns prose, code order and settings. Derived `.ipynb`
files are not independently editable sources. Include-only `_source_input.qmd`
fragments remain next to the consuming QMDs; generated notebooks contain their
cells and do not require the fragment when executing.

Regenerate the QMD-backed notebooks after editing:

```bash
just convert-notebooks
```

`just check-notebooks` renders temporary notebooks and compares ordered source,
code-cell IDs and metadata without executing or overwriting publication files.
Code cells have stable IDs, null execution counts and empty outputs. Retain
executed notebooks separately with their source, input, runtime and run identity;
never copy historical output into a changed source as proof of execution.

The repository pins
[SCGSim v3.0.0rc6](https://github.com/NCUPHY-LTLab/scgsim/tree/v3.0.0rc6)
(`4c3edca`). The Palace and geometry examples (SimplePad, CircularPad and
CpwFiniteGround Palace, Kosen2024 Xmon Palace, GeometrySemantics, and the
SimplePad Palace inset-band example) use its API and run on stock Palace
0.18.1. So do these AEDT examples, which run with AEDT 2024.2: SimplePad HFSS
Eigenmode (Prepare Handoff, Run, Run Directly and Analyze) and Q3D, and
CpwFiniteGround HFSS Eigenmode. The other AEDT and Q2D
examples still carry the API of their earlier checkpoints and do not run on
this pin until they are moved (NCUPHY-LTLab/orcapen-sc-pdk#66).
Each source states its exact runtime and optional backend prerequisites.
Source-only geometry observations and historical examples retain their own
declared checkpoints. Ordinary project dependencies and pins are not silently
changed by a notebook environment. AEDT and Palace remain separate notebooks.

## Models and evidence

The PDK base M1 film is 100 nm. TSV examples represent die-face metal as Thin
Film and preserve hollow walls and perforated Silicon as Solid. Airbridge
decks are local films; posts and indium bumps retain finite Solid declarations.
Other explicitly authored models keep their declared representation. Q2D uses
its own Nb 0.2 µm section, 10 µm gap and 40 µm grounds, not an automatic 3D slice.

Historical Xmon/finite-CPW entries and saved evidence remain outside the current
SCGSim example set with their original inputs and output attribution. An
authoring note is not a runnable solver example. Source availability and a
successful documentation render do not prove an AEDT model, solve or physics
result. The current examples remain CONVERGING.

Public notebooks contain no private layouts, private run paths or private
native evidence. See the [Simulation catalog](../docs/simulation/notebooks.qmd)
for requirements, example pages and downloads. Build the docs with `just docs`.
