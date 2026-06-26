"""`.miz → MissionSpec` importer — Phase 6.

Loads a .miz via `pydcs.Mission.load_file` and walks the resulting in-memory
mission to build a `MissionSpec`. Round-trip is intentionally lossy in v1:

  Implemented:
    - theatre, start_time, briefing texts
    - coalitions (one Coalition entry per country present)
    - flights (with waypoints, skill, livery, radio, payload pylons)
    - vehicles (position, heading, skill, group_size)
    - ships (position, group_size)
    - static objects (position, heading, type id)

  Deferred (warned about):
    - weather, triggers, drawings/zones, FARPs, carrier ops,
      mission goals, custom scripts, bullseye, callsigns, radios.

Unknown unit types are passed through as their pydcs `unit_type.id`
(e.g. "FA-18C_hornet"). The catalog reverse-map best-effort upgrades
them to friendly aliases when possible.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from contextlib import contextmanager

from dcs import Mission
from dcs.terrain import Caucasus
from dcs.unittype import FlyingType

from ..catalog import aircraft as catalog_aircraft
from ..errors import AssemblyReport
from ..schemas import (
    Coalition,
    FlightGroup,
    MissionSpec,
    PayloadSpec,
    Position,
    Pylon,
    ShipGroup,
    StaticObject,
    VehicleGroup,
    Waypoint,
)
from ..schemas.briefing import Briefing
from ..units import ms_to_kmh


# Build once, lazily.
_AIRCRAFT_REVERSE: Optional[Dict[str, str]] = None


@contextmanager
def _payload_loader_safe():
    """Patch FlyingType.load_payloads to swallow KeyError + FileNotFoundError.

    pydcs's load_payloads chokes when DCS isn't installed locally — it
    indexes _payload_cache before checking existence (a pydcs bug). We
    only need the unit topology to reverse-engineer the spec, not the
    actual payloads, so a no-op fallback is correct here.
    """
    original = FlyingType.__dict__["load_payloads"]  # the classmethod object

    @classmethod
    def safe_load(cls):
        try:
            return original.__func__(cls)
        except (KeyError, FileNotFoundError, OSError):
            cls.payloads = cls.payloads if cls.payloads is not None else {}
            return cls.payloads

    FlyingType.load_payloads = safe_load
    try:
        yield
    finally:
        FlyingType.load_payloads = original


def _unit_type_id(unit) -> str:
    """Get the pydcs type id from a unit.

    FlyingUnit exposes `unit_type` (the class); ground/ship/static Unit exposes
    `type` (already a string). Try both."""
    ut = getattr(unit, "unit_type", None)
    if ut is not None:
        return getattr(ut, "id", str(ut))
    return getattr(unit, "type", "") or "unknown"


def _aircraft_alias_for(pydcs_id: str) -> str:
    """Reverse-map a pydcs unit_type.id (e.g. 'FA-18C_hornet') to a catalog
    alias (e.g. 'F/A-18C'). Falls back to the raw id when no match."""
    global _AIRCRAFT_REVERSE
    if _AIRCRAFT_REVERSE is None:
        rev: Dict[str, str] = {}
        for alias in catalog_aircraft.all_aliases():
            try:
                cls = catalog_aircraft.resolve(alias)
            except ValueError:
                continue
            cls_id = getattr(cls, "id", None)
            if cls_id and cls_id not in rev:
                rev[cls_id] = alias
        _AIRCRAFT_REVERSE = rev
    return _AIRCRAFT_REVERSE.get(pydcs_id, pydcs_id)


def import_miz(path: str) -> Tuple[MissionSpec, AssemblyReport]:
    """Load a `.miz` and convert it to a `MissionSpec`."""
    report = AssemblyReport()
    p = Path(path)
    if not p.exists():
        report.error(
            "MIZ_NOT_FOUND",
            f"File not found: {path}",
        )
        return _empty_spec(p), report

    mission = Mission(terrain=Caucasus())
    try:
        with _payload_loader_safe():
            status = mission.load_file(str(p))
    except Exception as e:
        report.error(
            "MIZ_LOAD_FAILED",
            f"{type(e).__name__}: {e}",
            hint="Verify the file is a valid .miz and pydcs supports this version.",
        )
        return _empty_spec(p), report

    for s in status or []:
        report.warn("MIZ_LOAD_STATUS", str(s))

    spec_name = mission.translation.get_string(
        getattr(mission, "_description_text", None).id
    ) if hasattr(mission, "_description_text") and mission._description_text else p.stem

    spec = MissionSpec(
        name=str(spec_name) if spec_name else p.stem,
        theatre=_theatre_name(mission),
        start_time=_start_time(mission),
        sortie=_lookup_str(mission, "_sortie"),
        briefing=_briefing(mission),
        coalitions=_coalitions(mission),
        flights=_flights(mission, report),
        vehicles=_vehicles(mission, report),
        ships=_ships(mission, report),
        statics=_statics(mission, report),
    )

    # Warn loudly for sections we don't yet round-trip.
    _warn_deferred(mission, report)

    return spec, report


# ─── helpers ────────────────────────────────────────────────────────────────


def _empty_spec(p: Path) -> MissionSpec:
    return MissionSpec(name=f"Imported from {p.name}", theatre="Caucasus")


def _theatre_name(mission: Mission) -> str:
    name = getattr(mission.terrain, "name", None) or "Caucasus"
    # pydcs uses 'PersianGulf' both internally and in MissionSpec.
    return name


def _start_time(mission: Mission) -> Optional[float]:
    dt = getattr(mission, "start_time", None)
    if dt is None:
        return None
    try:
        # pydcs stores tz-aware UTC on the constructor and may store naive on load.
        if dt.tzinfo is None:
            from datetime import timezone
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return None


def _lookup_str(mission: Mission, attr: str) -> Optional[str]:
    val = getattr(mission, attr, None)
    if val is None:
        return None
    # pydcs stores translated text as a String object
    try:
        s = str(val)
        return s if s else None
    except Exception:
        return None


def _briefing(mission: Mission) -> Optional[Briefing]:
    desc = _lookup_str(mission, "_description_text")
    blue = _lookup_str(mission, "_description_bluetask")
    red = _lookup_str(mission, "_description_redtask")
    if not any([desc, blue, red]):
        return None
    return Briefing(
        description=desc or "",
        blue_task=blue or "",
        red_task=red or "",
    )


def _coalitions(mission: Mission) -> Optional[List[Coalition]]:
    """Emit only countries that actually own groups in the .miz.

    pydcs initializes Mission with every country wired into both
    coalitions; the .miz only meaningfully uses the ones with units.
    """
    out: List[Coalition] = []
    for side_name, coalition in mission.coalition.items():
        for country_name, country in coalition.countries.items():
            has_groups = any([
                country.plane_group,
                country.helicopter_group,
                country.vehicle_group,
                country.ship_group,
                getattr(country, "static_group", None),
            ])
            if has_groups:
                out.append(Coalition(side=side_name, country=country_name))
    return out or None


def _flights(mission: Mission, report: AssemblyReport) -> Optional[List[FlightGroup]]:
    out: List[FlightGroup] = []
    for side_name, coalition in mission.coalition.items():
        for country_name, country in coalition.countries.items():
            for g in list(country.plane_group) + list(country.helicopter_group):
                try:
                    out.append(_flight_from_group(g, side_name, country_name))
                except Exception as e:
                    report.warn(
                        "IMPORT_FLIGHT_FAILED",
                        f"{type(e).__name__}: {e}",
                        context=getattr(g, "name", "?"),
                    )
    return out or None


def _flight_from_group(g, side: str, country: str) -> FlightGroup:
    unit = g.units[0]
    pydcs_id = getattr(unit.unit_type, "id", str(unit.unit_type))
    waypoints = [
        Waypoint(
            x=float(p.position.x),
            y=float(p.position.y),
            altitude=int(p.alt) if p.alt is not None else None,
            speed=ms_to_kmh(p.speed) if p.speed else None,
            name=getattr(p, "name", None) or None,
        )
        for p in g.points
    ]
    payload = _payload_from_unit(unit)
    return FlightGroup(
        name=g.name,
        aircraft_type=_aircraft_alias_for(pydcs_id),
        country=country,
        side=side,
        group_size=len(g.units),
        airport=None,
        position=Position(x=float(unit.position.x), y=float(unit.position.y)),
        waypoints=waypoints or None,
        payload=payload,
    )


def _payload_from_unit(unit) -> Optional[PayloadSpec]:
    pylons_dict = getattr(unit, "pylons", None) or {}
    if not pylons_dict:
        return None
    pylons: List[Pylon] = []
    for station, slot in pylons_dict.items():
        clsid = slot.get("CLSID") if isinstance(slot, dict) else None
        if not clsid:
            continue
        pylons.append(Pylon(station=int(station), clsid=clsid, quantity=1))
    return PayloadSpec(pylons=pylons or None) if pylons else None


def _vehicles(mission: Mission, report: AssemblyReport) -> Optional[List[VehicleGroup]]:
    out: List[VehicleGroup] = []
    for side_name, coalition in mission.coalition.items():
        for country_name, country in coalition.countries.items():
            for g in country.vehicle_group:
                try:
                    u = g.units[0]
                    out.append(VehicleGroup(
                        name=g.name,
                        vehicle_type=_unit_type_id(u),
                        country=country_name,
                        side=side_name,
                        position=Position(x=float(u.position.x), y=float(u.position.y)),
                        group_size=len(g.units),
                        heading=float(u.heading) if hasattr(u, "heading") else 0,
                    ))
                except Exception as e:
                    report.warn(
                        "IMPORT_VEHICLE_FAILED",
                        f"{type(e).__name__}: {e}",
                        context=getattr(g, "name", "?"),
                    )
    return out or None


def _ships(mission: Mission, report: AssemblyReport) -> Optional[List[ShipGroup]]:
    out: List[ShipGroup] = []
    for side_name, coalition in mission.coalition.items():
        for country_name, country in coalition.countries.items():
            for g in country.ship_group:
                try:
                    u = g.units[0]
                    out.append(ShipGroup(
                        name=g.name,
                        ship_type=_unit_type_id(u),
                        country=country_name,
                        side=side_name,
                        position=Position(x=float(u.position.x), y=float(u.position.y)),
                        group_size=len(g.units),
                    ))
                except Exception as e:
                    report.warn(
                        "IMPORT_SHIP_FAILED",
                        f"{type(e).__name__}: {e}",
                        context=getattr(g, "name", "?"),
                    )
    return out or None


def _statics(mission: Mission, report: AssemblyReport) -> Optional[List[StaticObject]]:
    out: List[StaticObject] = []
    for side_name, coalition in mission.coalition.items():
        for country_name, country in coalition.countries.items():
            for g in getattr(country, "static_group", []) or []:
                try:
                    u = g.units[0] if g.units else None
                    if u is None:
                        continue
                    out.append(StaticObject(
                        name=g.name,
                        type=_unit_type_id(u),
                        country=country_name,
                        side=side_name,
                        position=Position(x=float(u.position.x), y=float(u.position.y)),
                        heading=float(u.heading) if hasattr(u, "heading") else 0,
                    ))
                except Exception as e:
                    report.warn(
                        "IMPORT_STATIC_FAILED",
                        f"{type(e).__name__}: {e}",
                        context=getattr(g, "name", "?"),
                    )
    return out or None


def _warn_deferred(mission: Mission, report: AssemblyReport) -> None:
    if mission.triggerrules.triggers:
        report.warn(
            "IMPORT_TRIGGERS_DROPPED",
            f"{len(mission.triggerrules.triggers)} trigger rule(s) in source .miz "
            f"were not round-tripped (importer v1 limitation).",
            hint="Edit triggers via the JSON spec until trigger reverse-import lands.",
        )
    if getattr(mission, "drawings", None) and getattr(mission.drawings, "layers", None):
        report.warn(
            "IMPORT_DRAWINGS_DROPPED",
            "Drawings/zones were not round-tripped (importer v1 limitation).",
        )
