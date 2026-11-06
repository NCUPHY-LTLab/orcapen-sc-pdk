"""Public two-die flip-chip disk transmon reference cell.

Independent OrcaPen source for a single-junction disk island inside a circular
ground clearance, with optional arc couplers at a fixed radius. Prior art:

- KQCircuits ``CircularTransmonSingleIsland`` (GPL-3.0), cited as published
  prior art only; no KQCircuits code is used.
- J. Braumüller et al., Appl. Phys. Lett. 108, 032601 (2016),
  https://doi.org/10.1063/1.4940230 (circular island and clearance).
- S. Kosen et al., Quantum Sci. Technol. 7, 035018 (2022),
  https://doi.org/10.1088/2058-9565/ac734b (two dies joined by indium bumps,
  readout and drive on the control die).

The four grounded or floating claws, the tapered junction leads and the
control-die readout/drive tips combine those patterns; they are not taken from
a single paper. Defaults are a layout preset, not a measured or qualified
device.
"""

from __future__ import annotations

import math

import gdsfactory as gf

import orcapen_sc_pdk.curve_sampling as curves
from orcapen_sc_pdk.cells.layout.indium import indium_bump
from orcapen_sc_pdk.cells.layout.junction import manhattan_style_junction
from orcapen_sc_pdk.tech import LAYER, Layer, coplanar_waveguide

QDRAW, QMASK = LAYER.D1_BOTTOM_M1_DRAW, LAYER.D1_BOTTOM_GROUND_MASK
CDRAW, CMASK = LAYER.D0_TOP_M1_DRAW, LAYER.D0_TOP_GROUND_MASK
JJ_DRAW = LAYER.D1_BOTTOM_JJ_DRAW
TC_SIDES = (("N", 90.0), ("E", 0.0), ("S", 270.0), ("W", 180.0))
GROUNDED_PRESET_DISK_RADIUS_UM = 110.5
FLOATING_PRESET_DISK_RADIUS_UM = 119.83949086316494
PRESET_HANDOFF_HALF_EXTENT_UM = 412.3141121612922
_JUNCTION_CROSS_CENTER_UM = (4.0, 4.0)


def _check_positive(name: str, value: float) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive, got {value!r}.")


def _layer(layer: Layer) -> tuple[int, int]:
    return tuple(gf.get_layer_tuple(layer))


def _union(component: gf.Component, layer: Layer) -> gf.Component:
    return gf.boolean(component, component, operation="or", layer=layer, layer1=layer, layer2=layer)


def _rounding_points(radius: float, points: int | None, sampling: curves.CurveSampling) -> int:
    return curves.circle_segments(radius, sampling) if points is None else points


def _round_corners(component: gf.Component, layer: Layer, radius: float, points: int):
    """Round every corner of one layer with KLayout's polygon rounding (DBU radii)."""
    rounded = gf.Component()
    flat = component.copy()
    flat.flatten()
    radius_dbu = round(radius / flat.kcl.dbu)
    for polygon in flat.get_polygons(by="tuple").get(_layer(layer), []):
        rounded.add_polygon(polygon.round_corners(radius_dbu, radius_dbu, points), layer=layer)
    return rounded


def _force_round_hull(points: list, radius_dbu: int, n: int) -> list:
    """Drop vertices that would stop KLayout reaching the full rounding radius.

    GDSFactory has no forced-radius rounding. Short boundary segments next to a
    sampled arc limit KLayout's cut length, so this removes or intersects them
    first. Points stay in database units inside this helper only.
    """
    corner_max_cos = math.cos(3 * math.pi / n)
    index = 0
    while index < len(points):
        if len(points) < 3:
            return []
        previous_index = index % len(points)
        corner_index = (index + 1) % len(points)
        next_index = (index + 2) % len(points)
        following_index = (index + 3) % len(points)
        previous_point = points[previous_index]
        corner_point = points[corner_index]
        next_point = points[next_index]
        following_point = points[following_index]
        previous_vector = corner_point - previous_point
        corner_vector = next_point - corner_point
        next_vector = following_point - next_point
        previous_length = previous_vector.length()
        corner_length = corner_vector.length()
        next_length = next_vector.length()
        if previous_length == 0 or corner_length == 0 or next_length == 0:
            points = [point for i, point in enumerate(points) if i != corner_index]
            index -= int(corner_index < index)
            continue
        previous_cos = previous_vector.sprod(corner_vector) / (previous_length * corner_length)
        next_cos = corner_vector.sprod(next_vector) / (corner_length * next_length)
        if previous_cos > corner_max_cos or next_cos > corner_max_cos:
            previous_cut = radius_dbu * math.sqrt((1 - previous_cos) / (1 + previous_cos))
            next_cut = radius_dbu * math.sqrt((1 - next_cos) / (1 + next_cos))
            if previous_cut + next_cut > corner_length:
                denominator = previous_vector.vprod(next_vector)
                previous_intercept = next_vector.vprod(previous_point - following_point)
                next_intercept = previous_vector.vprod(previous_point - following_point)
                if (
                    denominator != 0
                    and next_intercept * denominator < 0 < previous_intercept * denominator
                ):
                    cross_point = (
                        previous_point + previous_intercept / denominator * previous_vector
                    )
                    if cross_point not in (previous_point, following_point):
                        points[corner_index] = cross_point
                        points = [point for i, point in enumerate(points) if i != next_index]
                        index -= 1 + int(next_index < index)
                        continue
                points = [
                    point for i, point in enumerate(points) if i not in (corner_index, next_index)
                ]
                index -= 1 + int(corner_index < index) + int(next_index < index)
                continue
        index += 1
    return points


def _force_round_corners(component: gf.Component, layer: Layer, radius: float, points: int):
    """Round one layer to the full radius even next to sampled arcs."""
    flat = component.copy()
    flat.flatten()
    radius_dbu = round(radius / flat.kcl.dbu)
    rounded_region = gf.kdb.Region()
    for polygon in flat.get_region(_layer(layer), merge=True).each_merged():
        hull = _force_round_hull(list(polygon.each_point_hull()), radius_dbu, points)
        if len(hull) < 3:
            continue
        rounded = gf.kdb.Polygon(hull)
        for hole_index in range(polygon.holes()):
            hole = _force_round_hull(list(polygon.each_point_hole(hole_index)), radius_dbu, points)
            if len(hole) >= 3:
                rounded.insert_hole(hole)
        rounded_region.insert(rounded.round_corners(radius_dbu, radius_dbu, points))
    result = gf.Component()
    if not rounded_region.is_empty():
        rounded_region.merge()
        result.add_polygon(points=rounded_region, layer=layer)
    return result


def _rounded_lead(
    start: tuple[float, float],
    end: tuple[float, float],
    width: float,
    rounding_points: int,
) -> gf.Component:
    """Straight lead with full round caps; ``start`` is the junction contact."""
    radius = width / 2
    length = math.hypot(end[0] - start[0], end[1] - start[1])
    if length == 0:
        raise ValueError("junction lead start and end must differ")
    ux, uy = (end[0] - start[0]) / length, (end[1] - start[1]) / length
    # Extend behind the contact so the rounded cap is centred on it.
    extended_start = (start[0] - ux * radius, start[1] - uy * radius)
    lead = gf.Path([extended_start, end]).extrude(width=width, layer=QDRAW)
    return _round_corners(lead, QDRAW, radius, rounding_points)


def _radial_taper(
    neck_x: float,
    neck_y: float,
    landing_radius: float,
    landing_span: float,
    neck_width: float,
    sampling: curves.CurveSampling,
) -> gf.Component:
    """Taper a narrow lead neck to a sampled arc about the qubit centre."""
    half = landing_span / 2
    segments = curves.arc_points(landing_radius, landing_span, sampling) - 1
    arc = [
        (
            landing_radius * math.cos(math.radians(-half + landing_span * i / segments)),
            landing_radius * math.sin(math.radians(-half + landing_span * i / segments)),
        )
        for i in range(segments + 1)
    ]
    taper = gf.Component()
    taper.add_polygon(
        [(neck_x, neck_y - neck_width / 2), *arc, (neck_x, neck_y + neck_width / 2)],
        layer=QDRAW,
    )
    return taper


def _circle_x_at_y(radius: float, y: float, layer: Layer, sampling: curves.CurveSampling):
    """Largest x where the sampled circle boundary crosses height ``y``."""
    circle = curves.circle(radius=radius, layer=layer, sampling=sampling)
    crossings = []
    for polygon in circle.get_polygons_points(by="tuple").get(_layer(layer), []):
        points = list(polygon)
        for i, start in enumerate(points):
            end = points[(i + 1) % len(points)]
            if start[1] == end[1] or not min(start[1], end[1]) <= y <= max(start[1], end[1]):
                continue
            crossings.append(start[0] + (y - start[1]) / (end[1] - start[1]) * (end[0] - start[0]))
    positive = [x for x in crossings if x > 0]
    if not positive:
        raise ValueError("the ground clearance circle does not reach the claw extension mask edge")
    return max(positive)


def _signal_with_mask(source: gf.Component, draw: Layer, mask: Layer) -> gf.Component:
    """Merge touching signal metal while keeping the mask and the ``out`` port."""
    merged = gf.Component()
    merged.add_ref(_union(source, draw))
    merged.add_ref(source.extract([mask]))
    merged.add_port(name="out", port=source.ports["out"])
    return merged


def _disk_and_junction(
    disk_radius: float,
    ground_lead_end_radius: float,
    junction_angle: float,
    open_lead_angles: tuple[float, ...],
    overlap_radius: float,
    lead_span: float,
    lead_width: float,
    junction_width: float,
    junction_length: float,
    include_junction: bool,
    rounding_points: int,
    sampling: curves.CurveSampling,
) -> tuple[gf.Component, gf.Component, tuple[float, float]]:
    """Return the disk electrode with junction, the ground-side leads and the junction centre."""
    component = gf.Component()
    disk = curves.circle(radius=disk_radius, layer=QDRAW, sampling=sampling)
    authored = manhattan_style_junction(
        width=junction_width,
        length=junction_length,
        cross_center=_JUNCTION_CROSS_CENTER_UM,
        draw_layer=JJ_DRAW,
        sim_port_layer=LAYER.D1_BOTTOM_SIM_BOUNDARY,
        curve_sampling=sampling,
    )
    # The fabrication cross plus the straight simulation sheet; the arm ports
    # locate the two leads.
    junction_ref = component.add_ref(authored, name="Junction")
    junction_ref.dmove((overlap_radius, 0.0))

    disk_terminal = tuple(junction_ref.ports["o_arm1"].center)
    ground_terminal = tuple(junction_ref.ports["o_arm2"].center)
    disk_edge_y = abs(disk_terminal[1]) + lead_width / 2
    disk_anchor_x = math.sqrt(disk_radius**2 - disk_edge_y**2) - lead_width / 2
    disk_lead = _rounded_lead(
        disk_terminal, (disk_anchor_x, disk_terminal[1]), lead_width, rounding_points
    )
    if lead_span:
        disk_taper = _radial_taper(*disk_terminal, disk_radius, lead_span, lead_width, sampling)
        disk_lead = gf.boolean(disk_lead, disk_taper, operation="or", layer=QDRAW)
    disk_lead_holder = gf.Component()
    disk_lead_holder.add_ref(disk_lead)
    disk_electrode = gf.Component()
    disk_electrode.add_ref(gf.boolean(disk, disk_lead_holder, operation="or", layer=QDRAW)).drotate(
        junction_angle
    )
    disk_ref = component.add_ref(disk_electrode, name="Disk")

    ground_end = (
        math.sqrt(ground_lead_end_radius**2 - ground_terminal[1] ** 2),
        ground_terminal[1],
    )
    ground_lead = _rounded_lead(ground_terminal, ground_end, lead_width, rounding_points)
    if lead_span:
        ground_taper = _radial_taper(
            *ground_terminal, ground_lead_end_radius, lead_span, lead_width, sampling
        )
        ground_lead = gf.boolean(ground_lead, ground_taper, operation="or", layer=QDRAW)
    ground_leads = gf.Component()
    ground_leads.add_ref(ground_lead).drotate(junction_angle)
    junction_ref.drotate(junction_angle)
    if include_junction:
        component.add_port(name="o_junction_lumped", port=junction_ref.ports["o_junction_lumped"])
    # The Manhattan cross overlaps at its local origin, at the overlap radius.
    junction_center = (
        overlap_radius * math.cos(math.radians(junction_angle)),
        overlap_radius * math.sin(math.radians(junction_angle)),
    )

    if len(open_lead_angles) == 3:
        # Snap the authored electrodes to the grid once before exact quarter-turn
        # copies, so every copy rounds its half-DBU vertices the same way.
        snapped_disk = _union(disk_electrode, QDRAW)
        snapped_ground = _union(ground_leads, QDRAW)
        disk_parts, ground_parts = gf.Component(), gf.Component()
        for quarter_turn in range(4):
            disk_parts.add_ref(snapped_disk).drotate(90 * quarter_turn)
            ground_parts.add_ref(snapped_ground).drotate(90 * quarter_turn)
        component.insts.remove(disk_ref)
        component.add_ref(_union(disk_parts, QDRAW), name="Disk")
        ground_leads = _union(ground_parts, QDRAW)
    elif open_lead_angles:
        disk_parts = gf.Component()
        disk_parts.add_ref(disk_electrode)
        for angle in open_lead_angles:
            disk_parts.add_ref(disk_lead_holder).drotate(angle)
            ground_leads.add_ref(ground_lead).drotate(angle)
        component.insts.remove(disk_ref)
        component.add_ref(_union(disk_parts, QDRAW), name="Disk")
    if not include_junction:
        component.insts.remove(junction_ref)
    return component, ground_leads, junction_center


def _claw_taper(
    geometry: gf.Component,
    center_radius: float,
    width: float,
    landing_span: float,
    end_radius: float,
    cpw_width: float,
    cpw_gap: float,
) -> gf.Component:
    """Add a straight taper from the claw outer edge to the CPW, with its mask."""
    landing_radius = center_radius + width / 2
    half_angle = math.radians(landing_span / 2)
    upper = (landing_radius * math.cos(half_angle), landing_radius * math.sin(half_angle))
    lower = (upper[0], -upper[1])
    taper = gf.Component()
    taper.add_polygon(
        [(end_radius, -cpw_width / 2), lower, upper, (end_radius, cpw_width / 2)], layer=QDRAW
    )
    combined = gf.Component()
    combined.add_ref(geometry)
    combined.add_ref(taper)

    mask_extension = gf.Component()
    if width / 2 > cpw_width / 2:
        mask_edge = cpw_width / 2 + cpw_gap
        side_dx = upper[0] - end_radius
        side_dy = upper[1] - cpw_width / 2
        side_length = math.hypot(side_dx, side_dy)
        offset_x = cpw_gap * side_dy / side_length
        offset_y = -cpw_gap * side_dx / side_length
        mask_extension.add_polygon(
            [
                (end_radius, cpw_width / 2),
                upper,
                (upper[0] + offset_x, upper[1] + offset_y),
                (end_radius + offset_x, cpw_width / 2 + offset_y),
                (end_radius, mask_edge),
            ],
            layer=QMASK,
        )
        mask_extension.add_polygon(
            [
                (end_radius, -cpw_width / 2),
                lower,
                (lower[0] + offset_x, lower[1] - offset_y),
                (end_radius + offset_x, -cpw_width / 2 - offset_y),
                (end_radius, -mask_edge),
            ],
            layer=QMASK,
        )
    masks = gf.Component()
    if _layer(QMASK) in geometry.get_polygons_points(by="tuple"):
        masks.add_ref(geometry.extract([QMASK]))
    masks.add_ref(mask_extension)
    tapered = gf.Component()
    tapered.add_ref(_union(combined, QDRAW))
    tapered.add_ref(_union(masks, QMASK))
    tapered.add_port(name="out", port=geometry.ports["out"])
    return tapered


def _claw_segment(
    center_radius: float,
    width: float,
    span: float,
    lead_length: float,
    cpw_width: float,
    cpw_gap: float,
    mask_end_extension: float,
    corner_radius: float,
    rounding_points: int,
    sampling: curves.CurveSampling,
) -> gf.Component:
    """Arc claw on local +x with a radial CPW lead and an independent mask."""
    c = gf.Component()
    outer = center_radius + width / 2
    arc = c << gf.components.ring(
        radius=center_radius,
        width=width,
        angle=span,
        angle_resolution=360 / curves.circle_segments(outer, sampling),
        layer=QDRAW,
    )
    arc.drotate(-span / 2)
    cpw = coplanar_waveguide(
        width=cpw_width, gap=cpw_gap, draw_layer=QDRAW, ground_mask_layer=QMASK
    )
    lead = c << gf.path.straight(lead_length).extrude(cross_section=cpw)
    lead.dmovex(center_radius)
    out = _union(c, QDRAW)
    if corner_radius:
        # Round only the four arc corners and the two concave CPW shoulders;
        # the outgoing CPW stays flat.
        rounded = _force_round_corners(out, QDRAW, corner_radius, rounding_points)
        windows = gf.Component()
        inner = center_radius - width / 2
        corners = [
            (radius * math.cos(angle), radius * math.sin(angle))
            for radius in (inner, outer)
            for angle in (-math.radians(span / 2), math.radians(span / 2))
        ]
        shoulder_x = math.sqrt(outer**2 - (cpw_width / 2) ** 2)
        corners.extend((shoulder_x, sign * cpw_width / 2) for sign in (-1, 1))
        for point in corners:
            window = windows << curves.circle(
                radius=2 * corner_radius, layer=QDRAW, sampling=sampling
            )
            window.dmove(point)
        preserved = gf.boolean(out, windows, operation="not", layer=QDRAW)
        patches = gf.boolean(rounded, windows, operation="and", layer=QDRAW)
        out = gf.boolean(preserved, patches, operation="or", layer=QDRAW)
    mask_route = gf.path.straight(lead_length + mask_end_extension).extrude(cross_section=cpw)
    (out << mask_route.extract([QMASK])).dmovex(center_radius)
    out.add_port(name="out", port=lead.ports["o2"])
    return out


def _claw(
    center_radius: float,
    width: float,
    span: float,
    landing_span: float | None,
    taper_end_radius: float,
    handoff_radius: float,
    cpw_width: float,
    cpw_gap: float,
    extension: tuple[float, float, float, float] | None,
    clearance_radius: float,
    grounded: bool,
    corner_radius: float,
    rounding_points: int,
    sampling: curves.CurveSampling,
) -> gf.Component:
    """One claw on local +x: arc, optional taper, lead or extension, optional ground tail."""
    inner_end = extension[0] if extension else handoff_radius
    geometry = _claw_segment(
        center_radius=center_radius,
        width=width,
        span=span,
        lead_length=inner_end - center_radius,
        cpw_width=cpw_width,
        cpw_gap=cpw_gap,
        mask_end_extension=0.0 if extension else cpw_gap,
        corner_radius=corner_radius,
        rounding_points=rounding_points,
        sampling=sampling,
    )
    if extension:
        # The extension authors its own mask below; keep only the claw metal.
        signal = geometry.extract([QDRAW])
        signal.add_port(name="out", port=geometry.ports["out"])
        geometry = signal
    if landing_span is not None:
        geometry = _claw_taper(
            geometry, center_radius, width, landing_span, taper_end_radius, cpw_width, cpw_gap
        )

    if extension:
        start, ext_width, ext_gap, end_clearance = extension
        ext_cpw = coplanar_waveguide(
            width=ext_width, gap=ext_gap, draw_layer=QDRAW, ground_mask_layer=QMASK
        )
        combined = gf.Component()
        combined.add_ref(geometry)
        ext_ref = combined.add_ref(
            gf.path.straight(handoff_radius - start).extrude(cross_section=ext_cpw)
        )
        ext_ref.dmovex(start)
        masks = gf.Component()
        masks.add_ref(geometry.extract([QMASK]))
        inner_edge = cpw_width / 2 + cpw_gap
        outer_edge = ext_width / 2 + ext_gap
        mask_end = handoff_radius + end_clearance
        join = _circle_x_at_y(clearance_radius, outer_edge, QMASK, sampling)
        masks.add_polygon(
            [
                (center_radius, -inner_edge),
                (join, -inner_edge),
                (join, -outer_edge),
                (mask_end, -outer_edge),
                (mask_end, outer_edge),
                (join, outer_edge),
                (join, inner_edge),
                (center_radius, inner_edge),
            ],
            layer=QMASK,
        )
        extended = gf.Component()
        extended.add_ref(_union(combined, QDRAW))
        extended.add_ref(_union(masks, QMASK))
        extended.add_port(name="out", port=ext_ref.ports["o2"])
        geometry = extended

    claw = _signal_with_mask(geometry, QDRAW, QMASK)
    if grounded:
        # A radial tail of the output CPW width runs through the mask end into
        # the ground and overlaps it by one CPW width.
        out_width, mask_end = (
            (extension[1], handoff_radius + extension[3])
            if extension
            else (cpw_width, handoff_radius + cpw_gap)
        )
        tail = gf.Component()
        tail.add_polygon(
            [
                (handoff_radius, -out_width / 2),
                (mask_end + out_width, -out_width / 2),
                (mask_end + out_width, out_width / 2),
                (handoff_radius, out_width / 2),
            ],
            layer=QDRAW,
        )
        holder = gf.Component()
        holder.add_ref(claw)
        holder.add_ref(tail)
        grounded_claw = gf.Component()
        grounded_claw.add_ref(_union(holder, QDRAW))
        grounded_claw.add_ref(claw.extract([QMASK]))
        grounded_claw.add_port(name="out", port=claw.ports["out"])
        claw = grounded_claw
    return claw


def _rounded_tip_line(
    tip_radius: float,
    lead_length: float,
    cpw_width: float,
    cpw_gap: float,
    sampling: curves.CurveSampling,
) -> gf.Component:
    """Straight D0 CPW on local +x with a round inward tip at ``tip_radius``."""
    c = gf.Component()
    cap_radius = cpw_width / 2
    cap_center = tip_radius + cap_radius
    (c << curves.circle(radius=cap_radius, layer=CDRAW, sampling=sampling)).dmovex(cap_center)
    mask_cap = c << curves.circle(radius=cap_radius + cpw_gap, layer=CMASK, sampling=sampling)
    mask_cap.dmovex(cap_center)
    cpw = coplanar_waveguide(
        width=cpw_width, gap=cpw_gap, draw_layer=CDRAW, ground_mask_layer=CMASK
    )
    lead = c << gf.path.straight(lead_length - cap_radius).extrude(cross_section=cpw)
    lead.dmovex(cap_center)
    out = gf.boolean(c, c, operation="or", layer=CDRAW)
    # The mask runs one gap past the port so the line end stays cleared.
    mask_route = gf.path.straight(lead_length - cap_radius + cpw_gap).extrude(cross_section=cpw)
    mask_lead = gf.Component()
    (mask_lead << mask_route.extract([CMASK])).dmovex(cap_center)
    out << gf.boolean(mask_lead, mask_cap, operation="or", layer=CMASK)
    out.add_port(name="out", port=lead.ports["o2"])
    return _signal_with_mask(out, CDRAW, CMASK)


def _square_edge_radius(half_extent: float, angle: float) -> float:
    theta = math.radians(angle)
    return half_extent / max(abs(math.cos(theta)), abs(math.sin(theta)))


def _ground(half_extent: float, mask: gf.Component, draw: Layer, mask_layer: Layer, domain: Layer):
    """Ground metal (site square minus mask) plus the die domain it is derived from."""
    square = gf.components.rectangle(
        size=(2 * half_extent, 2 * half_extent), centered=True, layer=draw
    )
    ground = gf.Component()
    ground.add_ref(
        gf.boolean(square, mask, operation="not", layer=draw, layer1=draw, layer2=mask_layer)
    )
    ground.add_ref(
        gf.components.rectangle(
            size=(2 * half_extent, 2 * half_extent), centered=True, layer=domain
        )
    )
    return ground


def _flat_region(component: gf.Component, layer: Layer) -> gf.kdb.Region:
    flat = component.copy()
    flat.flatten()
    return flat.get_region(_layer(layer), merge=True)


def _probe(point: tuple[float, float], dbu: float) -> gf.kdb.Region:
    """A 2-DBU box at ``point``, to pick the merged polygon that contains it."""
    x, y = round(point[0] / dbu), round(point[1] / dbu)
    return gf.kdb.Region(gf.kdb.Box(x - 1, y - 1, x + 1, y + 1))


def _check_face_connectivity(
    face: str,
    conductors: gf.Component,
    draw: Layer,
    mask: gf.kdb.Region,
    half_extent: float,
    selectors: dict[str, tuple[float, float]],
    grounded: set[str],
) -> None:
    """Reject parameters whose flattened die face joins conductors the cell keeps apart.

    The face's metal is the drawn signal metal plus the site square minus the
    ground mask, as the ground instance derives it. Each isolated conductor
    must be its own merged piece away from the ground; each grounded one must
    reach the ground. Checking built geometry covers every parameter path that
    can move a conductor onto another, which per-parameter bounds cannot.
    """
    dbu = conductors.kcl.dbu
    edge = round(half_extent / dbu)
    site = gf.kdb.Region(gf.kdb.Box(-edge, -edge, edge, edge))
    ground = site - mask
    metal = (_flat_region(conductors, draw) & site) + ground
    metal.merge()
    for name, point in selectors.items():
        piece = metal.interacting(_probe(point, dbu))
        touches_ground = not piece.overlapping(ground).is_empty()
        if name in grounded:
            if not touches_ground:
                raise ValueError(
                    f"{face}: grounded {name} does not reach the ground metal inside the site"
                )
            continue
        if touches_ground:
            raise ValueError(f"{face}: {name} touches the ground metal")
        for other, other_point in selectors.items():
            if other != name and not piece.interacting(_probe(other_point, dbu)).is_empty():
                raise ValueError(f"{face}: {name} and {other} share metal")


@gf.cell(check_instances=False, tags=["layout", "qubit", "disk", "flip_chip"])
def disk_flip_chip_qubit(
    disk_radius: float | None = None,
    include_tc: bool = True,
    tc_grounded_sides: tuple[str, ...] = ("N", "E", "S", "W"),
    tc_disk_gap: float = 60.0,
    tc_disk_gap_by_side: tuple[tuple[str, float], ...] = (),
    tc_width: float = 60.0,
    tc_span: float = 45.0,
    tc_landing_span: float | None = 45.0,
    tc_cpw_width: float = 3.0,
    tc_cpw_gap: float = 40.0,
    tc_corner_radius: float = 5.0,
    tc_outer_extension_start_radius: float | None = None,
    tc_outer_extension_width: float | None = None,
    tc_outer_extension_gap: float | None = None,
    tc_outer_extension_end_clearance: float | None = None,
    ground_clearance_diameter: float = 700.0,
    ground_outer_half_extent: float = 500.0,
    handoff_half_extent: float = PRESET_HANDOFF_HALF_EXTENT_UM,
    junction_angle: float = 315.0,
    junction_open_lead_angles: tuple[float, ...] = (),
    junction_overlap_radius: float = 237.5,
    junction_lead_span: float = 20.0,
    junction_lead_width: float = 2.0,
    junction_ground_lead_end_radius: float = 360.0,
    junction_width: float = 0.09,
    junction_length: float = 5.0,
    include_junction: bool = True,
    ro_angle: float = 135.0,
    ro_tip_radius: float = 0.0,
    ro_cpw_width: float = 7.0,
    ro_cpw_gap: float = 6.0,
    xy_angle: float = 225.0,
    xy_tip_radius: float = 412.0,
    xy_cpw_width: float = 4.0,
    xy_cpw_gap: float = 6.0,
    bump_center_radius: float = 400.0,
    bump_lattice_count: int = 32,
    bump_skip_period: int = 4,
    indium_bump_size: float = 20.0,
    under_bump_size: float = 40.0,
    include_ground: bool = True,
    corner_rounding_points: int | None = None,
    curve_sampling: curves.CurveSampling = curves.FABRICATION,
) -> gf.Component:
    """Return a two-die flip-chip disk transmon site centred at the origin.

    Qubit die (``D1_BOTTOM``): a disk island inside a circular ground
    clearance, one Manhattan junction from the disk to ground with tapered
    leads, and optionally four arc claws (``include_tc``) at N/E/S/W. Each
    claw tapers to a CPW that ends at the ``tc_<side>`` port on the site
    square of half extent ``handoff_half_extent``. Claws named in
    ``tc_grounded_sides`` end in a radial tail into the ground; the others are
    floating, isolated conductors.

    Control die (``D0_TOP``): a circular clearance of the same diameter, a
    readout CPW whose round tip sits at ``ro_tip_radius`` and a drive CPW
    whose tip sits at ``xy_tip_radius``. Their ports ``ro_out`` and ``xy_out``
    lie on the same handoff square. Indium bumps sit on a ring between the
    dies: a lattice of ``bump_lattice_count`` sites with every
    ``bump_skip_period``-th site left empty.

    Each die's ground is a separate sub-instance (``QGround`` / ``CGround``:
    ground metal plus the die domain on ``D1_SUBSTRATE_AREA`` /
    ``D0_SUBSTRATE_AREA``) beside its mask (``QGroundMask`` / ``CGroundMask``),
    so a parent can draw one common ground over several sites:
    ``include_ground=False`` leaves out ``QGround`` and ``CGround`` and keeps
    the masks. The junction simulation sheet on ``D1_BOTTOM_SIM_BOUNDARY``
    carries the ``o_junction_lumped`` port. Signal conductors are ``Disk``
    (inside ``QFace``), ``TC_<side>``, ``RO`` and ``XY``.

    ``disk_radius=None`` selects the preset radius: 110.5 µm when all four
    claws are grounded, 119.839 µm when none are. A mixed set of grounded
    claws has no preset and needs an explicit ``disk_radius``. All defaults are a layout
    preset, not a measured or qualified device.

    Settings whose flattened geometry would join the disk, a floating claw or
    a line to another conductor or the ground, leave a grounded claw short of
    the ground, or put a bump on a signal clearance raise ``ValueError``.

    ``tc_disk_gap_by_side`` overrides the claw-to-disk gap per side, as
    ``(("E", 40.0), ...)``. ``tc_landing_span=None`` drops the claw taper. The
    four ``tc_outer_extension_*`` values, given together, end the claw taper
    at the clearance edge and continue with a CPW of their width and gap to
    the handoff, its mask ending ``tc_outer_extension_end_clearance`` past it.
    ``junction_open_lead_angles`` adds open lead pairs without a junction, at
    quarter turns from ``junction_angle``. ``corner_rounding_points=None``
    takes the corner-rounding point count from ``curve_sampling``.

    Prior art: KQCircuits ``CircularTransmonSingleIsland`` (GPL-3.0, cited
    only, no code used); Braumüller et al., APL 108, 032601 (2016); Kosen et
    al., QST 7, 035018 (2022). The claws, tapered leads and control-die lines
    are OrcaPen's adaptation.
    """
    grounded_sides = set(tc_grounded_sides)
    if len(grounded_sides) != len(tc_grounded_sides) or grounded_sides - {"N", "E", "S", "W"}:
        raise ValueError("tc_grounded_sides names each of N, E, S, W at most once")
    if disk_radius is None:
        if grounded_sides == {"N", "E", "S", "W"}:
            disk_radius = GROUNDED_PRESET_DISK_RADIUS_UM
        elif not grounded_sides:
            disk_radius = FLOATING_PRESET_DISK_RADIUS_UM
        else:
            raise ValueError("a mixed set of grounded claws needs an explicit disk_radius")
    for name, value in (
        ("disk_radius", disk_radius),
        ("tc_width", tc_width),
        ("tc_span", tc_span),
        ("tc_cpw_width", tc_cpw_width),
        ("tc_cpw_gap", tc_cpw_gap),
        ("ground_clearance_diameter", ground_clearance_diameter),
        ("ground_outer_half_extent", ground_outer_half_extent),
        ("handoff_half_extent", handoff_half_extent),
        ("junction_overlap_radius", junction_overlap_radius),
        ("junction_lead_width", junction_lead_width),
        ("junction_ground_lead_end_radius", junction_ground_lead_end_radius),
        ("junction_width", junction_width),
        ("junction_length", junction_length),
        ("ro_cpw_width", ro_cpw_width),
        ("ro_cpw_gap", ro_cpw_gap),
        ("xy_cpw_width", xy_cpw_width),
        ("xy_cpw_gap", xy_cpw_gap),
        ("bump_center_radius", bump_center_radius),
        ("indium_bump_size", indium_bump_size),
        ("under_bump_size", under_bump_size),
    ):
        _check_positive(name, value)
    if not math.isfinite(junction_lead_span) or junction_lead_span < 0:
        raise ValueError("junction_lead_span must be finite and non-negative")
    if not math.isfinite(tc_corner_radius) or tc_corner_radius < 0:
        raise ValueError("tc_corner_radius must be finite and non-negative")
    if tc_landing_span is not None:
        _check_positive("tc_landing_span", tc_landing_span)
    clearance_radius = ground_clearance_diameter / 2
    if disk_radius >= clearance_radius:
        raise ValueError("disk_radius must be smaller than the ground clearance radius")
    if not clearance_radius < handoff_half_extent < ground_outer_half_extent:
        raise ValueError(
            "handoff_half_extent must lie between the clearance radius and the site edge"
        )
    if not disk_radius < junction_overlap_radius < clearance_radius:
        raise ValueError("the junction must sit between the disk and the clearance edge")
    if junction_ground_lead_end_radius <= clearance_radius:
        raise ValueError("the junction ground lead must end beyond the clearance edge")
    if bump_center_radius <= clearance_radius:
        raise ValueError("the bump ring must lie outside the ground clearance")
    # The round tip needs half the CPW width of straight line before the handoff.
    for name, tip, angle, width in (
        ("RO", ro_tip_radius, ro_angle, ro_cpw_width),
        ("XY", xy_tip_radius, xy_angle, xy_cpw_width),
    ):
        if not 0 <= tip < _square_edge_radius(handoff_half_extent, angle) - width / 2:
            raise ValueError(
                f"{name.lower()}_tip_radius must be non-negative and half the {name} width"
                " inside the handoff square"
            )
    for name, value in (
        ("bump_lattice_count", bump_lattice_count),
        ("bump_skip_period", bump_skip_period),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    if corner_rounding_points is not None and corner_rounding_points < 4:
        raise ValueError("corner_rounding_points must be at least four")

    lead_angles = tuple(float(angle) % 360 for angle in junction_open_lead_angles)
    junction_angle = float(junction_angle) % 360
    if len(set(lead_angles + (junction_angle,))) != len(lead_angles) + 1 or len(lead_angles) > 3:
        raise ValueError("open lead angles must be distinct from each other and the junction")
    if any((angle - junction_angle) % 90 for angle in lead_angles):
        raise ValueError("open lead angles must be quarter turns from junction_angle")

    extension_values = (
        tc_outer_extension_start_radius,
        tc_outer_extension_width,
        tc_outer_extension_gap,
        tc_outer_extension_end_clearance,
    )
    extension = None
    if any(value is not None for value in extension_values):
        if any(value is None for value in extension_values):
            raise ValueError("the claw outer extension needs start radius, width, gap, clearance")
        for name, value in zip(
            ("start_radius", "width", "gap", "end_clearance"), extension_values, strict=True
        ):
            _check_positive(f"tc_outer_extension_{name}", value)
        if tc_landing_span is not None and tc_outer_extension_start_radius != clearance_radius:
            raise ValueError("a tapered claw extension must start at the clearance radius")
        if tc_outer_extension_start_radius >= handoff_half_extent:
            raise ValueError("the claw extension must start inside the handoff square")
        extension = extension_values

    gaps = dict(tc_disk_gap_by_side)
    if len(gaps) != len(tc_disk_gap_by_side) or set(gaps) - {"N", "E", "S", "W"}:
        raise ValueError("tc_disk_gap_by_side names each of N, E, S, W at most once")
    gaps = {side: gaps.get(side, tc_disk_gap) for side, _ in TC_SIDES}
    inner_lead_end = extension[0] if extension else handoff_half_extent
    if include_tc:
        for side, gap in gaps.items():
            _check_positive(f"tc_disk_gap[{side}]", gap)
            outer = disk_radius + gap + tc_width
            if disk_radius + gap + tc_width / 2 >= inner_lead_end:
                raise ValueError(f"claw {side} must start inside its CPW lead end")
            if outer >= clearance_radius:
                raise ValueError(f"claw {side} must stay inside the ground clearance")
            if extension and outer >= extension[0]:
                raise ValueError(f"claw {side} must stay inside the extension start")

    sampling = curve_sampling
    lead_points = _rounding_points(junction_lead_width / 2, corner_rounding_points, sampling)
    claw_points = _rounding_points(tc_corner_radius or 1.0, corner_rounding_points, sampling)

    def on_axis(radius, angle):
        return (radius * math.cos(math.radians(angle)), radius * math.sin(math.radians(angle)))

    c = gf.Component()
    qface, ground_leads, junction_center = _disk_and_junction(
        disk_radius=disk_radius,
        ground_lead_end_radius=junction_ground_lead_end_radius,
        junction_angle=junction_angle,
        open_lead_angles=lead_angles,
        overlap_radius=junction_overlap_radius,
        lead_span=junction_lead_span,
        lead_width=junction_lead_width,
        junction_width=junction_width,
        junction_length=junction_length,
        include_junction=include_junction,
        rounding_points=lead_points,
        sampling=sampling,
    )
    qface_ref = c.add_ref(qface, name="QFace")

    q_mask = gf.Component()
    q_mask.add_ref(curves.circle(radius=clearance_radius, layer=QMASK, sampling=sampling))
    if include_tc:
        for side, angle in TC_SIDES:
            claw = _claw(
                center_radius=disk_radius + gaps[side] + tc_width / 2,
                width=tc_width,
                span=tc_span,
                landing_span=tc_landing_span,
                taper_end_radius=clearance_radius,
                handoff_radius=handoff_half_extent,
                cpw_width=tc_cpw_width,
                cpw_gap=tc_cpw_gap,
                extension=extension,
                clearance_radius=clearance_radius,
                grounded=side in grounded_sides,
                corner_radius=tc_corner_radius,
                rounding_points=claw_points,
                sampling=sampling,
            )
            claw_ref = c.add_ref(claw, name=f"TC_{side}")
            claw_ref.drotate(angle)
            q_mask.add_ref(claw.extract([QMASK])).drotate(angle)
            c.add_port(name=f"tc_{side}", port=claw_ref.ports["out"])

    lines = {}
    for name, angle, tip, width, gap in (
        ("RO", ro_angle, ro_tip_radius, ro_cpw_width, ro_cpw_gap),
        ("XY", xy_angle, xy_tip_radius, xy_cpw_width, xy_cpw_gap),
    ):
        handoff = _square_edge_radius(handoff_half_extent, angle)
        line = _rounded_tip_line(tip, handoff - tip, width, gap, sampling)
        line_ref = c.add_ref(line, name=name)
        line_ref.drotate(angle)
        c.add_port(name=f"{name.lower()}_out", port=line_ref.ports["out"])
        lines[name] = (line, angle)
    if include_junction:
        c.add_port(name="o_junction_lumped", port=qface_ref.ports["o_junction_lumped"])

    # The ground-side junction lead stays metal: it is cut out of the mask.
    q_ground_mask = gf.boolean(
        _union(q_mask, QMASK),
        ground_leads,
        operation="not",
        layer=QMASK,
        layer1=QMASK,
        layer2=QDRAW,
    )
    c_mask = gf.Component()
    c_mask.add_ref(curves.circle(radius=clearance_radius, layer=CMASK, sampling=sampling))
    for line, angle in lines.values():
        c_mask.add_ref(line.extract([CMASK])).drotate(angle)
    c_ground_mask = _union(c_mask, CMASK)
    q_mask_region = _flat_region(q_ground_mask, QMASK)
    c_mask_region = _flat_region(c_ground_mask, CMASK)
    claw_selectors = {
        f"TC_{side}": on_axis(disk_radius + gaps[side] + tc_width / 2, angle)
        for side, angle in TC_SIDES
        if include_tc
    }
    _check_face_connectivity(
        "D1_BOTTOM",
        c,
        QDRAW,
        q_mask_region,
        ground_outer_half_extent,
        {"Disk": (0.0, 0.0), **claw_selectors},
        {f"TC_{side}" for side in grounded_sides},
    )
    _check_face_connectivity(
        "D0_TOP",
        c,
        CDRAW,
        c_mask_region,
        ground_outer_half_extent,
        {
            "RO": on_axis(ro_tip_radius + ro_cpw_width / 2, ro_angle),
            "XY": on_axis(xy_tip_radius + xy_cpw_width / 2, xy_angle),
        },
        set(),
    )
    c.add_ref(q_ground_mask, name="QGroundMask")
    c.add_ref(c_ground_mask, name="CGroundMask")
    if include_ground:
        c.add_ref(
            _ground(ground_outer_half_extent, q_ground_mask, QDRAW, QMASK, LAYER.D1_SUBSTRATE_AREA),
            name="QGround",
        )
        c.add_ref(
            _ground(ground_outer_half_extent, c_ground_mask, CDRAW, CMASK, LAYER.D0_SUBSTRATE_AREA),
            name="CGround",
        )

    bump = indium_bump(
        indium_bump_size=indium_bump_size,
        under_bump_size=under_bump_size,
        curve_sampling=sampling,
    )
    # A bump joins the two grounds, so its footprint must clear both dies' masks.
    bump_footprint = _flat_region(bump, LAYER.D0_D1_UNDER_BUMP)
    signal_clearance = q_mask_region + c_mask_region
    dbu = c.kcl.dbu
    bump_names = []
    for index in range(bump_lattice_count):
        if index % bump_skip_period == 0:
            continue
        center = on_axis(bump_center_radius, index * 360.0 / bump_lattice_count)
        name = f"bump_{index:02d}"
        placed = bump_footprint.moved(round(center[0] / dbu), round(center[1] / dbu))
        if not placed.overlapping(signal_clearance).is_empty():
            raise ValueError(f"{name} overlaps a signal clearance; move the bump ring or the lines")
        c.add_ref(bump, name=name).dmove(center)
        bump_names.append(name)

    tc_ports = [f"tc_{side}" for side, _ in TC_SIDES] if include_tc else []
    claw_sides = [side for side, _ in TC_SIDES] if include_tc else []
    floating_claws = [f"TC_{side}" for side in claw_sides if side not in grounded_sides]
    grounded_claws = [f"TC_{side}" for side in claw_sides if side in grounded_sides]
    c.info["topology"] = (
        "two-die flip-chip disk transmon: D1 disk with one Manhattan junction to ground"
        + (f", four claws ({len(grounded_claws)} grounded)" if include_tc else "")
        + "; D0 readout and drive tips; indium bump ring"
    )
    c.info["preset_provenance"] = "Layout preset defaults; not a measured or qualified device."
    c.info["disk_radius_um"] = float(disk_radius)
    c.info["tc_disk_gap_by_side_um"] = {side: float(gap) for side, gap in gaps.items()}
    c.info["junction_center_um"] = junction_center
    c.info["bump_instance_names"] = tuple(bump_names)
    c.info["ground_instance_names"] = (
        ("QGround", "CGround", "QGroundMask", "CGroundMask")
        if include_ground
        else ("QGroundMask", "CGroundMask")
    )
    c.info["grounded_tc_sides"] = tuple(claw.removeprefix("TC_") for claw in grounded_claws)
    c.info["ordered_port_names"] = (
        *tc_ports,
        "ro_out",
        "xy_out",
        *(("o_junction_lumped",) if include_junction else ()),
    )
    c.info["source_references"] = (
        "KQCircuits CircularTransmonSingleIsland (GPL-3.0; cited as prior art, no code used)",
        "https://doi.org/10.1063/1.4940230",
        "https://doi.org/10.1088/2058-9565/ac734b",
    )

    def region(semantic_id, level, layer, point, net):
        return {
            "semantic_id": semantic_id,
            "level": level,
            "gds_layer": _layer(layer),
            "geometry": {"geometry_source": "gds_polygon", "selector_point_um": point},
            "metadata": {"physical_net": net},
        }

    c.info["component_semantics"] = {
        "schema_version": 2,
        "conductor_regions": [
            region("Disk", "D1_BOTTOM_M1", QDRAW, (0.0, 0.0), "Disk"),
            *[
                region(
                    f"TC_{side}",
                    "D1_BOTTOM_M1",
                    QDRAW,
                    on_axis(disk_radius + gaps[side] + tc_width / 2, angle),
                    f"TC_{side}",
                )
                for side, angle in TC_SIDES
                if f"TC_{side}" in floating_claws
            ],
            region(
                "RO", "D0_TOP_M1", CDRAW, on_axis(ro_tip_radius + ro_cpw_width / 2, ro_angle), "RO"
            ),
            region(
                "XY", "D0_TOP_M1", CDRAW, on_axis(xy_tip_radius + xy_cpw_width / 2, xy_angle), "XY"
            ),
        ],
        "ground_plane_contributions": [
            {
                "local_id": instance,
                "plane_id": plane,
                "geometry_source": "die_face_minus_ground_mask",
                "mask_layer": _layer(mask),
            }
            for instance, plane, mask in (
                ("QGround", "D1_BOTTOM_GROUND_PLANE", QMASK),
                ("CGround", "D0_TOP_GROUND_PLANE", CMASK),
            )
            if include_ground
        ]
        + [
            {
                "local_id": claw,
                "plane_id": "D1_BOTTOM_GROUND_PLANE",
                "level": "D1_BOTTOM_M1",
                "layer": _layer(QDRAW),
                "selector_point_um": on_axis(disk_radius + gaps[side] + tc_width / 2, angle),
            }
            for side, angle in TC_SIDES
            if (claw := f"TC_{side}") in grounded_claws
        ],
        "ports": (
            [
                {
                    "name": "o_junction_lumped",
                    "layer": _layer(LAYER.D1_BOTTOM_SIM_BOUNDARY),
                    "target_layer": "D1_BOTTOM_M1",
                }
            ]
            if include_junction
            else []
        ),
    }
    curves.record_sampling(c, curve_sampling)
    return c


__all__ = ["disk_flip_chip_qubit"]


if __name__ == "__main__":
    # Imported here because orcapen_sc_pdk.pdk imports this module.
    from orcapen_sc_pdk.preview import show

    show(disk_flip_chip_qubit)
