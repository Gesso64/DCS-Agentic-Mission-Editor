# dcs-agentic

AI-driven DCS World mission and campaign editor. Generate `.miz` files
from declarative JSON specs or natural-language prompts. Edit existing
missions via tool-calling agents. Build full campaigns with persistent
state.

## Status

All 12 phases of [`PLAN.md`](PLAN.md) are complete: single-mission
generation, `.miz` round-trip importer, full trigger builder, full
Phase-4 builders (payloads, ROE/AlarmState, FARPs, drawings, carrier
TACAN), the three agents (designer / editor / campaign architect),
the validation layer, after-action parsing (Lua hook + TacView), and
CLI polish (`inspect`, `list`, `--version`). 88 tests pass.

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

## GUI (chat)

Prefer to just talk to the AI? Launch the desktop chat GUI:

```
run-gui.bat              # Windows — double-click, or:
python start-mission-gui.py
```

Type what you want ("2-ship F-16 CAP over Batumi at dawn"); it designs the
mission, assembles the `.miz`, and saves it to your output folder. Follow-up
messages edit that same mission ("add a tanker", "move the CAP north"). Set
your `ANTHROPIC_API_KEY` (and optional proxy base URL), theatre, output
folder, and model override in **Settings** (Ctrl+,). Requires `PySide6`
(`pip install PySide6`) and the `agents` extra.

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
| [`docs/architecture.md`](docs/architecture.md) | Module map + conventions + build order |
| [`docs/schema-reference.md`](docs/schema-reference.md) | Every Pydantic model and field |
| [`docs/cli.md`](docs/cli.md) | CLI subcommands (`build`, `design`, `edit`, `campaign`) |
| [`docs/pipeline.md`](docs/pipeline.md) | `MissionAssembler` + builders + error codes |
| [`docs/catalog.md`](docs/catalog.md) | Aircraft / vehicle / ship / country aliases |
| [`docs/agents.md`](docs/agents.md) | Designer / editor / campaign agents + 19-tool surface |
| [`docs/importer.md`](docs/importer.md) | `.miz → MissionSpec` reverse-pipeline |
| [`docs/validation.md`](docs/validation.md) | Phase 7 validation layer |
| [`docs/after_action.md`](docs/after_action.md) | Phase 11 outcome parsing (Lua hook, TacView) |
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

## License

Proprietary — All Rights Reserved. See [`LICENSE`](LICENSE). This is a
private project; access to the repository does not grant a license to
the code.
