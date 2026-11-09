"""Direct diagnostics for the central curve-sampling contract."""

import inspect
import math

import pytest

import orcapen_sc_pdk as pdk
from orcapen_sc_pdk import curve_sampling as curves


def port_records(component):
    return [
        (
            port.name,
            tuple(port.dcenter),
            port.dwidth,
            port.orientation,
            (port.layer_info.layer, port.layer_info.datatype),
            port.port_type,
        )
        for port in component.ports
    ]


def test_every_cell_takes_an_explicit_sampling_parameter():
    # GDSFactory+ only discovers plain @gf.cell factories, so sampling must be
    # an ordinary parameter rather than one injected by a custom decorator.
    for name, factory in pdk.get_pdk().cells.items():
        parameter = inspect.signature(factory).parameters.get("curve_sampling")
        assert parameter is not None, name
        assert parameter.default == curves.FABRICATION, name


def test_cache_selection_and_nested_policy():
    pdk.activate()
    name = "kosen2024_flip_chip_xmon_qubit"
    first = pdk.get_pdk().get_component(name, curve_sampling="simulation")
    second = pdk.get_pdk().get_component(name, curve_sampling="fabrication")
    again = pdk.get_pdk().get_component(name, curve_sampling="simulation")
    assert first.cell_index() == again.cell_index() != second.cell_index()
    assert port_records(first) == port_records(second)
    assert first.kcl.dbu == second.kcl.dbu == 0.001
    assert first.info["curve_sampling"]["points_per_circle"] is None
    assert first.info["curve_sampling"]["diameter_tiers_um"][0]["points"] == 16


def test_circle_count_and_radius_rule():
    pdk.activate()
    layer = pdk.LAYER.D0_TOP_M1_DRAW
    for count in (32, 256):
        circle = curves.circle(radius=350, layer=layer, sampling=(count, None))
        points = circle.get_polygons_points(by="tuple")[(1, 0)][0]
        assert len(points) == count
    count = curves.circle_segments(350, (32, 0.05))
    assert count % 4 == 0
    assert 350 * (1 - math.cos(math.pi / count)) <= 0.05
    assert curves.arc_points(350, 90, (32, None)) == 9


@pytest.mark.parametrize(
    "name",
    [
        "circular_pad_capacitor",
        "rounded_end_metal_segment",
        "rounded_rectangle",
        "bend_circular",
        "bend_euler",
        "resonator",
        "resonator_hanger",
        "resonator_meander",
        "interdigital_capacitor",
        "mtl_bend_coupling_section",
        "capacitive_coupling_intrinsic_individual_purcell_filter_readout_resonators",
    ],
)
def test_profile_preserves_ports(name):
    pdk.activate()
    coarse = pdk.get_pdk().get_component(name, curve_sampling=(32, None))
    fine = pdk.get_pdk().get_component(name, curve_sampling=(256, None))
    assert port_records(coarse) == port_records(fine)


def test_explicit_sampling_is_resolved_and_recorded():
    pdk.activate()
    assert curves.resolve_sampling("simulation") == ("diameter", None)
    assert curves.resolve_sampling("fabrication") == curves.FABRICATION
    cell = pdk.get_pdk().get_component("circular_pad_capacitor", curve_sampling=(64, None))
    assert cell.info["curve_sampling"]["points_per_circle"] == 64


def test_shared_radial_boundary():
    pdk.activate()
    layer = pdk.LAYER.D0_TOP_M1_DRAW
    sampling = (32, 0.05)
    disk = curves.circle(radius=100, layer=layer, sampling=sampling)
    annulus = curves.ring(radius=110, width=20, layer=layer, sampling=sampling)
    outer = curves.circle(radius=120, layer=layer, sampling=sampling)
    combined = disk.get_region(layer) + annulus.get_region(layer)
    assert (combined ^ outer.get_region(layer)).is_empty()
    assert (disk.get_region(layer) & annulus.get_region(layer)).is_empty()


@pytest.mark.parametrize(
    "diameter,count", [(4, 16), (19.999, 16), (20, 24), (99.999, 24), (100, 32), (700, 32)]
)
def test_simulation_diameter_tiers(diameter, count):
    assert curves.circle_segments(diameter / 2, "simulation") == count
    assert curves.circle_segments(diameter / 2, "fabrication") == 256


def test_rounded_end_independent_boundary_tiers():
    pdk.activate()
    cell = pdk.get_pdk().get_component(
        "rounded_end_metal_segment",
        length=40,
        width=6,
        ground_mask_margin=7,
        curve_sampling="simulation",
    )
    polygons = cell.get_polygons_points(by="tuple")
    metal = polygons[(1, 0)][0]
    mask = polygons[(110, 0)][0]
    # Include both endpoints of each semicircle, exclude the left cut plane.
    assert sum(x >= 37 for x, y in metal) == 9
    assert sum(x >= 37 for x, y in mask) == 13
    fixed = pdk.get_pdk().get_component(
        "rounded_end_metal_segment",
        length=40,
        width=6,
        ground_mask_margin=7,
        n_cap_points=5,
        curve_sampling="simulation",
    )
    assert len(fixed.get_polygons_points(by="tuple")[(1, 0)][0]) == 11


def test_bend_factory_spec_receives_the_cell_sampling():
    pdk.activate()
    layer = pdk.LAYER.D0_TOP_M1_DRAW
    bend_euler = pdk.get_pdk().cells["bend_euler"]

    def metal(bend_spec, curve_sampling):
        cell = pdk.get_pdk().get_component(
            "resonator_meander", bend_spec=bend_spec, curve_sampling=curve_sampling
        )
        return cell.get_region(layer)

    by_name = metal("bend_euler", "simulation")
    assert (by_name ^ metal(bend_euler, "simulation")).is_empty()
    assert not (by_name ^ metal(bend_euler, "fabrication")).is_empty()
