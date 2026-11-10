"""Geometry checks for the drawing defects fixed in Issue #58.

A1: each IDC comb in the Purcell filter is one polygon whose fingers are drawn
at their requested on-grid length. A6: the airbridge chip's etch layer and
ground mask give the same metal.
"""

import gdsfactory as gf
import pytest

from orcapen_sc_pdk.pdk import PDK
from orcapen_sc_pdk.samples.simulation_demos import small_airbridge_chip
from orcapen_sc_pdk.tech import LAYER

PURCELL = "capacitive_coupling_intrinsic_individual_purcell_filter_readout_resonators"
DRAW = LAYER.D0_TOP_M1_DRAW


def _comb_polygons(idc: gf.Component) -> list:
    """Unmerged draw polygons of the IDC's comb child (tapers and extensions have 4 points)."""
    combs = []
    for instance in idc.insts:
        child = gf.Component(base=instance.cell.base)
        for polygons in child.get_polygons(layers=[DRAW], merge=False).values():
            combs.extend(polygon for polygon in polygons if polygon.num_points() > 4)
    return combs


def _purcell_idc(purcell: gf.Component) -> tuple[gf.Component, object]:
    (instance,) = [i for i in purcell.insts if i.cell.name.startswith("interdigital_capacitor")]
    return gf.Component(base=instance.cell.base), instance


@pytest.mark.parametrize("curve_sampling", ["fabrication", "simulation"])
def test_purcell_idc_fingers_connect_through_their_own_comb(curve_sampling: str) -> None:
    PDK.activate()
    purcell = gf.get_component(PURCELL, curve_sampling=curve_sampling)
    idc, instance = _purcell_idc(purcell)
    finger_length_dbu = round(purcell.info["idc_finger_length_um"] / purcell.kcl.dbu)

    combs = _comb_polygons(idc)
    assert len(combs) == 2  # one polygon per electrode, 10 fingers each
    for comb in combs:
        edges = [edge.length() for edge in comb.each_edge()]
        assert edges.count(finger_length_dbu) == 2 * 10  # both long sides of every finger

    # In place, each electrode with its taper and terminal is one polygon:
    # no finger is separated from its taper by a slit.
    idc_area = gf.kdb.Region(instance.dbbox().to_itype(purcell.kcl.dbu))
    assert (purcell.get_region(DRAW, merge=True) & idc_area).count() == 2


def test_purcell_rejects_an_off_grid_idc_finger_length() -> None:
    PDK.activate()
    with pytest.raises(ValueError, match="idc_finger_length"):
        gf.get_component(PURCELL, idc_finger_length=59.92476)


def test_airbridge_chip_etch_and_ground_mask_give_the_same_metal() -> None:
    PDK.activate()
    chip = small_airbridge_chip()
    draw = chip.get_region(DRAW, merge=True)
    etch = chip.get_region(LAYER.D0_TOP_M1_ETCH, merge=True)
    mask = chip.get_region(LAYER.D0_TOP_GROUND_MASK, merge=True)
    plane = gf.kdb.Region(chip.dbbox().to_itype(chip.kcl.dbu))

    metal_from_etch = plane - (etch - draw)  # PDK stack: domain - (ETCH - DRAW)
    metal_from_mask = (plane - mask) + draw  # SCGSim: plane - GROUND_MASK, plus the drawn traces
    assert (metal_from_etch ^ metal_from_mask).is_empty()
