# Changelog

All notable changes to dcs-agentic. Format roughly follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions
use semver once we cut a tagged release.

## [Unreleased]

Initial development. All 12 PLAN.md phases complete. 91 tests pass.

### Pipeline
- `MissionAssembler` orchestrates per-concern builders (coalitions,
  weather, flights, ground, naval, carrier ops, statics, FARPs,
  drawings, triggers, custom scripts).
- Flight builder applies payload presets and explicit pylons.
- Ground builder wires ROE, AlarmState, late activation.
- Carrier ops builder emits `ActivateBeaconCommand` (TACAN).
- Drawings builder routes zones to Common layer, markers to per-side layers.
- Triggers builder maps `TriggerKind`/`ActionKind` to pydcs.
- `--strict` mode raises `AssemblyError` on errors.
- `validate=True` runs the validation layer pre-assembly.

### Catalog
- Aircraft, vehicles, ships, statics, countries, theatres with structured metadata.
- 14 payload presets across 9 aircraft.
- AWACS / tanker / JTAC callsign maps.

### Validation
- Five validators: `coordinate_sanity`, `fuel_range`, `weapons_match`,
  `route_sanity`, `references`.
- `validate(spec)` is pure and wraps each validator in try/except.

### Importer
- `.miz → MissionSpec` round-trip for theatre, briefing, coalitions
  (used countries only), flights (with task, airport, start_type,
  payload, waypoints), vehicles, ships, statics.
- Workaround for pydcs `FlyingType.load_payloads` KeyError when DCS isn't installed.
- Deferred: weather, triggers, drawings, FARPs, carrier ops, mission goals.

### Agents
- `design_mission`: prompt → `MissionSpec` with retry on validation failure.
- `edit_mission`: 19-tool surface (`add_flight`, `set_payload`, `validate_spec`, …).
- `design_campaign` + `render_mission` for the campaign architect.
- `LLMClient` resolves model aliases per role, supports `ANTHROPIC_BASE_URL` proxy, escalates on keywords.

### Campaign
- `CampaignRunner.load/record_outcome/is_complete` over a `MissionLink` graph.
- After-action sources: `parse_lua_callback`, `parse_tacview`, `load_outcome` autodispatch.
- `LUA_HOOK_SCRIPT` embeddable in mission scripting for auto-outcome JSON.

### CLI
- Subcommands: `build`, `validate`, `inspect`, `list`, `design`, `edit`, `campaign`.
- `--version` flag.

### Docs
- `index.md`, `architecture.md`, `schema-reference.md`, `cli.md`,
  `pipeline.md`, `catalog.md`, `agents.md`, `importer.md`,
  `validation.md`, `after_action.md`, `examples.md`.

### Examples
- `cap.json`, `strike_with_sead.json`, `carrier_ops.json`, `capabilities_demo.json`.

### Fixes
- Russian weapon UUID CLSIDs now resolve to names for `weapons_match`.
- Importer no longer mis-reads briefing description as mission name.
- Importer round-trips task, airport, start_type.
- Lua hook uses `env.mission.sortie`, not theatre, as filename.
- CLI subcommands use ASCII-only output (no mojibake on Windows cp1252).
