# Schema reference

Models live in topical modules under
[`src/dcs_agentic/schemas/`](../src/dcs_agentic/schemas/) and are
re-exported from `dcs_agentic.schemas`. Built on Pydantic v2.

**Source module per concern:**

| Module | Contents |
|---|---|
| [`schemas/enums.py`](../src/dcs_agentic/schemas/enums.py) | `TaskType`, `StartType`, `Skill`, `ROE`, `AlarmState`, `Modulation` |
| [`schemas/primitives.py`](../src/dcs_agentic/schemas/primitives.py) | `Position`, `Waypoint` |
| [`schemas/weather.py`](../src/dcs_agentic/schemas/weather.py) | `Weather`, `WindGround`, `WindHeight` |
| [`schemas/briefing.py`](../src/dcs_agentic/schemas/briefing.py) | `Briefing` |
| [`schemas/payload.py`](../src/dcs_agentic/schemas/payload.py) | `Pylon`, `PayloadSpec` |
| [`schemas/flight.py`](../src/dcs_agentic/schemas/flight.py) | `FlightGroup` |
| [`schemas/ground.py`](../src/dcs_agentic/schemas/ground.py) | `VehicleGroup`, `StaticObject`, `FARP` |
| [`schemas/naval.py`](../src/dcs_agentic/schemas/naval.py) | `ShipGroup`, `CarrierOps` |
| [`schemas/bullseye.py`](../src/dcs_agentic/schemas/bullseye.py) | `Bullseye` |
| [`schemas/radio.py`](../src/dcs_agentic/schemas/radio.py) | `RadioComms`, `ATCFrequency`, `AWACSComms`, `TankerComms`, `JTACComms` |
| [`schemas/drawing.py`](../src/dcs_agentic/schemas/drawing.py) | `Zone`, `MapMarker` |
| [`schemas/triggers.py`](../src/dcs_agentic/schemas/triggers.py) | `TriggerKind`, `ActionKind`, `TriggerCondition`, `TriggerAction`, `Trigger` (v1 closed-union) |
| [`schemas/mission.py`](../src/dcs_agentic/schemas/mission.py) | `MissionSpec`, `Coalition`, `CustomScript`, `MissionGoal`, `SCHEMA_VERSION` |
| [`schemas/campaign.py`](../src/dcs_agentic/schemas/campaign.py) | `CampaignSpec`, `CampaignState`, `MissionLink`, `AfterAction` (shape locked, runner not built — Phase 10) |

Top-level entry point: **[`MissionSpec`](#missionspec)**. Multi-mission
campaigns use **`CampaignSpec`** (see [Campaign](#campaign-models)).

**To add a new top-level model:** put it in the matching topical
submodule (or a new one), then add a re-export line to
[`schemas/__init__.py`](../src/dcs_agentic/schemas/__init__.py).

## Conventions

- **Units:** speed is **km/h** (pydcs convention; the schema converts to
  m/s internally), altitude is **meters MSL**, coordinates are **meters
  in pydcs's `(x, y)` system** where `x` is north-south and `y` is
  east-west.
- **Optional fields** default to `None` unless noted.
- **Side** is `"blue"`, `"red"`, or `"neutrals"`.

---

## Enums

### `TaskType`
Aircraft / vehicle primary task.

| Value | Notes |
|---|---|
| `CAP` | Combat Air Patrol |
| `CAS` | Close Air Support |
| `SEAD` | Suppression of Enemy Air Defences |
| `DEAD` | Maps to SEAD in pydcs |
| `STRIKE` | Maps to GroundAttack |
| `SWEEP` | Maps to CAP |
| `INTERCEPT` | Maps to CAP |
| `PATROL` | Maps to CAP |
| `ESCORT` | |
| `AWACS` | |
| `REFUELING` | Tanker |
| `TRANSPORT` | |
| `RECON` | Maps to Reconnaissance |
| `ANTISHIP` | Maps to AntishipStrike |
| `GROUND_ATTACK` | |
| `AFAC` | Airborne Forward Air Controller |
| `EWR` | Early Warning Radar — has no pydcs flight task; vehicle/static role only |

### `StartType`
| Value | Behavior |
|---|---|
| `cold` | Engines off, parking |
| `warm` | Engines on, parking |
| `runway` | Active on runway |

### `Skill`
| Value |
|---|
| `Player`, `Client`, `Excellent`, `Good`, `High`, `Average`, `Random` |

### `ROE`
| Value | Behavior |
|---|---|
| `WeaponFree` | Engage any enemy group detected |
| `OpenFireWeaponFree` | Engage any enemy, prioritize task targets |
| `OpenFire` | Engage only task-specified targets |
| `ReturnFire` | Engage only if fired upon |
| `WeaponHold` | Hold fire under all circumstances |

### `AlarmState`
| Value | Behavior |
|---|---|
| `Green` | Normal alert state |
| `Red` | High alert state |
| `Auto` | Auto-determined based on threat |

### `Modulation`
| Value |
|---|
| `AM` |
| `FM` |

---

## Primitives

### `Position`
| Field | Type | Required | Description |
|---|---|---|---|
| `x` | float | ✓ | X (north-south) in meters |
| `y` | float | ✓ | Y (east-west) in meters |

### `Waypoint`
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `x` | float | ✓ | | meters |
| `y` | float | ✓ | | meters |
| `altitude` | int | | None | meters MSL |
| `speed` | float | | None | km/h |
| `name` | str | | None | display name |
| `type` | str | | None | pydcs type, e.g. `"Turning Point"`, `"Land"`, `"TakeOff"` |
| `action` | str | | None | one of `TURNING_POINT`, `FROM_PARKING_AREA`, `FROM_PARKING_AREA_HOT`, `FROM_RUNWAY`, `LANDING`, `FLY_OVER_POINT`, `OFF_ROAD` |
| `tasks` | List[TaskType] | | None | tasks executed at this point |
| `eta_locked` | bool | | False | lock ETA |
| `airdrome_id` | int | | None | airport ID for landing/takeoff |

---

## Weather

### `WindGround`, `WindHeight`
| Field | Type | Default | Description |
|---|---|---|---|
| `speed` | float | 0 | m/s |
| `dir` | float | 0 | degrees, 0–360 |

### `Weather`
| Field | Type | Default | Description |
|---|---|---|---|
| `season` | str | None | currently a no-op (pydcs has no direct season attr) |
| `qnh` | int | None | mmHg |
| `temperature` | float | None | °C at ground |
| `fog_enabled` | bool | False | |
| `fog_visibility` | float | None | meters; defaults to 1000 if fog enabled |
| `clouds_thickness` | int | None | 0–10 |
| `clouds_density` | int | None | 0–10 |
| `clouds_base` | int | None | meters |
| `clouds_iprecptns` | int | None | passed to `Weather.Preceptions(int)` |
| `wind_at_ground` | WindGround | None | |
| `wind_at_height` | WindHeight | None | applied at 8000m |
| `enable_dust` | bool | False | flag only; no further params yet |

---

## Coalition / Briefing

### `Coalition`
| Field | Type | Required | Description |
|---|---|---|---|
| `side` | str | ✓ | `"blue"`, `"red"`, or `"neutrals"` |
| `country` | str | ✓ | e.g. `"USA"`, `"Russia"` — see [`catalog.md`](catalog.md) |

### `Briefing`
| Field | Type | Default | Description |
|---|---|---|---|
| `description` | str | None | general briefing text |
| `blue_task` | str | None | blue-side task description |
| `red_task` | str | None | red-side task description |
| `images_blue` | List[str] | None | paths to briefing images (not yet wired) |
| `images_red` | List[str] | None | paths to briefing images (not yet wired) |

---

## Payloads

### `Pylon`
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `station` | int | ✓ | | Pylon station number (1–20) |
| `clsid` | str | ✓ | | DCS CLSID, e.g. `'{AIM-9X}'` |
| `quantity` | int | | 1 | Number of weapons on this station |

### `PayloadSpec`
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `preset_name` | str | | None | Named preset from `catalog/payloads.py` |
| `pylons` | List[Pylon] | | None | Explicit pylon assignments (override preset) |
| `fuel` | float | | None | Fuel fraction 0..1 |
| `chaff` | int | | None | Chaff dispenser count |
| `flare` | int | | None | Flare dispenser count |
| `gun` | int | | None | Gun ammo percentage 0..100 |

At least one of `preset_name` or `pylons` should usually be set. If
neither is set, the aircraft spawns with its DCS-default loadout.

Added as `payload: Optional[PayloadSpec]` on `FlightGroup`.

---

## Groups

### `FlightGroup`
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | str | ✓ | | group name |
| `aircraft_type` | str | ✓ | | alias — see [`catalog.md`](catalog.md) |
| `country` | str | ✓ | | |
| `side` | str | | `"blue"` | |
| `group_size` | int | | 1 | 1–4 |
| `task` | TaskType | | None | |
| `start_type` | StartType | | `cold` | |
| `airport` | str | | None | airport name on the theatre |
| `position` | Position | | None | used if no airport (inflight spawn) |
| `altitude` | int | | None | cruise altitude in meters |
| `speed` | float | | None | cruise speed in km/h |
| `skill` | Skill | | `Average` | |
| `waypoints` | List[Waypoint] | | None | |
| `late_activation` | bool | | False | |
| `livery` | str | | None | |
| `callsign` | List[str] | | None | one callsign per unit |
| `radio_frequency` | float | | None | MHz |
| `modulation` | int | | 0 | 0=AM, 1=FM |
| `payload` | PayloadSpec | | None | weapons, fuel, countermeasures |

Behavior:
- Either `airport` *or* `position` must be set. Otherwise the assembler
  emits `FLIGHT_BUILD_FAILED`.
- If `airport` is set but unknown on the theatre, a warning is recorded
  (`AIRPORT_NOT_FOUND`) and the flight falls back to a position spawn —
  which will then fail unless `position` is also set.
- `radio_frequency`, `modulation`, `callsign`, `livery` are applied
  post-construction.

### `VehicleGroup`
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | str | ✓ | | |
| `vehicle_type` | str | ✓ | | alias — see [`catalog.md`](catalog.md) |
| `country` | str | ✓ | | |
| `side` | str | | `"red"` | |
| `position` | Position | ✓ | | |
| `group_size` | int | | 1 | |
| `heading` | float | | 0 | degrees |
| `skill` | Skill | | `Average` | |
| `waypoints` | List[Waypoint] | | None | |
| `late_activation` | bool | | False | |
| `visible` | bool | | True | visible before mission start |
| `roe` | ROE | | None | rules of engagement |
| `alarm_state` | AlarmState | | None | alert level |

Vehicle waypoint speeds are passed straight to pydcs's
`VehicleGroup.add_waypoint(pos, speed=N)`, which treats `N` as km/h
(defaults to 32 km/h if unspecified).

### `FARP`
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | str | ✓ | | |
| `country` | str | ✓ | | |
| `side` | str | | `"blue"` | |
| `position` | Position | ✓ | | |
| `heading` | float | 0 | degrees | |
| `invisible` | bool | False | not rendered on map | |
| `has_fuel` | bool | True | | |
| `has_ammo` | bool | True | | |
| `has_repair` | bool | True | | |

### `ShipGroup`
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | str | ✓ | | |
| `ship_type` | str | ✓ | | alias — see [`catalog.md`](catalog.md) |
| `country` | str | ✓ | | |
| `side` | str | | `"blue"` | |
| `position` | Position | ✓ | | |
| `group_size` | int | | 1 | |
| `heading` | float | | 0 | |
| `skill` | Skill | | `Average` | |
| `waypoints` | List[Waypoint] | | None | |

### `CarrierOps`
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `ship_name` | str | ✓ | | must match a ship in `spec.ships` |
| `tacan_channel` | int | ✓ | | 1–126 |
| `tacan_mode` | str | | `"X"` | X or Y |
| `tacan_callsign` | str | | `"STN"` | |
| `icls_channel` | int | | None | 1–20 |
| `base_recovery_course` | float | | None | 0–359 degrees |
| `link4_mhz` | float | | None | frequency in MHz |

### `StaticObject`
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | str | ✓ | | |
| `type` | str | ✓ | | string name resolved against `dcs.statics.{Fortification,GroundObject,Warehouse,Cargo}` |
| `country` | str | ✓ | | |
| `side` | str | | `"neutrals"` | |
| `position` | Position | ✓ | | |
| `heading` | float | | 0 | |
| `dead` | bool | | False | render as destroyed |

Type resolution: tries the raw name first, then `name.replace("-", "_").replace("/", "_").replace(" ", "_")`.
Unknown types raise `STATIC_BUILD_FAILED`.

---

## Bullseye

### `Bullseye`
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `blue` | Position | | None | Blue-coalition bullseye reference |
| `red` | Position | | None | Red-coalition bullseye reference |

If absent, the assembler falls back to theatre defaults from
`catalog/theatres.py`.

---

## Radio communications

### `ATCFrequency`
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `airport` | str | ✓ | | airport name |
| `tower_mhz` | float | | None | |
| `ground_mhz` | float | | None | |
| `approach_mhz` | float | | None | |

### `AWACSComms`
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `flight_name` | str | ✓ | | AWACS flight in `spec.flights` |
| `callsign` | str | | `"Magic"` | |
| `frequency_mhz` | float | ✓ | | |
| `modulation` | Modulation | | `AM` | |

### `TankerComms`
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `flight_name` | str | ✓ | | tanker flight in `spec.flights` |
| `callsign` | str | | `"Texaco"` | |
| `frequency_mhz` | float | ✓ | | |
| `tacan_channel` | int | | None | 1–126 |
| `tacan_mode` | str | | `"X"` | |

### `JTACComms`
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `unit_name` | str | ✓ | | JTAC unit in `spec.vehicles` |
| `callsign` | str | | `"Warrior"` | |
| `frequency_mhz` | float | ✓ | | |
| `code` | int | | 1688 | laser code |

### `RadioComms`
| Field | Type | Description |
|---|---|---|
| `atc` | List[ATCFrequency] | Airport ATC frequency overrides |
| `awacs` | List[AWACSComms] | AWACS flights |
| `tankers` | List[TankerComms] | Tanker flights |
| `jtac` | List[JTACComms] | JTAC ground units |

All fields are optional. Added as `radios` on `MissionSpec`.

---

## Drawings and markers

### `Zone`
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | str | ✓ | | referenced by trigger conditions |
| `center` | Position | ✓ | | |
| `radius` | float | ✓ | | meters |
| `color` | str | | `rgba(255,0,0,0.3)` | CSS-style color string |

### `MapMarker`
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | str | ✓ | | label |
| `position` | Position | ✓ | | |
| `text` | str | ✓ | | F10 map display text |
| `coalition` | str | | `"all"` | `"blue"`, `"red"`, or `"all"` |

---

## Triggers (v1 closed-union)

Replaces the v0 loose placeholder. Conditions and actions use typed
enums with `model_validator` ensuring required fields are present.

### `TriggerKind`
| Value | Required fields |
|---|---|
| `time_reached` | `time_seconds` |
| `unit_dead` | `unit_name` |
| `group_dead` | `group_name` |
| `unit_in_zone` | `unit_name`, `zone_name` |
| `flag_true` | `flag_name` |

### `ActionKind`
| Value | Required fields |
|---|---|
| `show_message` | `message` |
| `play_sound` | `sound_file` |
| `set_flag` | `flag_name` |
| `activate_group` | `group_name` |
| `end_mission` | `winner` |
| `set_goal_score` | `score` |

### `TriggerCondition`
| Field | Type | Required | Description |
|---|---|---|---|
| `kind` | TriggerKind | ✓ | |
| `time_seconds` | float | | for TIME_REACHED |
| `unit_name` | str | | for UNIT_DEAD, UNIT_IN_ZONE |
| `group_name` | str | | for GROUP_DEAD |
| `zone_name` | str | | for UNIT_IN_ZONE |
| `flag_name` | str | | for FLAG_TRUE |
| `params` | Dict | | extensibility |

### `TriggerAction`
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `kind` | ActionKind | ✓ | | |
| `message` | str | | None | SHOW_MESSAGE |
| `duration_seconds` | float | | 10 | |
| `sound_file` | str | | None | PLAY_SOUND |
| `flag_name` | str | | None | SET_FLAG |
| `flag_value` | int | | 1 | SET_FLAG value |
| `group_name` | str | | None | ACTIVATE_GROUP |
| `winner` | str | | None | END_MISSION: "blue"/"red"/"draw" |
| `score` | int | | None | SET_GOAL_SCORE |

### `Trigger`
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | str | ✓ | | |
| `once` | bool | | True | Fire once (True) or continuous (False) |
| `coalition` | str | | None | "blue", "red", or None for all |
| `conditions` | List[TriggerCondition] | ✓ | | AND-ed together |
| `actions` | List[TriggerAction] | ✓ | | executed on fire |
| `params` | Dict | | None | extensibility |

---

## Custom scripts

### `CustomScript`
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | str | ✓ | | script name |
| `content` | str | | None | inline Lua source |
| `file_path` | str | | None | path to external `.lua` file |
| `language` | str | | `"Lua"` | |

Behavior:
- `name == "init"` with `content` → set as `mission.init_script`
- Otherwise, `file_path` set → `mission.init_script_file`
- All other variants are accepted but currently ignored

---

## Mission goals

### `MissionGoal`
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `description` | str | ✓ | | human-readable goal |
| `score_target` | int | | None | target score |
| `coalition` | str | | None | "blue" or "red" |
| `category` | str | | None | e.g. "intercept", "destroy", "capture" |
| `params` | Dict | | None | extensibility |

---

## MissionSpec (top-level)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | str | ✓ | | mission display name |
| `theatre` | str | | `"Caucasus"` | one of: Caucasus, PersianGulf, Syria, Nevada, Normandy, TheChannel, MarianaIslands, Falklands |
| `sortie` | str | | None | sortie identifier |
| `version` | int | | 20 | MIZ format version |
| `start_time` | float | | None | unix timestamp (naive datetime) |
| `coalitions` | List[Coalition] | | None | |
| `briefing` | Briefing | | None | |
| `weather` | Weather | | None | |
| `flights` | List[FlightGroup] | | None | |
| `vehicles` | List[VehicleGroup] | | None | |
| `ships` | List[ShipGroup] | | None | |
| `statics` | List[StaticObject] | | None | |
| `farps` | List[FARP] | | None | Forward arming/refuelling points |
| `carrier_ops` | List[CarrierOps] | | None | Carrier ops (TACAN, ICLS, BRC) |
| `triggers` | List[Trigger] | | None | v1 closed-union triggers |
| `zones` | List[Zone] | | None | Map zones |
| `markers` | List[MapMarker] | | None | F10 map markers |
| `bullseye` | Bullseye | | None | Reference points per coalition |
| `radios` | RadioComms | | None | ATC/AWACS/Tanker/JTAC comms |
| `mission_goals` | List[MissionGoal] | | None | Victory conditions |
| `custom_scripts` | List[CustomScript] | | None | |
| `agent_notes` | str | | None | freeform notes from the agent |

### Theatre validation

Unknown theatres raise `ValidationError` at parse time. Known set:
```
{Caucasus, PersianGulf, Syria, Nevada, Normandy, TheChannel,
 MarianaIslands, Falklands}
```

---

## Schema version

```python
from dcs_agentic.schemas import SCHEMA_VERSION
# "0.2.0"
```

---

## Campaign models

> **Shape locked, runner not built.** These models are defined in
> [`schemas/campaign.py`](../src/dcs_agentic/schemas/campaign.py) so the
> shape is stable for templates and tooling, but
> [`campaign/`](../src/dcs_agentic/campaign/) is still an empty stub.
> The Phase 10 runner will consume these models.

### `MissionLink`
One node in the campaign graph. Identifies a mission and declares
branching successors based on outcome.

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | str | ✓ | Unique within the campaign |
| `spec` | MissionSpec | | Inline mission |
| `spec_file` | str | | Path to a `.json` mission spec |
| `spec_template` | str | | Path to a Jinja2 template rendered against `CampaignState` |
| `next_on_blue_win` | str | | Next mission name on blue win |
| `next_on_red_win` | str | | Next mission name on red win |
| `next_on_draw` | str | | Next mission name on draw |
| `next_unconditional` | str | | Overrides outcome-based routing |
| `description` | str | | Author-facing |

Exactly one of `spec` / `spec_file` / `spec_template` must be set.
At least one `next_*` should be set unless this is a terminal node.

### `CampaignState`
Per-run save file. Mutates after every mission. `extra='allow'` so
unknown keys from older versions survive round-trip.

| Field | Type | Default | Description |
|---|---|---|---|
| `schema_version` | str | `"0.1.0"` | bump on breaking change |
| `current_mission` | str \| None | None | next mission name; None = campaign complete |
| `completed_missions` | List[str] | `[]` | in order |
| `score` | Dict[str, int] | `{"blue":0,"red":0}` | cumulative per side |
| `losses` | Dict[str, List[str]] | `{"blue":[],"red":[]}` | unit names lost per side |
| `captured_airfields` | Dict[str, str] | `{}` | airfield → owning side |
| `flags` | Dict[str, Any] | `{}` | persistent flags for template variation |
| `current_date` | datetime \| None | None | in-fiction date |
| `day_number` | int | 1 | day counter |

### `AfterAction`
Outcome of one mission. Submitted via `campaign report`.

| Field | Type | Description |
|---|---|---|
| `mission_name` | str | which mission this is for |
| `winner` | str \| None | `"blue"`, `"red"`, `"draw"`, or None |
| `blue_score`, `red_score` | int | |
| `blue_losses`, `red_losses` | List[str] | lost unit names |
| `captured` | Dict[str, str] | airfield → new owning side |
| `flags_set` | Dict[str, Any] | flags to carry into `state.flags` |
| `duration_seconds` | float \| None | |
| `notes` | str \| None | |

### `CampaignSpec`
Top-level campaign definition.

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | str | ✓ | |
| `theatre` | str | | default `"Caucasus"` |
| `description` | str | | |
| `author` | str | | |
| `start_mission` | str | ✓ | name of first mission |
| `missions` | List[MissionLink] | ✓ | min length 1 |
| `initial_state` | CampaignState | | seed copied at `campaign init` |
| `agent_notes` | str | | from the campaign architect agent |