# Examples

## `examples/capabilities_demo.json`

The single committed example, exercising most of the schema in one
file. Walkthrough below.

### What it produces

A combined-arms mission near Sochi with five flights, six vehicle
groups, and two ships:

- **Magic AWACS** — E-3A orbit at FL300 over the Black Sea
- **CAP Dolly** — 2× F/A-18C combat air patrol
- **Strike Razor** — 2× F/A-18C low-level strike, pop to FL150 over target
- **SEAD Viper** — 2× F-16C HARM escort
- **Tanker Texaco** — KC-135 orbit at FL200

Red side: an SA-10 site (radar, CP, two launchers), a ZSU-23-4 AAA, and
a Tor-M2 (SA-15) point-defense.

Blue surface: a Ticonderoga cruiser and an Arleigh Burke destroyer
30 km offshore.

### Weather

Summer, 25°C, scattered clouds at 1500m, light westerly wind. QNH 760.

### Briefing

The blue task narrates the package's sequence; the red task says
"defend the Sochi AD sector." Both render in the DCS mission editor's
briefing screen.

### Coordinate map

All coordinates are in pydcs's Caucasus convention. The mission
clusters around `x ≈ -260000, y ≈ 620000` — Batumi / Sochi corridor.

| Element | Approx position | Notes |
|---|---|---|
| Batumi airfield | spawn for all blue flights | |
| AWACS orbit | (-265k, 645k) | offshore |
| CAP station | (-260k, 625k) | between Batumi and target |
| Strike pop point | (-285k, 615k) | climb from low level |
| SA-10 site | (-300k, 605k) | target |

### Running it

```
python -m dcs_agentic -s examples/capabilities_demo.json -o output/op-lion.miz
```

Expected report:
- 5× `FLIGHT_CREATED`
- 6× `VEHICLE_CREATED`
- 2× `SHIP_CREATED`
- Possibly several `PAYLOADS_UNAVAILABLE` warnings (one per flight) on
  any machine without a local DCS install — the manual fallback path
  handles them.

The `.miz` opens in the DCS mission editor and is flyable.

### Annotated excerpt

```jsonc
{
  "name": "AEW&C + CAP + Strike Package",
  "theatre": "Caucasus",
  "sortie": "OP-LION-01",

  // Both sides include two countries each — exercises the multi-country
  // coalition path in _setup_coalitions.
  "coalitions": [
    {"side": "blue", "country": "USA"},
    {"side": "blue", "country": "UK"},
    {"side": "red",  "country": "Russia"},
    {"side": "red",  "country": "Iran"}
  ],

  // Plain-text briefing rendered in DCS.
  "briefing": { ... },

  "flights": [
    {
      "name": "Magic AWACS",
      "aircraft_type": "E-3A",   // catalog alias
      "country": "USA", "side": "blue",
      "group_size": 1,
      "task": "AWACS",
      "start_type": "cold",
      "airport": "Batumi",
      "altitude": 9000,
      "speed": 350,              // km/h
      "waypoints": [
        // Three-leg orbit: ingress, turn, egress.
        {"x": -260000, "y": 640000, "altitude": 9000, "speed": 350, "name": "AWACS Orbit In"},
        {"x": -270000, "y": 645000, "altitude": 9000, "speed": 300, "name": "AWACS Orbit", "type": "Turning Point"},
        {"x": -260000, "y": 640000, "altitude": 9000, "speed": 350, "name": "AWACS Orbit Out"}
      ]
    },
    // ... CAP, Strike, SEAD, Tanker follow same shape
  ],

  // Six red-side ground groups making up the SAM threat.
  "vehicles": [
    {
      "name": "SA-10 Radar",
      "vehicle_type": "SA-10-SR",  // catalog alias
      "country": "Russia", "side": "red",
      "position": {"x": -300000, "y": 605000},
      "group_size": 1, "heading": 0,
      "skill": "Excellent"
    },
    // ... CP, two LNs, AAA, Tor-M2
  ],

  // Two blue-side surface combatants.
  "ships": [ ... ],

  // Optional weather block.
  "weather": {
    "season": "Summer",         // currently a no-op
    "qnh": 760,
    "temperature": 25,
    "clouds_thickness": 3,
    "clouds_density": 4,
    "clouds_base": 1500,
    "wind_at_ground": {"speed": 5, "dir": 270},
    "wind_at_height": {"speed": 15, "dir": 270}
  },

  // Free-form note; useful when the agent generates the spec.
  "agent_notes": "Mission designed for a 4-player co-op. ..."
}
```

## Demo missions in `__main__.py`

Two specs are hardcoded in [`src/dcs_agentic/__main__.py`](../src/dcs_agentic/__main__.py):

### `--demo-cap`

Minimal 2-flight CAP — 2× F/A-18C from Batumi vs 2× Su-27 from
Sochi-Adler. Both with a single waypoint. Good smoke test.

### `--demo-strike`

Adds the strike-package shape: F/A-18C strike + F-16C SEAD, with a 3-unit
SA-11 site (launcher group of 2, plus radar and CP). Tests the multi-flight
+ multi-vehicle path on the same theatre.

Both demos use the Excellent skill, cold-start at Batumi, and the
Caucasus theatre. They're meant for the test suite, not as good mission
design.
