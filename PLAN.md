# DCS Agentic Mission Editor — Implementation Plan

**Audience:** This document is the build plan for an AI coding assistant
(possibly with less context than the author of this plan). It is intentionally
explicit. Do not skip steps. Do not invent abbreviations. If something is
unclear, read the related source file before guessing.

**Project goal:** A tool that lets a human or an LLM agent design DCS World
missions and full campaigns. Output is `.miz` files that DCS opens correctly.
Input is either declarative JSON or natural-language prompts. The tool must
support both ground-up creation and editing existing missions. Campaigns are
a first-class concept, not a stretch goal.

**Non-goals (do not implement):**
- A GUI. CLI only.
- Real-time mission execution monitoring. (After-action parsing yes; live
  control no.)
- Hosting/multiplayer matchmaking.
- Anything outside producing/editing `.miz` files and orchestrating them
  into campaigns.

---

## Phase status

| Phase | Status | Notes |
|---|---|---|
| 1. Restructure | ✅ **DONE** | Module tree built; 5/5 tests pass; demo CLIs green |
| 2. Schema completeness | ✅ **DONE** | Payloads, bullseye, ATC, drawings, trigger v1, ROE/alarm state, FARPs, carrier ops, mission goals — 9/9 tests pass |
| 3. Catalog expansion | ✅ **DONE** | Role tags, payload presets (14 across 9 aircraft), theatre metadata, callsigns; 11/11 tests pass |
| 4. Builder refactor | ✅ **DONE** | All Phase-2 schema additions wired: payloads, ROE/AlarmState, FARPs, drawings (zones+markers), carrier ops (TACAN); ICLS/BRC/Link-4 surface as `CARRIER_OPS_PARTIAL` |
| 5. Triggers | ✅ **DONE** | Builder maps TriggerKind/ActionKind to pydcs condition/action classes; group/unit/zone refs resolved by name; coalition filter routes to `MessageToCoalition` |
| 6. Importer | ✅ **DONE** | `import_miz` round-trips theatre, coalitions (used countries only), flights+waypoints+pylons, vehicles, ships, statics; deferred sections (weather/triggers/drawings) warn but don't fail |
| 7. Validation | ✅ **DONE** | Five validators (coordinate / fuel / weapons / route / refs); `MissionAssembler(validate=True)` + `dcs-agentic validate` CLI |
| 8. Agent v1 (designer) | ✅ **DONE** | `design_mission()` with retry on validation failure; stub-LLM tests in `tests/test_agents.py` |
| 9. Agent v2 (editor) | ✅ **DONE** | 19 tools wired through `apply_tool` dispatcher; tool_use/tool_result history threaded correctly; full offline tool-surface tests |
| 10. Campaign | ✅ **DONE** | `CampaignRunner` load/record/branch + `design_campaign` + `render_mission` via Jinja templates; CLI `campaign init/run/report/inspect` |
| 11. After-action | ✅ **DONE** | `LUA_HOOK_SCRIPT` + `parse_lua_callback` + `parse_tacview` + `load_outcome` autodispatch; CLI `report --from <file>` |
| 12. CLI polish | ⬜ TODO | |

---

## 0. How to use this plan

Phases are roughly in dependency order. Each phase has:

- **Goal** — what success looks like
- **Files** — concrete paths to create or modify
- **Steps** — ordered, atomic
- **Acceptance criteria** — testable, runnable
- **Anti-patterns** — mistakes prior implementations made that you should not repeat

Work top-to-bottom. Ship each phase as a coherent unit: tests passing,
documentation updated, no dead code left behind. After each phase, run
`pytest tests/` and only proceed if all tests pass.

**Critical rule:** do not bypass the assembly report. Every warning, every
substitution, every fallback must go through `AssemblyReport`. If you find
yourself writing `print(f"WARN: ...")` or `sys.stderr.write(...)` in the
assembly path, stop and use `self.report.warn(...)` instead. Agents depend
on structured issues to self-correct.

---

## 0.1 Execution model — which model does which work

The Claude Code session this plan runs in has three model tiers configured:

| Tier | Model | Cost (in/out per 1M tok) | Context | Role |
|---|---|---|---|---|
| **Advisor** | Claude Sonnet (latest) | $3 / $15 | 1M | Architecture decisions, ambiguous calls, hard reviews |
| **Agent** | GLM-5.2 | $0.95 / $3 | 1M | Implements this plan turn-by-turn |
| **Subagent** | DeepSeek V4 Flash | $0.09 / $0.18 | 1M | Parallel research, file listing, grep, lookup |

**If you are reading this as the Agent (GLM-5.2):** you are competent at
mechanical work but less reliable than Sonnet at: holding consistency across
many files at once, inferring intent from sparse hints, multi-step
architectural reasoning. This plan compensates by being explicit. Do not
take shortcuts. When the plan says "the obvious approach," there is no
obvious approach — read the named source files first.

### When to escalate to the Advisor

Send a focused question to the Advisor (via the SendMessage tool, addressing
the `claude` agent) **before** starting work on:

- Any phase whose acceptance criteria you cannot describe in your own words
- Any cross-file refactor touching 5+ files at once (most of Phase 1, Phase 4)
- Any case where you would otherwise modify the architecture documented in
  §"Target module layout" (extension is fine; reshape needs approval)
- Any case where pydcs's API genuinely does not document what you need and
  the source is ambiguous (Phase 5 triggers, Phase 6 importer are high-risk)
- Any moment you would normally have phrased "I'll assume X" — assume nothing

Frame escalations as: "Goal: …. I read X, Y, Z. The unclear point is …. My
proposed approach is …. Approve or correct?" Do not dump file contents into
the message — the Advisor can read files itself.

### When to spawn a Subagent (DeepSeek V4 Flash)

Spawn one for **read-only, parallelizable** research. They are ~10× cheaper
per call than the Agent. Good fits:

- "Find every place in `.venv/.../dcs/` that uses `MovingPoint.tasks`"
- "List every static type defined under `dcs.statics.Fortification`"
- "Read these 4 pydcs source files and summarize the API surface for triggers"
- "Verify whether `dcs.action.MessageToAll` accepts a coalition filter"

Bad fits (do these yourself):

- Anything that writes code or changes files
- Multi-step reasoning chains where each step depends on the last
- Anything where the result needs interpretation against this plan

Use the Explore subagent type for searches; use general-purpose for "read
these files and summarize." Always specify "report in under 200 words" so
they don't bloat your context.

### When to checkpoint with the human

Stop and ask the user before:

- Any phase boundary (after Phase N tests pass, summarize and confirm before
  starting Phase N+1)
- Any time you'd add a dependency not listed in §"Standing rules" #7
- Any time you'd diverge from this plan's structure
- Any time `pytest` is failing in a way you cannot diagnose in 3 attempts

### Caching and turn economics

Anthropic prompt cache TTL is 5 minutes. The Agent is GLM, which does not
share Anthropic's cache, but the underlying provider (OpenRouter) has its
own caching for repeat prefixes. Practical rules:

- Do related file edits in one batch. Re-reading the same file three turns
  apart costs you the full read each time.
- Run `pytest` once at the end of a logical chunk, not after every edit.
- If you must wait for something (e.g. a long-running command), use the
  Bash `run_in_background` flag — don't sleep, don't poll.

### In-product agent model choices (used by the *runtime*, not by you)

These are the models the **tool itself** will call when shipping Phases
8–10 (the agentic features). Documented here so the Agent doesn't have
to re-derive them.

| Agent | Default model | Why |
|---|---|---|
| Mission designer (one-shot, Phase 8) | Claude Sonnet | Highest one-shot reasoning quality; schema-heavy; runs once per mission |
| Editor (multi-turn tool calls, Phase 9) | GLM-5.2 | Many cheap turns; tools constrain reasoning |
| Campaign architect (top-level, Phase 10) | Claude Sonnet | Cross-mission reasoning, narrative coherence |
| Per-mission template renderer (Phase 10) | GLM-5.2 | Called inside the campaign loop; routine |
| Lookup / validation tool handlers | (none — pure code) | No LLM required |
| After-action parser (Phase 11) | (none — pure code) | DCS Lua callback or TacView is structured data |

Honor the user's existing LiteLLM proxy aliases (`claude-opus-4-7`,
`claude-sonnet-4-6`, `claude-*`) via `ANTHROPIC_BASE_URL`. Do not bake
specific provider names into the code — the proxy is the indirection.

---

## Architecture

### The contract

```
┌─────────────────┐    ┌──────────────┐    ┌───────────────┐    ┌──────────┐
│ Human / LLM     │───▶│ MissionSpec  │───▶│ Assembler     │───▶│ .miz     │
│ (JSON / tools)  │    │ (Pydantic)   │    │ + Builders    │    │          │
└─────────────────┘    └──────────────┘    └───────────────┘    └──────────┘
                              ▲                                       │
                              │                                       ▼
                              └───────────────────── Importer ────────┘

         ┌──────────────────────────────────────────────────────────────┐
         │                  Campaign layer                              │
         │  CampaignSpec → CampaignRunner → MissionSpec[]               │
         │  AfterAction(.miz)  → updated CampaignState                  │
         └──────────────────────────────────────────────────────────────┘
```

**Why Pydantic-as-IR:**

1. LLMs produce JSON better than any other format. Pydantic's
   `model_json_schema()` is the LLM contract.
2. Validation is automatic and structured.
3. The spec is diffable, version-controllable, and round-trippable.
4. The same model works for one-shot generation, incremental edits via
   tool calls, and campaign state.

**Why split into modules:** the current `schemas/__init__.py` is one file
holding every model; `pipeline/assembler.py` is 700+ lines doing eight
unrelated things. Both will become unmaintainable as the schema grows to
cover payloads, ATC, drawings, triggers, and campaigns. Splitting now is
cheap; splitting later is invasive.

### Target module layout

```
src/dcs_agentic/
├── __init__.py
├── __main__.py                 # thin CLI dispatcher → cli/*
├── errors.py                   # AssemblyReport, AssemblyError, SpecValidationError
├── units.py                    # unit conversions (km/h ↔ m/s ↔ kt, m ↔ ft)
│
├── schemas/                    # All Pydantic models. Public contract.
│   ├── __init__.py             # re-exports
│   ├── primitives.py           # Position, Waypoint, BoundingBox
│   ├── enums.py                # TaskType, StartType, Skill, ROE, AlarmState, Modulation
│   ├── weather.py              # Weather, Wind, CloudPreset
│   ├── payload.py              # PayloadItem, PayloadPreset, Pylon
│   ├── radio.py                # RadioComms, ATCFrequency, JTACComms
│   ├── flight.py               # FlightGroup, FormationKind, AirToAirRefuel
│   ├── ground.py               # VehicleGroup, StaticObject, FARP
│   ├── naval.py                # ShipGroup, CarrierOps
│   ├── triggers.py             # Trigger, Condition, Action
│   ├── drawing.py              # Drawing, Zone, MapMarker
│   ├── briefing.py             # Briefing, BriefingImage
│   ├── bullseye.py             # Bullseye
│   ├── mission.py              # MissionSpec
│   └── campaign.py             # CampaignSpec, MissionLink, CampaignState
│
├── catalog/                    # Lookup tables and domain knowledge
│   ├── __init__.py
│   ├── aircraft.py             # Aliases + capability metadata
│   ├── helicopters.py
│   ├── vehicles.py
│   ├── ships.py
│   ├── statics.py
│   ├── countries.py
│   ├── theatres.py             # Airports per theatre, default bullseyes, bounds
│   ├── payloads.py             # Named loadout presets per aircraft
│   └── callsigns.py            # AWACS, tanker, JTAC, flight callsigns
│
├── pipeline/                   # Spec → Mission → .miz
│   ├── __init__.py
│   ├── assembler.py            # MissionAssembler orchestrator (thin)
│   └── builders/               # Per-element builders
│       ├── __init__.py
│       ├── coalitions.py
│       ├── weather.py
│       ├── flights.py
│       ├── ground.py
│       ├── naval.py
│       ├── statics.py
│       ├── triggers.py
│       ├── drawings.py
│       └── payloads.py
│
├── importer/                   # .miz → MissionSpec
│   ├── __init__.py
│   └── miz_reader.py
│
├── validation/                 # Cross-cutting checks beyond Pydantic
│   ├── __init__.py
│   ├── fuel_range.py           # Will this flight reach its waypoints?
│   ├── weapons_match.py        # Is payload compatible with task?
│   ├── coordinate_sanity.py    # Are coords within theatre bounds?
│   └── route_sanity.py         # Waypoints in order, no impossible turns
│
├── campaign/                   # Multi-mission orchestration
│   ├── __init__.py
│   ├── state.py
│   ├── runner.py
│   ├── branching.py
│   └── after_action.py
│
├── agents/                     # LLM agent layer
│   ├── __init__.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py           # Anthropic SDK wrapper
│   │   └── messages.py
│   ├── prompts/                # Plain-text system prompts
│   │   ├── mission_designer.md
│   │   ├── editor.md
│   │   ├── campaign_planner.md
│   │   └── after_action.md
│   ├── tools/                  # Tool definitions for Claude tool-use
│   │   ├── __init__.py
│   │   ├── mutations.py        # add_flight, move_waypoint, etc.
│   │   ├── lookups.py          # list_airports, list_aircraft, etc.
│   │   └── campaign_ops.py
│   ├── mission_agent.py        # From-scratch designer
│   ├── editor_agent.py         # Modifies existing spec
│   └── campaign_agent.py
│
└── cli/
    ├── __init__.py
    ├── build.py                # spec.json → mission.miz
    ├── design.py               # prompt → spec → miz
    ├── edit.py                 # miz → spec → modified → miz
    ├── inspect.py              # show what's in a .miz
    └── campaign.py             # campaign run/advance/inspect
```

---

## Phase 1 — Restructure (mechanical, no behavior change)

> ✅ **DONE.** This phase was executed by the Advisor (Claude Sonnet) in
> the session that produced this plan. The module tree, builders, catalog,
> units, errors, and all stubs are in place; 5/5 tests pass; both demo
> CLIs (`--demo-cap`, `--demo-strike`) build a valid `.miz` end-to-end.
> The text below is retained for context only — do not re-execute.

**Goal:** move existing code into the target layout without changing what
it does. Tests must pass before and after.

> **Execution notes (read before starting):**
> - This is the **highest-risk phase for GLM** because it touches many files
>   at once and consistency across them is what makes it correct.
> - **Escalate to the Advisor** with your file move plan *before* you start
>   moving anything. The Advisor can spot a wrong split in 30 seconds; you
>   will spend an hour discovering it via test failures.
> - **Subagent the survey:** before any edits, dispatch one DeepSeek
>   subagent to "list every public symbol exported from
>   `src/dcs_agentic/schemas/__init__.py` and `src/dcs_agentic/pipeline/assembler.py`,
>   noting which are used by tests and which by `__main__.py`. Under 200
>   words." Use the result to plan re-exports.
> - **Move one concern at a time** with `pytest` between each move. Do not
>   move all schemas in one commit and all builders in the next. The right
>   granularity: one file moved → tests pass → commit → next.
> - **Do not optimize while moving.** If you spot a bug or a simplification,
>   write it down and do it in a separate commit after the restructure
>   lands. Mixing cleanups with moves is how the restructure gets reverted.

### Files

Create the directory tree above (empty `__init__.py` files where needed).
Move the existing code as follows:

| From | To |
|---|---|
| `schemas/__init__.py` (the giant file) | Split into the files listed under `schemas/` |
| `pipeline/assembler.py` lookup maps | `catalog/aircraft.py`, `catalog/vehicles.py`, `catalog/ships.py`, `catalog/statics.py`, `catalog/countries.py` |
| `pipeline/assembler.py` `_resolve_*` helpers | Move to matching `catalog/*.py` |
| `pipeline/assembler.py` enum mappers (`_skill_to_pydcs`, `_task_to_pydcs`, `_start_type_to_pydcs`, `_point_action_for_wp`) | new `pipeline/builders/__init__.py` (private) |
| `pipeline/assembler.py` `_setup_*` methods | corresponding `pipeline/builders/*.py` files |

### Steps

1. **Keep public imports stable.** `schemas/__init__.py` must continue to
   re-export the original names so `from dcs_agentic.schemas import MissionSpec, FlightGroup, ...`
   keeps working. Use explicit re-exports:
   ```python
   from .mission import MissionSpec
   from .flight import FlightGroup
   from .ground import VehicleGroup, StaticObject
   # ...
   __all__ = ["MissionSpec", "FlightGroup", ...]
   ```

2. **Create `units.py`** with explicit converters. The current ambiguity
   around km/h vs knots vs m/s caused real bugs. Put it behind named functions:
   ```python
   def kmh_to_ms(v: float) -> float: return v / 3.6
   def kt_to_kmh(v: float) -> float: return v * 1.852
   def kt_to_ms(v: float) -> float:  return v * 0.5144
   def m_to_ft(v: float) -> float:   return v * 3.281
   def ft_to_m(v: float) -> float:   return v / 3.281
   ```
   Builders must call these by name. No bare `/ 3.6` anywhere outside `units.py`.

3. **Split the assembler.** `pipeline/assembler.py` becomes a thin orchestrator:
   ```python
   class MissionAssembler:
       def __init__(self, spec, strict=False):
           self.spec = spec
           self.strict = strict
           self.report = AssemblyReport()
           self.mission: Optional[Mission] = None

       def assemble(self) -> Mission:
           self.mission = Mission(terrain=resolve_terrain(self.spec.theatre, self.report))
           build_basic_info(self.mission, self.spec, self.report)
           build_coalitions(self.mission, self.spec, self.report)
           build_weather(self.mission, self.spec, self.report)
           build_flights(self.mission, self.spec, self.report)
           build_ground(self.mission, self.spec, self.report)
           build_naval(self.mission, self.spec, self.report)
           build_statics(self.mission, self.spec, self.report)
           build_triggers(self.mission, self.spec, self.report)
           build_drawings(self.mission, self.spec, self.report)
           build_custom_scripts(self.mission, self.spec, self.report)
           if self.strict and self.report.has_errors():
               raise AssemblyError(self.report)
           return self.mission
   ```
   Each `build_*` function lives in its own `builders/*.py` and takes
   `(mission, spec, report)`. No shared mutable state between builders.

4. **Move catalog data out.** `_build_aircraft_map`, `_build_vehicle_map`,
   `_build_ship_map`, the proxy aliases — these belong in `catalog/`.
   The `_resolve_*` functions become module-level functions like
   `catalog.aircraft.resolve("F/A-18C")` returning a pydcs class or
   raising `UnknownTypeError` (defined in `errors.py`).

5. **Run tests** after the restructure. They must still pass without
   modification. If a test breaks, your re-exports are wrong — do not
   modify the test, fix the imports.

### Acceptance

- `pytest tests/` passes 5/5
- `python -m dcs_agentic --demo-cap` produces `output/mission.miz`
- No file in `src/` exceeds 300 lines
- No `print()` calls in `pipeline/`, `catalog/`, or `schemas/` (only `cli/`)

### Anti-patterns

- Do **not** create one giant `catalog/__init__.py` that re-exports everything.
  The split is the point — each module is one concern.
- Do **not** copy code between phases "for now." If a function moves, it moves
  once, with all callers updated in the same commit.
- Do **not** add backward-compat shims like "if old import path used, re-export."
  This is a tiny codebase. Update callers in place.

---

## Phase 2 — Schema completeness

**Goal:** the spec must cover everything a serious DCS mission designer
uses. Today it covers maybe 40%. Without these, the agent cannot produce
real missions.

### What's missing today

| Concept | Why it's required |
|---|---|
| **Payloads** | Every flight has weapons. Without them, F/A-18s spawn empty. |
| **Bullseye** | DCS navigation reference; every mission has one. |
| **ATC frequencies** | Pilots need to know tower freqs. |
| **AWACS/Tanker/JTAC comms** | Co-op coordination depends on it. |
| **Drawings/Zones** | Combat zones, no-fly zones, target boxes. |
| **Mission goals** | DCS's scoring system. |
| **FARPs** | Helicopter ops, ground campaigns. |
| **Carrier ops** (TACAN, ICLS, BRC) | Naval missions. |
| **ROE / Alarm state** | Ground units need behavior modes. |
| **Triggers v1** | At minimum: time-based, flag-based, unit-killed. |
| **Failure/Win conditions** | Mission success criteria. |

### Files to add or expand

#### `schemas/payload.py`
```python
class Pylon(BaseModel):
    station: int = Field(..., ge=1, le=20, description="Pylon station number")
    clsid: str = Field(..., description="DCS CLSID, e.g. '{AIM-9X}'")
    quantity: Optional[int] = Field(1, ge=1)

class PayloadSpec(BaseModel):
    preset_name: Optional[str] = Field(
        None, description="Named preset from catalog/payloads.py; "
                         "if set, pylons may be omitted")
    pylons: Optional[List[Pylon]] = Field(
        None, description="Explicit pylon assignments; override preset")
    fuel: Optional[float] = Field(None, ge=0, le=1, description="Fuel fraction 0..1")
    chaff: Optional[int] = Field(None, ge=0)
    flare: Optional[int] = Field(None, ge=0)
    gun: Optional[int] = Field(None, ge=0, le=100, description="Gun ammo percentage")
```
Add `payload: Optional[PayloadSpec]` to `FlightGroup`.

#### `schemas/bullseye.py`
```python
class Bullseye(BaseModel):
    blue: Optional[Position] = None
    red: Optional[Position] = None
```
Add `bullseye: Optional[Bullseye]` to `MissionSpec`. If absent, the assembler
uses the theatre default from `catalog/theatres.py`.

#### `schemas/radio.py`
```python
class ATCFrequency(BaseModel):
    airport: str
    tower_mhz: Optional[float] = None
    ground_mhz: Optional[float] = None
    approach_mhz: Optional[float] = None

class AWACSComms(BaseModel):
    flight_name: str           # which flight is the AWACS
    callsign: str = "Magic"
    frequency_mhz: float
    modulation: Modulation = Modulation.AM

class TankerComms(BaseModel):
    flight_name: str
    callsign: str = "Texaco"
    frequency_mhz: float
    tacan_channel: Optional[int] = None
    tacan_mode: Optional[str] = "X"

class JTACComms(BaseModel):
    unit_name: str             # which ground unit is JTAC
    callsign: str = "Warrior"
    frequency_mhz: float
    code: Optional[int] = Field(1688, description="Laser code")
```
Add `radios: Optional[RadioComms]` aggregating these into `MissionSpec`.

#### `schemas/drawing.py`
Mirrors pydcs's `dcs.drawing.*`. Start minimal:
```python
class Zone(BaseModel):
    name: str
    center: Position
    radius: float = Field(..., description="meters")
    color: str = "rgba(255,0,0,0.3)"

class MapMarker(BaseModel):
    name: str
    position: Position
    text: str
    coalition: str = "blue"  # or 'red', 'all'
```
Add `zones: Optional[List[Zone]]`, `markers: Optional[List[MapMarker]]` to
`MissionSpec`. Defer arrows/polygons to a later sub-phase.

#### `schemas/triggers.py` (v1)
The current placeholder is too vague to implement. Replace with a closed
union of supported trigger types:
```python
class TriggerKind(str, Enum):
    TIME_REACHED       = "time_reached"
    UNIT_DEAD          = "unit_dead"
    GROUP_DEAD         = "group_dead"
    UNIT_IN_ZONE       = "unit_in_zone"
    FLAG_TRUE          = "flag_true"

class ActionKind(str, Enum):
    SHOW_MESSAGE       = "show_message"
    PLAY_SOUND         = "play_sound"
    SET_FLAG           = "set_flag"
    ACTIVATE_GROUP     = "activate_group"
    END_MISSION        = "end_mission"
    SET_GOAL_SCORE     = "set_goal_score"

class TriggerCondition(BaseModel):
    kind: TriggerKind
    # one of these is populated based on kind; use field_validator
    time_seconds: Optional[float] = None
    unit_name: Optional[str] = None
    group_name: Optional[str] = None
    zone_name: Optional[str] = None
    flag_name: Optional[str] = None

class TriggerAction(BaseModel):
    kind: ActionKind
    message: Optional[str] = None
    duration_seconds: Optional[float] = 10
    sound_file: Optional[str] = None
    flag_name: Optional[str] = None
    group_name: Optional[str] = None
    winner: Optional[str] = None    # 'blue' / 'red' / 'draw'
    score: Optional[int] = None

class Trigger(BaseModel):
    name: str
    once: bool = True
    coalition: Optional[str] = Field(None, description="'blue', 'red', or None for all")
    conditions: List[TriggerCondition]  # AND-ed
    actions: List[TriggerAction]
```

#### `schemas/ground.py` extensions
```python
class FARP(BaseModel):
    name: str
    country: str
    side: str = "blue"
    position: Position
    heading: float = 0
    invisible: bool = False
    has_fuel: bool = True
    has_ammo: bool = True
    has_repair: bool = True
```
Add `farps: Optional[List[FARP]]` to `MissionSpec`.

Add to `VehicleGroup`:
- `roe: Optional[ROE]` — Free, Hold, Return, Weapon
- `alarm_state: Optional[AlarmState]` — Green, Red, Auto

#### `schemas/naval.py` extensions
```python
class CarrierOps(BaseModel):
    ship_name: str             # which ship in spec.ships
    tacan_channel: int = Field(..., ge=1, le=126)
    tacan_mode: str = "X"
    tacan_callsign: str = "STN"
    icls_channel: Optional[int] = Field(None, ge=1, le=20)
    base_recovery_course: Optional[float] = Field(
        None, ge=0, lt=360, description="BRC in degrees")
    link4_mhz: Optional[float] = None
```
Add `carrier_ops: Optional[List[CarrierOps]]` to `MissionSpec`.

#### `schemas/mission.py` — `MissionSpec` additions
```python
mission_goals: Optional[List[MissionGoal]] = None
zones: Optional[List[Zone]] = None
markers: Optional[List[MapMarker]] = None
bullseye: Optional[Bullseye] = None
farps: Optional[List[FARP]] = None
carrier_ops: Optional[List[CarrierOps]] = None
radios: Optional[RadioComms] = None
```

### Acceptance

- Every new model has at least one example in `tests/fixtures/*.json` and
  loads cleanly with `MissionSpec.model_validate_json(...)`.
- `MissionSpec.model_json_schema()` is exported to `schemas/mission.schema.json`
  by a `scripts/dump_schema.py` script. Add a CI-friendly test that the
  on-disk schema matches what the model generates (so schema drift is caught).
- All existing tests still pass.

### Anti-patterns

- Do **not** make every new field required. Default to `Optional[...] = None`.
  The schema is the LLM contract; unnecessary required fields force the
  agent to invent values.
- Do **not** validate things across models with Pydantic validators (e.g.
  "this trigger references a flight name that exists"). Cross-references
  belong in `validation/`, not in Pydantic. Pydantic only validates the
  shape of one object.
- Do **not** add fields you can't assemble in Phase 4. If you add a schema
  field, the corresponding builder must populate the .miz from it. Schema
  without assembler = silent data loss.

---

## Phase 3 — Catalog expansion

**Goal:** the catalog is the *domain knowledge* layer. Agents and humans
will refer to friendly names. The catalog must cover enough of DCS for
real missions.

### Files

#### `catalog/aircraft.py`
Move existing aliases here. Add a structured model per type:
```python
@dataclass(frozen=True)
class AircraftInfo:
    alias: str                 # user-facing name, e.g. "F/A-18C"
    pydcs_class: type          # pydcs class
    role: tuple[str, ...]      # ("multirole", "strike", "cap")
    is_player_flyable: bool
    is_proxy: bool = False     # True if substituting for a not-yet-modelled jet
    default_country: str = "USA"
    notes: str = ""

CATALOG: dict[str, AircraftInfo] = {...}

def resolve(name: str) -> type: ...
def list_by_role(role: str) -> list[str]: ...
def all_aliases() -> list[str]: ...
```
Agent tools (`list_aircraft`, `aircraft_info`) consume this directly.

#### `catalog/payloads.py`
The most under-served gap today. Build named loadout presets:
```python
@dataclass(frozen=True)
class PayloadPreset:
    name: str                  # "CAP A-A", "STRIKE GBU-38", etc.
    aircraft_alias: str
    pylons: tuple[Pylon, ...]
    fuel: float = 1.0
    description: str = ""

PRESETS: dict[tuple[str, str], PayloadPreset] = {
    ("F/A-18C", "CAP A-A"): PayloadPreset(...),
    ("F/A-18C", "STRIKE GBU-38"): PayloadPreset(...),
    ("F-16C",  "SEAD HARM"): PayloadPreset(...),
    # ...
}

def resolve(aircraft_alias: str, preset_name: str) -> PayloadPreset: ...
def list_for_aircraft(aircraft_alias: str) -> list[str]: ...
```
**How to source the data:** the DCS payload Lua files in
`<DCS install>/CoreMods/aircraft/<jet>/UnitPayloads/<jet>.lua` define the
canonical pylons. Read them, transcribe presets for the top 10 player
aircraft (F/A-18C, F-16C, F-15C, F-15E, A-10C, AH-64D, F-14B, Su-27, MiG-29S,
Ka-50). If DCS isn't installed, source CLSIDs from the pydcs `weapons_data.py`
module: it has every weapon CLSID.

#### `catalog/theatres.py`
```python
@dataclass(frozen=True)
class TheatreInfo:
    name: str
    pydcs_class: type
    default_bullseye_blue: Position
    default_bullseye_red: Position
    bounds: BoundingBox        # coord ranges for sanity-check validators
    notable_airports: tuple[str, ...]

CATALOG: dict[str, TheatreInfo] = {...}
```
Populate from pydcs's `Terrain.airports` for each theatre — that's where
real airport names live. Bullseye defaults can be hand-picked sensible
positions per theatre.

#### `catalog/callsigns.py`
DCS uses callsign numeric IDs for AWACS/tanker/JTAC. Map friendly names:
```python
AWACS_CALLSIGNS = {
    "Overlord": 1, "Magic": 2, "Wizard": 3, "Focus": 4, "Darkstar": 5,
}
TANKER_CALLSIGNS = {
    "Texaco": 1, "Arco": 2, "Shell": 3,
}
JTAC_CALLSIGNS = {
    "Axeman": 1, "Darknight": 2, "Warrior": 3, "Pointer": 4,
    "Eyeball": 5, "Moonbeam": 6, "Whiplash": 7, "Finger": 8,
    "Pinpoint": 9, "Ferret": 10, "Shaba": 11, "Playboy": 12,
    "Hammer": 13, "Jaguar": 14, "Deathstar": 15, "Anvil": 16,
    "Firefly": 17, "Mantis": 18, "Badger": 19,
}
```
Verify against pydcs `dcs/atcradio.py` or the DCS mission editor before
shipping.

### Acceptance

- `from dcs_agentic.catalog import aircraft, payloads, theatres, callsigns` works
- `aircraft.list_by_role("strike")` returns non-empty
- `payloads.list_for_aircraft("F/A-18C")` returns at least 3 presets
- `theatres.CATALOG["Caucasus"].notable_airports` is non-empty
- Test: a flight with `payload=PayloadSpec(preset_name="CAP A-A")` for an
  F/A-18C produces a .miz where pydcs reports the expected pylons set.

### Anti-patterns

- Do **not** hardcode CLSIDs as bare strings without comments — they're
  opaque. Annotate each with the weapon name.
- Do **not** allow silent fallback when a preset is missing. If
  `("F/A-18C", "SEAD HARM")` doesn't exist, raise — agent must pick a real
  preset or supply explicit pylons.

---

## Phase 4 — Builder refactor

**Goal:** convert the monolithic assembler into per-concern builders.
Plus implement what Phase 2 added.

> **Execution notes:**
> - Implement **one builder at a time**, with a passing test after each.
>   Order: coalitions → weather → flights → ground → naval → statics →
>   payloads → drawings → triggers. Stop after flights and run the full
>   demo specs end-to-end before continuing — flights are where the most
>   breakage hides.
> - **Subagent for pydcs surface discovery:** before implementing the
>   payloads builder, dispatch a DeepSeek subagent: "Read
>   `.venv/Lib/site-packages/dcs/flyingunit.py` and `dcs/unit.py`. List
>   every public method on `Plane` and `FlyingUnit` related to pylons,
>   weapons, fuel, chaff/flare counts. Show one usage example per method.
>   Under 300 words." Use the output to design the builder; don't grep
>   piecemeal yourself.
> - **Escalate** if you're about to put more than ~150 lines in any single
>   `builders/*.py` file. That's a sign the builder has a sub-concern that
>   wants its own module (e.g. waypoint construction within flights).

### Pattern

Every builder is a function with the same signature:
```python
def build_<concern>(mission: Mission, spec: MissionSpec, report: AssemblyReport) -> None:
    if spec.<concern> is None:
        return
    for item in spec.<concern>:
        try:
            _build_one(mission, item, report)
        except Exception as e:
            report.error(
                code="<CONCERN>_BUILD_FAILED",
                message=f"{type(e).__name__}: {e}",
                context=item.name,
            )
```

### New builders to implement (with the schema additions from Phase 2)

#### `pipeline/builders/payloads.py`
For each `FlightGroup` with `payload`:
1. If `preset_name` set, resolve from `catalog.payloads`; expand to pylons.
2. Apply pylons via pydcs `unit.pylons[station] = {"CLSID": clsid}` on every
   unit in the group (or use pydcs's `load_pylon`).
3. Apply fuel fraction, chaff/flare counts, gun ammo.
4. On unknown CLSID: `report.error("UNKNOWN_CLSID", ...)`.

This builder runs **after** flights are created, since it needs the
already-existing pydcs group.

#### `pipeline/builders/triggers.py`
Map `TriggerKind` and `ActionKind` to pydcs trigger constructs in
`dcs.triggers` / `dcs.action` / `dcs.condition`. This is the most
DCS-internals-dependent builder; read pydcs source carefully.

**Specifically:**
- `TIME_REACHED` → `dcs.condition.TimeAfter`
- `UNIT_DEAD` → `dcs.condition.UnitDead` (or trigger-once flag)
- `UNIT_IN_ZONE` → `dcs.condition.UnitInZone`
- `SHOW_MESSAGE` → `dcs.action.MessageToAll` (or coalition-filtered variant)
- `END_MISSION` → mission-end action (specific call in pydcs)

When unsure of the pydcs API: grep the installed
`.venv/Lib/site-packages/dcs/triggers.py` and `dcs/action.py` for usage
patterns. Do **not** improvise. If a kind doesn't map cleanly, log
`report.warn("TRIGGER_UNIMPLEMENTED", ...)` and skip.

#### `pipeline/builders/drawings.py`
Map `Zone` and `MapMarker` to `dcs.drawing.*`. Use pydcs `Polygon` for zones
(circle approximated as many-sided polygon, or use the built-in circle
primitive if it exists).

#### `pipeline/builders/coalitions.py`
The current `_get_country` instantiates the country class twice. Fix:
```python
def get_or_add_country(mission: Mission, country_name: str, side: str, report):
    side = side.lower()
    coalition = mission.coalition.get(side)
    if coalition is None:
        raise SpecValidationError(f"Unknown coalition side: {side}")
    country_cls = catalog.countries.resolve(country_name)
    country_instance = country_cls()
    existing = coalition.country(country_instance.name)
    if existing is not None:
        return existing
    return coalition.add_country(country_instance)
```

### Acceptance

- Adding a `payload` to a CAP demo and inspecting the saved .miz with
  `dcs.Mission().load_file(path)` shows the expected pylons.
- A simple time-trigger ("show message at T+60s") produces a valid .miz
  that DCS opens without warning.
- Trigger kinds with no mapping warn loudly via the report.
- No builder reaches into another builder's internals; only `(mission, spec, report)`.

### Anti-patterns

- Do **not** catch broad `Exception` at the top of a builder unless you
  always re-report it. Silent swallow = silent broken mission.
- Do **not** mutate `spec` from inside a builder. The spec is the input
  contract — treat it as read-only.
- Do **not** add a new field to the schema and a corresponding builder in
  separate commits. Ship them together.

---

## Phase 5 — Trigger system (continued from 4 if you split)

> **Execution notes:**
> - The pydcs trigger/condition/action API is the **least documented**
>   surface in this project. Plan on reading source, not docs.
> - **Subagent the survey first:** "Read `.venv/Lib/site-packages/dcs/`
>   for files named `triggers.py`, `action.py`, `condition.py`. Produce
>   a flat table: class name, constructor signature, what `.dict()`
>   produces, and which pydcs Mission method is used to register it
>   (e.g. `mission.triggerrules.triggers.append(...)`). Under 500 words."
> - **Escalate to Advisor** with that table in hand: "Here's the pydcs
>   trigger surface. Here's the v1 schema from Phase 2. Approve this
>   mapping or correct it." Do not start coding until the mapping is
>   confirmed.
> - When uncertain how an action serializes, write a 10-line test that
>   adds the trigger to a Mission, saves, reopens, and asserts the
>   trigger is present. This catches "the trigger was added but doesn't
>   fire in DCS" failures earlier than reading source.

This warrants its own callout because triggers are the most complex
sub-domain. The v1 schema in Phase 2 is intentionally tiny. Once Phase 4
ships the v1 builder, expand iteratively:

**v2 trigger additions:**
- `RANDOM_FLAG_TRUE`, `FLAG_LESS`, `FLAG_MORE`
- Sub-conditions (OR groups via nested condition lists)
- `BLUE_PLAYERS_IN_ZONE`, `ALL_OF_GROUP_DEAD`

**v3:**
- Switched conditions (continuously evaluated)
- AI tasking actions (`PUSH_AI_TASK`, `SET_FREQUENCY`)
- Smoke / illumination / explosion actions

Do not try to cover every DCS trigger upfront. Each addition needs:
1. Schema entry
2. Builder mapping
3. Test that round-trips: spec → .miz → reopened pydcs Mission → check trigger present.

---

## Phase 6 — Importer (.miz → MissionSpec)

**Goal:** load an existing `.miz` and produce a `MissionSpec` that, when
re-assembled, is functionally equivalent. This is what makes the tool an
*editor*, not just a generator.

> **Execution notes:**
> - The importer is **the symmetric inverse of the builders**. Every field
>   the builder writes from spec → mission, the importer reads back from
>   mission → spec. If you cannot point to the builder that produced a
>   piece of the .miz, you cannot import it correctly.
> - **Escalate** before you start: send the Advisor your file list of
>   `read_*` functions you intend to write, paired 1:1 with `build_*`
>   from Phase 4. Missing pairs are the bug you want to catch up-front.
> - **Subagent the round-trip diff scaffolding:** "Write a recursive dict
>   diff that ignores keys named in IGNORE_KEYS and tells me which
>   sub-paths differ. Stand-alone function, ~30 lines. No tests." Use it
>   in the round-trip test.
> - When the round-trip diff shows differences that aren't pydcs-assigned
>   IDs, **do not paper over them**. They mean either (a) the builder is
>   dropping data, or (b) the importer is. Find which and fix the root.

### File: `importer/miz_reader.py`

```python
def import_miz(path: str) -> tuple[MissionSpec, AssemblyReport]:
    """Load a .miz and convert it to a MissionSpec.

    Returns (spec, report). Report contains:
      - INFO: each element imported
      - WARN: features present in .miz but not yet representable
              in MissionSpec (so the round-trip is lossy)
      - ERROR: import failures
    """
    pydcs_mission = Mission()
    pydcs_mission.load_file(path)
    ...
```

### Steps

1. Load via `pydcs_mission = Mission(); pydcs_mission.load_file(path)`.
2. Walk pydcs objects and translate back into Pydantic models. This is the
   inverse of the builders — there should be a clean symmetry. Match each
   Phase-4 builder with a `read_*` function.
3. For every loss (a pydcs feature not yet in schema), emit a WARN. Never
   silently drop.
4. Round-trip test: load any `.miz` we generate, re-assemble, diff the
   result. Differences should be limited to ordering or pydcs's auto-assigned
   IDs, not semantic content.

### Acceptance

- `import_miz("output/test_strike.miz")` returns a MissionSpec with the
  same flights, vehicles, ships, briefing as the original spec.
- A round-trip test compares `spec_v1 → miz → spec_v2` for semantic equality
  (ignoring auto-generated IDs).
- Importing a non-trivial `.miz` made in the DCS editor (a sample mission
  from a campaign) emits zero ERROR-level issues — only WARN for unsupported
  features.

### Anti-patterns

- Do **not** parse the `.miz` ZIP manually. Use `Mission.load_file()` —
  pydcs already does the work.
- Do **not** assume blue countries map 1:1 to spec — countries can appear
  in either coalition. Always check the actual side.
- Do **not** invent names for unnamed pydcs objects; fall back to
  `f"imported_unit_{id}"` and emit an INFO so the agent can rename.

---

## Phase 7 — Validation layer

**Goal:** catch errors Pydantic can't, *before* assembly fails or — worse —
produces a flyable-but-broken mission.

### Files

#### `validation/coordinate_sanity.py`
- Are flight/vehicle/ship coordinates within the theatre's bounds?
  Use `catalog.theatres.CATALOG[theatre].bounds`.
- Warn at 80% of bounds, error past 100%.

#### `validation/fuel_range.py`
- For each flight: compute total waypoint distance. Compare to the
  aircraft's combat radius (in `catalog.aircraft`). If route > radius,
  WARN that the flight may bingo.

#### `validation/weapons_match.py`
- For each flight: does the payload match the task?
  - CAP without A-A missiles → WARN
  - STRIKE without bombs/JDAMs → WARN
  - SEAD without HARM/Kh-58/Kh-31P → WARN
  - ANTISHIP without ASMs → WARN

#### `validation/route_sanity.py`
- Waypoints in geographic order? (Not strictly required but flags
  obvious typos like swapped x/y.)
- Altitude transitions sane? (Hornet descending from FL300 to 100ft in
  one waypoint = WARN.)
- Landing waypoint, if present, is at a real airport?

### API

```python
def validate(spec: MissionSpec) -> AssemblyReport:
    report = AssemblyReport()
    coordinate_sanity.check(spec, report)
    fuel_range.check(spec, report)
    weapons_match.check(spec, report)
    route_sanity.check(spec, report)
    return report
```

Validators do not mutate the spec. They only report.

### Integration

The CLI gets a `--validate-only` flag that runs validation without assembly.
The assembler optionally runs validation first (`MissionAssembler(spec, validate=True)`),
prepending validation issues to its own report.

### Acceptance

- A flight with CAP task and no missiles produces a WARN with code
  `WEAPONS_TASK_MISMATCH`.
- A waypoint at x=99999999 produces an ERROR with code `COORD_OUT_OF_BOUNDS`.
- Validators are pure (no side effects), so they can be called repeatedly.

---

## Phase 8 — Agent v1 (single-shot mission designer)

**Goal:** `--prompt "..."` works. Agent reads prompt → produces MissionSpec → assembler runs.

> **Default model:** `claude-opus-4-7` (resolves through the user's
> LiteLLM proxy to Claude Sonnet). Reasoning: one-shot quality dominates
> per-call cost here because each invocation produces a full mission.
> A bad spec wastes more human time than the price delta saves.
>
> **Override:** `--model` flag accepts any model alias the proxy knows
> (`claude-sonnet-4-6` for GLM-5.2, `claude-*` for DeepSeek). For a
> "draft fast then polish" workflow, GLM is acceptable for the first
> pass and Sonnet for the second.
>
> **Cost guardrails:** the system prompt with embedded schema + catalog
> summary will be 4–8k tokens. Cache the system prompt
> (`cache_control={"type": "ephemeral"}` on the system block) — every
> repeat call within 5 minutes is then nearly free on input. The user
> will run this many times in a session; caching matters.

### Files

#### `agents/llm/client.py`
Thin wrapper around the Anthropic SDK. Honor environment variables for
API key (`ANTHROPIC_API_KEY`) and base URL (`ANTHROPIC_BASE_URL` — this
project's user has a LiteLLM proxy per their global CLAUDE.md, so
respecting the env vars matters).

```python
import os
from anthropic import Anthropic

# Default model per agent role. Resolved by the user's LiteLLM proxy:
#   claude-opus-4-7   → Claude Sonnet (advisor tier)
#   claude-sonnet-4-6 → GLM-5.2       (agent tier)
#   claude-*          → DeepSeek      (subagent tier)
DEFAULT_MODELS = {
    "designer":         "claude-opus-4-7",    # one-shot quality matters most
    "editor":           "claude-sonnet-4-6",  # many cheap turns, tools constrain
    "campaign_arch":    "claude-opus-4-7",    # cross-mission reasoning
    "template_render":  "claude-sonnet-4-6",  # routine per-mission filling
}

class LLMClient:
    def __init__(self, model: str = None, role: str = "designer"):
        self.client = Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"],
            base_url=os.environ.get("ANTHROPIC_BASE_URL"),  # LiteLLM proxy
        )
        self.model = model or DEFAULT_MODELS[role]

    def message(self, system: str, user: str, tools: list = None,
                cache_system: bool = True) -> dict:
        # The system block is large (schema + catalog). Cache it so
        # repeat calls in a session pay tiny input cost.
        system_blocks = [{
            "type": "text",
            "text": system,
            "cache_control": {"type": "ephemeral"} if cache_system else None,
        }]
        ...
```

Provide a `--model` flag on every CLI subcommand that calls an LLM, so
the user can override (e.g. force the cheap tier for a draft pass).

#### `agents/prompts/mission_designer.md`
A long system prompt (1000–3000 words) that:
- Explains the agent's role: produce a `MissionSpec` JSON object
- Embeds the MissionSpec JSON schema (`MissionSpec.model_json_schema()`)
  injected at build time, not committed
- Embeds the catalog summary (airports per theatre, top aircraft, top
  payload presets) — see Phase 3
- Gives examples (the demo CAP + demo Strike specs)
- Lists hard rules: every flight needs `country` and `side`, every
  waypoint needs at least `x` and `y`, no invented aircraft types, etc.

#### `agents/mission_agent.py`
```python
def design_mission(prompt: str, theatre: str = "Caucasus") -> MissionSpec:
    system = load_prompt("mission_designer.md")
    system = render_system(system, theatre=theatre, schema=MissionSpec.model_json_schema())
    response = llm.message(system=system, user=prompt, response_format="json")
    spec = MissionSpec.model_validate_json(response.content)
    return spec
```

For v1, single-shot. If validation fails, re-prompt once with the error
message ("your spec was invalid: {pydantic_error}. Fix it.") — max 2 retries.

### CLI: `cli/design.py`

```
dcs-agentic design --prompt "..." --theatre Caucasus --output mission.miz
```

### Acceptance

- `dcs-agentic design --prompt "2-ship CAP from Batumi"` produces a
  valid .miz the assembler accepts with zero errors.
- If the LLM produces invalid JSON, the agent retries once with the
  validation error appended; if still invalid, it exits with the error
  and the raw response saved to `.last_response.json` for debugging.
- The system prompt is loadable as plain text — no f-string templating
  inside the .md file; do all interpolation in Python.

### Anti-patterns

- Do **not** put the schema string inline in `mission_designer.md`. Inject
  at runtime — schemas change, the prompt shouldn't.
- Do **not** swallow API errors silently. If the LLM call fails, fail loud.
- Do **not** call the LLM with `max_tokens` smaller than ~8000 — mission
  specs can be long. Set generously.

---

## Phase 9 — Agent v2 (editor with tool-call mutations)

**Goal:** the agent can load an existing mission, make incremental edits
in conversation, and save. This is the "editor" in the project name.

> **Default model:** `claude-sonnet-4-6` (resolves to GLM-5.2). Editing
> is many short turns; each tool call is well-constrained by the
> tool's JSON schema. GLM handles this reliably at ~10× lower cost than
> Sonnet.
>
> **When to escalate to Sonnet:** the editor agent should automatically
> escalate when the user instruction contains words like "redesign,"
> "rebuild," "rewrite," or "restructure" — these are signals for
> Sonnet-tier reasoning. Implement a simple keyword router with a
> `--force-model` override.
>
> **Tool-call caching:** the tool definitions list + system prompt is
> large (every mutation tool with its JSON schema). Cache the system
> block; never re-send the tools list mid-conversation.

### Files

#### `agents/tools/mutations.py`
Tool definitions in Anthropic's tool-use format:
```python
TOOLS = [
    {
        "name": "add_flight",
        "description": "Add a new flight group to the mission.",
        "input_schema": FlightGroup.model_json_schema(),
    },
    {
        "name": "remove_flight",
        "description": "Remove a flight group by name.",
        "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    },
    {
        "name": "move_waypoint",
        "description": "Move a waypoint in a flight's route.",
        "input_schema": {...},
    },
    {"name": "set_payload", ...},
    {"name": "add_vehicle_group", ...},
    {"name": "remove_vehicle_group", ...},
    {"name": "add_trigger", ...},
    {"name": "set_weather", ...},
    {"name": "set_briefing", ...},
    {"name": "validate_spec", ...},      # runs the validators
    {"name": "list_airports", ...},      # for the theatre
    {"name": "list_aircraft", ...},
    {"name": "list_payload_presets", ...},
]

def apply_tool(spec: MissionSpec, tool_name: str, tool_input: dict) -> MissionSpec:
    """Apply a tool call to the spec. Returns the mutated spec."""
    ...
```

Each tool mutates the spec in-place (or returns a new copy — your choice;
be consistent).

#### `agents/editor_agent.py`
A multi-turn loop:
```python
def edit_mission(spec: MissionSpec, instruction: str) -> MissionSpec:
    messages = [{"role": "user", "content": instruction}]
    while True:
        response = llm.message(system=EDITOR_PROMPT, messages=messages, tools=TOOLS)
        if response.stop_reason == "end_turn":
            break
        for tool_call in response.tool_calls:
            try:
                spec = apply_tool(spec, tool_call.name, tool_call.input)
                result = "ok"
            except Exception as e:
                result = f"error: {e}"
            messages.append({"role": "tool_result", "tool_use_id": tool_call.id, "content": result})
    return spec
```

### CLI

```
dcs-agentic edit input.miz --instruction "add an AWACS orbit east of Batumi" --output out.miz
```

### Acceptance

- An interactive session can: load a mission, add a flight, move a waypoint,
  validate, save — without re-generating the full spec.
- Tool errors come back to the LLM as tool_result messages, so the LLM can
  retry or pick a different tool.
- Each tool has a focused JSON schema (don't pass `FlightGroup` to a tool
  that only needs a waypoint coordinate).

### Anti-patterns

- Do **not** let tools call other tools internally. Each tool is one mutation.
  Composition happens in the LLM loop.
- Do **not** validate inside `apply_tool` with Python `assert` — return a
  structured error via the tool result so the LLM can recover.
- Do **not** let the LLM see the assembler. Its sole interface is the
  tool list + the MissionSpec it gets back.

---

## Phase 10 — Campaign layer

**Goal:** a campaign is a sequence of missions with persistent state.
Outcome of mission N feeds into mission N+1.

> **Two-tier model strategy.** Campaign design is hierarchical:
>
> 1. **Architect (Sonnet, `claude-opus-4-7`):** designs the campaign
>    structure — branching, narrative arc, attrition model, initial
>    state, win conditions. Runs once at `campaign init`. Output is a
>    `CampaignSpec` skeleton with mission *templates* (not full specs).
> 2. **Per-mission renderer (GLM, `claude-sonnet-4-6`):** fills a
>    template against current `CampaignState` to produce the next
>    runnable `MissionSpec`. Runs once per `campaign run`. Has access
>    to a small tool surface (state queries, catalog lookups).
>
> The split matters for cost: a 10-mission campaign would cost ~10×
> more to design *and* render with Sonnet than to design with Sonnet
> and render with GLM, with no quality loss on the render side because
> the templates constrain creativity.
>
> **Execution notes:**
> - Build the architect first, but **test it with hand-written
>   templates** before building the renderer. Order: schema → state
>   persistence → architect → templates → renderer → branching →
>   after-action.
> - **Escalate** before designing the `CampaignState` schema — getting
>   it wrong now means migrations later. The Advisor should review the
>   state shape (especially `losses`, `captured_airfields`,
>   `completed_missions`) against the branching rules you intend to
>   support.

### Files

#### `schemas/campaign.py`
```python
class MissionLink(BaseModel):
    name: str                          # mission identifier
    spec_file: Optional[str] = None    # if pre-authored
    spec_template: Optional[str] = None  # if generated from template
    next_on_blue_win: Optional[str] = None
    next_on_red_win: Optional[str] = None
    next_on_draw: Optional[str] = None
    next_unconditional: Optional[str] = None

class CampaignSpec(BaseModel):
    name: str
    theatre: str
    start_mission: str
    missions: list[MissionLink]
    initial_state: CampaignState
    description: Optional[str] = None
    agent_notes: Optional[str] = None

class CampaignState(BaseModel):
    """Persistent state across missions."""
    score: dict[str, int] = Field(default_factory=lambda: {"blue": 0, "red": 0})
    flags: dict[str, Any] = Field(default_factory=dict)  # mission flags carried forward
    losses: dict[str, list[str]] = Field(default_factory=dict)
        # {"blue": ["CAP Alpha-1", "Strike Lead-2"], "red": [...]}
    captured_airfields: dict[str, str] = Field(default_factory=dict)
        # {"Batumi": "red"}  -- which side currently holds each base
    completed_missions: list[str] = Field(default_factory=list)
    current_mission: str
    current_date: Optional[datetime] = None  # advances each mission
```

#### `campaign/runner.py`
```python
class CampaignRunner:
    def __init__(self, campaign: CampaignSpec, state_dir: str):
        self.campaign = campaign
        self.state_dir = Path(state_dir)
        self.state = self._load_or_init_state()

    def next_mission(self) -> tuple[MissionSpec, str]:
        """Produce the next MissionSpec, applying current state.

        Returns (spec, miz_output_path).
        """
        link = self._lookup_link(self.state.current_mission)
        if link.spec_file:
            spec = self._load_static_spec(link.spec_file)
        else:
            spec = self._render_template(link.spec_template)
        spec = self._apply_state_to_spec(spec)
        miz_path = self.state_dir / "missions" / f"{link.name}.miz"
        return spec, str(miz_path)

    def record_outcome(self, outcome: AfterAction):
        """Update state from a finished mission."""
        self.state.score["blue"] += outcome.blue_score
        self.state.score["red"] += outcome.red_score
        self.state.losses["blue"].extend(outcome.blue_losses)
        ...
        next_link = self._pick_next(outcome)
        if next_link:
            self.state.current_mission = next_link.name
        self._save_state()

    def is_complete(self) -> bool:
        return self.state.current_mission is None
```

#### `campaign/branching.py`
Logic to pick `next_*` from a `MissionLink` based on `AfterAction`. Keep
deterministic — campaigns must be reproducible from state.

#### `campaign/after_action.py`
Parses outcomes. Sources:
- **Option A (preferred): DCS Lua callback.** A `mission_end.lua` script
  embedded in the generated `.miz` writes JSON to a known path. Then we
  read it.
- **Option B (fallback): TacView ACMI parsing.** If the user records
  TacView, we can read the .acmi file.
- **Option C (manual): user CLI command.** `dcs-agentic campaign report
  --campaign foo --blue-score 50 --red-score 0 --next blue-win`.

Implement C first (always works). Layer A on top when comfortable with
DCS Lua API.

#### `campaign/state.py`
Persistence: `CampaignState` serializes to/from `campaign_state.json` in
the campaign's directory. Versioned (`schema_version: 1`) so future
migrations are tractable.

### Mission templates

A template is a `MissionSpec` with placeholder syntax (Jinja2 or simple
`{{ var }}` substitution) for state-dependent values. Example:

```json
{
  "name": "Campaign Day {{ day }}",
  "vehicles": [
    {"name": "SAM-1", "vehicle_type": "{{ red_sam_type }}", ...}
  ],
  "flights": "{{ available_blue_flights }}"
}
```

Use Jinja2 for templating (well-known, well-tested). Templates live in
`campaigns/<name>/templates/`.

### Agent integration

`agents/campaign_agent.py`:
```python
def design_campaign(prompt: str) -> CampaignSpec:
    """Generate a full CampaignSpec from a prompt like
       'a 5-mission strike campaign in Caucasus, blue vs red, 
        starting with a CAP sweep and ending with a deep strike'."""
    ...
```

The campaign agent has more tools than the editor agent:
`design_mission` (calls the mission agent), `link_missions`,
`set_branching_rule`, `define_initial_state`.

### CLI

```
dcs-agentic campaign init --name op-lion --from-prompt "..."
dcs-agentic campaign run --name op-lion    # produces next .miz
dcs-agentic campaign report --name op-lion --blue-win
dcs-agentic campaign inspect --name op-lion
```

### Acceptance

- A 3-mission linear campaign generates 3 distinct .miz files in sequence
  when `campaign run` is called repeatedly with `campaign report` between.
- A 5-mission branching campaign with one branch point produces the right
  .miz file based on whether the report says blue-win or red-win.
- Campaign state survives process restarts (round-trips through JSON).
- Mission losses recorded in mission N are reflected in mission N+1's spec
  (specifically: dead pilots don't reappear, destroyed SAMs don't respawn).

### Anti-patterns

- Do **not** store campaign state in the .miz files themselves. The .miz
  is an output; state lives in the campaign directory.
- Do **not** auto-advance the campaign on `run`. The user explicitly
  reports the outcome. Auto-advance creates surprises.
- Do **not** make the LLM responsible for state — give it tools to *query*
  state, but state mutation only happens via `record_outcome`.

---

## Phase 11 — After-action / outcome parsing

(Detail-light here because the design depends on how Phase 10 lands.)

**Goal:** automate the manual "blue-win" reporting from Phase 10.

Approach A — DCS Lua callback: embed a script in every campaign .miz that
writes outcome JSON to a known path on mission end. Read it.

Approach B — TacView .acmi: parse the ACMI text format (well-documented
by TacView) to extract kills/losses.

Each phase: schema for `AfterAction`, parser, validation, CLI command.

---

## Phase 12 — CLI, docs, examples

### `cli/`
Split the current monolithic `__main__.py` into subcommands using `argparse`
subparsers (or `click`/`typer` if you want — but argparse keeps deps minimal).

```
dcs-agentic build   spec.json [--output ...] [--strict]
dcs-agentic design  --prompt "..." [--theatre ...] [--output ...]
dcs-agentic edit    input.miz --instruction "..." [--output ...]
dcs-agentic inspect input.miz
dcs-agentic validate spec.json
dcs-agentic campaign init|run|report|inspect ...
```

### Docs

- `README.md`: install, quickstart, link to PLAN.md
- `CLAUDE.md`: project conventions for Claude sessions
  - Speed values are km/h (pydcs convention)
  - All `print()` belongs in `cli/`; assembler uses `report.*`
  - New schema field requires a builder, an importer, a validator (where
    applicable), and at least one test
- `docs/architecture.md`: re-derivable summary of this PLAN's architecture
- `examples/`: a CAP, a strike, a SEAD package, a campaign

### Acceptance

- `pip install -e .[dev,agents]` works on a fresh venv
- `dcs-agentic --help` lists every subcommand
- All examples produce playable missions

---

## Standing rules (read every phase)

1. **No silent failures.** Every fallback, every substitution, every "we
   couldn't" goes through `AssemblyReport`.
2. **Speed is km/h** at the schema boundary. Always. If a value needs to
   be in knots for display, convert in `cli/` only.
3. **No `print()` outside `cli/`.** Everything else uses the report or
   raises.
4. **No bare `except:`.** Catch named exceptions, or `Exception` only at
   builder top-level where you re-report.
5. **Pydantic doesn't validate references.** Cross-spec checks go in
   `validation/`.
6. **Schema + builder + test land in the same commit.** Schema without
   builder is silent data loss.
7. **No new dependencies without justification.** Existing: `pydcs`,
   `pydantic`, `pytest`. Adding agents needs `anthropic`. Adding templating
   needs `jinja2`. Anything else: ask in the PR.
8. **Coordinates are in pydcs convention.** `Point(x, y)` where x is
   north-south, y is east-west. The DCS editor calls these "X-coord" and
   "Z-coord" — but pydcs uses x and y. Do not invent a third convention.
9. **When pydcs's API is unclear, read its source.** The installed copy is
   at `.venv/Lib/site-packages/dcs/`. It's the only authoritative reference.
10. **Tests run via `pytest tests/`.** No `if __name__ == '__main__'`
    runner blocks in test files. If you write a quick verification script,
    put it in `scripts/`.
11. **Model usage in the product:** never hardcode a model ID inside a
    `mission_agent`, `editor_agent`, or `campaign_agent`. Always go
    through `LLMClient(role="...")` and `DEFAULT_MODELS`. The user's
    LiteLLM proxy is the single source of truth for which underlying
    provider answers — code talks to aliases, not providers.
12. **Subagent dispatch is for read-only work.** If a subagent's report
    leads you to change a file, *you* make the change. Never let a
    subagent write code; they have less context than you do and even
    less than the Advisor.

---

## Done definition

The project is "v1 complete" when:

- [ ] A user can write a JSON spec by hand and produce a flyable .miz
- [ ] A user can prompt an LLM to produce a flyable .miz
- [ ] A user can load an existing .miz, edit it via prompts, and re-save
- [ ] A user can author a multi-mission campaign with branching
- [ ] All builders are paired with importers (round-trip works for
      everything in the schema)
- [ ] The validation layer catches the top-10 common mission mistakes
- [ ] DCS opens the generated missions without warnings
- [ ] Every subsystem has tests; coverage isn't worshipped but no
      untested public function

Time estimate (rough, single competent human dev): 6–10 weeks of focused
work. Less if Phase 10 is descoped; more if trigger/drawing coverage is
broadened.

**With the configured Agent (GLM-5.2):** expect 2–3× more wall-clock
iteration than Sonnet would need on the same plan, primarily on Phases
1 (restructure), 5 (triggers), and 6 (importer) where pydcs surface
discovery dominates. Phases 2/3 (schema/catalog expansion) and 8/9
(agent code is short and pattern-following) will run at near-Sonnet
speed. The Advisor escalation budget — used the way this plan
prescribes — should be roughly one consultation per phase, ~5% of
total spend.
