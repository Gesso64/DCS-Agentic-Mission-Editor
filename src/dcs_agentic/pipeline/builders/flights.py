"""Flight (aircraft + helicopter) group builder.

The trickiest builder: three spawn paths (airport, inflight, manual
fallback) and an explicit task-setting fix in the fallback to prevent
the "every flight ships as CAS" silent bug.
"""

from dcs import Mission
from dcs.mapping import Point as MapPoint
from dcs.mission import StartType as PydcsStartType
from dcs.point import MovingPoint, PointProperties
from dcs.unit import Skill as PydcsSkill

from ...catalog import (
    aircraft as catalog_aircraft,
    payloads as catalog_payloads,
    theatres as catalog_theatres,
)
from ...errors import AssemblyReport
from ...schemas import FlightGroup, MissionSpec, StartType as SpecStartType
from ...units import kmh_to_ms
from . import point_action_for_wp, skill_to_pydcs, start_type_to_pydcs, task_to_pydcs
from .coalitions import get_or_add_country


def build_flights(mission: Mission, spec: MissionSpec, report: AssemblyReport) -> None:
    if not spec.flights:
        return
    for flight_spec in spec.flights:
        try:
            _build_one(mission, flight_spec, report)
        except Exception as e:
            report.error(
                "FLIGHT_BUILD_FAILED",
                f"{type(e).__name__}: {e}",
                context=flight_spec.name,
            )


def _build_one(mission: Mission, flight_spec: FlightGroup, report: AssemblyReport) -> None:
    aircraft_type = catalog_aircraft.resolve(flight_spec.aircraft_type)
    if catalog_aircraft.is_proxy(flight_spec.aircraft_type):
        report.warn(
            "AIRCRAFT_PROXY",
            f"'{flight_spec.aircraft_type}' is not modelled in pydcs; "
            f"substituting '{catalog_aircraft.proxy_target(flight_spec.aircraft_type)}'",
            context=flight_spec.name,
        )

    country = get_or_add_country(mission, flight_spec.country, flight_spec.side or "blue")
    maintask = task_to_pydcs(flight_spec.task) if flight_spec.task else None
    group_size = flight_spec.group_size or 1
    start_type = start_type_to_pydcs(flight_spec.start_type or SpecStartType.COLD)

    airport = None
    if flight_spec.airport:
        airport = catalog_theatres.lookup_airport(mission.terrain, flight_spec.airport)
        if airport is None:
            report.warn(
                "AIRPORT_NOT_FOUND",
                f"Airport '{flight_spec.airport}' not found on theatre "
                f"'{spec.theatre}'; falling back to position spawn.",
                context=flight_spec.name,
                hint="Check the theatre's airport list or supply a position",
            )

    if airport is None and flight_spec.position is not None:
        pos = MapPoint(flight_spec.position.x, flight_spec.position.y, mission.terrain)
        alt = flight_spec.altitude or 3000
        speed = flight_spec.speed or 500
        group = mission.flight_group_inflight(
            country=country, name=flight_spec.name, aircraft_type=aircraft_type,
            position=pos, altitude=alt, speed=speed, maintask=maintask,
            group_size=group_size,
        )
    elif airport is not None:
        try:
            group = mission.flight_group_from_airport(
                country=country, name=flight_spec.name, aircraft_type=aircraft_type,
                airport=airport, start_type=start_type, group_size=group_size,
            )
        except (FileNotFoundError, OSError, KeyError, RuntimeError) as e:
            report.warn(
                "PAYLOADS_UNAVAILABLE",
                f"DCS payload data not loadable, creating flight manually: {e}",
                context=flight_spec.name,
                hint="Install DCS World locally or specify explicit payloads in the spec",
            )
            group = _create_airport_group_manually(
                mission, flight_spec, aircraft_type, country, airport,
                start_type, group_size, maintask,
            )
    else:
        raise ValueError(
            f"Flight '{flight_spec.name}' needs either an airport or a position"
        )

    # Waypoints
    if flight_spec.waypoints:
        for wp_spec in flight_spec.waypoints:
            pos = MapPoint(wp_spec.x, wp_spec.y, mission.terrain)
            alt = wp_spec.altitude or flight_spec.altitude or 5000
            speed = wp_spec.speed or flight_spec.speed or 500
            wp = MovingPoint(pos)
            wp.type = wp_spec.type or "Turning Point"
            wp.action = point_action_for_wp(wp_spec)
            wp.alt = alt
            wp.speed = kmh_to_ms(speed)
            wp.ETA_locked = wp_spec.eta_locked or False
            wp.properties = PointProperties()
            if wp_spec.name:
                wp.name = wp_spec.name
            if wp_spec.airdrome_id is not None:
                wp.airdrome_id = wp_spec.airdrome_id
            if wp_spec.tasks:
                for wtask in wp_spec.tasks:
                    task_cls = task_to_pydcs(wtask)
                    if task_cls:
                        t = task_cls()
                        t.auto = True
                        wp.tasks.append(t)
            group.add_point(wp)

    if flight_spec.payload is not None:
        _apply_payload(group, flight_spec, report)

    if flight_spec.skill is not None:
        group.set_skill(skill_to_pydcs(flight_spec.skill))
    if flight_spec.late_activation:
        group.late_activation = True
    if flight_spec.livery:
        for unit in group.units:
            unit.livery_id = flight_spec.livery
    if flight_spec.radio_frequency is not None:
        group.frequency = flight_spec.radio_frequency
    if flight_spec.modulation is not None:
        group.modulation = flight_spec.modulation
    if flight_spec.callsign:
        for unit, cs in zip(group.units, flight_spec.callsign):
            unit.callsign = cs

    report.info(
        "FLIGHT_CREATED",
        f"Created flight '{flight_spec.name}': {group_size}x "
        f"{aircraft_type.id} at {flight_spec.airport or 'inflight'}",
    )


def _apply_payload(group, flight_spec: FlightGroup, report: AssemblyReport) -> None:
    """Apply PayloadSpec to every unit in the group.

    Precedence: explicit pylons override preset. Missing presets are an
    error (per Phase 3 anti-pattern: no silent fallback).
    """
    payload = flight_spec.payload
    pylons = payload.pylons
    if not pylons and payload.preset_name:
        try:
            preset = catalog_payloads.resolve(
                flight_spec.aircraft_type, payload.preset_name,
            )
        except ValueError as e:
            report.error(
                "PAYLOAD_PRESET_UNKNOWN",
                str(e),
                context=flight_spec.name,
                hint="Use catalog.payloads.list_for_aircraft() to see options",
            )
            return
        pylons = [_make_pylon(s, c, q) for (s, c, q) in preset.pylons]
        if payload.fuel is None:
            payload_fuel = preset.fuel
        else:
            payload_fuel = payload.fuel
    else:
        payload_fuel = payload.fuel

    for unit in group.units:
        if pylons:
            unit.pylons = {}
            for p in pylons:
                entry = {"CLSID": p.clsid}
                if p.quantity and p.quantity > 1:
                    entry["count"] = p.quantity
                unit.pylons[p.station] = entry
        if payload_fuel is not None:
            try:
                unit.fuel = unit.unit_type.fuel_max * payload_fuel
            except AttributeError:
                unit.fuel = payload_fuel
        if payload.chaff is not None:
            unit.chaff = payload.chaff
        if payload.flare is not None:
            unit.flare = payload.flare
        if payload.gun is not None:
            unit.gun = payload.gun


def _make_pylon(station: int, clsid: str, quantity: int):
    from ...schemas import Pylon
    return Pylon(station=station, clsid=clsid, quantity=quantity)


def _create_airport_group_manually(mission, flight_spec, aircraft_type, country,
                                    airport, start_type, group_size, maintask):
    """Fallback: create a plane group without loading DCS payload data.

    Used when pydcs cannot find the local DCS install. Sets the group's
    task explicitly — without that, FlyingGroup.task defaults to "CAS"
    and every flight would silently ship as a strike regardless of its
    declared TaskType.
    """
    from dcs.flyingunit import Plane
    from dcs.point import MovingPoint as WP, PointAction as PA, PointProperties as PP

    group = mission.plane_group(flight_spec.name)
    if maintask is not None and hasattr(maintask, "name"):
        group.task = maintask.name

    for i in range(group_size):
        u = Plane(
            mission.terrain,
            mission.next_unit_id(),
            f"{flight_spec.name} Unit #{i+1}",
            aircraft_type, country,
        )
        u.position = airport.position.point_from_heading(0, i * 20)
        u.heading = 0
        u.alt = 0
        u.skill = PydcsSkill.Average
        u.callsign_dict = {"name": f"{aircraft_type.id[0]}1", "1": 1, "2": 1, "3": i + 1}
        u.onboard_num = f"{i + 1:03d}"
        group.add_unit(u)

    mp = WP(group.units[0].position)
    if start_type == PydcsStartType.Cold:
        mp.type = "TakeOffParking"
        mp.action = PA.FromParkingArea
    elif start_type == PydcsStartType.Warm:
        mp.type = "TakeOffParkingHot"
        mp.action = PA.FromParkingAreaHot
    else:
        mp.type = "TakeOff"
        mp.action = PA.FromRunway
    mp.airdrome_id = airport.id
    mp.alt = 0
    mp.properties = PP()
    group.add_point(mp)
    country.add_plane_group(group)
    return group
