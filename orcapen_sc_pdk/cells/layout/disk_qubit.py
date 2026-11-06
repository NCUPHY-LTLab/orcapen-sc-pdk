"""Public flip-chip disk transmon reference cell.

One single-junction disk island inside a circular ground clearance on the qubit
die (D1), with optional four N/E/S/W tunable-coupler ("TC") claws, a readout and
an XY drive line on the facing control die (D0), and a ring of ground bumps.

This is OrcaPen-authored source. Public precedents, cited for provenance only:

- Braumüller et al., APL 108, 032601 (2016), https://doi.org/10.1063/1.4940230:
  a circular island inside a circular clearance.
- KQCircuits ``CircularTransmonSingleIsland``,
  https://iqm-finland.github.io/KQCircuits/api/kqcircuits.qubits.circular_transmon_single_island.html:
  a single island grounded through one junction, with arc couplers at a fixed
  radius. KQCircuits is GPL-3.0; none of its code is used here.
- Kosen et al., QST 7, 035018 (2022), https://doi.org/10.1088/2058-9565/ac734b:
  a qubit die and a control die joined by indium bumps, with readout and drive
  on the control die.

The four grounded claws, the tapered junction leads and moving readout and drive
to the control die are this design's own adaptations. The defaults are layout
preset values, not a measured or qualified device.
"""

from math import cos, isfinite, radians, sin, sqrt
from typing import Literal

import gdsfactory as gf

import orcapen_sc_pdk.curve_sampling as curves
from orcapen_sc_pdk.cells.layout.indium import indium_bump
from orcapen_sc_pdk.cells.layout.junction import manhattan_style_junction
from orcapen_sc_pdk.helpers.layout import add_etch_for_component
from orcapen_sc_pdk.helpers.layout.geometry import Point, polar_point
from orcapen_sc_pdk.tech import LAYER, Layer

type Side = Literal["N", "E", "S", "W"]
TC_SIDE_ANGLES_DEG: dict[Side, float] = {"N": 90.0, "E": 0.0, "S": 270.0, "W": 180.0}
ALL_TC_SIDES: tuple[Side, ...] = ("N", "E", "S", "W")
# Bumps sit on a 32-site lattice (11.25 deg pitch). The claw handoff plane is the
# outer edge of the two 40 um under-bumps beside each claw lead.
HANDOFF_RADIUS_UM = 400.0 * cos(radians(11.25)) + 20.0

Q_DRAW = LAYER.D1_BOTTOM_M1_DRAW
Q_ETCH = LAYER.D1_BOTTOM_M1_ETCH
Q_MASK = LAYER.D1_BOTTOM_GROUND_MASK
C_DRAW = LAYER.D0_TOP_M1_DRAW
C_ETCH = LAYER.D0_TOP_M1_ETCH
C_MASK = LAYER.D0_TOP_GROUND_MASK


@gf.cell(tags=["layout", "qubit", "disk", "flip_chip"])
def disk_flip_chip_qubit(
    disk_radius: float = 110.5,
    ground_clearance_diameter: float = 700.0,
    site_size: float = 1000.0,
    include_ground: bool = True,
    include_tc: bool = True,
    grounded_tc_sides: tuple[Side, ...] = ALL_TC_SIDES,
    tc_disk_gap: float = 60.0,
    tc_disk_gap_by_side: tuple[tuple[Side, float], ...] = (),
    tc_width: float = 60.0,
    tc_span_deg: float = 45.0,
    tc_landing_span_deg: float = 45.0,
    tc_cpw_width: float = 3.0,
    tc_cpw_gap: float = 40.0,
    tc_lead_start_radius: float | None = None,
    tc_lead_width: float = 3.0,
    tc_lead_gap: float = 40.0,
    tc_end_clearance: float = 40.0,
    handoff_radius: float = HANDOFF_RADIUS_UM,
    junction_angle_deg: float = 315.0,
    junction_radius: float = 237.5,
    junction_lead_width: float = 2.0,
    junction_taper_span_deg: float = 20.0,
    junction_ground_overlap: float = 10.0,
    readout_angle_deg: float = 135.0,
    readout_tip_radius: float = 0.0,
    readout_width: float = 7.0,
    readout_gap: float = 6.0,
    drive_angle_deg: float = 225.0,
    drive_tip_radius: float = 412.0,
    drive_width: float = 4.0,
    drive_gap: float = 6.0,
    bump_ring_radius: float = 400.0,
    bump_lattice_count: int = 32,
    bump_skip_period: int = 4,
    curve_sampling: curves.CurveSampling = curves.FABRICATION,
) -> gf.Component:
    """Return a single-junction disk transmon site on a two-die flip-chip stack.

    All lengths are in um and the site is centred at the origin.

    Qubit die, D1 bottom face: a disk of ``disk_radius`` inside a circular
    ground clearance. One Manhattan junction at ``junction_angle_deg`` and
    ``junction_radius`` joins the disk to ground; both junction leads taper to
    a ``junction_taper_span_deg`` arc where they land. With ``include_tc`` the
    four claws sit ``tc_disk_gap`` outside the disk (``tc_disk_gap_by_side``
    overrides single sides). Each claw tapers to a CPW that leaves the
    clearance and ends at ``handoff_radius``, where its ``tc_<side>`` port is.
    ``tc_lead_start_radius`` switches the CPW to a second
    ``tc_lead_width``/``tc_lead_gap`` section from that radius outward. A claw
    in ``grounded_tc_sides`` continues as a short strip through its
    ``tc_end_clearance`` into ground; the others stay floating.

    Control die, D0 top face: the same clearance, a readout CPW whose rounded
    tip is at ``readout_tip_radius`` (the default reaches the disk centre) and
    a drive CPW whose tip is at ``drive_tip_radius``. Their ``readout`` and
    ``drive`` ports lie on the handoff square, where max(|x|, |y|) equals
    ``handoff_radius``.

    Ground on each die is the ``site_size`` square minus its ground mask. Set
    ``include_ground=False`` to leave both grounds (and the die areas) out, so a
    parent can draw one ground over several sites. Ground bumps fill a
    ``bump_lattice_count`` lattice on ``bump_ring_radius``, skipping every
    ``bump_skip_period``-th site so the claw, readout, drive and junction
    directions stay free.

    The floating-claw preset uses ``grounded_tc_sides=()`` with
    ``disk_radius=119.839``. Defaults are layout presets, not paper-mask or
    measured dimensions.
    """

    clearance_radius = ground_clearance_diameter / 2
    tc_gaps = _resolved_tc_gaps(tc_disk_gap, tc_disk_gap_by_side)
    # Every argument plus the two derived values above.
    _check_settings(**locals())

    c = gf.Component()
    c << curves.circle(radius=disk_radius, layer=Q_DRAW, sampling=curve_sampling)
    for mask_layer in (Q_MASK, C_MASK):
        c << curves.circle(radius=clearance_radius, layer=mask_layer, sampling=curve_sampling)

    junction = _add_rotated(
        c,
        _disk_junction(
            disk_radius=disk_radius,
            junction_radius=junction_radius,
            lead_width=junction_lead_width,
            taper_span_deg=junction_taper_span_deg,
            ground_landing_radius=clearance_radius + junction_ground_overlap,
            curve_sampling=curve_sampling,
        ),
        junction_angle_deg,
    )
    c.add_port(name="o_junction_lumped", port=junction.ports["o_junction_lumped"])

    tc_sides = ALL_TC_SIDES if include_tc else ()
    for side in tc_sides:
        claw = _tc_claw(
            inner_radius=disk_radius + tc_gaps[side],
            width=tc_width,
            span_deg=tc_span_deg,
            landing_span_deg=tc_landing_span_deg,
            clearance_radius=clearance_radius,
            cpw_width=tc_cpw_width,
            cpw_gap=tc_cpw_gap,
            lead_start_radius=tc_lead_start_radius,
            lead_width=tc_lead_width,
            lead_gap=tc_lead_gap,
            end_clearance=tc_end_clearance,
            handoff_radius=handoff_radius,
            grounded=side in grounded_tc_sides,
            curve_sampling=curve_sampling,
        )
        claw = _add_rotated(c, claw, TC_SIDE_ANGLES_DEG[side])
        c.add_port(name=f"tc_{side}", port=claw.ports["o1"])

    for name, angle, tip_radius, width, gap in (
        ("readout", readout_angle_deg, readout_tip_radius, readout_width, readout_gap),
        ("drive", drive_angle_deg, drive_tip_radius, drive_width, drive_gap),
    ):
        line = _rounded_tip_cpw(
            tip_radius=tip_radius,
            port_radius=_handoff_square_radius(handoff_radius, angle),
            width=width,
            gap=gap,
            curve_sampling=curve_sampling,
        )
        line = _add_rotated(c, line, angle)
        c.add_port(name=name, port=line.ports["o1"])

    c = add_etch_for_component(c, draw_layer=Q_DRAW, mask_layer=Q_MASK, etch_layer=Q_ETCH)
    c = add_etch_for_component(c, draw_layer=C_DRAW, mask_layer=C_MASK, etch_layer=C_ETCH)

    if include_ground:
        # The positive ground is derived after every mask is placed, so it owns
        # exactly the complement of the openings on its die face.
        c.add_ref(
            _die_ground(c, site_size, LAYER.D1_SUBSTRATE_AREA, Q_DRAW, Q_MASK), name="d1_ground"
        )
        c.add_ref(
            _die_ground(c, site_size, LAYER.D0_SUBSTRATE_AREA, C_DRAW, C_MASK), name="d0_ground"
        )

    bump = indium_bump(curve_sampling=curve_sampling)
    bump_angles = _bump_angles_deg(bump_lattice_count, bump_skip_period)
    for index, angle in bump_angles.items():
        bump_ref = c.add_ref(bump, name=f"bump_{index:02d}")
        bump_ref.dmove(polar_point(bump_ring_radius, angle))

    floating_sides = [side for side in tc_sides if side not in grounded_tc_sides]
    c.info["topology"] = (
        "D1 disk island with one Manhattan junction to ground, "
        f"{len(tc_sides)} TC claws ({len(floating_sides)} floating), "
        "D0 readout and drive lines, ground bump ring"
    )
    c.info["source_references"] = (
        "10.1063/1.4940230",
        "10.1088/2058-9565/ac734b",
        "KQCircuits CircularTransmonSingleIsland (prior art only; GPL-3.0 code not used)",
    )
    c.info["preview_default_provenance"] = (
        "Layout preset defaults; not paper-mask or measured dimensions."
    )
    c.info["tc_sides"] = tc_sides
    c.info["grounded_tc_sides"] = tuple(side for side in tc_sides if side in grounded_tc_sides)
    c.info["tc_disk_gap_by_side_um"] = {side: tc_gaps[side] for side in tc_sides}
    c.info["handoff_radius_um"] = float(handoff_radius)
    c.info["junction_overlap_center_um"] = polar_point(junction_radius, junction_angle_deg)
    c.info["bump_count"] = len(bump_angles)
    c.info["include_ground"] = include_ground
    c.info["component_semantics"] = _component_semantics(
        tc_sides=tc_sides,
        floating_sides=floating_sides,
        tc_center_radii={side: disk_radius + tc_gaps[side] + tc_width / 2 for side in tc_sides},
        readout_selector=polar_point(readout_tip_radius + readout_width / 2, readout_angle_deg),
        drive_selector=polar_point(drive_tip_radius + drive_width / 2, drive_angle_deg),
        ground_selector=polar_point((clearance_radius + site_size / 2) / 2, 22.5),
        include_ground=include_ground,
    )
    curves.record_sampling(c, curve_sampling)
    return c


def _add_rotated(c: gf.Component, component: gf.Component, angle_deg: float) -> gf.Component:
    """Add ``component`` turned by ``angle_deg`` about the origin; return the placed copy.

    An oblique instance transform puts the instance off the manufacturing grid,
    so the turned copy is flattened, which snaps its polygons, and placed
    without a transform. Its ports carry the rotation.
    """

    rotated = gf.Component()
    ref = rotated << component
    ref.drotate(angle_deg)
    rotated.add_ports(ref.ports)
    rotated.flatten()
    c << rotated
    return rotated


def _resolved_tc_gaps(
    tc_disk_gap: float, tc_disk_gap_by_side: tuple[tuple[Side, float], ...]
) -> dict[Side, float]:
    overrides = dict(tc_disk_gap_by_side)
    if len(overrides) != len(tc_disk_gap_by_side) or set(overrides) - set(ALL_TC_SIDES):
        raise ValueError("tc_disk_gap_by_side must name each of N, E, S, W at most once.")
    return {side: float(overrides.get(side, tc_disk_gap)) for side in ALL_TC_SIDES}


_POSITIVE_SETTINGS = (
    "disk_radius",
    "ground_clearance_diameter",
    "site_size",
    "tc_width",
    "tc_span_deg",
    "tc_landing_span_deg",
    "tc_cpw_width",
    "tc_cpw_gap",
    "tc_lead_start_radius",
    "tc_lead_width",
    "tc_lead_gap",
    "tc_end_clearance",
    "handoff_radius",
    "junction_radius",
    "junction_lead_width",
    "junction_taper_span_deg",
    "junction_ground_overlap",
    "readout_width",
    "readout_gap",
    "drive_tip_radius",
    "drive_width",
    "drive_gap",
    "bump_ring_radius",
)


def _check_settings(**settings) -> None:
    """Reject settings whose geometry would overlap or leave its site."""

    s = settings
    for name in _POSITIVE_SETTINGS:
        value = s[name]
        if value is not None and (not isfinite(value) or value <= 0):
            raise ValueError(f"{name} must be finite and positive, got {value!r}.")
    if not isfinite(s["readout_tip_radius"]) or s["readout_tip_radius"] < 0:
        raise ValueError("readout_tip_radius must be finite and non-negative.")
    if set(s["grounded_tc_sides"]) - set(ALL_TC_SIDES):
        raise ValueError("grounded_tc_sides may only contain N, E, S and W.")

    clearance = s["clearance_radius"]
    handoff = s["handoff_radius"]
    if not s["disk_radius"] < s["junction_radius"] < clearance:
        raise ValueError("junction_radius must lie between the disk edge and the clearance.")
    if not clearance < handoff < s["site_size"] / 2:
        raise ValueError("handoff_radius must lie between the clearance and the site edge.")
    if s["include_tc"]:
        for side, gap in s["tc_gaps"].items():
            if not isfinite(gap) or gap <= 0:
                raise ValueError(f"TC_{side} disk gap must be finite and positive.")
            if s["disk_radius"] + gap + s["tc_width"] >= clearance:
                raise ValueError(f"TC_{side} must end inside the ground clearance.")
        lead_start = s["tc_lead_start_radius"]
        if lead_start is not None and not clearance <= lead_start < handoff:
            raise ValueError("tc_lead_start_radius must lie between the clearance and handoff.")
    if not s["drive_tip_radius"] < handoff:
        raise ValueError("drive_tip_radius must lie inside the handoff square.")
    if s["bump_lattice_count"] < 1 or s["bump_skip_period"] < 1:
        raise ValueError("bump_lattice_count and bump_skip_period must be positive.")


@gf.cell
def _disk_junction(
    disk_radius: float,
    junction_radius: float,
    lead_width: float,
    taper_span_deg: float,
    ground_landing_radius: float,
    curve_sampling: curves.CurveSampling = curves.FABRICATION,
) -> gf.Component:
    """Return the junction and its two tapered leads along local +x.

    The Manhattan overlap sits at ``junction_radius``. Its disk-side arm runs
    inward and lands on the disk edge; its ground-side arm runs outward and lands
    past the clearance edge, inside the ground.
    """

    c = gf.Component()
    junction = c << manhattan_style_junction(
        draw_layer=LAYER.D1_BOTTOM_JJ_DRAW,
        sim_port_layer=LAYER.D1_BOTTOM_SIM_BOUNDARY,
        curve_sampling=curve_sampling,
    )
    junction.dmove((junction_radius, 0.0))
    c.add_port(name="o_junction_lumped", port=junction.ports["o_junction_lumped"])

    for arm, landing_radius in (("o_arm1", disk_radius), ("o_arm2", ground_landing_radius)):
        terminal = tuple(float(value) for value in junction.ports[arm].center)
        c.add_polygon(
            _tapered_lead(terminal, landing_radius, lead_width, taper_span_deg, curve_sampling),
            layer=Q_DRAW,
        )
        # A round head centred on the junction terminal keeps the overlap
        # contact covered after the lead is snapped to the grid.
        head = c << curves.circle(radius=lead_width / 2, layer=Q_DRAW, sampling=curve_sampling)
        head.dmove(terminal)
    curves.record_sampling(c, curve_sampling)
    return c


def _tapered_lead(
    terminal: Point,
    landing_radius: float,
    width: float,
    span_deg: float,
    curve_sampling: curves.CurveSampling,
) -> list[Point]:
    """Polygon from a ``width`` neck at ``terminal`` to an arc at ``landing_radius``."""

    x, y = terminal
    count = curves.arc_points(landing_radius, span_deg, curve_sampling)
    arc = [
        polar_point(landing_radius, -span_deg / 2 + span_deg * index / (count - 1))
        for index in range(count)
    ]
    return [(x, y - width / 2), *arc, (x, y + width / 2)]


@gf.cell
def _tc_claw(
    inner_radius: float,
    width: float,
    span_deg: float,
    landing_span_deg: float,
    clearance_radius: float,
    cpw_width: float,
    cpw_gap: float,
    lead_start_radius: float | None,
    lead_width: float,
    lead_gap: float,
    end_clearance: float,
    handoff_radius: float,
    grounded: bool,
    curve_sampling: curves.CurveSampling = curves.FABRICATION,
) -> gf.Component:
    """Return one TC claw along local +x with its ground-mask channel.

    The claw is an annular sector. Its outer chord, ``landing_span_deg`` wide,
    tapers to the CPW centre width at the clearance edge. The CPW then runs to
    the ``o1`` port at ``handoff_radius``, and its mask channel ends
    ``end_clearance`` beyond. A grounded claw's centre strip crosses that
    clearance into ground.
    """

    outer_radius = inner_radius + width
    c = gf.Component()
    c.add_polygon(_annular_sector(inner_radius, outer_radius, span_deg, curve_sampling), Q_DRAW)

    landing = polar_point(outer_radius, landing_span_deg / 2)
    neck = (clearance_radius, cpw_width / 2)
    c.add_polygon(
        [(neck[0], -neck[1]), (landing[0], -landing[1]), landing, neck],
        layer=Q_DRAW,
    )
    for y_sign in (1, -1):
        c.add_polygon(_taper_side_mask(neck, landing, cpw_gap, y_sign), layer=Q_MASK)

    inner_end = handoff_radius if lead_start_radius is None else lead_start_radius
    outer_width = cpw_width if lead_start_radius is None else lead_width
    outer_gap = cpw_gap if lead_start_radius is None else lead_gap
    mask_end = handoff_radius + end_clearance
    _add_strip(c, inner_radius, inner_end, cpw_width, Q_DRAW)
    inner_mask_end = mask_end if lead_start_radius is None else inner_end
    _add_strip(c, inner_radius, inner_mask_end, cpw_width + 2 * cpw_gap, Q_MASK)
    if lead_start_radius is not None:
        _add_strip(c, lead_start_radius, handoff_radius, lead_width, Q_DRAW)
        # Start the wider channel where its edge meets the clearance circle so no
        # ground sliver is left between the circle and the channel.
        half_channel = lead_width / 2 + lead_gap
        channel_start = min(lead_start_radius, sqrt(clearance_radius**2 - half_channel**2))
        _add_strip(c, channel_start, mask_end, 2 * half_channel, Q_MASK)
    if grounded:
        _add_strip(c, handoff_radius, mask_end + outer_width, outer_width, Q_DRAW)

    c.add_port(
        name="o1",
        center=(handoff_radius, 0.0),
        width=outer_width,
        orientation=0,
        layer=Q_DRAW,
        port_type="electrical",
    )
    c.info["cpw_gap_um"] = float(outer_gap)
    curves.record_sampling(c, curve_sampling)
    return c


def _annular_sector(
    inner_radius: float, outer_radius: float, span_deg: float, curve_sampling: curves.CurveSampling
) -> list[Point]:
    half = span_deg / 2
    outer_count = curves.arc_points(outer_radius, span_deg, curve_sampling)
    inner_count = curves.arc_points(inner_radius, span_deg, curve_sampling)
    outer = [
        polar_point(outer_radius, -half + span_deg * i / (outer_count - 1))
        for i in range(outer_count)
    ]
    inner = [
        polar_point(inner_radius, half - span_deg * i / (inner_count - 1))
        for i in range(inner_count)
    ]
    return outer + inner


def _taper_side_mask(neck: Point, landing: Point, gap: float, y_sign: int) -> list[Point]:
    """Mask band ``gap`` wide along one taper side, joined to the CPW channel."""

    neck = (neck[0], y_sign * neck[1])
    landing = (landing[0], y_sign * landing[1])
    dx, dy = landing[0] - neck[0], landing[1] - neck[1]
    length = sqrt(dx**2 + dy**2)
    # Of the two side normals, take the one pointing away from the claw axis.
    normal = (dy / length, -dx / length)
    if normal[1] * y_sign < 0:
        normal = (-normal[0], -normal[1])
    offset = (gap * normal[0], gap * normal[1])
    return [
        neck,
        landing,
        (landing[0] + offset[0], landing[1] + offset[1]),
        (neck[0] + offset[0], neck[1] + offset[1]),
        (neck[0], neck[1] + y_sign * gap),
    ]


def _add_strip(c: gf.Component, start: float, end: float, width: float, layer: Layer) -> None:
    """Add an axis-aligned strip from ``start`` to ``end`` along local +x."""

    if end > start:
        c.add_polygon(
            [(start, -width / 2), (end, -width / 2), (end, width / 2), (start, width / 2)],
            layer=layer,
        )


@gf.cell
def _rounded_tip_cpw(
    tip_radius: float,
    port_radius: float,
    width: float,
    gap: float,
    curve_sampling: curves.CurveSampling = curves.FABRICATION,
) -> gf.Component:
    """Return a D0 CPW along local +x whose rounded tip metal starts at ``tip_radius``.

    The ``o1`` port is at ``port_radius``; the mask channel continues ``gap``
    beyond it so the line ends open until a route attaches there.
    """

    cap_center = (tip_radius + width / 2, 0.0)
    c = gf.Component()
    cap = c << curves.circle(radius=width / 2, layer=C_DRAW, sampling=curve_sampling)
    cap.dmove(cap_center)
    cap_mask = c << curves.circle(radius=width / 2 + gap, layer=C_MASK, sampling=curve_sampling)
    cap_mask.dmove(cap_center)
    _add_strip(c, cap_center[0], port_radius, width, C_DRAW)
    _add_strip(c, cap_center[0], port_radius + gap, width + 2 * gap, C_MASK)
    c.add_port(
        name="o1",
        center=(port_radius, 0.0),
        width=width,
        orientation=0,
        layer=C_DRAW,
        port_type="electrical",
    )
    c.info["cpw_gap_um"] = float(gap)
    curves.record_sampling(c, curve_sampling)
    return c


def _handoff_square_radius(handoff_radius: float, angle_deg: float) -> float:
    """Distance along ``angle_deg`` to the square where max(|x|, |y|) is ``handoff_radius``."""

    angle = radians(angle_deg)
    return handoff_radius / max(abs(cos(angle)), abs(sin(angle)))


def _die_ground(
    site: gf.Component,
    site_size: float,
    substrate_layer: Layer,
    draw_layer: Layer,
    mask_layer: Layer,
) -> gf.Component:
    """Return the die area and its positive ground, the area minus the ground mask."""

    die = gf.components.rectangle(size=(site_size, site_size), centered=True, layer=substrate_layer)
    ground = gf.Component()
    ground << die
    ground << gf.boolean(
        die,
        site.extract([mask_layer]),
        operation="not",
        layer=draw_layer,
        layer1=substrate_layer,
        layer2=mask_layer,
    )
    return ground


def _bump_angles_deg(lattice_count: int, skip_period: int) -> dict[int, float]:
    """Lattice index to angle for every bump site that is not skipped."""

    return {
        index: index * 360.0 / lattice_count
        for index in range(lattice_count)
        if index % skip_period
    }


def _component_semantics(
    tc_sides: tuple[Side, ...],
    floating_sides: list[Side],
    tc_center_radii: dict[Side, float],
    readout_selector: Point,
    drive_selector: Point,
    ground_selector: Point,
    include_ground: bool,
) -> dict:
    """Conductor selectors for SCGSim; grounded claws belong to the D1 ground."""

    def region(semantic_id: str, level: str, layer: Layer, point: Point) -> dict:
        return {
            "semantic_id": semantic_id,
            "level": level,
            "gds_layer": tuple(int(value) for value in layer),
            "geometry": {"geometry_source": "gds_polygon", "selector_point_um": point},
        }

    regions = [
        region("D1_DISK", "D1_BOTTOM_M1", Q_DRAW, (0.0, 0.0)),
        *(
            region(
                f"D1_TC_{side}",
                "D1_BOTTOM_M1",
                Q_DRAW,
                polar_point(tc_center_radii[side], TC_SIDE_ANGLES_DEG[side]),
            )
            for side in tc_sides
            if side in floating_sides
        ),
        region("D0_READOUT", "D0_TOP_M1", C_DRAW, readout_selector),
        region("D0_DRIVE", "D0_TOP_M1", C_DRAW, drive_selector),
    ]
    if include_ground:
        regions += [
            region("D1_GROUND", "D1_BOTTOM_M1", Q_DRAW, ground_selector),
            region("D0_GROUND", "D0_TOP_M1", C_DRAW, ground_selector),
        ]
    return {
        "schema_version": 2,
        "conductor_regions": regions,
        "ports": [
            {
                "name": "o_junction_lumped",
                "layer": tuple(int(value) for value in LAYER.D1_BOTTOM_SIM_BOUNDARY),
                "target_layer": "D1_BOTTOM_M1",
            }
        ],
        "metadata": {"component_contract": "disk_flip_chip_qubit public zero-argument cell"},
    }


__all__ = ["disk_flip_chip_qubit"]


if __name__ == "__main__":
    # Imported here because orcapen_sc_pdk.pdk imports this module.
    from orcapen_sc_pdk.preview import show

    show(disk_flip_chip_qubit)
