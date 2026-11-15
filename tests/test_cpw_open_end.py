"""Tests for the shared CPW open-end termination helper."""

import gdsfactory as gf
import pytest

from orcapen_sc_pdk.helpers.layout import add_cpw_open_end
from orcapen_sc_pdk.pdk import PDK
from orcapen_sc_pdk.tech import CPW_ETCH_POS, CPW_GROUND_MASK


@pytest.mark.parametrize("orientation", [0, 90, 180, 270])
def test_open_end_takes_sizes_and_layers_from_cross_section(orientation: int) -> None:
    PDK.activate()
    xs = gf.get_cross_section("cpw_6_10_6")
    etch = xs[CPW_ETCH_POS]
    ground_mask = xs[CPW_GROUND_MASK]
    component = gf.Component()
    anchor = gf.Port(
        name="anchor",
        center=(0, 0),
        width=int(xs.width * 1000),
        orientation=orientation,
        layer=xs.layer,
        port_type="optical",
    )

    outer_port = add_cpw_open_end(component, anchor, xs)

    # Rotate the result back to orientation 0 so the sizes read as (length, width).
    probe = gf.Component()
    probe_ref = probe << component
    probe_ref.drotate(-orientation)
    etch_box = probe.dbbox(probe.kcl.layout.layer(*etch.layer))
    mask_box = probe.dbbox(probe.kcl.layout.layer(*ground_mask.layer))
    assert (etch_box.width(), etch_box.height()) == pytest.approx(
        (etch.width, xs.width + 2 * etch.width)
    )
    assert (mask_box.width(), mask_box.height()) == pytest.approx((etch.width, ground_mask.width))
    # Both rectangles start at the port and extend away from the CPW.
    assert etch_box.left == pytest.approx(0)
    assert mask_box.left == pytest.approx(0)
    assert float(outer_port.orientation) % 360 == orientation
    assert (outer_port.dcenter[0], outer_port.dcenter[1]) == pytest.approx(
        _rotate((etch.width, 0.0), orientation)
    )


def _rotate(point: tuple[float, float], degrees: int) -> tuple[float, float]:
    quarter_turns = (degrees // 90) % 4
    x, y = point
    for _ in range(quarter_turns):
        x, y = -y, x
    return (x, y)
