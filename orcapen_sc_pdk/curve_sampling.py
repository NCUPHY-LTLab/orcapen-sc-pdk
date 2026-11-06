"""Repository-wide polygon sampling, passed to every cell as an explicit parameter.

Each PDK cell takes `curve_sampling` and passes it on to nested cells and to the
curve helpers here. Being an ordinary parameter, it is part of the GDSFactory
cache key and visible to GDSFactory+, which only discovers plain `@gf.cell`
factories.
"""

from __future__ import annotations

from inspect import signature
from math import asin, ceil, isfinite, pi, sqrt
from typing import Literal

import gdsfactory as gf

# One edit point for shared project profiles. Counts are unique full-circle
# segments before Boolean/grid quantization; fourfold grids preserve axes.
FABRICATION = (256, None)
type Sampling = tuple[int | Literal["diameter"], float | None]
# A profile name or an explicit (full-circle count, optional max sagitta in um).
type CurveSampling = Sampling | Literal["fabrication", "simulation"]
# 此直徑分級是否適合模擬尚待驗證；依 Human 肉眼判斷，預期不致對網格生成（meshing）造成過多負擔。
SIMULATION = ("diameter", None)
PROFILES = {"fabrication": FABRICATION, "simulation": SIMULATION}
DIAMETER_TIERS_UM = [
    {"below": 20, "points": 16},
    {"below": 100, "points": 24},
    {"below": None, "points": 32},
]


def resolve_sampling(value: CurveSampling) -> Sampling:
    """Resolve a profile name or (full-circle count, optional sagitta in um)."""
    if isinstance(value, str):
        value = PROFILES[value]
    count, error = value
    if count != "diameter" and (
        isinstance(count, bool) or not isinstance(count, int) or count < 4 or count % 4
    ):
        raise ValueError("full-circle count must be an integer multiple of four, at least four")
    if error is not None and (not isfinite(error) or error <= 0):
        raise ValueError("max sagitta must be a positive finite length in um")
    return count, None if error is None else float(error)


def record_sampling(component: gf.Component, sampling: CurveSampling) -> None:
    """Persist the source sampling setting with the geometry it produced."""
    count, error = resolve_sampling(sampling)
    component.info["curve_sampling"] = {
        "points_per_circle": None if count == "diameter" else count,
        "max_sagitta_um": error,
    }
    if count == "diameter":
        component.info["curve_sampling"]["diameter_tiers_um"] = [
            dict(tier) for tier in DIAMETER_TIERS_UM
        ]


def sampling_settings(spec, sampling: CurveSampling) -> dict[str, CurveSampling]:
    """Settings that pass `sampling` on to a component spec that accepts it.

    PDK cells, by name or factory, take `curve_sampling`. External factories,
    dict specs and prebuilt components keep their own sampling.
    """
    factory = gf.get_active_pdk().cells.get(spec) if isinstance(spec, str) else spec
    if callable(factory) and "curve_sampling" in signature(factory).parameters:
        return {"curve_sampling": sampling}
    return {}


def circle_segments(radius: float, sampling: CurveSampling) -> int:
    """Full-circle count, optionally increased to meet a circular sagitta bound.

    Bound applies to an ideal inscribed circle before DBU snapping/Booleans,
    not to mesh accuracy, arbitrary curves or manufacturing qualification.
    """
    if not isfinite(radius) or radius <= 0:
        raise ValueError("radius must be positive and finite")
    count, error = resolve_sampling(sampling)
    if count == "diameter":
        diameter = 2 * radius
        count = 16 if diameter < 20 else 24 if diameter < 100 else 32
    if error is not None and error < radius:
        # Equivalent to acos(1-e/R), avoiding cancellation for small e/R.
        needed = ceil(pi / (2 * asin(sqrt(error / (2 * radius)))))
        count = max(count, 4 * ceil(needed / 4))
    return count


def arc_points(radius: float, angle: float, sampling: CurveSampling) -> int:
    """Number of samples including both endpoints of a circular arc (degrees)."""
    if not isfinite(angle):
        raise ValueError("angle must be finite")
    return max(2, ceil(circle_segments(radius, sampling) * abs(angle) / 360) + 1)


def circle(*, radius=10.0, layer, sampling: CurveSampling, **kwargs):
    """GDSFactory circle with the selected full-circle count in its cache key."""
    kwargs.setdefault("angle_resolution", 360 / circle_segments(radius, sampling))
    return gf.components.circle(radius=radius, layer=layer, **kwargs)


def ring(*, radius=10.0, width=0.5, layer, sampling: CurveSampling):
    """Full ring with each radial boundary sampled by the same circle rule.

    With radius-aware sampling an inner circle may need fewer segments than
    the outer circle. Sampling each radius independently keeps a coincident
    disk boundary identical when it is authored with the same policy.
    """
    if width <= 0 or radius < width / 2:
        raise ValueError("positive ring width must fit its centerline radius")
    outer = circle(radius=radius + width / 2, layer=layer, sampling=sampling)
    if radius == width / 2:
        return outer
    inner = circle(radius=radius - width / 2, layer=layer, sampling=sampling)
    return gf.boolean(A=outer, B=inner, operation="not", layer=layer)


def arc(*, radius=10.0, angle=90.0, sampling: CurveSampling, **kwargs):
    """Native GF arc with explicit endpoint-inclusive sampling."""
    if kwargs.get("npoints") is None and kwargs.get("angular_step") is None:
        kwargs["npoints"] = arc_points(radius, angle, sampling)
    return gf.path.arc(radius=radius, angle=angle, **kwargs)


def euler(*, radius=10.0, angle=90.0, sampling: CurveSampling, **kwargs):
    """Native GF Euler path with an explicit sampling budget."""
    if kwargs.get("npoints") is None and kwargs.get("angular_step") is None:
        kwargs["npoints"] = arc_points(radius, angle, sampling)
    return gf.path.euler(radius=radius, angle=angle, **kwargs)


def bend(
    *,
    sampling: CurveSampling,
    euler=False,
    radius=None,
    angle=90.0,
    cross_section="cpw_6_7_6",
    **kwargs,
):
    """Native GF bend using the selected samples unless explicitly set.

    For Euler curves this is a sampling budget, not a circular-sagitta bound.
    GF retains the native bend algorithm, ports and floorplan behavior.
    """
    xs = gf.get_cross_section(cross_section)
    resolved_radius = radius if radius is not None else xs.radius
    if kwargs.get("npoints") is None and kwargs.get("angular_step") is None:
        kwargs["npoints"] = arc_points(resolved_radius, angle, sampling)
    factory = gf.components.bend_euler if euler else gf.components.bend_circular
    result = factory(radius=radius, angle=angle, cross_section=cross_section, **kwargs)
    # Native length is a polygonal arclength and changes with sample count.
    # Keep it, but give length-constrained PDK assemblies an analytic design
    # length so selecting a different polygon budget does not move ports.
    design_radius = resolved_radius
    if euler:
        path = gf.path.euler(
            radius=resolved_radius,
            angle=angle,
            p=kwargs.get("p", 0.5),
            use_eff=kwargs.get("with_arc_floorplan", True),
            npoints=kwargs.get("npoints"),
            angular_step=kwargs.get("angular_step"),
        )
        design_radius = path.info["Rmin"]
    factor = 1 + kwargs.get("p", 0.5) if euler else 1
    result = result.copy()
    result.info["design_length_um"] = factor * abs(angle) * pi / 180 * design_radius
    return result


def design_length(component) -> float:
    """PDK analytic design length; external custom bends retain their contract."""
    if "design_length_um" in component.info:
        return float(component.info["design_length_um"])
    return float(component.info["length"])


def bend_euler(*, sampling: CurveSampling, **kwargs):
    """Euler bend sampled by `sampling`; see `bend`."""
    return bend(euler=True, sampling=sampling, **kwargs)


def bend_circular(*, sampling: CurveSampling, **kwargs):
    """Circular bend sampled by `sampling`; see `bend`."""
    return bend(euler=False, sampling=sampling, **kwargs)
