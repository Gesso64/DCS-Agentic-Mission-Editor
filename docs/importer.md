# `.miz` importer

[`importer/miz_reader.py`](../src/dcs_agentic/importer/miz_reader.py)
loads a `.miz` file via pydcs's `Mission.load_file` and walks the
resulting in-memory mission to reconstruct a `MissionSpec`.

```python
from dcs_agentic.importer.miz_reader import import_miz

spec, report = import_miz("output/mission.miz")
print(spec.theatre, len(spec.flights or []))
for issue in report.issues:
    print(issue.severity, issue.code, issue.message)
```

`import_miz(path)` returns `(MissionSpec, AssemblyReport)`. Errors are
on the report, not raised — call sites decide whether to proceed.

## What round-trips today

| Field | Status | Notes |
|---|---|---|
| `theatre` | ✅ | From `mission.terrain.name` |
| `start_time` | ✅ | Converted to UTC unix timestamp |
| `briefing` | ✅ | description / blue_task / red_task strings |
| `coalitions` | ✅ | Only countries that own at least one group |
| `flights` (name, type, country, side, size) | ✅ | |
| `flights.task` | ✅ | Reverse-maps `g.task` string (e.g. `"CAP"`) to `TaskType.CAP` |
| `flights.airport` | ✅ | Resolved via the loaded terrain's `airports` dict (airdrome_id → name) |
| `flights.start_type` | ✅ | Inferred from first-waypoint action: `FromParkingArea` → COLD, `FromParkingAreaHot` → WARM, `FromRunway` → RUNWAY |
| `flights.waypoints` | ✅ | x, y, altitude; speed converted from m/s back to km/h. Parking spawn point is omitted when airport is set. |
| `flights.payload.pylons` | ✅ | Pylon dict → `Pylon(station, clsid, quantity=1)` |
| `flights.aircraft_type` alias upgrade | ✅ | Reverse-maps pydcs `unit_type.id` (e.g. `FA-18C_hornet`) to friendly alias (e.g. `F/A-18C`) when one exists |
| `vehicles` | ✅ | name, type, country, side, position, group_size, heading |
| `vehicles.vehicle_type` alias upgrade | ❌ | Comes back as the raw pydcs id (e.g. `SA-11 Buk LN 9A310M1` instead of `SA-11-LN`) |
| `ships` | ✅ | name, type, country, side, position, group_size |
| `statics` | ✅ | name, type, country, side, position, heading |

## What does not round-trip yet

| Section | Status | Code emitted |
|---|---|---|
| `weather` | ❌ | (silent — TODO) |
| `triggers` | ❌ | `IMPORT_TRIGGERS_DROPPED` warning if source had any |
| `zones` / `markers` (drawings) | ❌ | `IMPORT_DRAWINGS_DROPPED` warning |
| `farps`, `carrier_ops`, `bullseye`, `radios`, `mission_goals`, `custom_scripts` | ❌ | (silent — TODO) |

These will be added incrementally.

## Workaround: pydcs `load_payloads` KeyError

When DCS World isn't installed locally, pydcs's
`FlyingType.load_payloads()` raises `KeyError` — it indexes
`_payload_cache[payload_path]` before checking whether the path exists.
This is a pydcs bug, not a config issue.

The importer wraps `Mission.load_file` in a `_payload_loader_safe()`
context manager that temporarily replaces `FlyingType.load_payloads`
with a version that swallows `KeyError` / `FileNotFoundError` /
`OSError` and returns an empty payload dict. The original is restored
on context exit.

Practically: payload `clsid`s on the in-memory mission still come from
the .miz pylon dict (which has them inline), so the swallowed error
doesn't change what gets imported.

## Error codes

| Code | Severity | When |
|---|---|---|
| `MIZ_NOT_FOUND` | error | The path doesn't exist |
| `MIZ_LOAD_FAILED` | error | pydcs raised during `load_file` |
| `MIZ_LOAD_STATUS` | warning | pydcs returned a `StatusMessage` (e.g. old format) |
| `IMPORT_FLIGHT_FAILED` | warning | One flight failed to reconstruct; others continue |
| `IMPORT_VEHICLE_FAILED` | warning | One vehicle group failed |
| `IMPORT_SHIP_FAILED` | warning | One ship group failed |
| `IMPORT_STATIC_FAILED` | warning | One static failed |
| `IMPORT_TRIGGERS_DROPPED` | warning | Source had triggers; they weren't reverse-mapped |
| `IMPORT_DRAWINGS_DROPPED` | warning | Source had drawings/zones; they weren't reverse-mapped |

## Round-trip example

```python
from dcs_agentic.importer.miz_reader import import_miz
from dcs_agentic.pipeline import MissionAssembler
from dcs_agentic.schemas import MissionSpec, Coalition, FlightGroup, TaskType, StartType

# Build a .miz
spec_a = MissionSpec(
    name="RT", theatre="Caucasus",
    coalitions=[Coalition(side="blue", country="USA")],
    flights=[FlightGroup(
        name="Alpha", aircraft_type="F/A-18C", country="USA", side="blue",
        group_size=2, task=TaskType.CAP, start_type=StartType.COLD, airport="Batumi",
    )],
)
MissionAssembler(spec_a).save("output/rt.miz")

# Read it back
spec_b, report = import_miz("output/rt.miz")
assert spec_b.theatre == "Caucasus"
assert spec_b.flights[0].aircraft_type == "F/A-18C"
```
