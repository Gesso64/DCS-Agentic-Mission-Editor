"""Route-sanity validator.

Flags obvious waypoint mistakes:
  - extreme coordinates (likely x/y swap or unit confusion)
  - large altitude swings between consecutive waypoints
  - landing waypoint without a matching airport on the theatre
"""

from ..catalog import theatres
from ..errors import AssemblyReport


def check(spec, report: AssemblyReport) -> None:
    info = theatres.get_info(spec.theatre or "Caucasus")

    for flight in spec.flights or []:
        wps = flight.waypoints or []
        for wp in wps:
            if abs(wp.x) > 1_500_000 or abs(wp.y) > 1_500_000:
                report.warn(
                    "ROUTE_COORD_SUSPICIOUS",
                    f"Flight '{flight.name}' waypoint '{wp.name or '?'}' has "
                    f"extreme coordinates ({wp.x:.0f}, {wp.y:.0f}) — possible x/y swap?",
                    context=flight.name,
                )

        for i in range(1, len(wps)):
            prev, curr = wps[i - 1], wps[i]
            if prev.altitude is not None and curr.altitude is not None:
                delta = abs(curr.altitude - prev.altitude)
                if delta > 10000:
                    report.warn(
                        "ROUTE_ALTITUDE_SPIKE",
                        f"Flight '{flight.name}' altitude change of {delta}m "
                        f"between waypoint {i - 1} and {i}",
                        context=flight.name,
                    )

        # Landing waypoint (type or action) should reference a real airport
        # when a theatre is known.
        if info is None:
            continue
        for wp in wps:
            is_landing = (
                (wp.action and "LANDING" in wp.action.upper())
                or (wp.type and "land" in wp.type.lower())
            )
            if not is_landing:
                continue
            if wp.airdrome_id is None and not info.notable_airports:
                continue
            # We can't cross-check airdrome_id without loading the terrain
            # here, but we can flag "landing waypoint with no airdrome_id"
            # as a likely oversight.
            if wp.airdrome_id is None:
                report.warn(
                    "ROUTE_LANDING_NO_AIRDROME",
                    f"Flight '{flight.name}' landing waypoint '{wp.name or '?'}' "
                    f"has no airdrome_id — pydcs will fall back to an arbitrary airport",
                    context=flight.name,
                    hint="Set Waypoint.airdrome_id to the destination airport's pydcs id",
                )
