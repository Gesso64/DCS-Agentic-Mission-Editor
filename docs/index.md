# Documentation

| Doc | What it covers |
|---|---|
| [**mcp.md**](mcp.md) | MCP server setup for every supported AI host, full tool catalog |
| [**cli.md**](cli.md) | Every CLI subcommand and flag |
| [**schema-reference.md**](schema-reference.md) | Every Pydantic model — fields, types, defaults, units |
| [**catalog.md**](catalog.md) | Aircraft, vehicle, ship, country, theatre, payload, callsign aliases |
| [**examples.md**](examples.md) | Walkthrough of the bundled example specs |
| [**pipeline.md**](pipeline.md) | How `MissionAssembler` turns a spec into a `.miz` |
| [**agents.md**](agents.md) | Bundled AI agents — mission designer, editor, campaign architect |
| [**importer.md**](importer.md) | `.miz → MissionSpec` reverse pipeline |
| [**validation.md**](validation.md) | What the validator checks and what each error code means |
| [**after_action.md**](after_action.md) | Parsing mission outcomes from Lua hook JSON or TacView `.acmi` |
| [**architecture.md**](architecture.md) | Module map and internal conventions (for contributors) |

---

## What's included

**Mission building (no AI required)**
- Declarative `MissionSpec` schema covering flights, vehicles, ships, statics, weather, briefing, payloads, radio comms (ATC/AWACS/tanker/JTAC), zones, map markers, FARPs, carrier ops (TACAN), ROE/alarm state, triggers, custom Lua scripts, and mission goals.
- `MissionAssembler` turns a spec into a `.miz` via pydcs. All 8 supported theatres work.
- `import_miz()` converts an existing `.miz` back to a `MissionSpec` (flights, vehicles, ships, statics, coalitions; weather/triggers/drawings are deferred with warnings).
- Validation layer: coordinate sanity, fuel range, weapons compatibility, route logic, cross-spec references.
- 14 named payload presets across 9 aircraft (CAP, strike, SEAD, CAS, antiship).

**MCP server**
- 24 tools exposed over stdio: lifecycle (`new_mission`, `open_mission`, `build_mission`, `validate_mission`, `save_spec`) plus all 19 editor/lookup tools.
- Works with any MCP-capable host. Auto-setup for Claude Desktop, Claude Code, Cursor, Windsurf, and Zed.

**Bundled AI agents (Anthropic API key required)**
- `design_mission(prompt)` — one-shot mission generation.
- `edit_mission(spec, instruction)` — multi-turn tool-call editing loop.
- `design_campaign(prompt)` / `render_mission(campaign, state)` — multi-mission campaigns with persistent state and after-action outcome parsing.

**CLI**
- `build`, `validate`, `inspect`, `import`, `list`, `setup`, `mcp`, `design`, `edit`, `campaign`.

---

## Known gaps

| Area | Status |
|---|---|
| Carrier ops: ICLS / BRC / Link-4 | TACAN works; others need pydcs API additions |
| Trigger import (`.miz → spec`) | Importer warns and skips; triggers are dropped on import |
| Weather import | Not yet imported from `.miz`; defaults to pydcs defaults |
