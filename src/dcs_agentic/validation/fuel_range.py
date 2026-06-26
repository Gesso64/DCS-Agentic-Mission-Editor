"""Fuel-range validator.

Estimates total mission distance from waypoints (Euclidean) and compares
against the aircraft's `combat_radius_km`. A round-trip route should
fit comfortably inside 2× the combat radius — if it exceeds that, the
flight is at bingo risk.
"""

import math

from ..catalog import aircraft as catalog_aircraft
from ..errors import AssemblyReport


def check(spec, report: AssemblyReport) -> None:
    for flight in spec.flights or []:
        if not flight.waypoints or len(flight.waypoints) < 2:
            continue
        info = catalog_aircraft.get_info(flight.aircraft_type)
        if info is None:
            continue
        total_m = _route_length_m(flight.waypoints)
        total_km = total_m / 1000.0
        budget_km = info.combat_radius_km * 2.0  # out-and-back
        # 90% of radius is the "tight but OK" mark.
        if total_km > budget_km:
            report.error(
                "FUEL_RANGE_EXCEEDED",
                f"Flight '{flight.name}' route is {total_km:.0f} km but "
                f"{info.alias} combat radius round-trip is {budget_km:.0f} km",
                context=flight.name,
                hint="Add a tanker, shorten the route, or pick a longer-legged airframe",
            )
        elif total_km > budget_km * 0.9:
            report.warn(
                "FUEL_RANGE_TIGHT",
                f"Flight '{flight.name}' route is {total_km:.0f} km — "
                f"within 90% of {info.alias}'s {budget_km:.0f} km budget",
                context=flight.name,
            )


def _route_length_m(waypoints) -> float:
    total = 0.0
    for i in range(1, len(waypoints)):
        prev, curr = waypoints[i - 1], waypoints[i]
        total += math.hypot(curr.x - prev.x, curr.y - prev.y)
    return total
