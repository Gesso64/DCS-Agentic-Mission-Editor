"""Coordinate-sanity validator.

Reports waypoints / positions outside the theatre's bounding box.
"""

import math

from ..catalog import theatres
from ..errors import AssemblyReport


def check(spec, report: AssemblyReport) -> None:
    info = theatres.get_info(spec.theatre or "Caucasus")
    if info is None:
        report.warn(
            "UNKNOWN_THEATRE",
            f"Theatre '{spec.theatre}' not found in catalog",
        )
        return
    bounds = info.bounds
    # Width along each axis used for the 80% / 100% threshold.
    width = bounds.right - bounds.left
    height = bounds.top - bounds.bottom
    soft_margin_x = width * 0.1   # 80% boundary = bounds inset by 10%
    soft_margin_y = height * 0.1
    hard_margin = max(width, height) * 0.5  # treat anything > 1.5× bounds as definitely-broken

    for flight in spec.flights or []:
        for wp in flight.waypoints or []:
            _check_point(wp.x, wp.y, bounds, soft_margin_x, soft_margin_y, hard_margin,
                         f"Waypoint '{wp.name or '?'}' in flight '{flight.name}'",
                         flight.name, report)

    for vg in spec.vehicles or []:
        if vg.position:
            _check_point(vg.position.x, vg.position.y, bounds, soft_margin_x, soft_margin_y,
                         hard_margin, f"Vehicle group '{vg.name}'", vg.name, report)

    for sg in spec.ships or []:
        if sg.position:
            _check_point(sg.position.x, sg.position.y, bounds, soft_margin_x, soft_margin_y,
                         hard_margin, f"Ship group '{sg.name}'", sg.name, report)


def _check_point(x, y, bounds, sx, sy, hard_margin, label, ctx, report):
    inside_soft = (
        bounds.left + sx <= x <= bounds.right - sx
        and bounds.bottom + sy <= y <= bounds.top - sy
    )
    if inside_soft:
        return
    # Outside soft margin — is it just past 80% or truly off-map?
    way_off = (
        x < bounds.left - hard_margin
        or x > bounds.right + hard_margin
        or y < bounds.bottom - hard_margin
        or y > bounds.top + hard_margin
    )
    if way_off:
        report.error(
            "COORD_OUT_OF_BOUNDS",
            f"{label} ({x:.0f}, {y:.0f}) is far outside theatre bounds "
            f"[{bounds.left:.0f}…{bounds.right:.0f}, {bounds.bottom:.0f}…{bounds.top:.0f}]",
            context=ctx,
            hint="Likely an x/y swap or unit-confusion bug",
        )
    else:
        report.warn(
            "COORD_NEAR_BOUNDS",
            f"{label} ({x:.0f}, {y:.0f}) is within 20% of the theatre edge",
            context=ctx,
        )
