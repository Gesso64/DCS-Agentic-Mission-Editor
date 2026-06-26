# Documentation

This directory documents **what currently exists** in dcs-agentic. For
the forward-looking build plan, see [`PLAN.md`](../PLAN.md). For project
conventions, see [`CLAUDE.md`](../CLAUDE.md).

## Contents

| File | What it covers |
|---|---|
| [`schema-reference.md`](schema-reference.md) | Every Pydantic model — fields, types, defaults, units |
| [`cli.md`](cli.md) | `python -m dcs_agentic` subcommands and flags |
| [`pipeline.md`](pipeline.md) | `MissionAssembler` orchestrator + per-concern builders + error codes |
| [`catalog.md`](catalog.md) | Aliases for aircraft, vehicles, ships, countries, theatres, payloads, callsigns |
| [`agents.md`](agents.md) | AI agent layer — mission designer, editor (tool calls), campaign architect |
| [`importer.md`](importer.md) | `.miz → MissionSpec` reverse-pipeline |
| [`validation.md`](validation.md) | Phase 7 validation layer — checks, error codes, CLI integration |
| [`examples.md`](examples.md) | Walkthrough of `examples/capabilities_demo.json` |

## What works today

Phases 1–10 of [`PLAN.md`](../PLAN.md) are complete. Phase 11
(after-action parsing) and Phase 12 (CLI/docs polish) remain.

- **Declarative `MissionSpec`** (Pydantic) covers flights, vehicles, ships,
  statics, weather, briefing, custom Lua scripts, payloads, bullseye,
  radio comms (ATC/AWACS/tanker/JTAC), zones/markers, FARPs, carrier ops,
  mission goals, ROE/alarm state, and v1 triggers (closed-union typed
  conditions and actions). Models live in topical `schemas/<concern>.py` modules.
- **`MissionAssembler`** is a thin orchestrator (~100 lines) that delegates
  to per-concern builders under `pipeline/builders/`. All 8 supported
  theatres work.
- **Per-concern builders** for coalitions, weather, flights (with payload
  preset application), ground (with ROE/AlarmState), naval, **carrier
  ops** (TACAN beacon), statics, **FARPs**, **drawings** (zones +
  markers), **triggers (Phase 5)**, and custom scripts.
- **Catalog** includes fully-structured metadata for aircraft (with role
  tags, combat radius, player-flyable flags), vehicles (with role tags
  for SAM/AAA/artillery/armor), ships, statics, countries, and theatres
  (with bounding boxes, default bullseyes, notable airport lists).
  - **`catalog/payloads.py`** — 14 named loadout presets across 9 aircraft,
    covering CAP, STRIKE, SEAD, CAS, and antiship roles.
  - **`catalog/callsigns.py`** — verified callsign → numeric ID maps for
    AWACS, tanker, and JTAC.
- **Unit conversions** are centralized in `units.py` (km/h ↔ m/s ↔ kt, m ↔ ft).
- **CLI** with subcommands `build`, `design`, `edit`, `campaign` — see
  [`cli.md`](cli.md).
- **Structured `AssemblyReport`** records every fallback, substitution,
  and failure with a stable code and a hint. **No `print()` outside `cli/`.**
- **`--strict` mode** raises `AssemblyError` on any error-severity issue.
- **Proxy aircraft** (e.g. Su-35 → Su_27) surface as `AIRCRAFT_PROXY`
  warnings on the report — agents see the substitution.
- **Phase 5 triggers** — `build_triggers` maps `TriggerKind`/`ActionKind`
  to pydcs condition/action classes. Group/unit/zone references are
  resolved by name; missing refs warn-and-skip rather than crash.
- **Phase 6 importer** — `import_miz()` round-trips theatre, coalitions
  (only used countries), flights with waypoints + payload pylons,
  vehicles, ships, and statics. Deferred sections (weather, triggers,
  drawings) warn but don't fail.
- **Phase 8/9/10 agents** — `design_mission`, `edit_mission`, and
  `design_campaign` + `render_mission` plus a 19-tool editor surface
  (`apply_tool` dispatcher). See [`agents.md`](agents.md).
- **Phase 7 validation layer** — `validate(spec)` runs five checks
  (coordinate sanity, fuel range, weapons match, route sanity, cross
  references). `MissionAssembler(validate=True)` and `dcs-agentic
  validate spec.json` integrate it. See [`validation.md`](validation.md).
- **67 pytest tests** cover the assembler, schema drift, agent tool
  dispatch with stub LLMs, prompt rendering, trigger build, `.miz`
  round-trip, the Phase 4 tail, and the validation layer. All pass.

## What does not work yet

| Area | Status | Phase |
|---|---|---|
| Carrier ops: ICLS / BRC / Link-4 | Schema done; TACAN works; others surface as `CARRIER_OPS_PARTIAL` until pydcs has the API | 4 |
| After-action parsing from DCS/TacView | `parse_lua_callback`/`parse_tacview` are `NotImplementedError` | 11 |
| Trigger reverse-import (`.miz` → spec) | Importer warns and drops triggers; round-trip from spec→miz→spec→miz loses them | 6 (followup) |
| Live LLM smoke tests | Agent tests use stub LLMs; no integration test hits a real model | 8/9 |

See [`PLAN.md`](../PLAN.md) for how these get built.
