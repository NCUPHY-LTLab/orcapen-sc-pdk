"""Geometry added at the ports of a CPW (coplanar waveguide) component."""

import gdsfactory as gf

from orcapen_sc_pdk.tech import CPW_ETCH_POS, CPW_GROUND_MASK


def add_cpw_open_end(
    component: gf.Component,
    port: gf.Port,
    cross_section: gf.CrossSection,
) -> gf.Port:
    """Add the open-circuit termination of a CPW port and return its outer port.

    The termination is a rectangle on the ETCH layer, ``etch_width`` long and
    ``cpw_width + 2 * etch_width`` wide, so the etch wraps the end of the center
    conductor. A second rectangle on the GROUND_MASK layer, ``etch_width`` long
    and ``ground_mask_width`` wide, closes the ground mask over it. Widths and
    layers come from ``cross_section``; both rectangles are centered on ``port``.

    The returned port faces away from the CPW. The caller names it and adds it
    to ``component`` (or reads its position) as it needs.
    """

    etch_section = cross_section[CPW_ETCH_POS]
    ground_mask_section = cross_section[CPW_GROUND_MASK]

    etch_rectangle = gf.components.rectangle(
        size=(etch_section.width, 2 * etch_section.width + cross_section.width),
        layer=etch_section.layer,
        centered=True,
        port_type="optical",
        port_orientations=(0, 180),
    )
    ground_mask_rectangle = gf.components.rectangle(
        size=(etch_section.width, ground_mask_section.width),
        layer=ground_mask_section.layer,
        centered=True,
        port_type="optical",
        port_orientations=(0, 180),
    )

    etch_ref = component << etch_rectangle
    ground_mask_ref = component << ground_mask_rectangle
    # The CPW width differs from the rectangle's port width, and the rectangle
    # layers differ from the CPW's, so both mismatches are intended.
    for ref in (etch_ref, ground_mask_ref):
        ref.connect("o1", port, allow_width_mismatch=True, allow_layer_mismatch=True)

    return etch_ref.ports["o2"]
