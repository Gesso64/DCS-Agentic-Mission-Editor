# After-action / outcome parsing (Phase 11)

After a mission ends, the campaign runner needs an `AfterAction` to
advance state. Three sources are supported, in priority order:

1. **DCS Lua callback (recommended)** — a hook embedded in the mission
   writes an outcome JSON when the mission ends. Most accurate; survives
   client/server crashes.
2. **TacView .acmi** — parse a TacView recording. Best-effort: extracts
   destroyed objects by coalition and total duration.
3. **Manual CLI** — `dcs-agentic campaign report --winner blue …`.
   Always available; fastest for ad-hoc playtesting.

All three converge on the same `AfterAction` Pydantic model
([`schemas/campaign.py`](../src/dcs_agentic/schemas/campaign.py)), which
`CampaignRunner.record_outcome()` consumes.

## Auto-dispatch

```python
from dcs_agentic.campaign.after_action import load_outcome

outcome = load_outcome("Logs/op-lion-d-day.outcome.json")
# or
outcome = load_outcome("Tacview/recording.acmi")
```

`load_outcome` picks the parser by extension (`.json` → Lua, `.acmi` →
TacView). The CLI `campaign report --from <file>` uses it.

## Lua callback

[`LUA_HOOK_SCRIPT`](../src/dcs_agentic/campaign/after_action.py) is a
self-contained Lua snippet. Embed it in a `MISSION START` trigger or
attach it via `MissionSpec.custom_scripts` so every campaign mission
runs it. It tracks:

- Blue/red unit deaths via `S_EVENT_DEAD` / `S_EVENT_CRASH`
- Captured airfields via `S_EVENT_BASE_CAPTURED`
- Mission duration
- Writes JSON to `<Saved Games>/DCS/Logs/<mission_name>.outcome.json`
  on `S_EVENT_MISSION_END`

JSON schema produced by the hook (consumed by `parse_lua_callback`):

```json
{
  "mission_name":  "Op Lion D-Day",
  "winner":        "blue",
  "blue_score":    1000,
  "red_score":     200,
  "blue_losses":   ["Hornet 1-1"],
  "red_losses":    ["Bandit 2-1", "Bandit 2-2"],
  "captured":      {"Sochi-Adler": "blue"},
  "flags_set":     {"sam_destroyed": true},
  "duration":      1800.5
}
```

The hook doesn't decide `winner` — that's left to mission scripting
or a manual override (`--winner`). Score fields are also left to
mission scripting; the hook initializes them to 0.

## TacView .acmi

`parse_tacview(filepath, mission_name=None)` reads the ACMI text mode:

- `0,Title=…` → mission name (overridable)
- `<id>,T=…,Coalition=Allies|Enemies,Name=…` → object metadata
- `0,Event=Destroyed|<id>` → loss attributed to that object's coalition
- Highest `#<seconds>` frame seen → duration

Compressed `.zip.acmi` recordings must be extracted to plain text first.

What it doesn't extract: winner, score, captured airfields, flags. Pair
with `--winner` and `--blue-score` / `--red-score` if you want a
complete `AfterAction`:

```
dcs-agentic campaign report --name op-lion \
    --from tacview/mission1.acmi \
    --winner blue --blue-score 1000
```

## CLI

```
dcs-agentic campaign report --name op-lion \
    [--from <file>] \
    [--winner blue|red|draw] \
    [--blue-score N] [--red-score N]
```

| Flag | Behaviour |
|---|---|
| `--from <file>` | Auto-detect `.json` (Lua) or `.acmi` (TacView), parse, and feed into the runner |
| `--winner / --blue-score / --red-score` | Override fields from the parsed file. Without `--from` they form a manual outcome. |

The runner updates state.json with scores, losses, captured airfields,
and flags, then branches `current_mission` per the `MissionLink` graph.

## Not yet implemented

- `winner` inference from score deltas / mission goal completion
- Captured airfield → new coalition mapping (the Lua hook records the
  name but leaves `side="unknown"`)
- `.zip.acmi` decompression
- Score events from DCS's scoring system
