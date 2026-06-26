# dcs-agentic

AI-driven DCS World mission and campaign editor. Generate `.miz` files
from declarative JSON specs or natural-language prompts. Edit existing
missions via tool-calling agents. Build full campaigns with persistent
state.

## Status

Single-mission generation, `.miz` round-trip importer, trigger builder,
and the three agents (designer / editor / campaign architect) all work.
Phase 4 tail (drawings, FARP, carrier ops builders) and Phase 11
(after-action parsing) are still TODO. See [`PLAN.md`](PLAN.md) for the
full phase tracker.

## Install

```
pip install -e .[dev]
```

For the AI agent features:
```
pip install -e .[dev,agents]
```

Set `ANTHROPIC_API_KEY` (and optionally `ANTHROPIC_BASE_URL` for a
LiteLLM/OpenRouter proxy) before invoking `design` / `edit` / `campaign`.

## Quickstart

Build a mission from a JSON spec:
```
python -m dcs_agentic build examples/capabilities_demo.json -o output/op.miz
```

Design from a prompt:
```
python -m dcs_agentic design -p "2-ship CAP over Batumi" -o output/cap.miz
```

Edit an existing mission:
```
python -m dcs_agentic edit output/cap.miz -i "add an AWACS east of Batumi"
```

Run tests:
```
pytest tests/
```

## Documentation

| Doc | Covers |
|---|---|
| [`docs/index.md`](docs/index.md) | Orientation + what works / what doesn't |
| [`docs/schema-reference.md`](docs/schema-reference.md) | Every Pydantic model and field |
| [`docs/cli.md`](docs/cli.md) | CLI subcommands (`build`, `design`, `edit`, `campaign`) |
| [`docs/pipeline.md`](docs/pipeline.md) | `MissionAssembler` + builders + error codes |
| [`docs/catalog.md`](docs/catalog.md) | Aircraft / vehicle / ship / country aliases |
| [`docs/agents.md`](docs/agents.md) | Designer / editor / campaign agents + 19-tool surface |
| [`docs/importer.md`](docs/importer.md) | `.miz → MissionSpec` reverse-pipeline |
| [`docs/examples.md`](docs/examples.md) | Walkthrough of the bundled examples |
| [`PLAN.md`](PLAN.md) | Forward-looking build plan (12 phases) |
| [`CLAUDE.md`](CLAUDE.md) | Conventions for any Claude session in this repo |

## Repository layout

```
src/dcs_agentic/
├── __init__.py
├── __main__.py                 # CLI entry — dispatches to cli/*
├── errors.py                   # AssemblyReport, AssemblyError, Severity
├── units.py                    # km/h ↔ m/s ↔ kt, m ↔ ft converters
│
├── schemas/                    # Pydantic models — public contract
│   ├── primitives.py           # Position, Waypoint
│   ├── enums.py                # TaskType, StartType, Skill, ROE, AlarmState, …
│   ├── weather.py              # Weather, Wind*
│   ├── briefing.py             # Briefing
│   ├── flight.py               # FlightGroup
│   ├── payload.py              # PayloadSpec, Pylon
│   ├── ground.py               # VehicleGroup, FARP, StaticObject
│   ├── naval.py                # ShipGroup, CarrierOps
│   ├── triggers.py             # TriggerKind / ActionKind closed unions
│   ├── drawing.py              # Zone, MapMarker
│   ├── radio.py                # RadioComms (ATC, AWACS, tanker, JTAC)
│   ├── bullseye.py             # Bullseye per side
│   ├── mission.py              # MissionSpec, Coalition, MissionGoal, CustomScript
│   └── campaign.py             # CampaignSpec, CampaignState, MissionLink, AfterAction
│
├── catalog/                    # Domain knowledge: aliases + lookups
│   ├── aircraft.py             # planes + helicopters; resolve(), is_proxy(), list_by_role()
│   ├── vehicles.py             # AD, artillery, armor (with role tags)
│   ├── ships.py
│   ├── statics.py
│   ├── countries.py
│   ├── theatres.py             # CATALOG[name] → TheatreInfo (bounds, airports, bullseye)
│   ├── payloads.py             # 14 named loadout presets across 9 aircraft
│   └── callsigns.py            # AWACS / tanker / JTAC name → numeric ID
│
├── pipeline/                   # Spec → pydcs → .miz
│   ├── assembler.py            # MissionAssembler orchestrator
│   └── builders/               # Per-concern builders
│       ├── __init__.py         # shared enum mappers
│       ├── coalitions.py       # + get_or_add_country()
│       ├── weather.py
│       ├── flights.py          # incl. _apply_payload (preset or explicit pylons)
│       ├── ground.py
│       ├── naval.py
│       ├── statics.py
│       ├── triggers.py         # Phase 5: TriggerKind/ActionKind → pydcs
│       └── custom_scripts.py
│
├── importer/                   # Phase 6: .miz → MissionSpec
│   └── miz_reader.py           # import_miz() + load_payloads workaround
│
├── validation/                 # Phase 7 (partial): coordinate / weapons / route checks
├── campaign/                   # Phase 10: CampaignRunner + after_action
│   ├── runner.py
│   └── after_action.py
│
├── cli/                        # Subcommands wired via __main__.py
│   ├── build.py
│   ├── design.py
│   ├── edit.py
│   └── campaign.py
│
└── agents/                     # LLM agent layer — Phases 8/9/10
    ├── mission_agent.py        # Phase 8: design_mission()
    ├── editor_agent.py         # Phase 9: edit_mission() with tool-call loop
    ├── campaign_agent.py       # Phase 10: design_campaign(), render_mission()
    ├── llm/
    │   ├── client.py           # Anthropic SDK wrapper + role → model mapping
    │   └── messages.py         # Prompt template rendering + catalog injection
    ├── prompts/
    │   ├── mission_designer.md
    │   ├── editor.md
    │   └── campaign_architect.md
    └── tools/
        └── mutations.py        # 19 editor tools + apply_tool dispatcher
```

## Tests

46 pytest tests across:

- `test_assembler.py` — end-to-end mission build smoke tests + payload preset application
- `test_schema.py` — Pydantic drift checks
- `test_agents.py` — tool surface, prompt rendering, stub-LLM agent loops
- `test_triggers_and_importer.py` — trigger builder + `.miz` round-trip

```
pytest tests/
```

## Contributing

Read [`CLAUDE.md`](CLAUDE.md) first — it documents the conventions every
session (human or AI) in this repo must follow.
