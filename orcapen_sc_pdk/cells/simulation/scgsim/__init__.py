"""OrcaPen-owned source geometry and detached records for SCGSim examples.

These factories and getters do not configure or launch a solver; callers own
runtime settings and final electrical Nets.
"""

from orcapen_sc_pdk.cells.simulation.scgsim.cpw_coupons import (
    cpw_meander_airbridge_lumped_coupon,
    cpw_meander_airbridge_wave_coupon,
    finite_ground_cpw_coupon,
    get_cpw_meander_airbridge_source_records,
)
from orcapen_sc_pdk.cells.simulation.scgsim.simple_pad import (
    circular_pad_capacitor,
    square_pad_capacitor,
    straight_to_circular_strip,
)
from orcapen_sc_pdk.cells.simulation.scgsim.spline_strip import (
    bspline_strip,
    interpolation_spline_strip,
)
from orcapen_sc_pdk.cells.simulation.scgsim.test_components import (
    cpw_airbridge_coupon,
    flip_chip_pad_coupon,
)
from orcapen_sc_pdk.cells.simulation.scgsim.tsv import (
    get_tsv_source_records,
    tsv_concentric_signal_coupon,
    tsv_ground_stitched_cpw,
)

__all__ = [
    "bspline_strip",
    "circular_pad_capacitor",
    "cpw_airbridge_coupon",
    "cpw_meander_airbridge_lumped_coupon",
    "cpw_meander_airbridge_wave_coupon",
    "finite_ground_cpw_coupon",
    "flip_chip_pad_coupon",
    "get_cpw_meander_airbridge_source_records",
    "get_tsv_source_records",
    "interpolation_spline_strip",
    "square_pad_capacitor",
    "straight_to_circular_strip",
    "tsv_concentric_signal_coupon",
    "tsv_ground_stitched_cpw",
]
