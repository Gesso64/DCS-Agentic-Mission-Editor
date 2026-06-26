"""Ship group builder."""

from dcs import Mission
from dcs.mapping import Point as MapPoint

from ...catalog import ships as catalog_ships
from ...errors import AssemblyReport
from ...schemas import MissionSpec, ShipGroup
from .coalitions import get_or_add_country


def build_naval(mission: Mission, spec: MissionSpec, report: AssemblyReport) -> None:
    if not spec.ships:
        return
    for ship_spec in spec.ships:
        try:
            _build_one(mission, ship_spec, report)
        except Exception as e:
            report.error(
                "SHIP_BUILD_FAILED",
                f"{type(e).__name__}: {e}",
                context=ship_spec.name,
            )


def _build_one(mission: Mission, ship_spec: ShipGroup, report: AssemblyReport) -> None:
    ship_type = catalog_ships.resolve(ship_spec.ship_type)
    country = get_or_add_country(mission, ship_spec.country, ship_spec.side or "blue")
    pos = MapPoint(ship_spec.position.x, ship_spec.position.y, mission.terrain)

    sg = mission.ship_group(
        country=country, name=ship_spec.name, _type=ship_type,
        position=pos, heading=ship_spec.heading or 0,
        group_size=ship_spec.group_size or 1,
    )

    if ship_spec.waypoints:
        for wp_spec in ship_spec.waypoints:
            wp_pos = MapPoint(wp_spec.x, wp_spec.y, mission.terrain)
            sg.add_waypoint(wp_pos, 20)

    report.info(
        "SHIP_CREATED",
        f"Created ship group '{ship_spec.name}': {ship_type.id}",
    )
