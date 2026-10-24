# Shared layout primitives

These four registered factories are public source geometry, not electrical
models, native simulation inputs or fabrication targets. Their neutral preview
dimensions use public 7/10 µm traces, 6 µm clearance and 100 µm routing radius.
Activate OrcaPen and import them from `orcapen_sc_pdk.cells`, or build their
registered names with `gf.get_component`.

## CPW handoff

`cpw_handoff(length=200, taper_length=50, native_width=10, native_gap=6,
route_width=7, route_gap=6, radius=100, draw_layer=..., etch_layer=...,
ground_mask_layer=...)` reuses the public CPW cross-section, straight and taper.
The straight occupies `length - taper_length`; the outgoing taper is included
once in the total length. `o1` is at `(0, 0)`, facing 180°, with native width;
`o2` is at `(length, 0)`, facing 0°, with route width. Both ports are on DRAW.
Radius is cross-section/routing metadata, not a bend in this straight cell.

Length must be positive and `0 <= taper_length <= length`. A taper-only segment
is supported. With zero taper, native and route widths **and gaps** must match:
the factory does not disguise an absent transition by changing a port width.
Existing cross-section/native GF errors own invalid trace/gap inputs.

## Metal segment with one rounded end

`rounded_end_metal_segment(length=100, width=10, ground_mask_margin=6,
n_cap_points=17, draw_layer=..., etch_layer=..., ground_mask_layer=...)`
has a flat face at local X=0 and a semicircular right end. The cap radius is
`width/2`, its centre is `(length-width/2, 0)`, and its tip is `(length, 0)`.
Length includes the cap extent once; it is not a resonator or electrical length.
The positive width requires `length >= width/2`. Sampling has `n_cap_points`
points per quarter of the semicircle, including its apex and endpoints; at
least two points per quarter are needed to retain those endpoints.

One DRAW polygon supplies the GroundMask polygon, expanded by the public GF
offset operation in µm using its default corner mode. ETCH is `MASK - DRAW`.
This is polygon offset geometry, not a claim of exact analytic offset circles.
The nonnegative margin is a source clearance input, not a mesh-size policy.
Route port `o1` is at `(0, 0)`, facing 180°, with trace width. `o_mesh` is a
named mesh-region locator on DRAW at the cap centre, facing 0°, with trace
width. It is **not** a second route port, junction, load or assigned solver mesh.
At `length == width/2` the shape is a half-disk: `o_mesh` is on the flat
boundary at the same centre as `o1`, with opposite orientation and a distinct
locator type. A cap-centre marker does not guarantee strict interior placement.
Private multi-term lengths and placement offsets remain caller composition:
the caller supplies the resulting geometric length and places the flat anchor.

## Rounded rectangle

`rounded_rectangle(width=100, height=50, corner_radius=7,
n_corner_points=20, ground_mask_margin=6, draw_layer=...,
ground_mask_layer=None, port_type="electrical")` delegates the centred DRAW
polygon to `gf.components.rounded_rectangle`, with equal X/Y corner radii.
Positive dimensions and `0 <= corner_radius <= min(width,height)/2` define the
fitting corner domain; larger radii are rejected, not silently clamped.
Sampling is GF's points **per corner**, not a private KLayout whole-rounding
parameter. `n_corner_points` must include the two quarter-arc endpoints.

An optional GroundMask is a separately rounded rectangle of dimensions
`width+2*margin`, `height+2*margin`, with radius `corner_radius+margin`.
It has no ports and this factory generates no ETCH. A supplied mask requires
nonnegative margin. Without a mask the margin is unused.

`port_type=None` supplies no ports. Otherwise the factory forwards GF's actual
edge ports and naming: side-port widths are `height-2*radius`, top/bottom widths
are `width-2*radius`, not the original full rectangle edges. GF owns naming,
pins and errors for degenerate port widths. Sampling and ports therefore
**differ** from private rounded-rectangle helpers; source equivalence is not
asserted, and callers must migrate their sampling and port assumptions explicitly.

## Wire corner

`wire_corner(cross_section="cpw_6_7_6", port_names=("e1","e2"),
port_types=("electrical","electrical"), width=None, radius=None)` is a thin
adapter to GF's first-party wire corner. Selected GF 9.48 accepts but ignores
radius; this is a sharp corner, not a curved bend. With cross-section width W,
the native ports are `(-W/2,0)` facing 180° and `(0,W/2)` facing 90°. GF owns
the cross-section bounding geometry, electrical pins and supplied port contract.
Caller-selected cross-sections remain explicit; no private CPW default is copied.

## Migration and delivery

There are no `as_` aliases, private imports, sibling-device factories or fallback
implementations. The public names and the above anchor, sampling and port
differences are the migration surface. Private composition and callers stay
with their consumer owner until an exact usable producer delivery is available.
These factories are a local source candidate. The published old-namespace base
cannot deliver an independent `orcapen_sc_pdk` patch; usable delivery depends on
the pending OrcaPen namespace/integration lane and its privacy review. Local
build success or a version string does not establish publication or adoption.
