# Agent layer

Three agents live under [`src/dcs_agentic/agents/`](../src/dcs_agentic/agents/):

| Agent | Phase | Module | Role |
|---|---|---|---|
| Mission designer | 8 | [`mission_agent.py`](../src/dcs_agentic/agents/mission_agent.py) | One-shot `prompt → MissionSpec` |
| Editor | 9 | [`editor_agent.py`](../src/dcs_agentic/agents/editor_agent.py) | Multi-turn tool-call edits to an existing spec |
| Campaign architect | 10 | [`campaign_agent.py`](../src/dcs_agentic/agents/campaign_agent.py) | Designs a `CampaignSpec`; renders per-mission specs from Jinja templates |

All three share a thin Anthropic SDK wrapper:
[`agents/llm/client.py`](../src/dcs_agentic/agents/llm/client.py).

## LLM client

```python
from dcs_agentic.agents.llm.client import LLMClient

client = LLMClient(role="editor")    # role → default model alias
response = client.message(system="…", user="…", tools=TOOLS)
```

`role` maps to a model alias resolved by your LiteLLM/OpenRouter proxy:

| Role | Default alias | Intended tier |
|---|---|---|
| `designer` | `claude-opus-4-7` | Advisor (one-shot quality) |
| `editor` | `claude-sonnet-4-6` | Agent (cheap multi-turn) |
| `campaign_arch` | `claude-opus-4-7` | Advisor |
| `template_render` | `claude-sonnet-4-6` | Agent |

The client uses `ANTHROPIC_API_KEY` and (optionally) `ANTHROPIC_BASE_URL`
for proxy endpoints. System prompts are cache-eligible
(`cache_control: {"type": "ephemeral"}`) so repeated calls re-use the
prompt cache.

### Escalation
`LLMClient.check_for_escalation(text)` returns `"claude-opus-4-7"` when
the input contains "redesign", "rebuild", "rewrite", or "restructure",
otherwise `None`. The editor uses this on the user instruction at start.

## Prompt rendering

[`agents/llm/messages.py`](../src/dcs_agentic/agents/llm/messages.py)
loads `.md` templates from
[`agents/prompts/`](../src/dcs_agentic/agents/prompts/) and substitutes
runtime values:

| Template variable | Source |
|---|---|
| `{{ SCHEMA_JSON }}` | `MissionSpec.model_json_schema()` |
| `{{ THEATRE_AIRPORTS }}` | `catalog.theatres.get_info(theatre).notable_airports` |
| `{{ THEATRE_BULLSEYE }}` | `default_bullseye` (shared default, not per-side) |
| `{{ THEATRE_BOUNDS }}` | bounding box coords for sanity checking |
| `{{ AIRCRAFT_BY_ROLE }}` | `catalog.aircraft.list_by_role(role)` for cap/strike/sead/cas/recon/awacs/tanker/transport/helicopter |
| `{{ VEHICLE_BY_ROLE }}` | sam/aaa/ewr/artillery/armor/infantry |
| `{{ SHIP_LIST }}` | top 30 ship aliases |
| `{{ PAYLOAD_PRESETS }}` | preset names per aircraft (top 10) |
| `{{ TOOL_LIST }}` | editor only — names + descriptions of all 19 tools |

Template paths can be absolute or `agents/...` — the latter is resolved
relative to the package root, so the CLI works from any cwd.

## Mission designer (Phase 8)

```python
from dcs_agentic.agents.mission_agent import design_mission

spec = design_mission(
    "2-ship CAP over Batumi",
    theatre="Caucasus",
    max_retries=2,
)
```

The agent emits a single JSON `MissionSpec`. Markdown code fences are
stripped before parsing. On `ValidationError` or bad JSON, the next
turn is sent with the prior error and previous output so the model
can self-correct.

## Editor (Phase 9)

```python
from dcs_agentic.agents.editor_agent import edit_mission

new_spec = edit_mission(spec, "add an AWACS east of Batumi", theatre="Caucasus")
```

The editor:
1. Builds the system prompt + injects the current spec as JSON.
2. Loops up to `max_turns` (default 20). Each turn the model emits
   text and/or `tool_use` blocks.
3. The assistant message (text + tool_use blocks) is appended to
   history; tool results (one per `tool_use`) come back as a single
   `user` message with `tool_result` content blocks. **This threading
   is what the Anthropic API requires** — a `tool_use` block without
   the matching `tool_result` in the next user turn is rejected.
4. Exits when `stop_reason == "end_turn"` or no tools were called.

### Tool surface — 19 tools

Implemented in
[`agents/tools/mutations.py`](../src/dcs_agentic/agents/tools/mutations.py).
Each tool maps to a handler that returns `(updated_spec, result_message)`.

| Tool | Purpose |
|---|---|
| `add_flight` | Add a `FlightGroup` to `spec.flights` |
| `remove_flight` | Remove a flight by name |
| `move_waypoint` | Move waypoint N of a flight |
| `add_waypoint` | Append a waypoint to a flight's route |
| `set_payload` | Set/replace payload (preset name or explicit pylons) |
| `add_vehicle_group` | Add a `VehicleGroup` |
| `remove_vehicle_group` | Remove by name |
| `add_ship_group` | Add a `ShipGroup` |
| `remove_ship_group` | Remove by name |
| `set_weather` | Replace the weather block |
| `set_briefing` | Replace briefing texts |
| `set_start_time` | Set `start_time` (unix timestamp) |
| `add_trigger` | Append a `Trigger` |
| `get_spec` | Return the current spec as JSON |
| `list_airports` | List airports for the current theatre |
| `list_aircraft` | List aircraft aliases (optionally filtered by role) |
| `list_vehicles` | List vehicle aliases (optionally filtered by role) |
| `list_payload_presets` | List presets (optionally for one aircraft) |
| `validate_spec` | Run the validation layer; returns issues |

### `apply_tool`

```python
from dcs_agentic.agents.tools.mutations import apply_tool

new_spec, msg = apply_tool(spec, "add_waypoint", {
    "flight_name": "Alpha",
    "x": -250000, "y": 625000,
    "altitude": 5000, "speed": 480, "name": "IP",
})
```

Errors are returned as strings (`"Error: …"`) — never raised — so the
LLM can read the failure and adjust on the next turn. Every mutation
deepcopies the spec before modifying, so the caller's input is never
clobbered.

## Campaign architect (Phase 10)

```python
from dcs_agentic.agents.campaign_agent import design_campaign, render_mission
from dcs_agentic.campaign.runner import CampaignRunner

campaign = design_campaign("5-mission strike campaign in Caucasus", theatre="Caucasus")
runner = CampaignRunner.load("campaigns/op-lion")
mission = render_mission(campaign, runner.state, template_dir="campaigns/op-lion/templates")
```

`design_campaign` mirrors `design_mission` but for `CampaignSpec`.
`render_mission` looks up the current `MissionLink`'s `spec_template`,
renders it with Jinja (variables: `state`, `campaign`), and validates
the result as a `MissionSpec`.

`CampaignRunner.record_outcome(after_action)` updates scores/losses/flags
in `state.json` and branches `current_mission` per the `MissionLink`'s
`next_unconditional` / `next_on_blue_win` / `next_on_red_win` /
`next_on_draw` fields.

## Testing

The agent layer ships with offline tests in
[`tests/test_agents.py`](../tests/test_agents.py): 27 tests covering
the tool surface, prompt rendering, the `apply_tool` dispatcher, and
both agent loops with a stubbed Anthropic SDK. **No real LLM is hit**;
the stub responses are constructed in-test. This means CI is fast and
deterministic, but doesn't catch model-behavior regressions.

For real-model smoke testing, set `ANTHROPIC_API_KEY` and invoke the
CLI: `dcs-agentic design -p "..." -o output/test.miz`.
