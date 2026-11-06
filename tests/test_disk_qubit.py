"""Geometry checks for the public flip-chip disk transmon cell."""

from math import cos, hypot, radians, sin

import gdsfactory as gf
import pytest
from gdsfactory import kdb

from orcapen_sc_pdk.cells.layout.disk_qubit import disk_flip_chip_qubit
from orcapen_sc_pdk.pdk import PDK
from orcapen_sc_pdk.tech import LAYER

SIDE_ANGLES = {"N": 90.0, "E": 0.0, "S": 270.0, "W": 180.0}
FLOATING = {"grounded_tc_sides": (), "disk_radius": 119.839}


@pytest.fixture(autouse=True)
def _active_pdk() -> None:
    PDK.activate()


def polar(radius: float, angle_deg: float) -> tuple[float, float]:
    return radius * cos(radians(angle_deg)), radius * sin(radians(angle_deg))


def is_metal(component: gf.Component, layer, point: tuple[float, float]) -> bool:
    """Whether the merged layer covers a 2 nm box centred on ``point`` (um)."""

    dbu = component.kcl.dbu
    x, y = (round(value / dbu) for value in point)
    probe = kdb.Region(kdb.Box(x - 1, y - 1, x + 1, y + 1))
    return (component.get_region(layer, merge=True) & probe).area() == probe.area()


def same_polygon(component: gf.Component, layer, first, second) -> bool:
    """Whether two points lie on one merged polygon of ``layer``."""

    dbu = component.kcl.dbu
    for polygon in component.get_region(layer, merge=True).each():
        hits = [
            polygon.inside(kdb.Point(round(x / dbu), round(y / dbu))) for x, y in (first, second)
        ]
        if any(hits):
            return all(hits)
    return False


def test_zero_argument_cell_builds_by_name_with_its_ports() -> None:
    component = gf.get_component("disk_flip_chip_qubit")

    assert {port.name for port in component.ports} == {
        "tc_N",
        "tc_E",
        "tc_S",
        "tc_W",
        "readout",
        "drive",
        "o_junction_lumped",
    }
    for side, angle in SIDE_ANGLES.items():
        port = component.ports[f"tc_{side}"]
        assert port.dcenter == pytest.approx(polar(412.3141121612922, angle), abs=1e-3)
        assert port.orientation == pytest.approx(angle)
    assert component.ports["readout"].dcenter == pytest.approx((-412.314, 412.314), abs=1e-3)
    assert component.ports["drive"].dcenter == pytest.approx((-412.314, -412.314), abs=1e-3)


def test_disk_and_clearance_match_the_preset() -> None:
    component = disk_flip_chip_qubit()

    # 45 deg lies between two claws and away from the junction, readout and drive.
    assert is_metal(component, LAYER.D1_BOTTOM_M1_DRAW, polar(110.0, 45))
    assert not is_metal(component, LAYER.D1_BOTTOM_M1_DRAW, polar(111.0, 45))
    for draw in (LAYER.D1_BOTTOM_M1_DRAW, LAYER.D0_TOP_M1_DRAW):
        assert not is_metal(component, draw, polar(349.5, 45))
        assert is_metal(component, draw, polar(350.5, 45))


@pytest.mark.parametrize("side", SIDE_ANGLES)
def test_each_claw_keeps_its_gap_width_and_span(side: str) -> None:
    component = disk_flip_chip_qubit(**FLOATING)
    draw = LAYER.D1_BOTTOM_M1_DRAW
    axis = SIDE_ANGLES[side]
    inner, outer = 119.839 + 60.0, 119.839 + 120.0

    for offset in (-22.4, 22.4):
        angle = axis + offset
        assert not is_metal(component, draw, polar(inner - 0.5, angle))
        assert is_metal(component, draw, polar(inner + 0.5, angle))
        assert is_metal(component, draw, polar(outer - 0.5, angle))
        assert not is_metal(component, draw, polar(outer + 0.5, angle))
    # Just outside the 45 deg span the claw has no metal at all.
    for radius in (inner + 1, (inner + outer) / 2, outer - 1):
        assert not is_metal(component, draw, polar(radius, axis + 23.0))


def test_claw_gap_can_be_overridden_per_side() -> None:
    component = disk_flip_chip_qubit(tc_disk_gap_by_side=(("N", 40.0),))
    draw = LAYER.D1_BOTTOM_M1_DRAW

    assert is_metal(component, draw, polar(110.5 + 40.5, 90 + 22.4))
    assert not is_metal(component, draw, polar(110.5 + 40.5, 0 + 22.4))
    assert component.info["tc_disk_gap_by_side_um"] == {"N": 40.0, "E": 60.0, "S": 60.0, "W": 60.0}


def test_grounded_claws_join_ground_and_floating_claws_do_not() -> None:
    draw = LAYER.D1_BOTTOM_M1_DRAW
    ground_point = polar(425.0, 22.5)

    grounded = disk_flip_chip_qubit()
    floating = disk_flip_chip_qubit(**FLOATING)

    for side, axis in SIDE_ANGLES.items():
        assert same_polygon(grounded, draw, polar(200.0, axis), ground_point), side
        assert not same_polygon(floating, draw, polar(210.0, axis), ground_point), side
    # A floating claw's CPW stops at the handoff; the 40 um open end is etched.
    assert is_metal(floating, draw, polar(412.0, 0))
    assert not is_metal(floating, draw, polar(430.0, 0))
    assert is_metal(grounded, draw, polar(430.0, 0))


def test_junction_sits_at_its_overlap_radius_with_both_leads_attached() -> None:
    component = disk_flip_chip_qubit()
    draw = LAYER.D1_BOTTOM_M1_DRAW
    overlap = polar(237.5, 315)

    assert is_metal(component, LAYER.D1_BOTTOM_JJ_DRAW, overlap)
    assert component.info["junction_overlap_center_um"] == pytest.approx(overlap)
    # The disk-side lead joins the disk, the ground-side lead joins ground.
    assert same_polygon(component, draw, polar(200.0, 315), (0.0, 0.0))
    assert same_polygon(component, draw, polar(300.0, 315), polar(425.0, 22.5))
    assert not same_polygon(component, draw, (0.0, 0.0), polar(425.0, 22.5))


def test_bump_ring_has_24_bumps_on_radius_400() -> None:
    component = disk_flip_chip_qubit()
    dbu = component.kcl.dbu
    centers = [
        (polygon.bbox().center().x * dbu, polygon.bbox().center().y * dbu)
        for polygon in component.get_region(LAYER.D0_D1_INDIUM_BUMP, merge=True).each()
    ]

    assert len(centers) == component.info["bump_count"] == 24
    assert all(hypot(x, y) == pytest.approx(400.0, abs=1e-3) for x, y in centers)
    # Every 4th lattice site is left free: the claw, diagonal and junction directions.
    assert not any(
        hypot(x - bx, y - by) < 1.0
        for bx, by in (polar(400.0, angle) for angle in range(0, 360, 45))
        for x, y in centers
    )


def test_readout_reaches_the_disk_centre_and_drive_stops_at_its_tip() -> None:
    component = disk_flip_chip_qubit()
    draw = LAYER.D0_TOP_M1_DRAW

    assert is_metal(component, draw, polar(0.3, 135))
    assert not is_metal(component, draw, polar(0.3, 315))
    assert is_metal(component, draw, polar(412.5, 225))
    assert not is_metal(component, draw, polar(411.5, 225))
    assert not same_polygon(component, draw, polar(500.0, 225), polar(425.0, 22.5))


def test_disk_only_variant_has_no_claws() -> None:
    component = disk_flip_chip_qubit(include_tc=False)

    assert not any(port.name.startswith("tc_") for port in component.ports)
    assert not is_metal(component, LAYER.D1_BOTTOM_M1_DRAW, polar(200.0, 0))


def test_ground_can_be_left_to_the_parent() -> None:
    component = disk_flip_chip_qubit(include_ground=False)

    assert component.get_region(LAYER.D1_SUBSTRATE_AREA).is_empty()
    assert component.get_region(LAYER.D0_SUBSTRATE_AREA).is_empty()
    assert not is_metal(component, LAYER.D1_BOTTOM_M1_DRAW, polar(425.0, 22.5))
    assert is_metal(component, LAYER.D1_BOTTOM_GROUND_MASK, polar(349.0, 45))
    semantic_ids = {
        row["semantic_id"] for row in component.info["component_semantics"]["conductor_regions"]
    }
    assert "D1_GROUND" not in semantic_ids


def test_claw_lead_switches_to_its_own_cpw_section() -> None:
    component = disk_flip_chip_qubit(
        tc_lead_start_radius=360.0, tc_lead_width=10.0, tc_lead_gap=6.0, tc_end_clearance=6.0
    )
    draw = LAYER.D1_BOTTOM_M1_DRAW

    assert component.ports["tc_E"].width == pytest.approx(10.0)
    assert is_metal(component, draw, (380.0, 4.5))
    assert not is_metal(component, draw, (380.0, 8.0))
    assert is_metal(component, draw, (380.0, 12.0))


def test_claw_that_leaves_the_clearance_is_rejected() -> None:
    with pytest.raises(ValueError, match="TC_N must end inside the ground clearance"):
        disk_flip_chip_qubit(tc_disk_gap_by_side=(("N", 200.0),))
