"""Vehicle group builder."""

from dcs import Mission
from dcs.mapping import Point as MapPoint

from ...catalog import vehicles as catalog_vehicles
from ...errors import AssemblyReport
from ...schemas import MissionSpec, VehicleGroup
from . import skill_to_pydcs
from .coalitions import get_or_add_country


def build_ground(mission: Mission, spec: MissionSpec, report: AssemblyReport) -> None:
    if not spec.vehicles:
        return
    for vehicle_spec in spec.vehicles:
        try:
            _build_one(mission, vehicle_spec, report)
        except Exception as e:
            report.error(
                "VEHICLE_BUILD_FAILED",
                f"{type(e).__name__}: {e}",
                context=vehicle_spec.name,
            )


def _build_one(mission: Mission, vehicle_spec: VehicleGroup, report: AssemblyReport) -> None:
    vehicle_type = catalog_vehicles.resolve(vehicle_spec.vehicle_type)
    country = get_or_add_country(mission, vehicle_spec.country, vehicle_spec.side or "red")
    pos = MapPoint(vehicle_spec.position.x, vehicle_spec.position.y, mission.terrain)

    vg = mission.vehicle_group(
        country=country, name=vehicle_spec.name, _type=vehicle_type,
        position=pos, heading=vehicle_spec.heading or 0,
        group_size=vehicle_spec.group_size or 1,
    )

    if vehicle_spec.skill is not None:
        vg.set_skill(skill_to_pydcs(vehicle_spec.skill))
    if vehicle_spec.waypoints:
        for wp_spec in vehicle_spec.waypoints:
            # pydcs's VehicleGroup.add_waypoint takes speed in km/h
            # (it divides by 3.6 internally to store m/s).
            wp_pos = MapPoint(wp_spec.x, wp_spec.y, mission.terrain)
            vg.add_waypoint(wp_pos, speed=wp_spec.speed or 32)

    report.info(
        "VEHICLE_CREATED",
        f"Created vehicle group '{vehicle_spec.name}': {vehicle_type.id}",
    )
