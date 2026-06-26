# Bundled examples

Four ready-to-build specs under [`examples/`](../examples/). Each can
be turned into a `.miz`:

```
dcs-agentic build examples/<name>.json -o output/<name>.miz
```

## `cap.json` — Batumi CAP

Two-ship F/A-18C CAP launching from Batumi, with a hostile Su-27 pair
at Sochi-Adler. CAP loadout on both sides. Minimal — useful as a sanity
check that builds and basic agent prompts produce.

```
dcs-agentic build examples/cap.json -o output/cap.miz
dcs-agentic inspect examples/cap.json
```

## `strike_with_sead.json` — SA-11 strike

Hornet strike (4× GBU-38 via the `STRIKE GBU-38` preset) escorted by
SEAD-tasked F-16Cs. Target is a 3-vehicle SA-11 battery (LN + SR + CP)
with `roe=WeaponFree` and `alarm_state=Red`. The target area is marked
with a red zone.

Exercises: payload presets, ROE/AlarmState wiring, drawings.

## `carrier_ops.json` — Stennis TACAN

Single-carrier setup with full `CarrierOps` block. TACAN ch 72X "WSH"
gets wired through `ActivateBeaconCommand`. ICLS / BRC / Link-4 surface
as `CARRIER_OPS_PARTIAL` warnings until pydcs exposes those APIs.

```
dcs-agentic build examples/carrier_ops.json -o output/carrier.miz
```

## `capabilities_demo.json` — every feature

The original kitchen-sink spec. Used by the test suite. Read it to see
what every schema field looks like in practice. **Don't trim it** — it
doubles as the schema-coverage regression test.

## Running the agents against the examples

```
# Designer: produce a new spec from a prompt
dcs-agentic design -p "Batumi CAP with 2 Hornets" -o output/test.miz

# Editor: tweak an existing one
dcs-agentic edit examples/cap.json -i "add an AWACS east of Batumi"

# Validate without assembling
dcs-agentic validate examples/strike_with_sead.json
```

## Browsing the catalog

```
dcs-agentic list aircraft --role cap
dcs-agentic list vehicles --role sam
dcs-agentic list payloads --aircraft F/A-18C
dcs-agentic list airports --theatre Caucasus
dcs-agentic list callsigns
```
