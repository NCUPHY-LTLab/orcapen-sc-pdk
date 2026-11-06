"""Dicing-edge keepout ring used by chip-level assemblies."""

import gdsfactory as gf

import orcapen_sc_pdk.curve_sampling as curves
from orcapen_sc_pdk.tech import LAYER


@gf.cell(tags=["layout", "dicing"])
def dicing_edge(
    size: tuple[float, float] = (10000.0, 10000.0),
    width: float = 50.0,
    layer: tuple[int, int] = LAYER.D0_TOP_M1_ETCH,
    curve_sampling: curves.CurveSampling = curves.FABRICATION,
) -> gf.Component:
    """Return a rectangular edge ring on the requested layer.

    The ring is authored as outer minus inner rectangles so chip assemblies can
    place it on an ETCH or marker layer without inventing another edge helper.
    """

    sx, sy = size

    outer_size = (sx + 2 * width, sy + 2 * width)
    outer = gf.components.rectangle(size=outer_size, layer=layer, centered=True)
    inner = gf.components.rectangle(size=size, layer=layer, centered=True)

    ring = gf.boolean(
        A=outer,
        B=inner,
        operation="A-B",
        layer=layer,
    )

    curves.record_sampling(ring, curve_sampling)
    return ring


if __name__ == "__main__":
    # Imported here because orcapen_sc_pdk.pdk imports this module.
    from orcapen_sc_pdk.preview import show

    show(dicing_edge)
