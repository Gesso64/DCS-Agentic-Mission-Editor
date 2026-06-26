"""Editor agent tool surface — fully implemented for Phase 9.

This module exposes:

  TOOLS   — list of tool definitions in Anthropic tool-use format.
            The set of tools is locked. Adding a tool requires updating
            this file AND extending apply_tool() to dispatch it.

  apply_tool(spec, name, input) — applies one tool call to a MissionSpec.
                                  Returns (updated_spec, result_message).

────────────────────────────────────────────────────────────────────
DESIGN RULES (do not break when implementing):

1. Each tool is a SINGLE mutation. Composition happens in the LLM loop,
   not in apply_tool. No "add_strike_package" mega-tool.

2. Tool input schemas are TIGHT. Pass only what the mutation needs.
   Don't pass the whole FlightGroup schema to a tool that only needs
   "(flight_name, waypoint_index, new_x, new_y)".

3. Errors come back to the LLM as `tool_result` content, not exceptions.
   Tool failures must be repairable from the error text alone.

4. Read-only lookup tools (list_airports, list_aircraft, …) live here
   too. The agent uses them to verify before mutating.

5. apply_tool MUST NOT call the assembler. Mutation operates on the
   spec only; the user runs assembly separately. This keeps tool calls
   fast and deterministic.
────────────────────────────────────────────────────────────────────
"""

import json
from typing import Any, Dict, List, Optional, Tuple
from copy import deepcopy

from ...schemas import MissionSpec, FlightGroup, VehicleGroup, ShipGroup
from ...schemas import Weather, Briefing, Trigger, Position, Waypoint, PayloadSpec
from ...catalog import aircraft, vehicles, payloads, ships, theatres


# ─── Tool definitions ────────────────────────────────────────────────────
# Each entry: {"name": str, "description": str, "input_schema": dict}
# input_schema is JSON Schema (Anthropic tool-use accepts standard JSON Schema).

def _flightgroup_schema():
    return FlightGroup.model_json_schema()

def _vehiclegroup_schema():
    return VehicleGroup.model_json_schema()

def _shipgroup_schema():
    return ShipGroup.model_json_schema()

def _weather_schema():
    return Weather.model_json_schema()

def _briefing_schema():
    return Briefing.model_json_schema()

def _trigger_schema():
    return Trigger.model_json_schema()

TOOLS: list[Dict[str, Any]] = [
    # ── Mutations: flights ──────────────────────────────────────────────
    {
        "name": "add_flight",
        "description": "Add a new flight group to the mission. Input is a full FlightGroup.",
        "input_schema": _flightgroup_schema(),
    },
    {
        "name": "remove_flight",
        "description": "Remove a flight group by name.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "move_waypoint",
        "description": "Move a waypoint in a flight's route.",
        "input_schema": {
            "type": "object",
            "properties": {
                "flight_name": {"type": "string"},
                "waypoint_index": {"type": "integer", "minimum": 0},
                "x": {"type": "number"},
                "y": {"type": "number"},
                "altitude": {"type": "integer", "nullable": True},
                "speed": {"type": "number", "nullable": True, "description": "km/h"},
            },
            "required": ["flight_name", "waypoint_index", "x", "y"],
        },
    },
    {
        "name": "add_waypoint",
        "description": "Append a waypoint to a flight's route.",
        "input_schema": {
            "type": "object",
            "properties": {
                "flight_name": {"type": "string"},
                "x": {"type": "number"},
                "y": {"type": "number"},
                "altitude": {"type": "integer"},
                "speed": {"type": "number", "description": "km/h"},
                "name": {"type": "string"},
            },
            "required": ["flight_name", "x", "y"],
        },
    },
    {
        "name": "set_payload",
        "description": "Set or replace the payload on a flight. "
                       "Accepts a preset name or explicit pylon list.",
        "input_schema": {
            "type": "object",
            "properties": {
                "flight_name": {"type": "string"},
                "preset_name": {"type": "string", "nullable": True},
                "pylons": {"type": "array", "nullable": True,
                           "description": "Array of {station, clsid, quantity}"},
            },
            "required": ["flight_name"],
        },
    },
    # ── Mutations: ground ───────────────────────────────────────────────
    {
        "name": "add_vehicle_group",
        "description": "Add a ground vehicle group.",
        "input_schema": _vehiclegroup_schema(),
    },
    {
        "name": "remove_vehicle_group",
        "description": "Remove a vehicle group by name.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    # ── Mutations: naval ────────────────────────────────────────────────
    {
        "name": "add_ship_group",
        "description": "Add a ship group.",
        "input_schema": _shipgroup_schema(),
    },
    {
        "name": "remove_ship_group",
        "description": "Remove a ship group by name.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    # ── Mutations: mission-level ────────────────────────────────────────
    {
        "name": "set_weather",
        "description": "Replace the mission weather block.",
        "input_schema": _weather_schema(),
    },
    {
        "name": "set_briefing",
        "description": "Replace the mission briefing texts.",
        "input_schema": _briefing_schema(),
    },
    {
        "name": "set_start_time",
        "description": "Set mission start time as unix timestamp.",
        "input_schema": {
            "type": "object",
            "properties": {"start_time": {"type": "number"}},
            "required": ["start_time"],
        },
    },
    {
        "name": "add_trigger",
        "description": "Add a trigger. Requires Phase 5 trigger schema.",
        "input_schema": _trigger_schema(),
    },
    # ── Read-only lookups ───────────────────────────────────────────────
    {
        "name": "get_spec",
        "description": "Return the current MissionSpec as JSON.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_airports",
        "description": "List airports available on the current theatre.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_aircraft",
        "description": "List aircraft type aliases.",
        "input_schema": {
            "type": "object",
            "properties": {
                "role": {
                    "type": "string", "nullable": True,
                    "description": "Filter by role: cap, strike, sead, awacs, tanker, helicopter, …",
                },
            },
        },
    },
    {
        "name": "list_vehicles",
        "description": "List vehicle type aliases.",
        "input_schema": {
            "type": "object",
            "properties": {
                "role": {"type": "string", "nullable": True,
                         "description": "Filter by role: sam, ewr, artillery, armor, …"},
            },
        },
    },
    {
        "name": "list_payload_presets",
        "description": "List payload presets, optionally for a specific aircraft.",
        "input_schema": {
            "type": "object",
            "properties": {
                "aircraft_alias": {"type": "string", "nullable": True},
            },
        },
    },
    # ── Validation ──────────────────────────────────────────────────────
    {
        "name": "validate_spec",
        "description": "Run the validation layer over the current spec. "
                       "Returns issues without modifying the spec.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


# ─── Dispatcher ──────────────────────────────────────────────────────────

def apply_tool(spec: MissionSpec, name: str, tool_input: Dict[str, Any]) -> Tuple[MissionSpec, str]:
    """Apply one tool call to the spec.

    Returns (updated_spec, result_message). On success, message is "ok"
    or a short status. On failure, message is a structured error the
    LLM can read and recover from — never raise out of this function.
    """
    # All handlers return (spec, message). We deepcopy to avoid mutating
    # the caller's spec until we know the operation will succeed.
    try:
        if name == "add_flight":
            return _handle_add_flight(spec, tool_input)
        elif name == "remove_flight":
            return _handle_remove_flight(spec, tool_input)
        elif name == "move_waypoint":
            return _handle_move_waypoint(spec, tool_input)
        elif name == "add_waypoint":
            return _handle_add_waypoint(spec, tool_input)
        elif name == "set_payload":
            return _handle_set_payload(spec, tool_input)
        elif name == "add_vehicle_group":
            return _handle_add_vehicle_group(spec, tool_input)
        elif name == "remove_vehicle_group":
            return _handle_remove_vehicle_group(spec, tool_input)
        elif name == "add_ship_group":
            return _handle_add_ship_group(spec, tool_input)
        elif name == "remove_ship_group":
            return _handle_remove_ship_group(spec, tool_input)
        elif name == "set_weather":
            return _handle_set_weather(spec, tool_input)
        elif name == "set_briefing":
            return _handle_set_briefing(spec, tool_input)
        elif name == "set_start_time":
            return _handle_set_start_time(spec, tool_input)
        elif name == "add_trigger":
            return _handle_add_trigger(spec, tool_input)
        elif name == "get_spec":
            return _handle_get_spec(spec, tool_input)
        elif name == "list_airports":
            return _handle_list_airports(spec, tool_input)
        elif name == "list_aircraft":
            return _handle_list_aircraft(spec, tool_input)
        elif name == "list_vehicles":
            return _handle_list_vehicles(spec, tool_input)
        elif name == "list_payload_presets":
            return _handle_list_payload_presets(spec, tool_input)
        elif name == "validate_spec":
            return _handle_validate_spec(spec, tool_input)
        else:
            return spec, f"Error: unknown tool '{name}'"
    except Exception as e:
        return spec, f"Error applying {name}: {type(e).__name__}: {e}"


# ─── Handler implementations ─────────────────────────────────────────────

def _handle_add_flight(spec: MissionSpec, inp: Dict[str, Any]) -> Tuple[MissionSpec, str]:
    """Add a new flight group."""
    flight = FlightGroup.model_validate(inp)
    new_spec = deepcopy(spec)
    if new_spec.flights is None:
        new_spec.flights = []
    # Check for duplicate name
    for f in new_spec.flights:
        if f.name == flight.name:
            return new_spec, f"Error: flight '{flight.name}' already exists"
    new_spec.flights.append(flight)
    return new_spec, f"ok: added flight '{flight.name}'"


def _handle_remove_flight(spec: MissionSpec, inp: Dict[str, Any]) -> Tuple[MissionSpec, str]:
    """Remove a flight group by name."""
    name = inp["name"]
    if not spec.flights:
        return spec, f"Error: no flights to remove"
    new_spec = deepcopy(spec)
    before = len(new_spec.flights)
    new_spec.flights = [f for f in new_spec.flights if f.name != name]
    if len(new_spec.flights) == before:
        return new_spec, f"Error: flight '{name}' not found"
    return new_spec, f"ok: removed flight '{name}'"


def _handle_move_waypoint(spec: MissionSpec, inp: Dict[str, Any]) -> Tuple[MissionSpec, str]:
    """Move a waypoint in a flight's route."""
    flight_name = inp["flight_name"]
    idx = inp["waypoint_index"]
    if not spec.flights:
        return spec, f"Error: no flights"
    flight = next((f for f in spec.flights if f.name == flight_name), None)
    if flight is None:
        return spec, f"Error: flight '{flight_name}' not found"
    if not flight.waypoints or idx >= len(flight.waypoints):
        return spec, f"Error: waypoint index {idx} out of range for flight '{flight_name}'"
    new_spec = deepcopy(spec)
    new_flight = next(f for f in new_spec.flights if f.name == flight_name)
    wp = new_flight.waypoints[idx]
    wp.x = inp["x"]
    wp.y = inp["y"]
    if "altitude" in inp and inp["altitude"] is not None:
        wp.altitude = inp["altitude"]
    if "speed" in inp and inp["speed"] is not None:
        wp.speed = inp["speed"]
    return new_spec, f"ok: moved waypoint {idx} of '{flight_name}'"


def _handle_add_waypoint(spec: MissionSpec, inp: Dict[str, Any]) -> Tuple[MissionSpec, str]:
    """Append a waypoint to a flight's route."""
    flight_name = inp["flight_name"]
    if not spec.flights:
        return spec, f"Error: no flights"
    flight = next((f for f in spec.flights if f.name == flight_name), None)
    if flight is None:
        return spec, f"Error: flight '{flight_name}' not found"
    new_spec = deepcopy(spec)
    new_flight = next(f for f in new_spec.flights if f.name == flight_name)
    wp = Waypoint(
        x=inp["x"],
        y=inp["y"],
        altitude=inp.get("altitude", 5000),
        speed=inp.get("speed", 400),
        name=inp.get("name", f"WP{len(new_flight.waypoints or []) + 1}"),
    )
    if new_flight.waypoints is None:
        new_flight.waypoints = []
    new_flight.waypoints.append(wp)
    return new_spec, f"ok: added waypoint '{wp.name}' to '{flight_name}'"


def _handle_set_payload(spec: MissionSpec, inp: Dict[str, Any]) -> Tuple[MissionSpec, str]:
    """Set payload on a flight."""
    flight_name = inp["flight_name"]
    if not spec.flights:
        return spec, f"Error: no flights"
    flight = next((f for f in spec.flights if f.name == flight_name), None)
    if flight is None:
        return spec, f"Error: flight '{flight_name}' not found"
    new_spec = deepcopy(spec)
    new_flight = next(f for f in new_spec.flights if f.name == flight_name)
    preset_name = inp.get("preset_name")
    pylons_data = inp.get("pylons")

    if preset_name:
        try:
            preset = payloads.resolve(new_flight.aircraft_type, preset_name)
            new_flight.payload = PayloadSpec(preset_name=preset_name)
        except ValueError as e:
            return new_spec, f"Error: {e}"
    elif pylons_data:
        new_flight.payload = PayloadSpec(
            pylons=pylons_data,
        )
    else:
        return new_spec, f"Error: must provide preset_name or pylons"

    return new_spec, f"ok: set payload on '{flight_name}'"


def _handle_add_vehicle_group(spec: MissionSpec, inp: Dict[str, Any]) -> Tuple[MissionSpec, str]:
    """Add a vehicle group."""
    group = VehicleGroup.model_validate(inp)
    new_spec = deepcopy(spec)
    if new_spec.vehicles is None:
        new_spec.vehicles = []
    for v in new_spec.vehicles:
        if v.name == group.name:
            return new_spec, f"Error: vehicle group '{group.name}' already exists"
    new_spec.vehicles.append(group)
    return new_spec, f"ok: added vehicle group '{group.name}'"


def _handle_remove_vehicle_group(spec: MissionSpec, inp: Dict[str, Any]) -> Tuple[MissionSpec, str]:
    """Remove a vehicle group by name."""
    name = inp["name"]
    if not spec.vehicles:
        return spec, f"Error: no vehicle groups"
    new_spec = deepcopy(spec)
    before = len(new_spec.vehicles)
    new_spec.vehicles = [v for v in new_spec.vehicles if v.name != name]
    if len(new_spec.vehicles) == before:
        return new_spec, f"Error: vehicle group '{name}' not found"
    return new_spec, f"ok: removed vehicle group '{name}'"


def _handle_add_ship_group(spec: MissionSpec, inp: Dict[str, Any]) -> Tuple[MissionSpec, str]:
    """Add a ship group."""
    group = ShipGroup.model_validate(inp)
    new_spec = deepcopy(spec)
    if new_spec.ships is None:
        new_spec.ships = []
    for s in new_spec.ships:
        if s.name == group.name:
            return new_spec, f"Error: ship group '{group.name}' already exists"
    new_spec.ships.append(group)
    return new_spec, f"ok: added ship group '{group.name}'"


def _handle_remove_ship_group(spec: MissionSpec, inp: Dict[str, Any]) -> Tuple[MissionSpec, str]:
    """Remove a ship group by name."""
    name = inp["name"]
    if not spec.ships:
        return spec, f"Error: no ship groups"
    new_spec = deepcopy(spec)
    before = len(new_spec.ships)
    new_spec.ships = [s for s in new_spec.ships if s.name != name]
    if len(new_spec.ships) == before:
        return new_spec, f"Error: ship group '{name}' not found"
    return new_spec, f"ok: removed ship group '{name}'"


def _handle_set_weather(spec: MissionSpec, inp: Dict[str, Any]) -> Tuple[MissionSpec, str]:
    """Replace weather block."""
    weather = Weather.model_validate(inp)
    new_spec = deepcopy(spec)
    new_spec.weather = weather
    return new_spec, "ok: weather updated"


def _handle_set_briefing(spec: MissionSpec, inp: Dict[str, Any]) -> Tuple[MissionSpec, str]:
    """Replace briefing block."""
    briefing = Briefing.model_validate(inp)
    new_spec = deepcopy(spec)
    new_spec.briefing = briefing
    return new_spec, "ok: briefing updated"


def _handle_set_start_time(spec: MissionSpec, inp: Dict[str, Any]) -> Tuple[MissionSpec, str]:
    """Set mission start time."""
    new_spec = deepcopy(spec)
    new_spec.start_time = inp["start_time"]
    return new_spec, f"ok: start_time set to {inp['start_time']}"


def _handle_add_trigger(spec: MissionSpec, inp: Dict[str, Any]) -> Tuple[MissionSpec, str]:
    """Add a trigger."""
    trigger = Trigger.model_validate(inp)
    new_spec = deepcopy(spec)
    if new_spec.triggers is None:
        new_spec.triggers = []
    new_spec.triggers.append(trigger)
    return new_spec, f"ok: added trigger '{trigger.name}'"


def _handle_get_spec(spec: MissionSpec, inp: Dict[str, Any]) -> Tuple[MissionSpec, str]:
    """Return current spec as JSON string."""
    return spec, spec.model_dump_json(indent=2)


def _handle_list_airports(spec: MissionSpec, inp: Dict[str, Any]) -> Tuple[MissionSpec, str]:
    """List airports for the current theatre."""
    theatre = spec.theatre or "Caucasus"
    info = theatres.get_info(theatre)
    if not info:
        return spec, f"No airports found for theatre '{theatre}'"
    airport_list = "\n".join(f"  - {a}" for a in info.notable_airports)
    return spec, f"Airports for {theatre}:\n{airport_list}"


def _handle_list_aircraft(spec: MissionSpec, inp: Dict[str, Any]) -> Tuple[MissionSpec, str]:
    """List aircraft type aliases, optionally filtered by role."""
    role = inp.get("role")
    if role:
        names = aircraft.list_by_role(role)
        if not names:
            return spec, f"No aircraft found for role '{role}'"
        return spec, f"Aircraft for role '{role}':\n" + "\n".join(f"  - {n}" for n in names)
    else:
        names = aircraft.all_aliases()
        return spec, "All aircraft:\n" + "\n".join(f"  - {n}" for n in names)


def _handle_list_vehicles(spec: MissionSpec, inp: Dict[str, Any]) -> Tuple[MissionSpec, str]:
    """List vehicle type aliases, optionally filtered by role."""
    role = inp.get("role")
    if role:
        names = vehicles.list_by_role(role)
        if not names:
            return spec, f"No vehicles found for role '{role}'"
        return spec, f"Vehicles for role '{role}':\n" + "\n".join(f"  - {n}" for n in names)
    else:
        names = vehicles.all_aliases()
        return spec, "All vehicles:\n" + "\n".join(f"  - {n}" for n in names)


def _handle_list_payload_presets(spec: MissionSpec, inp: Dict[str, Any]) -> Tuple[MissionSpec, str]:
    """List payload presets, optionally for a specific aircraft."""
    alias = inp.get("aircraft_alias")
    if alias:
        presets = payloads.list_for_aircraft(alias)
        if not presets:
            return spec, f"No payload presets for aircraft '{alias}'"
        return spec, f"Payload presets for {alias}:\n" + "\n".join(f"  - {p}" for p in presets)
    else:
        all_p = payloads.all_presets()
        lines = []
        for (ac, name), preset in all_p.items():
            lines.append(f"  {ac}: {name}")
        return spec, "All payload presets:\n" + "\n".join(lines)


def _handle_validate_spec(spec: MissionSpec, inp: Dict[str, Any]) -> Tuple[MissionSpec, str]:
    """Run validation over the spec and return issues."""
    from ...validation import validate
    report = validate(spec)
    if not report.issues:
        return spec, "Validation passed — no issues found."
    return spec, report.format()