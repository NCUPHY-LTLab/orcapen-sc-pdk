"""Tests for flip-chip coupon indium-bump placement."""

import gdsfactory as gf
import pytest

from orcapen_sc_pdk.cells.layout.disk_qubit import disk_flip_chip_qubit
from orcapen_sc_pdk.cells.layout.qubit import kosen2024_flip_chip_xmon_qubit
from orcapen_sc_pdk.helpers.assembly import (
    author_common_flip_chip_ground_planes,
    place_flip_chip_ground_short_bumps,
)
from orcapen_sc_pdk.pdk import PDK
from orcapen_sc_pdk.tech import LAYER


def _indium_polygon_count(component) -> int:
    region = component.get_region(LAYER.D0_D1_INDIUM_BUMP, merge=True)
    return int(region.count())


def _under_bump_centers(component) -> tuple[tuple[float, float], ...]:
    region = component.get_region(LAYER.D0_D1_UNDER_BUMP, merge=True)
    dbu = float(component.kcl.dbu)
    centers = []
    for polygon in region.each():
        box = polygon.bbox()
        centers.append(((box.left + box.right) * dbu / 2, (box.bottom + box.top) * dbu / 2))
    return tuple(centers)


def _assert_pitch_separation(centers: tuple[tuple[float, float], ...], pitch_um: float) -> None:
    for index, (x, y) in enumerate(centers):
        for ox, oy in centers[index + 1 :]:
            assert abs(x - ox) >= pitch_um - 1e-6 or abs(y - oy) >= pitch_um - 1e-6


def test_kosen_zero_argument_cell_keeps_the_preview_bump_ring() -> None:
    PDK.activate()
    component = kosen2024_flip_chip_xmon_qubit()

    assert component.info["bump_count"] == 16
    assert _indium_polygon_count(component) == 16


def test_kosen_bump_ring_count_zero_omits_cell_bumps() -> None:
    PDK.activate()
    component = kosen2024_flip_chip_xmon_qubit(bump_ring_count_per_side=0)

    assert component.info["bump_count"] == 0
    assert _indium_polygon_count(component) == 0


def test_kosen_bump_ring_count_rejects_odd_nonzero_values() -> None:
    with pytest.raises(ValueError, match="0 or an even integer"):
        kosen2024_flip_chip_xmon_qubit(bump_ring_count_per_side=1)


def test_place_flip_chip_ground_short_bumps_authors_kosen_corner_sites() -> None:
    PDK.activate()
    device = kosen2024_flip_chip_xmon_qubit(bump_ring_count_per_side=0)
    device_bbox = device.dbbox()
    coupon = place_flip_chip_ground_short_bumps(
        device,
        coupon_padding_um=150.0,
        clearance_um=30.0,
        placement_mode="corner_anchors",
    )

    wrapped = coupon.component
    wrapped_bbox = wrapped.dbbox()
    bump_count = _indium_polygon_count(wrapped)
    semantics = wrapped.info["component_semantics"]
    bump_records = [
        record
        for record in semantics["conductor_regions"]
        if record.get("semantic_id") == "D0_D1_INDIUM_BUMP"
    ]

    assert bump_count == 8
    assert coupon.placement_mode == "corner_anchors"
    _assert_pitch_separation(_under_bump_centers(wrapped), pitch_um=80.0)
    assert all(record["metadata"]["source_kind"] == "authored" for record in bump_records)
    assert coupon.stack_coupon_padding_um >= 0.0
    assert coupon.coupon_padding_um >= coupon.requested_coupon_padding_um
    assert abs(float(device_bbox.left)) < 1e4  # GDSFactory physical um, not DBU
    assert float(wrapped_bbox.left) < float(device_bbox.left)
    assert float(wrapped_bbox.right) > float(device_bbox.right)
    assert callable(coupon.plot)
    assert "o_junction_lumped" in wrapped.ports


def test_place_flip_chip_ground_short_bumps_grows_undersized_coupon() -> None:
    PDK.activate()
    device = kosen2024_flip_chip_xmon_qubit(bump_ring_count_per_side=0)
    coupon = place_flip_chip_ground_short_bumps(
        device,
        coupon_padding_um=20.0,
        clearance_um=30.0,
        placement_mode="corner_anchors",
    )

    assert coupon.requested_coupon_padding_um == pytest.approx(20.0)
    assert coupon.coupon_padding_um > coupon.requested_coupon_padding_um
    assert _indium_polygon_count(coupon.component) == 8
    _assert_pitch_separation(_under_bump_centers(coupon.component), pitch_um=80.0)
    assert coupon.stack_coupon_padding_um >= 0.0


def test_place_flip_chip_ground_short_bumps_full_field_authors_gds_lattice() -> None:
    PDK.activate()
    device = kosen2024_flip_chip_xmon_qubit(bump_ring_count_per_side=0)
    coupon = place_flip_chip_ground_short_bumps(
        device,
        coupon_padding_um=75.0,
        clearance_um=30.0,
        placement_mode="full_field",
    )

    bump_count = _indium_polygon_count(coupon.component)
    assert coupon.placement_mode == "full_field"
    assert bump_count > 8
    _assert_pitch_separation(_under_bump_centers(coupon.component), pitch_um=80.0)
    assert coupon.coupon_padding_um >= coupon.requested_coupon_padding_um
    assert coupon.stack_coupon_padding_um >= 0.0


def _single_site_assembly(**settings):
    PDK.activate()
    device = disk_flip_chip_qubit(include_ground=False, include_tc=False, **settings)
    parent = gf.Component()
    parent.add_ref(device, name="device")
    return parent


def test_common_ground_planes_refuse_a_mask_on_their_outline() -> None:
    # Without claws, the readout and drive masks set the site's bounding box.
    with pytest.raises(ValueError, match="D0_TOP_GROUND_MASK reaches the ground plane outline"):
        author_common_flip_chip_ground_planes(_single_site_assembly())


@pytest.mark.parametrize("lead_span", [20.0, 0.0])
def test_common_ground_planes_take_the_given_site_bounds(lead_span) -> None:
    parent = author_common_flip_chip_ground_planes(
        _single_site_assembly(junction_lead_span=lead_span),
        plane_bounds_um=(-500.0, -500.0, 500.0, 500.0),
    )
    site = gf.kdb.Region(gf.kdb.Box(-500_000, -500_000, 500_000, 500_000))
    for layer in (LAYER.D0_SUBSTRATE_AREA, LAYER.D1_SUBSTRATE_AREA):
        assert (parent.get_region(layer, merge=True) ^ site).is_empty()
    planes = parent.info["component_semantics"]["conductor_regions"]
    assert [plane["semantic_id"] for plane in planes] == [
        "D0_TOP_GROUND_PLANE",
        "D1_BOTTOM_GROUND_PLANE",
    ]


def test_common_ground_plane_bounds_must_hold_the_assembly() -> None:
    with pytest.raises(ValueError, match="must contain the whole assembly"):
        author_common_flip_chip_ground_planes(
            _single_site_assembly(), plane_bounds_um=(-400.0, -400.0, 400.0, 400.0)
        )
