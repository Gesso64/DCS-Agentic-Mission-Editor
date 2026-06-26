"""Validation layer — Phase 7 (minimal implementation).

Cross-cutting checks beyond what Pydantic catches. Each check is a pure
function that reads a MissionSpec and reports issues via AssemblyReport.

Public API:
    from dcs_agentic.validation import validate
    report = validate(spec)
"""

from typing import List

from ..errors import AssemblyReport


def validate(spec) -> AssemblyReport:
    """Run all registered validators against a MissionSpec.

    Args:
        spec: A MissionSpec instance to validate

    Returns:
        AssemblyReport containing all findings
    """
    report = AssemblyReport()
    _validate_coordinate_sanity(spec, report)
    _validate_weapons_match(spec, report)
    _validate_route_sanity(spec, report)
    return report


def _validate_coordinate_sanity(spec, report: AssemblyReport) -> None:
    """Check all coordinates are within theatre bounds."""
    from ..catalog import theatres

    theatre_info = theatres.get_info(spec.theatre or "Caucasus")
    if theatre_info is None:
        report.warn("UNKNOWN_THEATRE", f"Theatre '{spec.theatre}' not found in catalog")
        return

    bounds = theatre_info.bounds
    margin = 50000  # 50 km margin

    # Check flights
    for flight in (spec.flights or []):
        for wp in (flight.waypoints or []):
            if not bounds.contains(wp.x, wp.y, margin):
                report.warn(
                    "COORD_OUT_OF_BOUNDS",
                    f"Waypoint '{wp.name}' in flight '{flight.name}' "
                    f"({wp.x:.0f}, {wp.y:.0f}) is outside theatre bounds",
                    context=flight.name,
                )

    # Check vehicle positions
    for vg in (spec.vehicles or []):
        if vg.position and not bounds.contains(vg.position.x, vg.position.y, margin):
            report.warn(
                "COORD_OUT_OF_BOUNDS",
                f"Vehicle group '{vg.name}' position ({vg.position.x:.0f}, {vg.position.y:.0f}) "
                f"is outside theatre bounds",
                context=vg.name,
            )

    # Check ship positions
    for sg in (spec.ships or []):
        if sg.position and not bounds.contains(sg.position.x, sg.position.y, margin):
            report.warn(
                "COORD_OUT_OF_BOUNDS",
                f"Ship group '{sg.name}' position ({sg.position.x:.0f}, {sg.position.y:.0f}) "
                f"is outside theatre bounds",
                context=sg.name,
            )


def _validate_weapons_match(spec, report: AssemblyReport) -> None:
    """Check payloads match declared tasks."""
    from ..catalog import payloads
    # Define what weapon categories match what tasks
    AA_MISSILES = {"AIM-9", "AIM-120", "R-73", "R-27", "R-77", "Python", "Derby"}
    ANTI_RADIATION = {"AGM-88", "AGM-45", "Kh-58", "Kh-31"}
    BOMBS = {"GBU", "Mk-82", "Mk-83", "Mk-84", "BLU", "SDB", "CBU", "KAB"}
    ASM = {"AGM-84", "AGM-158", "Kh-35", "3M-54", "Exocet"}
    CAS_MISSILES = {"AGM-65", "AGM-114", "Vikhr", "BGM-71"}

    for flight in (spec.flights or []):
        task = flight.task
        if task is None:
            continue
        task_str = task.value if hasattr(task, 'value') else str(task)

        p = flight.payload
        if p is None:
            # No payload defined — warn unless it's a non-combat task
            if task_str not in ("recon", "transport", "awacs", "tanker"):
                report.warn(
                    "WEAPONS_TASK_MISMATCH",
                    f"Flight '{flight.name}' has task '{task_str}' but no payload defined",
                    context=flight.name,
                )
            continue

        # Check payload content against task
        if p.preset_name:
            # Resolve preset to check
            try:
                preset = payloads.resolve(flight.aircraft_type, p.preset_name)
                # Get weapon names for matching
                weapon_names = set()
                for station, clsid, qty in preset.pylons:
                    weapon_names.add(clsid)
            except ValueError:
                continue
        elif p.pylons:
            weapon_names = {item.clsid for item in p.pylons}
        else:
            continue

        # Task-specific checks
        if task_str == "cap" and not any(
            any(aa in w.upper() for aa in AA_MISSILES) for w in weapon_names
        ):
            report.warn(
                "WEAPONS_TASK_MISMATCH",
                f"Flight '{flight.name}' has CAP task but no A-A missiles in payload",
                context=flight.name,
            )
        elif task_str == "sead" and not any(
            any(ar in w.upper() for ar in ANTI_RADIATION) for w in weapon_names
        ):
            report.warn(
                "WEAPONS_TASK_MISMATCH",
                f"Flight '{flight.name}' has SEAD task but no anti-radiation missiles in payload",
                context=flight.name,
            )
        elif task_str == "strike" and not any(
            any(b in w.upper() for b in BOMBS) for w in weapon_names
        ):
            report.warn(
                "WEAPONS_TASK_MISMATCH",
                f"Flight '{flight.name}' has STRIKE task but no bombs in payload",
                context=flight.name,
            )
        elif task_str == "antiship" and not any(
            any(a in w.upper() for a in ASM) for w in weapon_names
        ):
            report.warn(
                "WEAPONS_TASK_MISMATCH",
                f"Flight '{flight.name}' has ANTISHIP task but no anti-ship missiles in payload",
                context=flight.name,
            )


def _validate_route_sanity(spec, report: AssemblyReport) -> None:
    """Check waypoints are in plausible order and altitudes make sense."""
    for flight in (spec.flights or []):
        wps = flight.waypoints
        if not wps or len(wps) < 1:
            continue

        # Check for unrealistic altitude changes between consecutive waypoints
        for i in range(1, len(wps)):
            prev, curr = wps[i - 1], wps[i]
            if prev.altitude and curr.altitude:
                delta = abs(curr.altitude - prev.altitude)
                # Warn if altitude change > 10000m between waypoints
                if delta > 10000:
                    report.warn(
                        "ROUTE_ALTITUDE_SPIKE",
                        f"Flight '{flight.name}': altitude change of {delta}m "
                        f"between waypoint {i - 1} and {i}",
                        context=flight.name,
                    )

        # Check for obvious coordinate swaps (x and y swapped)
        for wp in wps:
            if abs(wp.x) > 1000000 or abs(wp.y) > 1000000:
                report.warn(
                    "ROUTE_COORD_SUSPICIOUS",
                    f"Flight '{flight.name}': waypoint '{wp.name}' "
                    f"has extreme coordinates ({wp.x:.0f}, {wp.y:.0f}) — "
                    f"possible x/y swap?",
                    context=flight.name,
                )