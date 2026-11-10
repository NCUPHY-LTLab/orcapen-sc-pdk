"""Flattened-geometry checks for the public disk flip-chip qubit."""

import math

import gdsfactory as gf
import pytest
from geometry_checks import MIN_EDGE_DBU, construction_report, interior_angles, polygon_defects
from kfactory import kdb

from orcapen_sc_pdk.pdk import PDK
from orcapen_sc_pdk.tech import LAYER

HANDOFF = 412.3141121612922
GROUND_INSTANCES = ("QGround", "CGround", "QGroundMask", "CGroundMask")


def _region(component, layer, instance=None):
    source = component
    if instance is not None:
        source = gf.Component()
        reference = component.insts[instance]
        source.add_ref(reference.cell).dcplx_trans = reference.dcplx_trans
    flat = source.copy()
    flat.flatten()
    return flat.get_region(layer, merge=True)


def _covers(region, radius, angle, offset=0.0) -> bool:
    """Whether a 2 nm probe at polar (radius, angle), shifted sideways, is inside."""
    theta = math.radians(angle)
    x = radius * math.cos(theta) - offset * math.sin(theta)
    y = radius * math.sin(theta) + offset * math.cos(theta)
    probe = gf.kdb.Region(
        gf.kdb.Box(round(x * 1e3) - 1, round(y * 1e3) - 1, round(x * 1e3) + 1, round(y * 1e3) + 1)
    )
    return (probe - region).is_empty()


@pytest.fixture(scope="module")
def grounded():
    PDK.activate()
    return PDK.get_component("disk_flip_chip_qubit")


@pytest.fixture(scope="module")
def floating():
    PDK.activate()
    return PDK.get_component("disk_flip_chip_qubit", tc_grounded_sides=())


def test_default_ports_sit_on_the_handoff_square(grounded) -> None:
    ports = {port.name: port for port in grounded.ports}
    assert list(ports) == ["tc_N", "tc_E", "tc_S", "tc_W", "ro_out", "xy_out", "o_junction_lumped"]
    for name, angle in (("tc_N", 90), ("tc_E", 0), ("tc_S", 270), ("tc_W", 180)):
        center = ports[name].dcenter
        assert math.hypot(*center) == pytest.approx(HANDOFF, abs=1e-3)
        assert ports[name].orientation == pytest.approx(angle)
        assert ports[name].dwidth == pytest.approx(3.0)
    assert tuple(ports["ro_out"].dcenter) == pytest.approx((-HANDOFF, HANDOFF), abs=1e-3)
    assert tuple(ports["xy_out"].dcenter) == pytest.approx((-HANDOFF, -HANDOFF), abs=1e-3)
    assert grounded.dbbox().width() == pytest.approx(1000.0)


def test_disk_radius_and_clearance_on_both_dies(grounded, floating) -> None:
    for component, radius in ((grounded, 110.5), (floating, 119.83949086316494)):
        disk = _region(component, LAYER.D1_BOTTOM_M1_DRAW, "QFace")
        for angle in (0, 90, 180):
            assert _covers(disk, radius - 0.2, angle)
            assert not _covers(disk, radius + 0.2, angle)
    for layer in (LAYER.D1_BOTTOM_GROUND_MASK, LAYER.D0_TOP_GROUND_MASK):
        mask = _region(grounded, layer)
        assert _covers(mask, 349.8, 45)
        assert not _covers(mask, 350.2, 45)
    q_ground = _region(grounded, LAYER.D1_BOTTOM_M1_DRAW, "QGround")
    assert _covers(q_ground, 350.2, 45)
    assert not _covers(q_ground, 349.8, 45)


def test_claw_gaps_widths_and_per_side_override() -> None:
    PDK.activate()
    component = PDK.get_component(
        "disk_flip_chip_qubit",
        tc_grounded_sides=(),
        disk_radius=110.0,
        tc_disk_gap_by_side=(("E", 40.0),),
        tc_landing_span=None,
    )
    draw = _region(component, LAYER.D1_BOTTOM_M1_DRAW)
    for side, angle in (("N", 90), ("E", 0), ("S", 270), ("W", 180)):
        gap = 40.0 if side == "E" else 60.0
        inner = 110.0 + gap
        # 15 degrees off axis clears the CPW lead and the rounded arc ends.
        probe = angle + 15
        assert not _covers(draw, 110.5, probe)
        assert not _covers(draw, inner - 0.5, probe)
        assert _covers(draw, inner + 0.5, probe)
        assert _covers(draw, inner + 59.5, probe)
        assert not _covers(draw, inner + 60.5, probe)
    assert component.info["tc_disk_gap_by_side_um"] == {"N": 60.0, "E": 40.0, "S": 60.0, "W": 60.0}


def test_junction_sits_at_its_overlap_radius(grounded) -> None:
    junction = _region(grounded, LAYER.D1_BOTTOM_JJ_DRAW)
    assert junction.count() == 1
    box = junction.bbox()
    center = 237.5 * math.cos(math.radians(315)), 237.5 * math.sin(math.radians(315))
    assert grounded.info["junction_center_um"] == pytest.approx(center)
    # The 5 um Manhattan arms reach about 4 um from the overlap point.
    assert abs(box.center().x / 1e3 - center[0]) < 5
    assert abs(box.center().y / 1e3 - center[1]) < 5
    # The ground-side lead is ground metal; the disk side lead is part of the disk.
    q_ground = _region(grounded, LAYER.D1_BOTTOM_M1_DRAW, "QGround")
    disk = _region(grounded, LAYER.D1_BOTTOM_M1_DRAW, "QFace")
    assert _covers(q_ground, 300.0, 315, offset=-4.0)
    assert _covers(disk, 180.0, 315)
    assert disk.interacting(q_ground).is_empty()


def test_bump_ring(grounded) -> None:
    names = grounded.info["bump_instance_names"]
    assert len(names) == 24
    for name in names:
        center = grounded.insts[name].dcplx_trans.disp
        assert math.hypot(center.x, center.y) == pytest.approx(400.0, abs=1e-3)
    assert _region(grounded, LAYER.D0_D1_INDIUM_BUMP).count() == 24
    for polygon in _region(grounded, LAYER.D0_D1_INDIUM_BUMP).each():
        assert (polygon.bbox().width(), polygon.bbox().height()) == (20_000, 20_000)


def test_readout_and_drive_tips(grounded) -> None:
    readout = _region(grounded, LAYER.D0_TOP_M1_DRAW, "RO")
    drive = _region(grounded, LAYER.D0_TOP_M1_DRAW, "XY")
    assert _covers(readout, 0.2, 135)
    assert not _covers(readout, 0.2, 315)
    assert _covers(drive, 412.2, 225)
    assert not _covers(drive, 411.8, 225)


def test_grounded_and_floating_claw_connectivity(grounded, floating) -> None:
    for component, is_grounded in ((grounded, True), (floating, False)):
        q_ground = _region(component, LAYER.D1_BOTTOM_M1_DRAW, "QGround")
        disk = _region(component, LAYER.D1_BOTTOM_M1_DRAW, "QFace")
        for side in "NESW":
            claw = _region(component, LAYER.D1_BOTTOM_M1_DRAW, f"TC_{side}")
            assert claw.interacting(q_ground).is_empty() is not is_grounded
            assert claw.interacting(disk).is_empty()


def test_disk_only_variant_and_separable_ground() -> None:
    PDK.activate()
    component = PDK.get_component("disk_flip_chip_qubit", include_tc=False)
    assert [port.name for port in component.ports] == ["ro_out", "xy_out", "o_junction_lumped"]
    assert not any(instance.name.startswith("TC_") for instance in component.insts)
    signals = component.copy()
    for name in GROUND_INSTANCES:
        signals.insts.remove(signals.insts[name])
    assert _region(signals, LAYER.D1_SUBSTRATE_AREA).is_empty()
    assert _region(signals, LAYER.D1_BOTTOM_GROUND_MASK).is_empty()
    d0 = _region(signals, LAYER.D0_TOP_M1_DRAW)
    assert d0.count() == 2
    assert _region(component, LAYER.D1_SUBSTRATE_AREA).area() == 1000 * 1000 * 1e6


def test_claws_are_grounded_per_side() -> None:
    PDK.activate()
    component = PDK.get_component(
        "disk_flip_chip_qubit", tc_grounded_sides=("N", "W"), disk_radius=115.0
    )
    q_ground = _region(component, LAYER.D1_BOTTOM_M1_DRAW, "QGround")
    for side in "NESW":
        claw = _region(component, LAYER.D1_BOTTOM_M1_DRAW, f"TC_{side}")
        assert claw.interacting(q_ground).is_empty() is (side not in "NW")
    assert component.info["grounded_tc_sides"] == ("N", "W")


def test_mixed_grounding_needs_an_explicit_disk_radius() -> None:
    PDK.activate()
    with pytest.raises(ValueError, match="explicit disk_radius"):
        PDK.get_component("disk_flip_chip_qubit", tc_grounded_sides=("N",))


def test_include_ground_false_keeps_only_the_masks() -> None:
    PDK.activate()
    component = PDK.get_component("disk_flip_chip_qubit", include_ground=False)
    names = {instance.name for instance in component.insts}
    assert {"QGroundMask", "CGroundMask"} <= names
    assert not {"QGround", "CGround"} & names
    assert _region(component, LAYER.D1_SUBSTRATE_AREA).is_empty()
    assert _region(component, LAYER.D0_SUBSTRATE_AREA).is_empty()
    assert not _covers(_region(component, LAYER.D1_BOTTOM_M1_DRAW), 425.0, 22.5)


def test_junction_lumped_port_sits_on_the_simulation_sheet(grounded) -> None:
    port = grounded.ports["o_junction_lumped"]
    sheet = _region(grounded, LAYER.D1_BOTTOM_SIM_BOUNDARY)
    assert sheet.count() == 1
    x, y = port.dcenter
    assert _covers(sheet, math.hypot(x, y), math.degrees(math.atan2(y, x)))
    # The sheet spans the two lead contacts, about 4 um from the overlap point.
    assert math.hypot(x - 167.938, y + 167.938) < 4.0


# Defaults and the corners of the supported range named in #53, at both curve
# samplings; junction angles off the diagonals need include_tc=False.
CONSTRUCTION_BUILDS = {
    "defaults": {},
    "include_ground=False": {"include_ground": False},
    "tc_grounded_sides=()": {"tc_grounded_sides": ()},
    "include_tc=False": {"include_tc": False},
    "tc_span=40": {"tc_span": 40.0},
    "tc_span=60": {"tc_span": 60.0},
    "tc_landing_span=None": {"tc_landing_span": None},
    "junction_lead_span=0": {"junction_lead_span": 0.0},
    "junction_angle=0": {"include_tc": False, "junction_angle": 0.0},
    "junction_angle=17.3": {"include_tc": False, "junction_angle": 17.3},
    "N, W grounded": {"tc_grounded_sides": ("N", "W"), "disk_radius": 115.0},
}


def _intended_holes(component, settings) -> dict[tuple[int, int], kdb.Region]:
    """The cut-outs drawn on purpose, in DBU: each die's ground opening.

    On D0 they are the clearance, which the readout line's mask joins, and the
    drive line's mask. On D1 the clearance and the claw masks form one opening;
    a grounded claw reaches into it from the ground. Signal conductors inside
    an opening are islands and do not change its outline.
    """
    if not settings.get("include_ground", True):
        return {}
    d1_opening = _region(component, LAYER.D1_BOTTOM_GROUND_MASK, "QGroundMask")
    for side in component.info["grounded_tc_sides"]:
        d1_opening -= _region(component, LAYER.D1_BOTTOM_M1_DRAW, f"TC_{side}")
    return {
        tuple(LAYER.D0_TOP_M1_DRAW): _region(component, LAYER.D0_TOP_GROUND_MASK, "CGroundMask"),
        tuple(LAYER.D1_BOTTOM_M1_DRAW): d1_opening.merged(),
    }


@pytest.mark.parametrize("sampling", ["fabrication", "simulation"])
@pytest.mark.parametrize("build", list(CONSTRUCTION_BUILDS))
def test_every_polygon_is_drawn_as_meant(build, sampling) -> None:
    """Construction checks (R8) on every flattened polygon and every merged layer."""
    PDK.activate()
    settings = CONSTRUCTION_BUILDS[build]
    component = PDK.get_component("disk_flip_chip_qubit", curve_sampling=sampling, **settings)
    intended = _intended_holes(component, settings)
    # D0: the clearance with the readout mask, and the drive mask. D1: one opening.
    counts = {tuple(LAYER.D0_TOP_M1_DRAW): 2, tuple(LAYER.D1_BOTTOM_M1_DRAW): 1}
    for layer, report in construction_report(component).items():
        assert not report.defects, (layer, report.defects[:5])
        assert report.min_edge_dbu >= MIN_EDGE_DBU, layer
        assert report.holes.count() == (counts[layer] if layer in intended else 0), layer
        assert (report.holes ^ intended.get(layer, kdb.Region())).is_empty(), layer
        # Reported only; the interior angle has no threshold yet.
        print(f"{build} [{sampling}] {layer}: min interior angle {report.min_angle_deg}°")


@pytest.mark.parametrize("sampling", ["fabrication", "simulation"])
def test_disk_and_grounds_are_each_one_valid_polygon(sampling) -> None:
    PDK.activate()
    component = PDK.get_component("disk_flip_chip_qubit", curve_sampling=sampling)
    for instance, layer in (
        ("QFace", LAYER.D1_BOTTOM_M1_DRAW),
        ("QGround", LAYER.D1_BOTTOM_M1_DRAW),
        ("CGround", LAYER.D0_TOP_M1_DRAW),
    ):
        region = _region(component, layer, instance)
        assert region.count() == 1, instance
        assert not polygon_defects(next(iter(region.each()))), instance


@pytest.mark.parametrize("sampling", ["fabrication", "simulation"])
def test_lead_fan_meets_the_disk_without_a_crack(sampling) -> None:
    """#47 C1: between the fan's sides the disk edge is metal, not a gap between samplings."""
    PDK.activate()
    component = PDK.get_component("disk_flip_chip_qubit", curve_sampling=sampling)
    disk = _region(component, LAYER.D1_BOTTOM_M1_DRAW, "QFace")
    # The default fan spans junction_angle ± 10° on the 110.5 µm disk; the
    # crack ran inside the disk circle, within the sagitta of its chords.
    for radius in (110.5, 110.4, 110.3, 110.2, 110.1, 110.0):
        for offset in (-9.5 + 0.5 * step for step in range(39)):
            assert _covers(disk, radius, 315 + offset), (radius, offset)


@pytest.mark.parametrize("sampling", ["fabrication", "simulation"])
def test_claws_are_rounded_once_with_a_square_lead_end(sampling) -> None:
    """#47 C4: no corner is added back after rounding; only the lead's end stays square."""
    PDK.activate()
    component = PDK.get_component(
        "disk_flip_chip_qubit", curve_sampling=sampling, tc_grounded_sides=()
    )
    for side in "NESW":
        (claw,) = _region(component, LAYER.D1_BOTTOM_M1_DRAW, f"TC_{side}").each()
        points = list(claw.each_point_hull())
        # A corner turning by more than 45° is one the rounding left sharp.
        sharp = [
            (point.x / 1e3, point.y / 1e3)
            for point, angle in zip(points, interior_angles(points), strict=True)
            if abs(angle - 180) > 45
        ]
        assert len(sharp) == 2, (side, sharp)
        assert all(math.hypot(*point) == pytest.approx(HANDOFF, abs=0.01) for point in sharp)


def _covers_point(region, point) -> bool:
    x, y = point
    return _covers(region, math.hypot(x, y), math.degrees(math.atan2(y, x)))


@pytest.mark.parametrize(
    ("settings", "contributors"),
    [
        ({}, ["QGround", "CGround"]),
        ({"tc_grounded_sides": ("N", "W"), "disk_radius": 115.0}, ["QGround", "CGround"]),
        ({"include_ground": False}, ["TC_N", "TC_E", "TC_S", "TC_W"]),
        ({"include_ground": False, "tc_grounded_sides": ()}, []),
    ],
)
def test_ground_contributions_use_the_scgsim_keys(settings, contributors) -> None:
    """Each entry selects ground metal on its own layer, in SCGSim's documented form."""
    PDK.activate()
    component = PDK.get_component("disk_flip_chip_qubit", **settings)
    entries = component.info["component_semantics"]["ground_plane_contributions"]
    assert [entry["local_id"] for entry in entries] == contributors
    for entry in entries:
        assert set(entry) == {"local_id", "plane_id", "level", "layer", "selector_point_um"}
        region = _region(component, tuple(entry["layer"]), entry["local_id"])
        assert _covers_point(region, entry["selector_point_um"]), entry["local_id"]


@pytest.mark.parametrize(
    ("settings", "message"),
    [
        # A floating claw past the clearance radius lands on the ground metal.
        (
            {
                "tc_grounded_sides": (),
                "tc_landing_span": None,
                "tc_disk_gap_by_side": (("E", 200.0),),
            },
            "claw E must stay inside the ground clearance",
        ),
        # Adjacent claws would close the room left for the diagonal leads.
        ({"tc_span": 61.0}, "tc_span must be at most 60 degrees"),
        # The grounding tail stays inside its own mask past the site edge.
        ({"handoff_half_extent": 480.0}, "mask end plus one CPW width must fit in the site"),
        # The disk lead runs through the grounded E claw.
        ({"junction_angle": 0.0}, r"junction and open lead angles must be 45° \+ k·90°"),
        # A bump lands on the readout, on a line the skip period no longer
        # clears, or reaches a claw lead with an oversized indium body.
        ({"ro_angle": 11.25}, "bump_01 overlaps the RO clearance"),
        ({"bump_lattice_count": 16}, "bump_06 overlaps the RO clearance"),
        ({"indium_bump_size": 70.0}, "bump_01 overlaps the TC_E clearance"),
        ({"indium_bump_size": 120.0}, "bump ring must lie outside the ground clearance"),
        # The two lead caps meet and join the disk to ground around the junction.
        ({"junction_lead_width": 6.0}, "junction_lead_width must be below the 5.657 µm"),
        # The round tip leaves no straight line before the handoff.
        ({"ro_tip_radius": 582.0}, "half the RO width inside the handoff square"),
        # A taper landing next to a claw's outer corner leaves no room for the
        # corner radius, on either side of the corner.
        ({"tc_landing_span": 44.99}, "tc_landing_span must equal tc_span or differ from it"),
        ({"tc_span": 43.0}, r"by at least 2\.486° \(claw N\)"),
    ],
)
def test_settings_outside_the_supported_scope_are_rejected(settings, message) -> None:
    PDK.activate()
    with pytest.raises(ValueError, match=message):
        PDK.get_component("disk_flip_chip_qubit", **settings)
