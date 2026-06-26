# Pipeline reference

Covers [`MissionAssembler`](../src/dcs_agentic/pipeline/assembler.py),
the per-concern builders under
[`pipeline/builders/`](../src/dcs_agentic/pipeline/builders/), the report
system in [`errors.py`](../src/dcs_agentic/errors.py), and the order of
operations.

## High level

```
MissionSpec  ──▶  MissionAssembler.assemble()  ──▶  pydcs Mission  ──▶  .miz
                          │
                          ├──▶ build_coalitions(mission, spec, report)
                          ├──▶ build_weather(mission, spec, report)
                          ├──▶ build_flights(mission, spec, report)
                          ├──▶ build_ground(mission, spec, report)
                          ├──▶ build_naval(mission, spec, report)
                          ├──▶ build_statics(mission, spec, report)
                          ├──▶ build_triggers(mission, spec, report)
                          └──▶ build_custom_scripts(mission, spec, report)
                                              │
                                              └──▶  AssemblyReport (issues)
```

The orchestrator is intentionally thin (98 lines). All real work lives
in per-concern builder modules. To add a new concern: write
`pipeline/builders/<concern>.py` with a `build_<concern>(mission, spec,
report)` function and call it from `assemble()`.

## `MissionAssembler`

```python
from dcs_agentic.pipeline import MissionAssembler
from dcs_agentic.schemas import MissionSpec

spec = MissionSpec.model_validate_json(open("mission.json").read())
asm = MissionAssembler(spec, strict=False)
asm.save("output/mission.miz")

for issue in asm.report.issues:
    print(issue.severity, issue.code, issue.message)
```

### Constructor
| Arg | Type | Default | Description |
|---|---|---|---|
| `spec` | `MissionSpec` | — | the validated input |
| `strict` | `bool` | `False` | if True, `assemble()` raises `AssemblyError` when any error-severity issue is in the report |

### Methods
| Method | Description |
|---|---|
| `assemble() -> Mission` | builds and returns the pydcs `Mission`. Populates `self.report`. |
| `save(filepath: str) -> str` | calls `assemble()`, writes the `.miz`, returns the path. |

### Attributes
| Attribute | Description |
|---|---|
| `self.spec` | the input `MissionSpec` (read-only by convention) |
| `self.mission` | the pydcs `Mission` after `assemble()` runs (else `None`) |
| `self.report` | the `AssemblyReport` accumulator |
| `self.strict` | bool |

## Builder pattern

Every public builder has the same signature:

```python
def build_<concern>(mission: Mission, spec: MissionSpec, report: AssemblyReport) -> None:
    if spec.<concern> is None:
        return
    for item in spec.<concern>:
        try:
            _build_one(mission, item, report)
        except Exception as e:
            report.error(
                "<CONCERN>_BUILD_FAILED",
                f"{type(e).__name__}: {e}",
                context=item.name,
            )
```

Builders read the spec, mutate the mission, and accumulate issues. They
do not raise out of one-element failures — the failure of one flight
should not block the other flights from being built. Catastrophic
failures (e.g. unknown theatre) are recorded as errors and may halt
in strict mode at the orchestrator level.

### Per-concern builders

| Module | Function | What it builds | Status |
|---|---|---|---|
| [`builders/coalitions.py`](../src/dcs_agentic/pipeline/builders/coalitions.py) | `build_coalitions` | Adds countries to blue/red coalitions. Also exposes `get_or_add_country()` — the helper every group builder uses to attach groups to a country. | ✅ Complete |
| [`builders/weather.py`](../src/dcs_agentic/pipeline/builders/weather.py) | `build_weather` | Translates `spec.weather` to a pydcs `Weather` object. | ✅ Complete |
| [`builders/flights.py`](../src/dcs_agentic/pipeline/builders/flights.py) | `build_flights` | Three spawn paths: airport, inflight, manual fallback (when DCS payload Lua files aren't available). The fallback explicitly sets `group.task` to prevent the "every flight ships as CAS" silent bug. Applies `flight_spec.payload` (preset → pylons, or explicit pylons) to every unit. | ✅ Complete |
| [`builders/ground.py`](../src/dcs_agentic/pipeline/builders/ground.py) | `build_ground` | Vehicle groups + waypoints. | 🔶 ROE/AlarmState not yet wired |
| [`builders/naval.py`](../src/dcs_agentic/pipeline/builders/naval.py) | `build_naval` | Ship groups + waypoints. | 🔶 CarrierOps not yet wired |
| [`builders/statics.py`](../src/dcs_agentic/pipeline/builders/statics.py) | `build_statics` | Static objects (buildings, FARPs, dead vehicles). | ✅ Complete |
| [`builders/triggers.py`](../src/dcs_agentic/pipeline/builders/triggers.py) | `build_triggers` | Maps `TriggerKind`/`ActionKind` → pydcs `condition.*`/`action.*`; uses `TriggerOnce`/`TriggerContinious`; `MessageToCoalition` when `trigger.coalition` is set; group/unit/zone refs resolved by name with warn-and-skip on misses. | ✅ Complete |
| [`builders/custom_scripts.py`](../src/dcs_agentic/pipeline/builders/custom_scripts.py) | `build_custom_scripts` | Wires init script content / file path. | ✅ Complete |
| **`builders/drawings.py`** | `build_drawings` | **Not yet implemented.** Zones and map markers. | ❌ Missing |

### Shared helpers (`builders/__init__.py`)

The four enum mappers used by multiple builders:

| Function | Purpose |
|---|---|
| `skill_to_pydcs(Skill)` | spec Skill → `dcs.unit.Skill` |
| `start_type_to_pydcs(StartType)` | spec StartType → `dcs.mission.StartType` |
| `task_to_pydcs(TaskType)` | spec TaskType → pydcs task class (None for EWR) |
| `point_action_for_wp(Waypoint)` | spec waypoint action string → `dcs.point.PointAction` |

## Build order

`assemble()` calls builders in this order. Each may add issues to
`self.report` but does not abort on failure (except where noted).

1. **Theatre resolution** — `spec.theatre` → terrain class via
   `catalog.theatres.resolve()`. Unknown → `UNKNOWN_THEATRE` (error) +
   fall back to Caucasus.
2. **Basic info** (`_setup_basic_info`) — briefing texts, sortie,
   start time. `start_time` is converted to a tz-aware UTC datetime
   then stripped of `tzinfo` (pydcs wants naive). Using bare
   `fromtimestamp()` would interpret the timestamp in the host's
   local zone — don't.
3. **Coalitions** — `build_coalitions`.
4. **Weather** — `build_weather` (only if `spec.weather` is set).
5. **Flights** — `build_flights`.
6. **Vehicles** — `build_ground`.
7. **Ships** — `build_naval`.
8. **Statics** — `build_statics`.
9. **Triggers** — `build_triggers`. Conditions and actions are
   translated to pydcs classes; rules are appended to
   `mission.triggerrules.triggers`.
10. **Custom scripts** — `build_custom_scripts`.
11. **Strict check** — if `strict=True` and `report.has_errors()`, raise `AssemblyError`.

### Remaining builder work (Phase 4 tail)

Payload application is now inside [`builders/flights.py`](../src/dcs_agentic/pipeline/builders/flights.py) (`_apply_payload`)
rather than a separate builder. Outstanding:

| Builder | When it should run | What it consumes |
|---|---|---|
| `build_drawings` | After statics | `spec.zones`, `spec.markers` → pydcs drawing objects |
| `build_farps` | After ground | `spec.farps` → FARP static objects |
| `build_carrier_ops` | After ships | `spec.carrier_ops` → TACAN/ICLS/BRC on carriers |

**Known conversion required in Phase 4:**
- `AlarmState` enum values ("Green"/"Red"/"Auto") must be mapped to integers (0/1/2) when constructing pydcs `OptAlarmState(value=...)`.
- `ROE` enum values map 1:1 to `OptROE.Values` attribute names — use `getattr(OptROE.Values, roe_value)`.
- `Modulation` enum maps by name to `dcs.task.Modulation` — use `dcs.task.Modulation[ours.value]`.

## Unit conversions

All speed/altitude conversions go through
[`units.py`](../src/dcs_agentic/units.py). No bare `/ 3.6` or `* 1.852`
anywhere else in the codebase.

| Function | Conversion |
|---|---|
| `kmh_to_ms(v)` | km/h → m/s (used in `builders/flights.py` for waypoint speeds) |
| `ms_to_kmh(v)` | inverse |
| `kt_to_kmh(v)` | knots → km/h |
| `kmh_to_kt(v)` | inverse |
| `kt_to_ms(v)` | knots → m/s direct |
| `m_to_ft(v)` / `ft_to_m(v)` | altitude |

## Report system

Defined in [`errors.py`](../src/dcs_agentic/errors.py).

### `Severity`
| Value | Use |
|---|---|
| `INFO` | something happened (e.g. flight created) |
| `WARNING` | something fell back or substituted |
| `ERROR` | something failed |

### `AssemblyIssue`
| Field | Type | Description |
|---|---|---|
| `severity` | `Severity` | |
| `code` | str | stable identifier — see [Error codes](#error-codes) |
| `message` | str | human-readable |
| `context` | str \| None | usually a group name |
| `hint` | str \| None | how to fix; surfaces to agents |

### `AssemblyReport`
| Method / property | Description |
|---|---|
| `add(severity, code, message, context=None, hint=None)` | low-level |
| `info(code, message, **kw)` | shortcut |
| `warn(code, message, **kw)` | shortcut |
| `error(code, message, **kw)` | shortcut |
| `issues: List[AssemblyIssue]` | all entries |
| `errors`, `warnings` | filtered views |
| `has_errors() -> bool` | |
| `format() -> str` | multi-line human-readable rendering |

### `AssemblyError`
Raised when `strict=True` and the report has errors. Carries `.report`.

### `SpecValidationError`
Reserved for the future validation layer (Phase 7). Not raised by the
assembler today.

## Error codes

All codes currently emitted. These are stable — downstream code and
agents may match on them.

| Code | Severity | Emitter | When |
|---|---|---|---|
| `UNKNOWN_THEATRE` | error | assembler | `spec.theatre` not in the theatre map; falls back to Caucasus |
| `UNKNOWN_COUNTRY` | error | `build_coalitions` | country alias not in `catalog.countries` |
| `COALITION_SIDE_INVALID` | warning | `build_coalitions` | side is not 'blue' or 'red' |
| `AIRPORT_NOT_FOUND` | warning | `build_flights` | airport name not on theatre |
| `AIRCRAFT_PROXY` | warning | `build_flights` | aircraft alias resolves to a stand-in (e.g. Su-35 → Su_27) |
| `PAYLOADS_UNAVAILABLE` | warning | `build_flights` | pydcs cannot read DCS payload Lua files; manual fallback used |
| `PAYLOAD_PRESET_UNKNOWN` | error | `build_flights` | `PayloadSpec.preset_name` not found for this aircraft |
| `FLIGHT_CREATED` | info | `build_flights` | flight built successfully |
| `FLIGHT_BUILD_FAILED` | error | `build_flights` | exception during flight construction |
| `VEHICLE_CREATED` | info | `build_ground` | |
| `VEHICLE_BUILD_FAILED` | error | `build_ground` | |
| `SHIP_CREATED` | info | `build_naval` | |
| `SHIP_BUILD_FAILED` | error | `build_naval` | |
| `STATIC_CREATED` | info | `build_statics` | |
| `STATIC_BUILD_FAILED` | error | `build_statics` | |
| `TRIGGER_CREATED` | info | `build_triggers` | trigger rule built |
| `TRIGGER_BUILD_FAILED` | error | `build_triggers` | exception during trigger construction |
| `TRIGGER_NO_VALID_CONDITIONS` | warning | `build_triggers` | all conditions failed to resolve; rule skipped |
| `TRIGGER_NO_VALID_ACTIONS` | warning | `build_triggers` | all actions failed to resolve; rule skipped |
| `TRIGGER_GROUP_UNKNOWN` | warning | `build_triggers` | condition/action references an unknown group name |
| `TRIGGER_UNIT_UNKNOWN` | warning | `build_triggers` | condition references an unknown unit name |
| `TRIGGER_ZONE_UNKNOWN` | warning | `build_triggers` | condition references an unknown trigger zone |
| `TRIGGER_UNSUPPORTED_CONDITION` | warning | `build_triggers` | `TriggerKind` value has no pydcs mapping yet |
| `TRIGGER_UNSUPPORTED_ACTION` | warning | `build_triggers` | `ActionKind` value has no pydcs mapping yet |
| `TRIGGER_SOUND_NOT_WIRED` | warning | `build_triggers` | `PLAY_SOUND` emitted as an empty `SoundToAll` — no asset pipeline yet |
| `TRIGGER_SET_GOAL_SCORE_FALLBACK` | warning | `build_triggers` | `SET_GOAL_SCORE` emitted via `SetFlagValue` shim |
| `SCRIPT_INSTALLED` | info | `build_custom_scripts` | init script wired |
| `SCRIPT_IGNORED` | warning | `build_custom_scripts` | custom script with no content or file_path |

## Defaults applied silently (intentional)

| Field | Fallback |
|---|---|
| `Skill` not set | `Skill.AVERAGE` |
| `StartType` not set | `cold` |
| `group_size` not set | 1 |
| `Waypoint.altitude` not set | flight's `altitude`, else 5000m |
| `Waypoint.speed` not set | flight's `speed`, else 500 km/h |
| `vehicle.heading` not set | 0 |
| `vehicle waypoint speed` not set | 32 km/h |

These are reasonable defaults. They are not reported.
