"""Nominal hollow TSV source; physical recipes are not backend CAD readback.

OrcaPen owns the die, bore, wall, landing geometry and intended end-face contacts.
Callers own final electrical Nets and any backend/export/inspection treatment.
The detached getter uses SCG's existing normalized source record shape without
importing its runtime. No native-body registration or solver launch is supplied.
"""

from collections.abc import Mapping
from copy import deepcopy
from typing import Literal

import gdsfactory as gf

import orcapen_sc_pdk.curve_sampling as curves
from orcapen_sc_pdk.materials import get_material_records
from orcapen_sc_pdk.ports import add_junction_lumped_port
from orcapen_sc_pdk.tech import LAYER, LAYER_STACK


def _circle_curves(radius_um: float, *, hole: bool = False) -> list[dict]:
    """Two authored semicircles; holes use the opposite orientation."""
    sign = -1 if hole else 1
    return [
        {
            "kind": "circular_arc",
            "points_um": [[radius_um, 0.0], [0.0, sign * radius_um], [-radius_um, 0.0]],
        },
        {
            "kind": "circular_arc",
            "points_um": [[-radius_um, 0.0], [0.0, -sign * radius_um], [radius_um, 0.0]],
        },
    ]


@curves.sampled_cell(tags=["simulation", "tsv", "ground", "hollow", "single_die"])
def tsv_ground_coupon(
    die: Literal["D0", "D1"] = "D0",
    die_side_um: float = 1000.0,
    bore_diameter_um: float = 60.0,
    wall_thickness_um: float = 0.2,
    landing_outer_radius_um: float = 100.0,
) -> gf.Component:
    """One selected die with cut Si, uniform TiN wall and open Al end landings.

    Defaults are a nominal research model, not a published-process replica.
    The substrate and Al thickness/face locations come from the selected PDK
    levels. GDS witnesses are sampled circles; authored recipes retain exact
    circular radii. The inner bore remains empty through both Al landings.
    """
    if die not in {"D0", "D1"}:
        raise ValueError("die must select D0 or D1")
    outer_radius = bore_diameter_um / 2
    inner_radius = outer_radius - wall_thickness_um
    if not 0 < inner_radius < outer_radius:
        raise ValueError("a hollow TSV requires positive inner radius and wall thickness")
    if landing_outer_radius_um < outer_radius:
        raise ValueError("end landings must cover the whole TSV wall")
    if die_side_um <= 2 * landing_outer_radius_um:
        raise ValueError("die must contain the annular end landings")

    substrate_id = f"{die}_SUBSTRATE"
    wall_level_id = "D0_TOP_TSV" if die == "D0" else "D1_BOTTOM_TSV"
    bottom_id, top_id = f"{die}_BOTTOM_M1", f"{die}_TOP_M1"
    substrate = LAYER_STACK.layers[substrate_id]
    wall = LAYER_STACK.layers[wall_level_id]
    bottom, top = LAYER_STACK.layers[bottom_id], LAYER_STACK.layers[top_id]
    substrate_layer = tuple(getattr(LAYER, f"{die}_SUBSTRATE_AREA"))
    wall_layer = tuple(getattr(LAYER, wall_level_id))
    bottom_layer = tuple(getattr(LAYER, f"{bottom_id}_DRAW"))
    top_layer = tuple(getattr(LAYER, f"{top_id}_DRAW"))

    # Public GF Boolean construction actually removes the source bore and caps.
    c = gf.Component()
    die_rectangle = gf.components.rectangle(
        size=(die_side_um, die_side_um), centered=True, layer=substrate_layer
    )
    bore = curves.circle(radius=outer_radius, layer=wall_layer)
    central_hole = curves.circle(radius=inner_radius, layer=wall_layer)
    silicon = gf.boolean(
        die_rectangle,
        bore,
        operation="not",
        layer=substrate_layer,
        layer1=substrate_layer,
        layer2=wall_layer,
    )
    liner = gf.boolean(
        bore,
        central_hole,
        operation="not",
        layer=wall_layer,
        layer1=wall_layer,
        layer2=wall_layer,
    )
    c.add_ref(silicon, name="CUT_SI")
    c.add_ref(liner, name="HOLLOW_TIN_WALL")
    for name, layer in (("BOTTOM_LANDING", bottom_layer), ("TOP_LANDING", top_layer)):
        landing_disk = curves.circle(radius=landing_outer_radius_um, layer=layer)
        landing = gf.boolean(
            landing_disk,
            central_hole,
            operation="not",
            layer=layer,
            layer1=layer,
            layer2=wall_layer,
        )
        c.add_ref(landing, name=name)

    half_die = die_side_um / 2
    square = [
        [-half_die, -half_die],
        [half_die, -half_die],
        [half_die, half_die],
        [-half_die, half_die],
    ]
    regions = []
    for local_id, level_id, level, layer, recipe in (
        (
            "SI",
            substrate_id,
            substrate,
            substrate_layer,
            {
                "kind": "rectangle_minus_circular_bore_prism",
                "outer_xy_um": square,
                "bore_center_um": [0.0, 0.0],
                "bore_radius_um": outer_radius,
            },
        ),
        (
            "TSV_WALL",
            wall_level_id,
            wall,
            wall_layer,
            {
                "kind": "annular_prism",
                "center_um": [0.0, 0.0],
                "outer_radius_um": outer_radius,
                "inner_radius_um": inner_radius,
            },
        ),
        (
            "BOTTOM_LANDING",
            bottom_id,
            bottom,
            bottom_layer,
            {
                "kind": "annular_prism",
                "center_um": [0.0, 0.0],
                "outer_radius_um": landing_outer_radius_um,
                "inner_radius_um": inner_radius,
            },
        ),
        (
            "TOP_LANDING",
            top_id,
            top,
            top_layer,
            {
                "kind": "annular_prism",
                "center_um": [0.0, 0.0],
                "outer_radius_um": landing_outer_radius_um,
                "inner_radius_um": inner_radius,
            },
        ),
    ):
        if local_id == "SI":
            outer_curves = [
                {"kind": "line_segment", "points_um": [point, square[(i + 1) % 4]]}
                for i, point in enumerate(square)
            ]
            hole_radius = outer_radius
        else:
            outer_curves = _circle_curves(recipe["outer_radius_um"])
            hole_radius = inner_radius
        regions.append(
            {
                "body_id": f"{die}/{local_id}",
                "source_entity_ids": [f"{die}/{local_id}"],
                "source_occurrence_path": {
                    "SI": "CUT_SI",
                    "TSV_WALL": "HOLLOW_TIN_WALL",
                    "BOTTOM_LANDING": "BOTTOM_LANDING",
                    "TOP_LANDING": "TOP_LANDING",
                }[local_id],
                "physical_level_id": f"orcapen_sc_pdk:{level_id}",
                "level_id": level_id,
                "layer": layer,
                "material_id": level.material,
                "dimension": 3,
                "z_interval_um": [level.zmin, level.zmin + level.thickness],
                "physical_thickness_um": level.thickness,
                "region_recipe": recipe,
                "boundary_curves": [
                    {
                        "boundary_id": f"{die}/{local_id}/OUTER",
                        "role": "outer",
                        "curves": outer_curves,
                    },
                    {
                        "boundary_id": f"{die}/{local_id}/HOLE",
                        "role": "hole",
                        "hole_index": 0,
                        "curves": _circle_curves(hole_radius, hole=True),
                    },
                ],
            }
        )
    materials = get_material_records()
    c.info["tsv_source"] = {
        "schema_version": 1,
        "model": "nominal_research_hollow_tsv",
        "geometry_stage": "gf_source_with_authored_physical_recipes_not_native_readback",
        "coordinate_unit": "um",
        "die": die,
        "parameters": {
            "die_side_um": die_side_um,
            "bore_diameter_um": bore_diameter_um,
            "wall_thickness_um": wall_thickness_um,
            "landing_outer_radius_um": landing_outer_radius_um,
        },
        "source_regions": regions,
        "material_records": {name: materials[name] for name in ("Si", "TiN", "Al")},
        "contacts": [
            {
                "contact_id": f"{die}/TSV_TO_{side}_LANDING",
                "body_ids": [f"{die}/TSV_WALL", f"{die}/{side}_LANDING"],
                "z_um": z,
                "radial_interval_um": [inner_radius, outer_radius],
                "wall_face_normal": [0, 0, normal],
                "landing_face_normal": [0, 0, -normal],
                "state": "source_end_face_contact_intent_not_backend_contact_readback",
            }
            for side, z, normal in (
                ("BOTTOM", substrate.zmin, -1),
                ("TOP", substrate.zmin + substrate.thickness, 1),
            )
        ],
        "empty_bore": {
            "radius_um": inner_radius,
            "z_interval_um": [bottom.zmin, top.zmin + top.thickness],
            "meaning": "empty geometric hole; no fill or cavity material body inferred",
        },
        "final_nets": "caller_owned; ground intent does not assign an electrical Net",
        "ports": "none",
        "backend_registration": "not provided",
    }
    c.info["source_record_getter"] = "get_tsv_source_records"
    return c


def _grounded_system(
    *,
    die: Literal["D0", "D1"],
    die_side_um: float,
    bore_diameter_um: float,
    wall_thickness_um: float,
    tsv_offset_um: float,
    signal_size_um: tuple[float, float],
    gap_um: float,
    simple_pad: bool,
    junction_width_um: float = 2.0,
    tsv_centers_um: tuple[tuple[float, float], ...] | None = None,
) -> gf.Component:
    """Build positive planes once; contact subsets never add landing metal."""
    # Reuse the coupon's real cut/wall construction and physical source facts.
    coupon = tsv_ground_coupon(
        die=die,
        die_side_um=die_side_um,
        bore_diameter_um=bore_diameter_um,
        wall_thickness_um=wall_thickness_um,
    )
    template = deepcopy(coupon.info["tsv_source"])
    substrate_id = f"{die}_SUBSTRATE"
    wall_id = "D0_TOP_TSV" if die == "D0" else "D1_BOTTOM_TSV"
    substrate_layer = tuple(getattr(LAYER, f"{die}_SUBSTRATE_AREA"))
    wall_layer = tuple(getattr(LAYER, wall_id))
    top_layer = tuple(getattr(LAYER, f"{die}_TOP_M1_DRAW"))
    bottom_layer = tuple(getattr(LAYER, f"{die}_BOTTOM_M1_DRAW"))
    outer_radius = bore_diameter_um / 2
    inner_radius = outer_radius - wall_thickness_um
    centers = (
        list(tsv_centers_um)
        if tsv_centers_um is not None
        else [
            (-tsv_offset_um, -tsv_offset_um),
            (-tsv_offset_um, tsv_offset_um),
            (tsv_offset_um, -tsv_offset_um),
            (tsv_offset_um, tsv_offset_um),
        ]
    )
    c = gf.Component()
    die_rectangle = gf.components.rectangle(
        size=(die_side_um, die_side_um), centered=True, layer=substrate_layer
    )
    bores, holes = gf.Component(), gf.Component()
    outer = curves.circle(radius=outer_radius, layer=wall_layer)
    inner = curves.circle(radius=inner_radius, layer=wall_layer)
    liner = gf.boolean(outer, inner, operation="not", layer=wall_layer)
    for center in centers:
        bores.add_ref(outer).move(center)
        holes.add_ref(inner).move(center)
    silicon = gf.boolean(
        die_rectangle,
        bores,
        operation="not",
        layer=substrate_layer,
        layer1=substrate_layer,
        layer2=wall_layer,
    )
    c.add_ref(silicon, name="CUT_SI")
    for index, center in enumerate(centers):
        c.add_ref(liner, name=f"TSV_{index}").move(center)
    back = gf.boolean(
        die_rectangle,
        holes,
        operation="not",
        layer=bottom_layer,
        layer1=substrate_layer,
        layer2=wall_layer,
    )
    c.add_ref(back, name="BACK_GROUND")
    sx, sy = signal_size_um
    opening_size = (sx + 2 * gap_um, sy + 2 * gap_um) if simple_pad else (sx, sy + 2 * gap_um)
    opening = gf.components.rectangle(size=opening_size, centered=True, layer=wall_layer)
    cutouts = gf.Component()
    cutouts.add_ref(holes)
    cutouts.add_ref(opening)
    top_ground = gf.boolean(
        die_rectangle,
        cutouts,
        operation="not",
        layer=top_layer,
        layer1=substrate_layer,
        layer2=wall_layer,
    )
    c.add_ref(top_ground, name="TOP_GROUND")
    signal = gf.components.rectangle(size=signal_size_um, centered=True, layer=top_layer)
    c.add_ref(signal, name="PAD" if simple_pad else "SIGNAL")
    if simple_pad:
        sheet_layer = tuple(getattr(LAYER, f"{die}_TOP_SIM_BOUNDARY"))
        overlap = c.kcl.dbu
        center = (sx / 2 + gap_um / 2, 0.0)
        sheet = gf.components.rectangle(
            size=(gap_um + 2 * overlap, junction_width_um),
            centered=True,
            layer=sheet_layer,
        )
        c.add_ref(sheet, name="JUNCTION_LOCATOR").move(center)
        add_junction_lumped_port(
            c,
            name="o_junction_lumped",
            center=center,
            width=junction_width_um,
            orientation=0.0,
            layer=sheet_layer,
        )
        c.info["junction_sheet_overlap_um"] = overlap
    else:
        for name, x, orientation in (("o1", -sx / 2, 180), ("o2", sx / 2, 0)):
            c.add_port(
                name,
                center=(x, 0),
                width=sy,
                orientation=orientation,
                layer=top_layer,
                port_type="electrical",
            )

    regions = []
    # Recipes carry authored intent; actual references below own polygon witnesses.
    for local_id, level_id, layer, recipe, occurrence in (
        (
            "SI",
            substrate_id,
            substrate_layer,
            {
                "kind": "rectangle_minus_circular_bores_prism",
                "die_side_um": die_side_um,
                "bore_centers_um": centers,
                "bore_radius_um": outer_radius,
            },
            "CUT_SI",
        ),
        (
            "BACK_GROUND",
            f"{die}_BOTTOM_M1",
            bottom_layer,
            {
                "kind": "plane_minus_holes",
                "die_side_um": die_side_um,
                "hole_centers_um": centers,
                "hole_radius_um": inner_radius,
            },
            "BACK_GROUND",
        ),
        (
            "TOP_GROUND",
            f"{die}_TOP_M1",
            top_layer,
            {
                "kind": "plane_minus_opening_and_holes",
                "die_side_um": die_side_um,
                "opening_size_um": opening_size,
                "hole_centers_um": centers,
                "hole_radius_um": inner_radius,
            },
            "TOP_GROUND",
        ),
        (
            "PAD" if simple_pad else "SIGNAL",
            f"{die}_TOP_M1",
            top_layer,
            {"kind": "rectangle_prism", "size_um": signal_size_um},
            "PAD" if simple_pad else "SIGNAL",
        ),
    ):
        level = LAYER_STACK.layers[level_id]
        regions.append(
            {
                "body_id": f"{die}/{local_id}",
                "source_entity_ids": [f"{die}/{local_id}"],
                "source_occurrence_path": occurrence,
                "level_id": level_id,
                "physical_level_id": f"orcapen_sc_pdk:{level_id}",
                "layer": layer,
                "material_id": level.material,
                "dimension": 3,
                "z_interval_um": [level.zmin, level.zmin + level.thickness],
                "physical_thickness_um": level.thickness,
                "region_recipe": recipe,
            }
        )
    for index, center in enumerate(centers):
        region = deepcopy(template["source_regions"][1])
        region.update(
            body_id=f"{die}/TSV_{index}",
            source_entity_ids=[f"{die}/TSV_{index}"],
            source_occurrence_path=f"TSV_{index}",
        )
        region["region_recipe"]["center_um"] = center
        for boundary in region["boundary_curves"]:
            boundary["boundary_id"] = boundary["boundary_id"].replace("TSV_WALL", f"TSV_{index}")
            boundary["coordinate_frame"] = "source_occurrence_local_um"
        # Curves in this template are child-local; the actual occurrence places them.
        regions.append(region)
    contacts = [
        {
            "contact_id": f"{die}/TSV_{index}_TO_{side}_GROUND",
            "body_ids": [f"{die}/TSV_{index}", f"{die}/{plane}"],
            "source_occurrence_path": f"TSV_{index}",
            "center_um": center,
            "z_um": z,
            "radial_interval_um": [inner_radius, outer_radius],
            "wall_face_normal": [0, 0, normal],
            "landing_face_normal": [0, 0, -normal],
            "state": "source_contact_subset_not_native_contact_readback",
        }
        for index, center in enumerate(centers)
        for side, plane, z, normal in (
            ("BOTTOM", "BACK_GROUND", LAYER_STACK.layers[substrate_id].zmin, -1),
            (
                "TOP",
                "TOP_GROUND",
                LAYER_STACK.layers[substrate_id].zmin + LAYER_STACK.layers[substrate_id].thickness,
                1,
            ),
        )
    ]
    template.update(
        model="nominal_research_tsv_grounded_simple_pad"
        if simple_pad
        else "nominal_research_tsv_grounded_cpw",
        source_regions=regions,
        contacts=contacts,
        parameters={
            "die_side_um": die_side_um,
            "bore_diameter_um": bore_diameter_um,
            "wall_thickness_um": wall_thickness_um,
            "tsv_offset_um": tsv_offset_um,
            "signal_size_um": signal_size_um,
            "gap_um": gap_um,
        },
        proposed_ground_members=[f"{die}/BACK_GROUND", f"{die}/TOP_GROUND"]
        + [f"{die}/TSV_{index}" for index in range(len(centers))],
        ports=[port.name for port in c.ports],
    )
    template["empty_bore"]["centers_um"] = centers
    c.info["tsv_source"] = template
    c.info["source_record_getter"] = "get_tsv_source_records"
    return c


@curves.sampled_cell(tags=["simulation", "tsv", "simple_pad", "single_die"])
def tsv_grounded_simple_pad(
    die: Literal["D0", "D1"] = "D0",
    pad_side_um: float = 200.0,
    gap_um: float = 20.0,
    die_side_um: float = 1000.0,
    junction_width_um: float = 2.0,
    bore_diameter_um: float = 60.0,
    wall_thickness_um: float = 0.2,
    tsv_offset_um: float = 300.0,
) -> gf.Component:
    """Positive top/back Ground with four hollow TSVs and an east pad locator."""
    return _grounded_system(
        die=die,
        die_side_um=die_side_um,
        bore_diameter_um=bore_diameter_um,
        wall_thickness_um=wall_thickness_um,
        tsv_offset_um=tsv_offset_um,
        signal_size_um=(pad_side_um, pad_side_um),
        gap_um=gap_um,
        simple_pad=True,
        junction_width_um=junction_width_um,
    )


@curves.sampled_cell(tags=["simulation", "tsv", "cpw", "single_die"])
def tsv_grounded_cpw(
    die: Literal["D0", "D1"] = "D0",
    width_um: float = 10.0,
    gap_um: float = 6.0,
    die_side_um: float = 1000.0,
    bore_diameter_um: float = 60.0,
    wall_thickness_um: float = 0.2,
    tsv_offset_um: float = 300.0,
) -> gf.Component:
    """Uniform exterior-cut CPW with widened positive Ground and four TSVs."""
    return _grounded_system(
        die=die,
        die_side_um=die_side_um,
        bore_diameter_um=bore_diameter_um,
        wall_thickness_um=wall_thickness_um,
        tsv_offset_um=tsv_offset_um,
        signal_size_um=(die_side_um, width_um),
        gap_um=gap_um,
        simple_pad=False,
    )


@curves.sampled_cell(tags=["simulation", "tsv", "cpw", "ground_stitching", "single_die"])
def tsv_ground_stitched_cpw(
    die: Literal["D0", "D1"] = "D0",
    width_um: float = 10.0,
    gap_um: float = 6.0,
    die_side_um: float = 1000.0,
    bore_diameter_um: float = 60.0,
    wall_thickness_um: float = 0.2,
    tsv_row_y_um: float = 100.0,
    tsv_x_um: tuple[float, ...] = (-300.0, -100.0, 100.0, 300.0),
) -> gf.Component:
    """Discrete Ground stitching for a later distance/density study, not Q2D.

    Row/pitch values are proposed source settings, not a scientific optimum.
    The uniform signal reaches both die X edges; final Nets remain caller-owned.
    """
    c = _grounded_system(
        die=die,
        die_side_um=die_side_um,
        bore_diameter_um=bore_diameter_um,
        wall_thickness_um=wall_thickness_um,
        tsv_offset_um=tsv_row_y_um,
        signal_size_um=(die_side_um, width_um),
        gap_um=gap_um,
        simple_pad=False,
        tsv_centers_um=tuple((x, y) for y in (-tsv_row_y_um, tsv_row_y_um) for x in tsv_x_um),
    )
    records = c.info["tsv_source"]
    records["model"] = "nominal_research_ground_stitched_cpw"
    records["parameters"].pop("tsv_offset_um")
    records["parameters"].update(
        tsv_row_y_um=tsv_row_y_um,
        tsv_x_um=tsv_x_um,
        tsv_x_pitch_um=[right - left for left, right in zip(tsv_x_um, tsv_x_um[1:], strict=False)],
        bore_edge_to_gap_outer_edge_um=abs(tsv_row_y_um)
        - bore_diameter_um / 2
        - width_um / 2
        - gap_um,
    )
    records["purpose"] = (
        "proposed Ground stitching distance/density source; no optimum or field result"
    )
    records["proposed_signal_members"] = [f"{die}/SIGNAL"]
    records["final_nets"] = (
        "caller_owned; proposed conductor membership does not assign electrical Nets"
    )
    return c


@curves.sampled_cell(tags=["simulation", "tsv", "concentric", "through_signal", "single_die"])
def tsv_concentric_signal_coupon(
    die: Literal["D0", "D1"] = "D0",
    die_side_um: float = 1000.0,
    bore_diameter_um: float = 60.0,
    wall_thickness_um: float = 0.2,
    signal_outer_radius_um: float = 100.0,
    gap_um: float = 20.0,
    ground_tsv_offset_um: float = 300.0,
) -> gf.Component:
    """Annular Signal pads joined by a hollow wall; separate stitched Ground.

    Full-3D capacitance extraction demonstration source, not a filled TSV or
    a frequency/port/field result. Both positive Ground planes exclude the
    concentric Signal opening; there are no caps closing the inner bore.
    """
    coupon = tsv_ground_coupon(
        die=die,
        die_side_um=die_side_um,
        bore_diameter_um=bore_diameter_um,
        wall_thickness_um=wall_thickness_um,
        landing_outer_radius_um=signal_outer_radius_um,
    )
    template = deepcopy(coupon.info["tsv_source"])
    outer_radius = bore_diameter_um / 2
    inner_radius = outer_radius - wall_thickness_um
    wall_id = "D0_TOP_TSV" if die == "D0" else "D1_BOTTOM_TSV"
    wall_layer = tuple(getattr(LAYER, wall_id))
    substrate_layer = tuple(getattr(LAYER, f"{die}_SUBSTRATE_AREA"))
    ground_centers = [
        (x, y)
        for x in (-ground_tsv_offset_um, ground_tsv_offset_um)
        for y in (-ground_tsv_offset_um, ground_tsv_offset_um)
    ]
    centers = [(0.0, 0.0), *ground_centers]
    c = gf.Component()
    rectangle = gf.components.rectangle(
        size=(die_side_um, die_side_um), centered=True, layer=substrate_layer
    )
    outer = curves.circle(radius=outer_radius, layer=wall_layer)
    inner = curves.circle(radius=inner_radius, layer=wall_layer)
    bores, ground_holes = gf.Component(), gf.Component()
    for center in centers:
        bores.add_ref(outer).move(center)
    for center in ground_centers:
        ground_holes.add_ref(inner).move(center)
    silicon = gf.boolean(
        rectangle,
        bores,
        operation="not",
        layer=substrate_layer,
        layer1=substrate_layer,
        layer2=wall_layer,
    )
    c.add_ref(silicon, name="CUT_SI")
    regions = [deepcopy(template["source_regions"][0])]
    regions[0]["region_recipe"] = {
        "kind": "rectangle_minus_circular_bores_prism",
        "die_side_um": die_side_um,
        "bore_centers_um": centers,
        "bore_radius_um": outer_radius,
    }
    # The single-bore template boundary no longer describes this five-bore body.
    regions[0].pop("boundary_curves")
    for index, center in enumerate(centers):
        name = "SIGNAL_WALL" if index == 0 else f"GROUND_TSV_{index - 1}"
        c.add_ref(gf.Component(base=coupon.insts["HOLLOW_TIN_WALL"].cell.base), name=name).move(
            center
        )
        region = deepcopy(template["source_regions"][1])
        region.update(
            body_id=f"{die}/{name}",
            source_entity_ids=[f"{die}/{name}"],
            source_occurrence_path=name,
        )
        region["region_recipe"]["center_um"] = center
        for boundary in region["boundary_curves"]:
            boundary["boundary_id"] = boundary["boundary_id"].replace("TSV_WALL", name)
            boundary["coordinate_frame"] = "source_occurrence_local_um"
        regions.append(region)
    opening = curves.circle(radius=signal_outer_radius_um + gap_um, layer=wall_layer)
    cutouts = gf.Component()
    cutouts.add_ref(ground_holes)
    cutouts.add_ref(opening)
    for side, template_index in (("BOTTOM", 2), ("TOP", 3)):
        name = f"{side}_SIGNAL"
        c.add_ref(gf.Component(base=coupon.insts[f"{side}_LANDING"].cell.base), name=name)
        signal_region = deepcopy(template["source_regions"][template_index])
        signal_region.update(
            body_id=f"{die}/{name}",
            source_entity_ids=[f"{die}/{name}"],
            source_occurrence_path=name,
        )
        for boundary in signal_region["boundary_curves"]:
            boundary["boundary_id"] = boundary["boundary_id"].replace(f"{side}_LANDING", name)
        regions.append(signal_region)
        ground_name = "BACK_GROUND" if side == "BOTTOM" else "TOP_GROUND"
        layer = tuple(signal_region["layer"])
        ground = gf.boolean(
            rectangle,
            cutouts,
            operation="not",
            layer=layer,
            layer1=substrate_layer,
            layer2=wall_layer,
        )
        c.add_ref(ground, name=ground_name)
        region = deepcopy(signal_region)
        region.update(
            body_id=f"{die}/{ground_name}",
            source_entity_ids=[f"{die}/{ground_name}"],
            source_occurrence_path=ground_name,
            region_recipe={
                "kind": "plane_minus_circular_opening_and_holes",
                "die_side_um": die_side_um,
                "opening_radius_um": signal_outer_radius_um + gap_um,
                "hole_centers_um": ground_centers,
                "hole_radius_um": inner_radius,
            },
        )
        region.pop("boundary_curves")
        regions.append(region)
    contacts = []
    substrate = LAYER_STACK.layers[f"{die}_SUBSTRATE"]
    for index, center in enumerate(centers):
        wall_name = "SIGNAL_WALL" if index == 0 else f"GROUND_TSV_{index - 1}"
        for side, z, normal in (
            ("BOTTOM", substrate.zmin, -1),
            ("TOP", substrate.zmin + substrate.thickness, 1),
        ):
            plane = (
                f"{side}_SIGNAL"
                if index == 0
                else ("BACK_GROUND" if side == "BOTTOM" else "TOP_GROUND")
            )
            contacts.append(
                {
                    "contact_id": f"{die}/{wall_name}_TO_{plane}",
                    "body_ids": [f"{die}/{wall_name}", f"{die}/{plane}"],
                    "source_occurrence_path": wall_name,
                    "center_um": center,
                    "z_um": z,
                    "radial_interval_um": [inner_radius, outer_radius],
                    "wall_face_normal": [0, 0, normal],
                    "landing_face_normal": [0, 0, -normal],
                    "state": "source_end_face_contact_intent_not_backend_contact_readback",
                }
            )
    template.update(
        model="nominal_research_concentric_through_signal_tsv",
        source_regions=regions,
        contacts=contacts,
        parameters={
            "die_side_um": die_side_um,
            "bore_diameter_um": bore_diameter_um,
            "wall_thickness_um": wall_thickness_um,
            "signal_outer_radius_um": signal_outer_radius_um,
            "gap_um": gap_um,
            "ground_tsv_offset_um": ground_tsv_offset_um,
        },
        proposed_signal_members=[
            f"{die}/{name}" for name in ("BOTTOM_SIGNAL", "TOP_SIGNAL", "SIGNAL_WALL")
        ],
        proposed_ground_members=[f"{die}/BACK_GROUND", f"{die}/TOP_GROUND"]
        + [f"{die}/GROUND_TSV_{i}" for i in range(4)],
        purpose="full-3D capacitance extraction source; through Signal and separate reference",
        ports="none",
    )
    template["empty_bore"]["centers_um"] = centers
    template["final_nets"] = (
        "caller_owned; proposed conductor membership does not assign electrical Nets"
    )
    c.info["tsv_source"] = template
    c.info["source_record_getter"] = "get_tsv_source_records"
    return c


def get_tsv_source_records(
    component: gf.Component,
    *,
    host_solution_region: Mapping,
) -> dict:
    """Detach real source facts in the existing SCG normalized-input field shape.

    The caller supplies its complete host solution Entity (including its ID,
    material and domain geometry); this source never invents vacuum padding,
    final Nets or solver settings. Consumers construct SCG's public input models.
    This is not a component_semantics-v2 GeometryPlan.prepare adapter. AEDT uses
    the explicitly selected sampled polygon witness; exact-circle recipes stay
    inactive source intent. Empty route maps do not support Palace compilation.
    """
    records = deepcopy(component.info["tsv_source"])
    host = deepcopy(dict(host_solution_region))
    host_id = host["semantic_id"]
    # Consume the required public Entity fields; missing fields retain native
    # mapping errors, and the consumer's public SCG constructor owns validation.
    host = {
        key: host[key]
        for key in (
            "semantic_id",
            "role",
            "material_id",
            "material_kind",
            "priority",
            "geometry_kind",
            "geometry",
        )
    } | {"metadata": host.get("metadata", {})}
    polygons, entities, layers, occurrences = [], [], [], []
    solution_regions = {
        host_id: {key: value for key, value in host.items() if key != "semantic_id"}
    }
    entities.append(host)
    dbu = component.kcl.dbu
    bounds = component.dbbox()
    domain_bounds = {
        "x_min_um": bounds.left,
        "x_max_um": bounds.right,
        "y_min_um": bounds.bottom,
        "y_max_um": bounds.top,
    }
    # One detached declaration per selected source level, shared by its bodies.
    # Never mutate the global process catalogue or infer radial thickness from Z.
    physical_layers = {
        region["level_id"]: deepcopy(LAYER_STACK.layers[region["level_id"]].info["physical_layer"])
        for region in records["source_regions"]
    }
    wall_level_id = "D0_TOP_TSV" if records["die"] == "D0" else "D1_BOTTOM_TSV"
    physical_layers[wall_level_id]["physical_dimensions"]["radial_wall_thickness_um"] = records[
        "parameters"
    ]["wall_thickness_um"]
    entity_aliases = {region["body_id"]: region["body_id"] for region in records["source_regions"]}
    for region in records["source_regions"]:
        occurrence = region["source_occurrence_path"]
        reference = component.insts[occurrence]
        child = gf.Component(base=reference.cell.base)
        transform = reference.dcplx_trans
        # Narrow read-only interop: GF points expose cutline contours, not true
        # hull/hole loops. Read native polygon loops and convert DBU -> µm here;
        # no KLayout construction or types escape this extraction boundary.
        source_polygons = child.get_polygons(by="tuple")[tuple(region["layer"])]
        tx, ty = transform.disp.x, transform.disp.y
        angle = transform.angle
        if angle != 0 or transform.is_mirror() or transform.mag != 1:
            raise ValueError("TSV source occurrences require their authored translation-only frame")
        loops = []
        entity_polygon_ids = []
        entity_id = region["body_id"]
        for index, polygon in enumerate(source_polygons):
            exterior = [(p.x * dbu + tx, p.y * dbu + ty) for p in polygon.each_point_hull()]
            holes = [
                [(p.x * dbu + tx, p.y * dbu + ty) for p in polygon.each_point_hole(i)]
                for i in range(polygon.holes())
            ]
            polygon_id = f"{entity_id}__P{index:04d}"
            entity_polygon_ids.append(polygon_id)
            loops.append({"exterior": exterior, "holes": holes})
            polygons.append(
                {
                    "polygon_id": polygon_id,
                    "layer": f"{region['layer'][0]}/{region['layer'][1]}",
                    "exterior": exterior,
                    "holes": holes,
                    "object_name": entity_id,
                    "metadata": {
                        "source": "actual_gf_source_occurrence",
                        "source_occurrence_path": occurrence,
                        "source_polygon_index": index,
                        "source_dbu_um": dbu,
                    },
                }
            )
        level = LAYER_STACK.layers[region["level_id"]]
        metadata = {
            "source_occurrence_path": occurrence,
            "source_local_entity_id": entity_id.split("/")[-1],
            "logical_layer_id": region["level_id"],
            "physical_layer_id": region["physical_level_id"],
            "source_cell_name": child.name,
            "source_frame_um": [1, 0, 0, 1, tx, ty],
        }
        metadata["physical_layer"] = physical_layers[region["level_id"]]
        low, high = region["z_interval_um"]
        geometry = {
            "z_um": low,
            "z_min_um": low,
            "z_max_um": high,
            "thickness_um": region["physical_thickness_um"],
            "gds_layer": region["layer"][0],
            "gds_datatype": region["layer"][1],
            "source_occurrence_polygons_um": loops,
        }
        entity = {
            "semantic_id": entity_id,
            "role": "solution_region" if region["material_id"] == "Si" else "metal",
            "material_id": level.material,
            "material_kind": "dielectric" if region["material_id"] == "Si" else "conductor",
            "priority": level.mesh_order or 0,
            "geometry_kind": "domain" if region["material_id"] == "Si" else "layout_extrusion",
            "part_role": None,
            "net_id": None,
            "route_representations": {},
            "polygon_ids": entity_polygon_ids,
            "host_void_semantic_id": None if region["material_id"] == "Si" else host_id,
            "geometry": geometry,
            "metadata": metadata,
        }
        if region["material_id"] == "Si":
            (outer,) = loops
            geometry.update(
                z_min_um=low,
                z_max_um=high,
                domain_bounds_um=domain_bounds,
                outer_loop=outer["exterior"],
                hole_loops=outer["holes"],
            )
            solution_regions[entity_id] = {
                key: value for key, value in entity.items() if key != "semantic_id"
            }
        else:
            layers.append({**entity, "layer": region["layer"][0], "datatype": region["layer"][1]})
        entities.append(entity)
        occurrences.append(
            {
                "path": occurrence,
                "cell_name": child.name,
                "transform_um": [1, 0, 0, 1, tx, ty],
                "source_entity_ids": [entity_id],
            }
        )
    port_records = []
    for port in component.ports:
        record = {
            "name": port.name,
            "center_um": tuple(port.center),
            "width_um": port.width,
            "orientation_deg": port.orientation,
            "gds_layer": gf.get_layer_tuple(port.layer),
            "port_type": port.port_type,
            "source_local_level_id": f"{records['die']}_TOP_M1",
        }
        if port.port_type == "sim_junction_lumped":
            ref = component.insts["JUNCTION_LOCATOR"]
            sheet = gf.Component(base=ref.cell.base)
            sheet_points = sheet.get_polygons_points(by="tuple")[gf.get_layer_tuple(port.layer)][0]
            record.update(
                polygon_um=[
                    (float(x) + ref.dcplx_trans.disp.x, float(y) + ref.dcplx_trans.disp.y)
                    for x, y in sheet_points
                ],
                z_um=LAYER_STACK.layers[f"{records['die']}_TOP_SIM_BOUNDARY"].zmin,
                contact_normal=[0, 0, 1],
                directed_endpoints_um=[
                    (records["parameters"]["signal_size_um"][0] / 2, 0),
                    (
                        records["parameters"]["signal_size_um"][0] / 2
                        + records["parameters"]["gap_um"],
                        0,
                    ),
                ],
                meaning="nonmetal source locator; caller owns L/C and terminal assignment",
            )
        port_records.append(record)
    # Existing wall/landing contacts remain verbatim. Supporting-Si incidence
    # is newly authored source intent, not inferred/native continuity.
    die = records["die"]
    substrate = next(
        region for region in records["source_regions"] if region["body_id"] == f"{die}/SI"
    )
    source_owner_incidence = []
    for region in records["source_regions"]:
        for source_level_id, landing_face, substrate_face, endpoint in (
            (f"{die}_BOTTOM_M1", "upper", "lower", 0),
            (f"{die}_TOP_M1", "lower", "upper", 1),
        ):
            if region["level_id"] == source_level_id:
                source_owner_incidence.append(
                    {
                        "classification": "source_owner_intent_not_native_or_field_side_proof",
                        "entity_id": region["body_id"],
                        "entity_face": landing_face,
                        "supporting_entity_id": substrate["body_id"],
                        "supporting_face": substrate_face,
                        "source_plane_um": substrate["z_interval_um"][endpoint],
                        "host_void_entity_id": host_id,
                    }
                )
    contact_graph = {
        "classification": "source_owner_intent_in_one_selected_LayerStack_frame",
        "entity_aliases": entity_aliases,
        "source_contacts": deepcopy(records["contacts"]),
        "source_supports": deepcopy(port_records),
        "source_owner_incidence": source_owner_incidence,
    }
    for declaration in physical_layers.values():
        declaration["actual_entity_contact_graph"] = deepcopy(contact_graph)
    metadata = {
        "source_dbu_um": dbu,
        "top_cell_name": component.name,
        "cell_bounds_um": domain_bounds,
        "source_occurrences": occurrences,
        "boundary_representation": "explicit_actual_gds_polygon_witness",
        "authored_exact_circle_intent": records,
        "source_ports": port_records,
        "source_contacts": records["contacts"],
        "caller_owned": "final Nets, host solution region, solver settings and junction L/C",
        "native_mesh_solver": "unobserved",
    }
    return {
        "geometry_input": {
            "polygons": polygons,
            "entities": entities,
            "solution_regions": solution_regions,
            "metadata": deepcopy(metadata),
            "boundary_curves": [],
            "boundary_reconstruction": [],
        },
        "stack": deepcopy(
            {
                "layers": layers,
                "materials": get_material_records(),
                "solution_regions": solution_regions,
                "metadata": deepcopy(metadata),
            }
        ),
        "source_occurrences": occurrences,
    }
