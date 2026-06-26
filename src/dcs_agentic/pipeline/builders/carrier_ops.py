"""Carrier ops builder.

Wires TACAN beacon (and ICLS / BRC / Link-4 metadata as comments) onto
a ship group already added by build_naval.
"""

from dcs import Mission
from dcs.task import ActivateBeaconCommand

from ...errors import AssemblyReport
from ...schemas import CarrierOps, MissionSpec


def build_carrier_ops(mission: Mission, spec: MissionSpec, report: AssemblyReport) -> None:
    if not spec.carrier_ops:
        return
    for ops in spec.carrier_ops:
        try:
            _build_one(mission, ops, report)
        except Exception as e:
            report.error(
                "CARRIER_OPS_BUILD_FAILED",
                f"{type(e).__name__}: {e}",
                context=ops.ship_name,
            )


def _find_ship_group(mission: Mission, name: str):
    """Locate a ship group by name across all countries."""
    for coalition in mission.coalition.values():
        for country in coalition.countries.values():
            for sg in country.ship_group:
                if sg.name == name:
                    return sg
    return None


def _find_carrier_unit_id(group) -> int:
    """Return the unit_id of the first carrier-capable unit in the group.

    For pure-ship groups the first unit is fine; the beacon is added to
    the group, not to a specific unit. Returning 0 is safe — DCS routes
    the beacon to the group's first unit.
    """
    if not group.units:
        return 0
    return group.units[0].id


def _build_one(mission: Mission, ops: CarrierOps, report: AssemblyReport) -> None:
    sg = _find_ship_group(mission, ops.ship_name)
    if sg is None:
        report.error(
            "CARRIER_NOT_FOUND",
            f"Carrier ops references ship '{ops.ship_name}' but no ship "
            f"group with that name exists",
            context=ops.ship_name,
            hint="Add the carrier to spec.ships first",
        )
        return

    if not sg.points:
        report.warn(
            "CARRIER_NO_WAYPOINTS",
            f"Carrier '{ops.ship_name}' has no waypoints; TACAN beacon "
            f"will be added at unit position 0",
            context=ops.ship_name,
        )
        return

    unit_id = _find_carrier_unit_id(sg)
    beacon = ActivateBeaconCommand(
        channel=ops.tacan_channel,
        modechannel=ops.tacan_mode or "X",
        callsign=ops.tacan_callsign or "STN",
        bearing=True,
        unit_id=unit_id,
        aa=False,
    )
    sg.points[0].tasks.append(beacon)

    extras = []
    if ops.icls_channel is not None:
        extras.append(f"ICLS ch {ops.icls_channel}")
    if ops.base_recovery_course is not None:
        extras.append(f"BRC {ops.base_recovery_course:.0f}°")
    if ops.link4_mhz is not None:
        extras.append(f"Link-4 {ops.link4_mhz} MHz")
    if extras:
        report.warn(
            "CARRIER_OPS_PARTIAL",
            f"Carrier '{ops.ship_name}': {', '.join(extras)} not yet "
            f"wired to pydcs — TACAN ch {ops.tacan_channel}{ops.tacan_mode or 'X'} applied",
            context=ops.ship_name,
        )
    else:
        report.info(
            "CARRIER_OPS_CREATED",
            f"Carrier '{ops.ship_name}': TACAN ch "
            f"{ops.tacan_channel}{ops.tacan_mode or 'X'} '{ops.tacan_callsign or 'STN'}'",
        )
