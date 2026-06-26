# Architecture

One-pager summary of how dcs-agentic is laid out, the data shape, and
the conventions every module follows. Use this to orient before
reading any specific file.

## Core idea

dcs-agentic turns a **declarative spec** into a `.miz` and back.

```
MissionSpec (Pydantic)
        │
        │   pipeline/  ───  per-concern builders
        ▼
   pydcs Mission ───────▶  .miz on disk
        ▲                       │
        │                       │ importer/miz_reader.py
        │                       ▼
        └──────────────  MissionSpec (round-tripped)
```

The same `MissionSpec` is the contract for human authors, AI agents,
and the campaign runner.

## Module map

| Layer | Module | Responsibility |
|---|---|---|
| **Contract** | `schemas/` | Pydantic models — what a mission can describe. Pure declaration; no behavior. |
| **Domain knowledge** | `catalog/` | Aliases for aircraft/vehicles/ships/statics/countries/theatres + payload presets + callsigns. |
| **Forward pipeline** | `pipeline/` | `MissionAssembler` orchestrator + per-concern builders. Spec → pydcs → `.miz`. |
| **Reverse pipeline** | `importer/` | `.miz` → `MissionSpec`. Best-effort; not every field round-trips yet. |
| **Validation** | `validation/` | Cross-cutting checks beyond Pydantic. Pure. |
| **Conversions** | `units.py` | km/h ↔ m/s ↔ kt, m ↔ ft. The only place these constants live. |
| **Errors** | `errors.py` | `AssemblyReport` accumulator + structured `AssemblyIssue` + `AssemblyError`. |
| **Campaign** | `campaign/` | `CampaignRunner` (state machine over a `CampaignSpec` graph) + `after_action` (Lua hook, TacView, JSON dispatch). |
| **Agents** | `agents/` | LLM-driven mission designer, editor (19-tool surface), campaign architect. Wraps Anthropic SDK. |
| **CLI** | `cli/` + `__main__.py` | Subcommand entry points: `build`, `validate`, `design`, `edit`, `campaign`, `inspect`, `list`. |

## Conventions (all enforced)

1. **No silent failures inside `pipeline/`, `catalog/`, `validation/`,
   `importer/`, `campaign/`.** Use `report.warn/error/info`. `print()`
   lives only in `cli/` and `__main__.py`.
2. **Speeds at the schema boundary are km/h** (matches pydcs).
   Conversion happens via `units.kmh_to_ms` / `units.kt_to_kmh` at the
   builder. No bare `/ 3.6` or `* 1.852` anywhere else.
3. **`Point(x, y)` is pydcs convention** — x is north-south, y is
   east-west. Don't invent a third name.
4. **Schema + builder + importer + validator + test land in the same
   commit.** A new field with no builder = silent data loss.
5. **No bare `except:`.** Catch named exceptions or `Exception` at a
   builder's top level (immediately followed by `report.error`).
6. **Cross-spec validation lives in `validation/`, not in Pydantic
   `field_validator`s.** Pydantic catches type/shape errors; the
   validation layer catches "this trigger references a flight that
   doesn't exist."
7. **Catalog lookups use friendly aliases.** `F/A-18C` not
   `FA-18C_hornet`. The aliases resolve to the pydcs class via
   `catalog.aircraft.resolve()`.
8. **When pydcs's API is unclear, read its source** at
   `.venv/Lib/site-packages/dcs/`. It's the only authoritative reference.

## Build order

`MissionAssembler.assemble()` calls builders in dependency order:

1. theatre resolution
2. basic info (briefing, sortie, start_time)
3. coalitions
4. weather
5. flights (incl. payload application)
6. ground (incl. ROE, AlarmState)
7. naval
8. carrier_ops (TACAN beacon on waypoint 0)
9. statics
10. FARPs
11. drawings (zones + markers)
12. triggers
13. custom scripts
14. strict check

See [`pipeline.md`](pipeline.md) for the full builder/error-code table.

## Agent loop shape

Editor agent (similar shape for designer):

```
build_system_prompt + inject(catalog + schema)
        │
        ▼
LLMClient.message_with_history(system, messages, tools=TOOLS)
        │
        ├── text → end
        └── tool_use[] ──▶ apply_tool(spec, name, input)
                              │
                              ▼
                          tool_result[] (next user message)
                              │
                              ▼
                          (loop)
```

The assistant `tool_use` blocks **must** be appended to history before
the next `tool_result` message — the Anthropic API enforces this.

## Where to read next

- [`schema-reference.md`](schema-reference.md) — every model, field, default
- [`pipeline.md`](pipeline.md) — builders + error codes
- [`agents.md`](agents.md) — agent layer + tool surface
- [`validation.md`](validation.md) — Phase 7 checks
- [`importer.md`](importer.md) — .miz reverse pipeline
- [`after_action.md`](after_action.md) — Phase 11 outcome parsing
- [`PLAN.md`](../PLAN.md) — the build plan with full rationale (verbose,
  but the architectural decisions are documented with their why)
