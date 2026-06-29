# MCP Server

`dcs-agentic` exposes its mission-building tool surface over the
[Model Context Protocol](https://modelcontextprotocol.io) so any MCP host
— Claude Desktop, Claude Code, Cursor, Windsurf, Zed, Cline, Continue —
can build and edit DCS World `.miz` missions. The model is never locked;
it lives in whatever host you connect.

## Setup

### Quick install

```
python install.py              # interactive menu - pick what to install and which host
python install.py --mcp        # MCP server - prompts for your AI host
python install.py --all        # everything: mcp + agents + gui + dev tools
```

Windows users: double-click **`setup.bat`**.

The installer detects what's already set up and skips it. It will ask
which AI host to register with (Claude Desktop, Claude Code, Cursor,
Windsurf, Zed, and more).

### Manual install

```
pip install -e .[mcp]
python -m dcs_agentic setup --host claude-code          # Claude Code (global)
python -m dcs_agentic setup --host claude-code-project  # Claude Code (this project)
python -m dcs_agentic setup --host claude-desktop       # Claude Desktop
python -m dcs_agentic setup --host cursor               # Cursor (global)
python -m dcs_agentic setup --host cursor-project       # Cursor (this project)
python -m dcs_agentic setup --host windsurf             # Windsurf
python -m dcs_agentic setup --host zed                  # Zed
python -m dcs_agentic setup --dry-run                   # preview without writing
```

Omitting `--host` shows an interactive host picker.

The setup command writes into your host's config file. It merges safely -
other MCP servers you have registered are not touched - and backs up the
file before any change.

### 3. Restart your host

- **Claude Desktop** — fully quit and relaunch (Ctrl+Q / Cmd+Q).
- **Claude Code** — run `claude mcp list` to verify it's registered.
- **Cursor / Windsurf** — picked up automatically; check Settings → MCP.
- **Zed** — auto-restarts on settings.json save, no relaunch needed.

---

### Manual config snippets

For hosts the setup command doesn't cover (Cline, Continue), or if you prefer
to edit the file yourself:

**Claude Desktop** — `~/AppData/Roaming/Claude/claude_desktop_config.json`
(Windows) / `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS):
```json
{
  "mcpServers": {
    "dcs-agentic": {
      "command": "C:\\path\\to\\python.exe",
      "args": ["-m", "dcs_agentic", "mcp"]
    }
  }
}
```

**Claude Code** — `~/.claude.json` (global) or `.mcp.json` (project):
```json
{
  "mcpServers": {
    "dcs-agentic": {
      "command": "/path/to/python",
      "args": ["-m", "dcs_agentic", "mcp"]
    }
  }
}
```

**Cursor** — `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project):
```json
{
  "mcpServers": {
    "dcs-agentic": {
      "command": "/path/to/python",
      "args": ["-m", "dcs_agentic", "mcp"]
    }
  }
}
```

**Windsurf** — `~/.codeium/windsurf/mcp_config.json`:
```json
{
  "mcpServers": {
    "dcs-agentic": {
      "command": "/path/to/python",
      "args": ["-m", "dcs_agentic", "mcp"]
    }
  }
}
```

**Zed** — `~/.config/zed/settings.json` (note: Zed uses `context_servers`,
not `mcpServers`):
```json
{
  "context_servers": {
    "dcs-agentic": {
      "command": "/path/to/python",
      "args": ["-m", "dcs_agentic", "mcp"]
    }
  }
}
```

**Cline (VS Code extension)** — VS Code `settings.json` (use the Cline panel
→ MCP Servers → Add, or edit directly):
```json
{
  "cline.mcpServers": {
    "dcs-agentic": {
      "command": "/path/to/python",
      "args": ["-m", "dcs_agentic", "mcp"],
      "disabled": false
    }
  }
}
```

**Continue (VS Code / JetBrains)** — `~/.continue/config.yaml`:
```yaml
mcpServers:
  - name: dcs-agentic
    type: stdio
    command: /path/to/python
    args: ["-m", "dcs_agentic", "mcp"]
```

> **Finding your Python path:** run `python -m dcs_agentic setup --dry-run`
> and copy the `Command` line — it shows the exact interpreter path to paste
> into any of the snippets above.

---

## Session model

Each stdio session holds one **working `MissionSpec`** in memory. The
typical flow:

1. `new_mission` or `open_mission` — establish the working spec
2. Edit tools (`add_flight`, `set_weather`, …) — mutate it
3. `build_mission` — assemble and save the `.miz`

State is not persisted between sessions. Use `save_spec` to write a JSON
snapshot you can reload later with `open_mission`.

---

## Tool catalog

### Lifecycle tools

| Tool | Description |
|------|-------------|
| `new_mission(name, theatre?)` | Create a fresh mission. Theatre defaults to `Caucasus`. |
| `open_mission(path)` | Load a `.miz` or JSON spec file. Returns an import report. |
| `build_mission(output_path)` | Assemble and save the `.miz`. Returns build report. |
| `validate_mission()` | Run the validation layer without building. |
| `save_spec(output_path)` | Save the working spec as JSON for inspection or version control. |

### Flight tools

| Tool | Description |
|------|-------------|
| `add_flight(…)` | Add a `FlightGroup` (full schema). |
| `remove_flight(name)` | Remove a flight group by name. |
| `move_waypoint(flight_name, waypoint_index, x, y, altitude?, speed?)` | Reposition one waypoint. |
| `add_waypoint(flight_name, x, y, altitude?, speed?, name?)` | Append a waypoint. |
| `set_payload(flight_name, preset_name?, pylons?)` | Set or replace payload. |

### Ground / naval tools

| Tool | Description |
|------|-------------|
| `add_vehicle_group(…)` | Add a ground vehicle group. |
| `remove_vehicle_group(name)` | Remove a vehicle group. |
| `add_ship_group(…)` | Add a ship group. |
| `remove_ship_group(name)` | Remove a ship group. |

### Mission-level tools

| Tool | Description |
|------|-------------|
| `set_weather(…)` | Replace the weather block. |
| `set_briefing(…)` | Replace the briefing texts. |
| `set_start_time(start_time)` | Set mission start time (unix timestamp). |
| `add_trigger(…)` | Add a mission trigger. |

### Read-only lookups

| Tool | Description |
|------|-------------|
| `get_spec()` | Return the full working spec as JSON. |
| `list_airports(?)` | List airports for the current theatre. |
| `list_aircraft(role?)` | List aircraft aliases, optionally filtered by role. |
| `list_vehicles(role?)` | List vehicle aliases, optionally filtered by role. |
| `list_payload_presets(aircraft_alias?)` | List available payload presets. |
| `validate_spec()` | Run validation and return issues (alias for `validate_mission`). |

---

## Example session

```
User: Create a 2-ship F-16 CAP over Batumi at dawn.

Agent calls:
  new_mission(name="Op Falcon", theatre="Caucasus")
  set_start_time(start_time=1696118400)   # 06:00 local
  add_flight(name="Falcon 1", aircraft_type="F-16C_50", country="USA",
             side="blue", group_size=2, task="CAP",
             start_type="cold", airport="Batumi", skill="Excellent",
             waypoints=[...])
  validate_mission()
  build_mission(output_path="output/op_falcon.miz")
```

The resulting `.miz` opens directly in DCS World.

---

## Coordinate system

Positions use **pydcs's `Point(x, y)` convention**: `x` is north-south,
`y` is east-west. This matches what the DCS editor calls "X-coord" and
"Z-coord". Values are in metres relative to the theatre origin.

## Speed values

All speed inputs are **km/h** (matches pydcs internally). Convert knots
with `knots × 1.852`.
