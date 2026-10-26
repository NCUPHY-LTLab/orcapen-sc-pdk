"""Repository-wide polygon sampling, resolved before GDSFactory cache lookup."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from inspect import Parameter, signature
from math import asin, ceil, isfinite, pi, sqrt

import gdsfactory as gf

# One edit point for shared project profiles. Counts are unique full-circle
# segments before Boolean/grid quantization; fourfold grids preserve axes.
FABRICATION = (256, None)
SIMULATION = (32, None)
PROFILES = {"fabrication": FABRICATION, "simulation": SIMULATION}
_current = ContextVar("orcapen_curve_sampling", default=FABRICATION)


def resolve_sampling(value=None) -> tuple[int, float | None]:
    """Resolve a profile name or (full-circle count, optional sagitta in um)."""
    if value is None:
        value = _current.get()
    if isinstance(value, str):
        value = PROFILES[value]
    count, error = value
    if isinstance(count, bool) or not isinstance(count, int) or count < 4 or count % 4:
        raise ValueError("full-circle count must be an integer multiple of four, at least four")
    if error is not None and (not isfinite(error) or error <= 0):
        raise ValueError("max sagitta must be a positive finite length in um")
    return count, None if error is None else float(error)


@contextmanager
def curve_sampling(profile="fabrication"):
    """Use one immutable sampling setting for this context and nested cells."""
    token = _current.set(resolve_sampling(profile))
    try:
        yield _current.get()
    finally:
        _current.reset(token)


def circle_segments(radius: float, sampling=None) -> int:
    """Full-circle count, optionally increased to meet a circular sagitta bound.

    Bound applies to an ideal inscribed circle before DBU snapping/Booleans,
    not to mesh accuracy, arbitrary curves or manufacturing qualification.
    """
    if not isfinite(radius) or radius <= 0:
        raise ValueError("radius must be positive and finite")
    count, error = resolve_sampling(sampling)
    if error is not None and error < radius:
        # Equivalent to acos(1-e/R), avoiding cancellation for small e/R.
        needed = ceil(pi / (2 * asin(sqrt(error / (2 * radius)))))
        count = max(count, 4 * ceil(needed / 4))
    return count


def arc_points(radius: float, angle: float, sampling=None) -> int:
    """Number of samples including both endpoints of a circular arc (degrees)."""
    if not isfinite(angle):
        raise ValueError("angle must be finite")
    return max(2, ceil(circle_segments(radius, sampling) * abs(angle) / 360) + 1)


def sampled_cell(function=None, **options):
    """PDK cell decorator with an explicit cache-key sampling parameter.

    Resolve context before gf.cell is called, not inside its cached body.
    Nested cells inherit the immutable tuple. No upstream monkeypatch or
    clear-cache operation is needed when switching profiles in one process.
    """

    def decorate(func):
        original = signature(func)
        if "curve_sampling" in original.parameters:
            raise TypeError("curve_sampling is reserved for the PDK sampling setting")
        params = list(original.parameters.values())
        extra = Parameter(
            "curve_sampling",
            Parameter.KEYWORD_ONLY,
            default=FABRICATION,
            annotation=tuple[int, float | None],
        )
        insertion = next(
            (i for i, p in enumerate(params) if p.kind == Parameter.VAR_KEYWORD), len(params)
        )
        params.insert(insertion, extra)

        @wraps(func)
        def construct(*args, **kwargs):
            selected = resolve_sampling(kwargs.pop("curve_sampling"))
            with curve_sampling(selected):
                result = func(*args, **kwargs)
            # Persist explicit source settings with the geometry, before locking.
            if result.locked:
                result = result.copy()
            result.info["curve_sampling"] = {
                "points_per_circle": selected[0],
                "max_sagitta_um": selected[1],
            }
            return result

        construct.__signature__ = original.replace(parameters=params)
        cached = gf.cell(construct, **options)

        @wraps(cached)
        def call(*args, **kwargs):
            kwargs["curve_sampling"] = resolve_sampling(kwargs.get("curve_sampling"))
            return cached(*args, **kwargs)

        return call

    return decorate(function) if function is not None else decorate


def circle(*, radius=10.0, layer, **kwargs):
    """GDSFactory circle with the central full-circle count in its cache key."""
    kwargs.setdefault("angle_resolution", 360 / circle_segments(radius))
    return gf.components.circle(radius=radius, layer=layer, **kwargs)


def ring(*, radius=10.0, width=0.5, layer):
    """Full ring with each radial boundary sampled by the same circle rule.

    With radius-aware sampling an inner circle may need fewer segments than
    the outer circle. Sampling each radius independently keeps a coincident
    disk boundary identical when it is authored with the same policy.
    """
    if width <= 0 or radius < width / 2:
        raise ValueError("positive ring width must fit its centerline radius")
    outer = circle(radius=radius + width / 2, layer=layer)
    if radius == width / 2:
        return outer
    inner = circle(radius=radius - width / 2, layer=layer)
    return gf.boolean(A=outer, B=inner, operation="not", layer=layer)


def arc(*, radius=10.0, angle=90.0, **kwargs):
    """Native GF arc with explicit endpoint-inclusive sampling."""
    if kwargs.get("npoints") is None and kwargs.get("angular_step") is None:
        kwargs["npoints"] = arc_points(radius, angle)
    return gf.path.arc(radius=radius, angle=angle, **kwargs)


def euler(*, radius=10.0, angle=90.0, **kwargs):
    """Native GF Euler path with an explicit central sampling budget."""
    if kwargs.get("npoints") is None and kwargs.get("angular_step") is None:
        kwargs["npoints"] = arc_points(radius, angle)
    return gf.path.euler(radius=radius, angle=angle, **kwargs)


def bend(*, euler=False, radius=None, angle=90.0, cross_section="cpw_6_7_6", **kwargs):
    """Native GF bend using centrally selected samples unless explicitly set.

    For Euler curves this is a sampling budget, not a circular-sagitta bound.
    GF retains the native bend algorithm, ports and floorplan behavior.
    """
    xs = gf.get_cross_section(cross_section)
    resolved_radius = radius if radius is not None else xs.radius
    if kwargs.get("npoints") is None and kwargs.get("angular_step") is None:
        kwargs["npoints"] = arc_points(resolved_radius, angle)
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


def bend_euler(**kwargs):
    return bend(euler=True, **kwargs)


def bend_circular(**kwargs):
    return bend(euler=False, **kwargs)
