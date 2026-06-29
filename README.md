# DCS Agentic Mission Editor

**Generate DCS World `.miz` mission files by describing what you want in plain language.**

Tell your AI what you want — _"2-ship F-16 CAP over Batumi at dawn with a SA-10 threat, save to output/op.miz"_ — and it builds the mission file ready to load in DCS World. Works with Claude Desktop, Claude Code, Cursor, Windsurf, Zed, Cline, Continue, or any MCP-capable AI host. The model is never locked.

---

## Prerequisites

- **Python 3.11+**
- **DCS World** installed (to load the generated `.miz` files)
- One of:
  - An **MCP-capable AI host** (Claude Desktop, Claude Code, Cursor, Windsurf, Zed, Cline, Continue) — no API key needed, the model lives in the host
  - An **Anthropic API key** — for the bundled agent / chat GUI path

---

## Quickstart

### Option A — MCP server (recommended)

Connect the tool to your AI host and drive it with any model you already use.

**1–2. Install & register (one command)**

```
python install.py              # interactive menu - pick what to install and which host
python install.py --mcp        # MCP server - prompts for your AI host
python install.py --all        # everything: mcp + agents + gui + dev tools
```

Windows users: double-click **`setup.bat`** to run the interactive menu.

The installer detects what's already set up and skips it. It will ask
which AI host to register with (Claude Desktop, Claude Code, Cursor,
Windsurf, Zed, and more).

Alternatively, install and register manually:
```
pip install -e .[mcp]
python -m dcs_agentic setup --host claude-code          # Claude Code
python -m dcs_agentic setup --host claude-desktop       # Claude Desktop
python -m dcs_agentic setup --host cursor               # Cursor
python -m dcs_agentic setup --host windsurf             # Windsurf
python -m dcs_agentic setup --host zed                  # Zed
```

Omitting `--host` shows an interactive host picker.

Then restart your host (or run `claude mcp list` for Claude Code) to verify.

**3. Create a mission**

Open a chat in your AI host and describe what you want:

> _Create a 2-ship F-16C CAP starting cold at Batumi, SA-10 threat north of the track, save to output/cap.miz_

The AI calls `new_mission` → `add_flight` → `add_vehicle_group` → `build_mission`. The `.miz` is written to disk and opens directly in DCS World.

---

### Option B — Chat GUI (no terminal required)

For DCS players who prefer a desktop chat window over an AI host.

**Requirements:** an Anthropic API key. Install via the setup script or manually:

```
python install.py              # select "Chat GUI" when prompted
```
or:
```
pip install -e .[agents,gui]
python start-mission-gui.py
```

Configure your API key, output folder, and theatre in **Settings** (Ctrl+,). Type what you want; follow-up messages edit the same mission.

---

### Option C — CLI without AI

Build missions from JSON specs or import existing `.miz` files — no AI or API key required.

```
# Build a .miz from a JSON spec
python -m dcs_agentic build examples/capabilities_demo.json -o output/op.miz

# Inspect what's in a .miz
python -m dcs_agentic inspect output/op.miz

# Import an existing .miz back to a JSON spec
python -m dcs_agentic import existing.miz -o spec.json

# Validate a spec without building
python -m dcs_agentic validate examples/capabilities_demo.json
```

See [`examples/`](examples/) for sample specs covering CAP, strike with SEAD, and carrier ops.

---

## Supported theatres

Caucasus · Syria · Persian Gulf · Nevada · Normandy · The Channel · Mariana Islands · Falklands

## Supported AI hosts

| Host | Setup command |
|------|--------------|
| Claude Desktop | `python -m dcs_agentic setup --host claude-desktop` |
| Claude Code | `python -m dcs_agentic setup --host claude-code` |
| Cursor | `python -m dcs_agentic setup --host cursor` |
| Windsurf | `python -m dcs_agentic setup --host windsurf` |
| Zed | `python -m dcs_agentic setup --host zed` |
| Cline (VS Code) | Manual - see [docs/mcp.md](docs/mcp.md) |
| Continue | Manual - see [docs/mcp.md](docs/mcp.md) |

---

## Documentation

| | |
|---|---|
| [**MCP setup & tool catalog**](docs/mcp.md) | Connecting AI hosts, all 24 tools, session model |
| [**CLI reference**](docs/cli.md) | Every subcommand and flag |
| [**Schema reference**](docs/schema-reference.md) | FlightGroup, VehicleGroup, Weather, Trigger, … |
| [**Aircraft & vehicle catalog**](docs/catalog.md) | Type aliases, roles, payload presets |
| [**Examples walkthrough**](docs/examples.md) | CAP, strike/SEAD, carrier ops explained |
| [**Validation**](docs/validation.md) | What gets checked before a `.miz` is built |
| [**Bundled agents**](docs/agents.md) | `design`, `edit`, `campaign` commands (API key path) |
| [**Importer**](docs/importer.md) | `.miz → JSON spec` reverse pipeline |
| [**After-action parsing**](docs/after_action.md) | Lua hook + TacView `.acmi` outcome parsing |

---

## Contributing

1. Read [`CLAUDE.md`](CLAUDE.md) — project conventions every session must follow.
2. `pip install -e .[dev]` then `pytest tests/` — all 107 tests must stay green.
3. Schema + builder + importer + test in the same commit (adding a field without all three causes silent data loss).

---

## License

See [`LICENSE`](LICENSE).
