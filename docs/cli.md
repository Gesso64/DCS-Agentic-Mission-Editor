# CLI reference

The CLI entry point is [`src/dcs_agentic/__main__.py`](../src/dcs_agentic/__main__.py).
Invoke as either:

```
python -m dcs_agentic <subcommand> [flags]
dcs-agentic <subcommand> [flags]              # if installed via `pip install -e .`
```

## Subcommands

| Subcommand | Purpose |
|---|---|
| `build` | Build a `.miz` from a JSON `MissionSpec` file |
| `validate` | Run validation checks over a JSON spec without assembling |
| `design` | Use an LLM to create a mission from a natural-language prompt |
| `edit` | Edit an existing mission (`.miz` or `spec.json`) via LLM tool calls |
| `campaign` | Initialize, run, report, and inspect multi-mission campaigns |

Each subcommand prints a usage banner via `--help`.

## `build`

```
dcs-agentic build SPEC_FILE [-o OUTPUT] [--strict]
```

Reads a JSON `MissionSpec`, runs the assembler, writes a `.miz`, and
prints the `AssemblyReport`.

| Flag | Description |
|---|---|
| `SPEC_FILE` | Path to a JSON mission spec (positional, required) |
| `-o`, `--output` | Output `.miz` path (default: `output/mission.miz`) |
| `--strict` | Exit non-zero if any error-severity issue occurred |

## `validate`

```
dcs-agentic validate SPEC_FILE [--strict]
```

Runs the Phase 7 validation layer (`coordinate_sanity`, `fuel_range`,
`weapons_match`, `route_sanity`, `references`) against the spec without
touching pydcs. Exits 1 if any error is reported; with `--strict`,
warnings also fail.

| Flag | Description |
|---|---|
| `SPEC_FILE` | Path to a JSON mission spec (positional, required) |
| `--strict` | Treat warnings as failures |

## `design`

```
dcs-agentic design -p PROMPT [-t THEATRE] [-o OUTPUT] [--model MODEL] [--strict]
```

Calls `agents.mission_agent.design_mission()` to generate a `MissionSpec`
from a natural-language prompt, validates it, and assembles a `.miz`.
Retries on validation failure (up to 2 times).

| Flag | Description |
|---|---|
| `-p`, `--prompt` | Natural-language description (required) |
| `-t`, `--theatre` | Theatre/map (default: `Caucasus`) |
| `-o`, `--output` | Output `.miz` path (default: `output/mission.miz`) |
| `--model` | LLM model alias override (e.g. `claude-sonnet-4-6` for GLM) |
| `--strict` | Exit non-zero on assembly errors |

Requires `ANTHROPIC_API_KEY` (or `ANTHROPIC_BASE_URL` for a LiteLLM proxy).

## `edit`

```
dcs-agentic edit INPUT -i INSTRUCTION [-o OUTPUT] [--model MODEL] [--strict]
```

Loads a mission (from `.miz` via the importer, or from a `spec.json`),
runs `agents.editor_agent.edit_mission()` which drives a multi-turn
tool-call loop, then assembles the result.

| Flag | Description |
|---|---|
| `INPUT` | `.miz` file or `spec.json` to edit (positional, required) |
| `-i`, `--instruction` | Natural-language edit instruction (required) |
| `-o`, `--output` | Output `.miz` path (default: `output/edited_mission.miz`) |
| `--model` | LLM model alias override |
| `--strict` | Exit non-zero on assembly errors |

The editor uses 19 tools (`add_flight`, `move_waypoint`, `set_payload`, …)
— see [`agents.md`](agents.md) for the full list.

## `campaign`

```
dcs-agentic campaign init    --name NAME --prompt PROMPT [--theatre T] [--model M] [--dir D]
dcs-agentic campaign run     --name NAME [--model M] [--dir D]
dcs-agentic campaign report  --name NAME [--winner blue|red|draw] [--blue-score N] [--red-score N] [--dir D]
dcs-agentic campaign inspect --name NAME [--dir D]
```

Manages a multi-mission campaign rooted at `<DIR>/<NAME>/`. `init`
designs the `CampaignSpec` and writes `campaign.json` + `state.json`;
`run` renders the current mission template and saves a `.miz`;
`report` records an outcome and advances the branch; `inspect` prints
state.

| Flag | Subcommand | Description |
|---|---|---|
| `--name` | all | Campaign name (matches directory) |
| `--prompt` | init | Campaign description |
| `--theatre` | init | Default: `Caucasus` |
| `--model` | init / run | LLM model override |
| `--dir` | all | Campaigns root (default: `campaigns`) |
| `--winner` | report | `blue`, `red`, or `draw` |
| `--blue-score` | report | Defaults to 0 |
| `--red-score` | report | Defaults to 0 |
| `--from <file>` | report | Read outcome from `.json` (Lua hook) or `.acmi` (TacView). CLI flags override file values when set. See [`after_action.md`](after_action.md). |

## Output (build / design / edit)

Standard output contains, in order:
1. A short header (name, theatre, counts).
2. The block `Assembly report:` followed by every issue from
   [`AssemblyReport`](../src/dcs_agentic/errors.py) in the format
   `SEVERITY CODE [context]: message  hint: ...`.
3. `Done! Mission saved to: <path>`.
4. If errors occurred: a summary line `(N error(s), M warning(s))`.

If `--strict` is set and the assembly produces any error, the process
raises `AssemblyError` and exits non-zero. Without `--strict`, errors
are reported but the `.miz` is still written.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | success (or non-strict with errors) |
| 1 | no subcommand given, or strict mode with errors |
| 2 | `edit` invoked with a `.miz` whose importer returned `IMPORTER_NOT_IMPLEMENTED` (defensive guard — current importer implements round-trip, but the guard remains) |

## Examples

```
# Build from a JSON spec
dcs-agentic build examples/capabilities_demo.json -o output/op-lion.miz

# Design from a prompt
dcs-agentic design -p "2-ship CAP over Batumi, Russian Su-27 threat from Sochi"

# Edit an existing mission
dcs-agentic edit output/op-lion.miz -i "add an AWACS orbiting 100km east of Batumi"

# Campaign workflow
dcs-agentic campaign init --name op-lion --prompt "5-mission strike campaign in Caucasus"
dcs-agentic campaign run  --name op-lion
dcs-agentic campaign report --name op-lion --winner blue --blue-score 1000
dcs-agentic campaign inspect --name op-lion
```
