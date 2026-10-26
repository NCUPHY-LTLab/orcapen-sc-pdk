"""Project-scoped GF primitive adapters used by private layout routing."""

from __future__ import annotations

from math import cos, pi, sin

import gdsfactory as gf
from gdsfactory.typings import CrossSectionSpec, LayerSpec, PortNames, PortTypes

import orcapen_sc_pdk.curve_sampling as curves
from orcapen_sc_pdk.cells.layout.taper import taper
from orcapen_sc_pdk.ports import add_mesh_port
from orcapen_sc_pdk.tech import LAYER, coplanar_waveguide


@curves.sampled_cell(tags=["layout", "primitive", "bend_circular", "circular_arc"])
def bend_circular(
    radius: float | None = None,
    angle: float = 90.0,
    npoints: int | None = None,
    angular_step: float | None = None,
    layer: LayerSpec | None = None,
    width: float | None = None,
    cross_section: CrossSectionSpec = "cpw_6_7_6",
    allow_min_radius_violation: bool = False,
) -> gf.Component:
    """Return a GF circular bend with a project CPW default cross-section."""

    return curves.bend_circular(
        radius=radius,
        angle=angle,
        npoints=npoints,
        angular_step=angular_step,
        layer=layer,
        width=width,
        cross_section=cross_section,
        allow_min_radius_violation=allow_min_radius_violation,
    )


@curves.sampled_cell(tags=["layout", "primitive", "bend_euler"])
def bend_euler(
    radius: float | None = None,
    angle: float = 90.0,
    p: float = 0.5,
    with_arc_floorplan: bool = True,
    npoints: int | None = None,
    angular_step: float | None = None,
    layer: LayerSpec | None = None,
    width: float | None = None,
    cross_section: CrossSectionSpec = "cpw_6_7_6",
    allow_min_radius_violation: bool = False,
) -> gf.Component:
    """Return a GF Euler bend with a project CPW default cross-section."""

    return curves.bend_euler(
        radius=radius,
        angle=angle,
        p=p,
        with_arc_floorplan=with_arc_floorplan,
        npoints=npoints,
        angular_step=angular_step,
        layer=layer,
        width=width,
        cross_section=cross_section,
        allow_min_radius_violation=allow_min_radius_violation,
    )


@curves.sampled_cell(tags=["layout", "primitive", "straight"])
def straight(
    length: float = 10.0,
    npoints: int = 2,
    cross_section: CrossSectionSpec = "cpw_6_7_6",
    width: float | None = None,
) -> gf.Component:
    """Return a GF straight with a project CPW default cross-section."""

    return gf.components.straight(
        length=length,
        npoints=npoints,
        cross_section=cross_section,
        width=width,
    )


@curves.sampled_cell(tags=["layout", "primitive", "cpw", "taper"])
def cpw_handoff(
    length: float = 200.0,
    taper_length: float = 50.0,
    native_width: float = 10.0,
    native_gap: float = 6.0,
    route_width: float = 7.0,
    route_gap: float = 6.0,
    radius: float | None = 100.0,
    draw_layer: LayerSpec = LAYER.D0_TOP_M1_DRAW,
    etch_layer: LayerSpec = LAYER.D0_TOP_M1_ETCH,
    ground_mask_layer: LayerSpec = LAYER.D0_TOP_GROUND_MASK,
) -> gf.Component:
    """Join public CPW dimensions along X; total length includes taper once.

    DRAW o1/o2 face -X/+X at0/length with native/route widths. Radius is
    routing metadata, not a bend. No taper requires identical trace and gap.
    Defaults are neutral public previews, not consumer design targets.
    """
    if length <= 0 or not 0 <= taper_length <= length:
        raise ValueError("length must be positive and taper_length must fit inside length")
    if taper_length == 0 and (native_width != route_width or native_gap != route_gap):
        raise ValueError("a zero taper cannot change CPW trace width or gap")
    native_xs = coplanar_waveguide(
        width=native_width,
        gap=native_gap,
        radius=radius,
        draw_layer=draw_layer,
        etch_layer=etch_layer,
        ground_mask_layer=ground_mask_layer,
    )
    coplanar_waveguide(
        width=route_width,
        gap=route_gap,
        radius=radius,
        draw_layer=draw_layer,
        etch_layer=etch_layer,
        ground_mask_layer=ground_mask_layer,
    )
    c = gf.Component()
    straight_length = length - taper_length
    if straight_length > 0:
        lead = c << straight(length=straight_length, cross_section=native_xs)
        c.add_port("o1", port=lead.ports["o1"])
    if taper_length > 0:
        transition = c << taper(
            width1=native_width,
            width2=route_width,
            gap1=native_gap,
            gap2=route_gap,
            length=taper_length,
            draw_layer=draw_layer,
            etch_layer=etch_layer,
            ground_mask_layer=ground_mask_layer,
        )
        if straight_length > 0:
            transition.connect("o_taper_in", lead.ports["o2"])
        else:
            c.add_port("o1", port=transition.ports["o_taper_in"])
        c.add_port("o2", port=transition.ports["o_taper_out"])
    else:
        c.add_port("o2", port=lead.ports["o2"])
    c.info["length"] = length
    c.info["taper_length"] = taper_length
    c.info["radius"] = radius
    return c


@curves.sampled_cell(tags=["layout", "primitive", "metal", "rounded_end"])
def rounded_end_metal_segment(
    length: float = 100.0,
    width: float = 10.0,
    ground_mask_margin: float = 6.0,
    n_cap_points: int | None = None,
    draw_layer: LayerSpec = LAYER.D0_TOP_M1_DRAW,
    etch_layer: LayerSpec = LAYER.D0_TOP_M1_ETCH,
    ground_mask_layer: LayerSpec = LAYER.D0_TOP_GROUND_MASK,
) -> gf.Component:
    """Flat X=0 face and width/2 cap ending at X=length, counted once.

    Points per quarter include the actual cap apex. The same sampled DRAW
    outline supplies GF-offset MASK and MASK-DRAW ETCH. o_mesh marks the
    cap centre, not a route/load/mesh-size policy. See shared-primitives guide.
    At length=width/2 the half-disk marker lies on the flat boundary, sharing
    o1's centre but not its orientation or type; strict interior is not promised.
    """
    if width <= 0 or length < width / 2:
        raise ValueError("width must be positive and length must contain the half-width cap")
    if ground_mask_margin < 0:
        raise ValueError("ground_mask_margin must be nonnegative for expansion")
    if n_cap_points is None:
        n_cap_points = curves.arc_points(width / 2, 90)
    if n_cap_points < 2:
        raise ValueError("each cap quarter needs its two endpoints")
    radius = width / 2
    center_x = length - radius
    angles = [-pi / 2 + i * pi / (2 * (n_cap_points - 1)) for i in range(n_cap_points)]
    angles += [i * pi / (2 * (n_cap_points - 1)) for i in range(1, n_cap_points)]
    points = [
        (0.0, -radius),
        *[(center_x + radius * cos(a), radius * sin(a)) for a in angles],
        (0.0, radius),
    ]
    c = gf.Component()
    draw = gf.Component()
    draw.add_polygon(points, layer=draw_layer)
    c << draw
    mask = gf.Component()
    mask.add_polygon(points, layer=ground_mask_layer)
    mask.offset(layer=ground_mask_layer, distance=ground_mask_margin)
    c << mask
    c << gf.boolean(
        A=mask,
        B=draw,
        operation="not",
        layer=etch_layer,
        layer1=ground_mask_layer,
        layer2=draw_layer,
    )
    c.add_port("o1", center=(0.0, 0.0), width=width, orientation=180.0, layer=draw_layer)
    add_mesh_port(
        c, name="o_mesh", center=(center_x, 0.0), width=width, orientation=0.0, layer=draw_layer
    )
    return c


@curves.sampled_cell(tags=["layout", "primitive", "rounded_rectangle"])
def rounded_rectangle(
    width: float = 100.0,
    height: float = 50.0,
    corner_radius: float = 7.0,
    n_corner_points: int | None = None,
    ground_mask_margin: float = 6.0,
    draw_layer: LayerSpec = LAYER.D0_TOP_M1_DRAW,
    ground_mask_layer: LayerSpec | None = None,
    port_type: str | None = "electrical",
) -> gf.Component:
    """Centred GF rounded DRAW with optional independently expanded MASK.

    Sampling is points per corner; actual GF edge ports span the remaining
    straight edge, not the full unrounded edge. Reject oversize radii instead
    of using GF's clamp. No private rounding/port equivalence is claimed.
    """
    if width <= 0 or height <= 0 or not 0 <= corner_radius <= min(width, height) / 2:
        raise ValueError("positive dimensions must contain the nonnegative corner radius")
    if n_corner_points is None:
        sampling_radius = corner_radius + (
            ground_mask_margin if ground_mask_layer is not None else 0
        )
        n_corner_points = curves.arc_points(sampling_radius, 90) if sampling_radius > 0 else 2
    if n_corner_points < 2:
        raise ValueError("each rounded corner needs its two endpoints")
    c = gf.Component()
    draw = c << gf.components.rounded_rectangle(
        width=width,
        height=height,
        corner_radius_x=corner_radius,
        corner_radius_y=corner_radius,
        n_corner_points=n_corner_points,
        layer=draw_layer,
        port_type=port_type,
    )
    c.add_ports(draw.ports)
    if ground_mask_layer is not None:
        if ground_mask_margin < 0:
            raise ValueError("ground_mask_margin must be nonnegative for expansion")
        c << gf.components.rounded_rectangle(
            width=width + 2 * ground_mask_margin,
            height=height + 2 * ground_mask_margin,
            corner_radius_x=corner_radius + ground_mask_margin,
            corner_radius_y=corner_radius + ground_mask_margin,
            n_corner_points=n_corner_points,
            layer=ground_mask_layer,
        )
    return c


@curves.sampled_cell(tags=["layout", "primitive", "wire_corner"])
def wire_corner(
    cross_section: CrossSectionSpec = "cpw_6_7_6",
    port_names: PortNames = ("e1", "e2"),
    port_types: PortTypes = ("electrical", "electrical"),
    width: float | None = None,
    radius: float | None = None,
) -> gf.Component:
    """Forward GF's sharp wire corner; GF9.48 accepts but ignores radius."""
    return gf.components.wire_corner(
        cross_section=cross_section,
        port_names=port_names,
        port_types=port_types,
        width=width,
        radius=radius,
    )


__all__ = [
    "bend_circular",
    "bend_euler",
    "straight",
    "cpw_handoff",
    "rounded_end_metal_segment",
    "rounded_rectangle",
    "wire_corner",
]
