"""Public capacitor primitives."""

from __future__ import annotations

from itertools import chain
from math import atan2, ceil, cos, hypot, isfinite, pi, sin, tan

import gdsfactory as gf
from gdsfactory.typings import CrossSectionSpec, Layer

import orcapen_sc_pdk.curve_sampling as curves
from orcapen_sc_pdk.helpers.layout import add_etch_for_component
from orcapen_sc_pdk.tech import LAYER


def _rounded_contour(points, radius: float, cutplanes: tuple[float, float]):
    """Fillet a merged micrometre contour, leaving outer CPW planes intact.

    Circular tangent arcs use the central sampling profile,
    including both tangent endpoints. GDSFactory quantizes these samples to its
    existing grid. This is polygonal geometry, not a fabrication accuracy claim.
    Adjacent tangent setbacks must fit their original edge; never clamp radius.
    """
    vertices = [tuple(p) for p in points]
    corners = []
    for index, point in enumerate(vertices):
        previous, following = vertices[index - 1], vertices[(index + 1) % len(vertices)]
        incoming = (point[0] - previous[0], point[1] - previous[1])
        outgoing = (following[0] - point[0], following[1] - point[1])
        before, after = hypot(*incoming), hypot(*outgoing)
        u = (incoming[0] / before, incoming[1] / before)
        v = (outgoing[0] / after, outgoing[1] / after)
        turn = atan2(u[0] * v[1] - u[1] * v[0], u[0] * v[0] + u[1] * v[1])
        setback = 0.0 if point[0] in cutplanes else radius * tan(abs(turn) / 2)
        corners.append((point, u, turn, setback, after))
    for index, (_, _, _, setback, length) in enumerate(corners):
        if setback + corners[(index + 1) % len(corners)][3] > length:
            raise ValueError(
                f"corner_radius_um={radius!r} does not fit tangent segments "
                f"at {vertices[index]!r} -> {vertices[(index + 1) % len(vertices)]!r}."
            )
    rounded = []
    for point, u, turn, setback, _ in corners:
        if setback == 0:
            rounded.append(point)
            continue
        direction = 1 if turn > 0 else -1
        start = (point[0] - setback * u[0], point[1] - setback * u[1])
        center = (start[0] - direction * radius * u[1], start[1] + direction * radius * u[0])
        angle = atan2(start[1] - center[1], start[0] - center[0])
        steps = curves.arc_points(radius, turn * 180 / pi) - 1
        rounded.extend(
            (
                center[0] + radius * cos(angle + turn * i / steps),
                center[1] + radius * sin(angle + turn * i / steps),
            )
            for i in range(steps + 1)
        )
    return rounded


@curves.sampled_cell(tags=["layout", "capacitor", "interdigital"])
def interdigital_capacitor(
    fingers: int = 20,
    finger_length: float = 100.0,
    finger_gap: float = 3.3,
    finger_width: float = 3.3,
    taper_length: float = 150.0,
    terminal_extension_length_um: float = 100.0,
    capacitor_ground_gap: float = 85.0,
    cpw_xs: CrossSectionSpec = "coplanar_waveguide",
    half: bool = False,
    draw_layer: Layer = LAYER.D0_TOP_M1_DRAW,
    etch_layer: Layer = LAYER.D0_TOP_M1_ETCH,
    ground_mask_layer: Layer = LAYER.D0_TOP_GROUND_MASK,
    corner_radius_um: float = 0.0,
) -> gf.Component:
    """Return an IDC with symmetric CPW terminal extensions and derived etch.

    The public ports are the outer CPW cut planes: standalone terminals remain
    open for Q3D extraction, while assembled CPW routes connect at those planes.
    Zero radius retains sharp geometry. Positive radius fillets the merged metal
    and ground-mask contours, excluding the flat outer CPW cut planes; nominal
    straight finger/end gaps and port definitions stay fixed. A radius that
    cannot fit adjacent tangent segments raises ValueError instead of shrinking.
    """

    xs = gf.get_cross_section(cpw_xs)
    cpw_width = xs["cpw_draw"].width
    cpw_gap = xs["cpw_etch_pos"].width
    if not isfinite(corner_radius_um) or corner_radius_um < 0:
        raise ValueError("corner_radius_um must be finite and nonnegative.")

    component = gf.Component()
    core_capacitor_temp = gf.Component()
    if fingers < 1:
        raise ValueError("fingers must be at least 1.")
    if not isfinite(terminal_extension_length_um) or terminal_extension_length_um <= 0:
        raise ValueError(
            "terminal_extension_length_um must be finite and positive, "
            f"got {terminal_extension_length_um!r}."
        )

    width = finger_length + finger_gap if not half else finger_length
    height = fingers * finger_width + (fingers - 1) * finger_gap

    points_1 = [
        (0, 0),
        (0, height),
        (finger_length, height),
        (finger_length, height - finger_width),
        (0, height - finger_width),
        *chain.from_iterable(
            (
                (0, height - (2 * index) * (finger_width + finger_gap)),
                (
                    finger_length,
                    height - (2 * index) * (finger_width + finger_gap),
                ),
                (
                    finger_length,
                    height - (2 * index) * (finger_width + finger_gap) - finger_width,
                ),
                (
                    0,
                    height - (2 * index) * (finger_width + finger_gap) - finger_width,
                ),
            )
            for index in range(ceil(fingers / 2))
        ),
        (0, 0),
    ]
    core_capacitor_temp.add_polygon(points=points_1, layer=draw_layer)

    if not half:
        points_2 = [
            (width, 0),
            (width, height),
            *chain.from_iterable(
                (
                    (width, height - (2 * index + 1) * (finger_width + finger_gap)),
                    (
                        width - finger_length,
                        height - (2 * index + 1) * (finger_width + finger_gap),
                    ),
                    (
                        width - finger_length,
                        height - (2 * index + 1) * (finger_width + finger_gap) - finger_width,
                    ),
                    (
                        width,
                        height - (2 * index + 1) * (finger_width + finger_gap) - finger_width,
                    ),
                )
                for index in range(fingers // 2)
            ),
        ]
        core_capacitor_temp.add_polygon(points=points_2, layer=draw_layer)

    core_capacitor = component << core_capacitor_temp
    core_capacitor.move((-core_capacitor_temp.x, -core_capacitor_temp.y))

    in_taper = component << gf.components.taper(
        length=taper_length,
        width1=cpw_width,
        width2=height,
        layer=draw_layer,
    )
    in_taper.movex(-(taper_length + core_capacitor_temp.x))
    out_taper = component << gf.components.taper(
        length=taper_length,
        width1=height,
        width2=cpw_width,
        layer=draw_layer,
    )
    out_taper.movex(core_capacitor_temp.x)

    terminal_extension = gf.path.extrude(
        gf.path.straight(terminal_extension_length_um),
        width=cpw_width,
        layer=draw_layer,
    )
    in_extension = component << terminal_extension
    in_extension.dmovex(in_taper.xmin - in_extension.xmax)
    out_extension = component << terminal_extension
    out_extension.dmovex(out_taper.xmax - out_extension.xmin)

    component.add_port(
        name="o_capacitor_in",
        center=(component.xmin, 0),
        width=cpw_width,
        orientation=180,
        layer=draw_layer,
    )
    component.add_port(
        name="o_capacitor_out",
        center=(component.xmax, 0),
        width=cpw_width,
        orientation=0,
        layer=draw_layer,
    )

    mask_points = [
        (component.xmin, cpw_width / 2 + cpw_gap),
        (in_taper.xmin, cpw_width / 2 + cpw_gap),
        (core_capacitor.xmin, height / 2 + capacitor_ground_gap),
        (core_capacitor.xmax, height / 2 + capacitor_ground_gap),
        (out_taper.xmax, cpw_width / 2 + cpw_gap),
        (component.xmax, cpw_width / 2 + cpw_gap),
        (component.xmax, -cpw_width / 2 - cpw_gap),
        (out_taper.xmax, -cpw_width / 2 - cpw_gap),
        (core_capacitor.xmax, -height / 2 - capacitor_ground_gap),
        (core_capacitor.xmin, -height / 2 - capacitor_ground_gap),
        (in_taper.xmin, -cpw_width / 2 - cpw_gap),
        (component.xmin, -cpw_width / 2 - cpw_gap),
    ]
    component.add_polygon(points=mask_points, layer=ground_mask_layer)

    if corner_radius_um > 0:
        # Merge before filleting: taper/finger shared edges are not corners.
        # GF's points API serializes holes with artificial hull bridges. Read
        # native hull/hole iterators only at this narrow readback boundary:
        # get_polygons preserves topology; integer coordinates become um here.
        # All geometry authoring/composition remains on public GF APIs.
        rounded = gf.Component()
        contours = {}
        dbu = component.kcl.dbu
        for layer in (draw_layer, ground_mask_layer):
            merged = component.extract([layer])
            contours[layer] = []
            for polygons in merged.get_polygons(merge=True).values():
                for polygon in polygons:
                    hull = [(p.x * dbu, p.y * dbu) for p in polygon.each_point_hull()]
                    holes = [
                        [(p.x * dbu, p.y * dbu) for p in polygon.each_point_hole(i)]
                        for i in range(polygon.holes())
                    ]
                    contours[layer].append((hull, holes))
        # Use actual extracted grid coordinates, not unsnapped construction floats.
        xs_on_grid = [
            point[0] for polygons in contours.values() for hull, _ in polygons for point in hull
        ]
        cutplanes = (min(xs_on_grid), max(xs_on_grid))
        for layer, polygons in contours.items():
            for hull, holes in polygons:
                outer = gf.Component()
                outer.add_polygon(_rounded_contour(hull, corner_radius_um, cutplanes), layer=layer)
                if holes:
                    voids = gf.Component()
                    for hole in holes:
                        voids.add_polygon(
                            _rounded_contour(hole, corner_radius_um, cutplanes), layer=layer
                        )
                    rounded << gf.boolean(outer, voids, operation="not", layer=layer)
                else:
                    rounded << outer
        rounded.add_ports(component.ports)
        component = rounded

    result = add_etch_for_component(
        component=component,
        draw_layer=draw_layer,
        mask_layer=ground_mask_layer,
        etch_layer=etch_layer,
    )
    result.info["cpw_gap_um"] = float(cpw_gap)
    return result
