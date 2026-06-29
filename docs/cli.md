# CLI reference

Invoke as either:

```
python -m dcs_agentic <subcommand> [flags]
dcs-agentic <subcommand> [flags]
```

Run `--help` at any level for usage details.

## Subcommands

| Subcommand | Purpose | Requires AI? |
|---|---|---|
| `build` | Build a `.miz` from a JSON spec | No |
| `validate` | Check a spec for errors without building | No |
| `inspect` | Show what's inside a `.miz` or spec | No |
| `import` | Convert a `.miz` to a JSON spec | No |
| `list` | Browse the aircraft / vehicle / payload catalog | No |
| `setup` | Register the MCP server with your AI host | No |
| `mcp` | Start the MCP server (stdio) | No |
| `design` | Generate a mission from a natural-language prompt | Yes — API key |
| `edit` | Edit a mission via natural-language instruction | Yes — API key |
| `campaign` | Manage multi-mission campaigns | Yes — API key |

---

## `build`

```
dcs-agentic build SPEC_FILE [-o OUTPUT] [--strict]
```

Reads a JSON `MissionSpec`, assembles it with pydcs, and writes a `.miz`.

| Flag | Description |
|---|---|
| `SPEC_FILE` | Path to a JSON mission spec (required) |
| `-o`, `--output` | Output `.miz` path (default: `output/mission.miz`) |
| `--strict` | Exit non-zero if any error-severity issue is reported |

---

## `validate`

```
dcs-agentic validate SPEC_FILE [--strict]
```

Runs coordinate sanity, fuel range, weapons compatibility, route logic, and
cross-reference checks against the spec without touching pydcs. Fast — use
it before `build`.

| Flag | Description |
|---|---|
| `SPEC_FILE` | Path to a JSON mission spec (required) |
| `--strict` | Treat warnings as failures |

---

## `inspect`

```
dcs-agentic inspect INPUT [--json]
```

Prints a section-by-section summary of a `.miz` or JSON spec: coalitions,
flights, vehicles, ships, statics, FARPs, carrier ops, triggers, zones,
markers. `--json` dumps the full raw spec instead.

---

## `import`

```
dcs-agentic import INPUT [-o OUTPUT] [--json]
```

Converts an existing `.miz` file into a JSON `MissionSpec`. Useful for
inspecting community missions, round-tripping edits, or seeding a spec
you'll then edit with the MCP server.

| Flag | Description |
|---|---|
| `INPUT` | Path to a `.miz` file (required) |
| `-o`, `--output` | Output JSON path (default: `<input>.json`) |
| `--json` | Print JSON to stdout instead of writing a file |

Warnings are printed for fields the importer doesn't yet handle (weather,
triggers, drawings). The rest imports cleanly.

---

## `list`

```
dcs-agentic list {aircraft|vehicles|ships|statics|payloads|theatres|airports|callsigns} [filters]
```

Browse the bundled catalog. Helpful when writing JSON specs by hand.

| Flag | Applies to | Description |
|---|---|---|
| `--role` | aircraft / vehicles | Filter by role tag (`cap`, `strike`, `sam`, `armor`, …) |
| `--aircraft` | payloads | Show presets for one aircraft alias |
| `--theatre` | airports | Show airports for one theatre |

Examples:

```
dcs-agentic list aircraft --role cap
dcs-agentic list payloads --aircraft F/A-18C
dcs-agentic list airports --theatre Syria
dcs-agentic list callsigns
```

---

## `setup`

```
dcs-agentic setup [--host HOST] [--dry-run]
```

Registers the MCP server with your AI host by writing into its config file.
Backs up the existing config before writing. Safe to run multiple times —
it only updates the `dcs-agentic` entry, leaving other servers untouched.

| Flag | Description |
|---|---|
| `--host` | Target host (see table below). Default: `claude-desktop` |
| `--dry-run` | Show what would be written without modifying any files |

| `--host` value | Config file written |
|---|---|
| `claude-desktop` | `~/AppData/Roaming/Claude/claude_desktop_config.json` (Windows) |
| `claude-code` | `~/.claude.json` |
| `claude-code-project` | `.mcp.json` in the current directory |
| `cursor` | `~/.cursor/mcp.json` |
| `cursor-project` | `.cursor/mcp.json` in the current directory |
| `windsurf` | `~/.codeium/windsurf/mcp_config.json` |
| `zed` | `~/.config/zed/settings.json` |

For Cline and Continue, see the manual snippets in [`docs/mcp.md`](mcp.md).

---

## `mcp`

```
dcs-agentic mcp
```

Starts the MCP server on stdio. Normally your AI host launches this
automatically — you only need to run it manually for debugging or when
using an MCP client that doesn't auto-launch servers.

Requires `pip install -e .[mcp]`.

---

## `design`

```
dcs-agentic design -p PROMPT [-t THEATRE] [-o OUTPUT] [--model MODEL] [--strict]
```

Generates a `MissionSpec` from a natural-language prompt using the bundled
AI agent, then assembles the `.miz`. Requires `ANTHROPIC_API_KEY`.

| Flag | Description |
|---|---|
| `-p`, `--prompt` | Mission description in natural language (required) |
| `-t`, `--theatre` | Theatre/map (default: `Caucasus`) |
| `-o`, `--output` | Output `.miz` path (default: `output/mission.miz`) |
| `--model` | Model override (default: `claude-opus-4-5`) |
| `--strict` | Exit non-zero on assembly errors |

---

## `edit`

```
dcs-agentic edit INPUT -i INSTRUCTION [-o OUTPUT] [--model MODEL] [--strict]
```

Loads an existing mission and edits it via a multi-turn AI tool-call loop.
Requires `ANTHROPIC_API_KEY`.

| Flag | Description |
|---|---|
| `INPUT` | `.miz` file or JSON spec to edit (required) |
| `-i`, `--instruction` | Natural-language edit instruction (required) |
| `-o`, `--output` | Output `.miz` path (default: `output/edited_mission.miz`) |
| `--model` | Model override (default: `claude-sonnet-4-5`) |
| `--strict` | Exit non-zero on assembly errors |

---

## `campaign`

```
dcs-agentic campaign init    --name NAME --prompt PROMPT [--theatre T] [--model M] [--dir D]
dcs-agentic campaign run     --name NAME [--model M] [--dir D]
dcs-agentic campaign report  --name NAME [--winner blue|red|draw] [--blue-score N] [--red-score N] [--dir D]
dcs-agentic campaign inspect --name NAME [--dir D]
```

Manages a multi-mission campaign stored under `<DIR>/<NAME>/`. `init` designs
the campaign structure; `run` renders the current mission template to a `.miz`;
`report` records the outcome and advances the campaign branch; `inspect` shows
current state.

| Flag | Subcommand | Description |
|---|---|---|
| `--name` | all | Campaign name (matches directory) |
| `--prompt` | init | Campaign description |
| `--theatre` | init | Default: `Caucasus` |
| `--model` | init / run | Model override |
| `--dir` | all | Campaigns root directory (default: `campaigns`) |
| `--winner` | report | `blue`, `red`, or `draw` |
| `--blue-score` | report | Defaults to 0 |
| `--red-score` | report | Defaults to 0 |
| `--from FILE` | report | Read outcome from a `.json` (Lua hook) or `.acmi` (TacView) file |

Requires `ANTHROPIC_API_KEY`. See [`after_action.md`](after_action.md) for the
outcome file formats.

---

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Error (missing argument, strict mode with assembly errors, import failure) |
