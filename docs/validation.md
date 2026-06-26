# Validation layer (Phase 7)

The validation layer catches errors Pydantic can't — wrong coordinates,
mismatched payloads, impossible routes, dangling references — before
assembly even starts.

```python
from dcs_agentic.validation import validate

report = validate(spec)
for issue in report.issues:
    print(issue.severity, issue.code, issue.message)
```

`validate(spec)` is pure: it doesn't mutate the spec, it doesn't write
anything to disk, and it returns a fresh `AssemblyReport`.

## Validators

Each is a module under [`src/dcs_agentic/validation/`](../src/dcs_agentic/validation/)
exposing `check(spec, report) -> None`.

| Module | What it checks |
|---|---|
| `coordinate_sanity` | Waypoints / positions inside the theatre's bounding box (warns near the edge, errors when far outside) |
| `fuel_range` | Total Euclidean route distance vs. `AircraftInfo.combat_radius_km * 2` |
| `weapons_match` | Payload matches declared task (CAP needs A-A, STRIKE needs bombs, SEAD needs anti-radiation, …) |
| `route_sanity` | Extreme coords (likely x/y swap), >10 km altitude swings between consecutive waypoints, landing waypoints without `airdrome_id` |
| `references` | Triggers reference real groups / units / zones; `carrier_ops.ship_name` matches a ship group |

A buggy validator is wrapped in a try/except so one crash doesn't take
down the rest of the run — it surfaces as `VALIDATOR_CRASHED`.

## Severity guide

| Severity | Use |
|---|---|
| `WARNING` | Likely wrong but might be intentional |
| `ERROR` | Almost certainly broken (route 5× combat radius, coords on the opposite hemisphere, missing referenced ship) |

## Integration

### Assembler

```python
asm = MissionAssembler(spec, validate=True)
asm.assemble()
```

When `validate=True` the assembler runs the validation layer first and
prepends any issues to its own report. Combined with `strict=True`, any
validation error halts the build.

### CLI — `validate` subcommand

```
dcs-agentic validate spec.json [--strict]
```

Reads the spec, runs all validators, prints the report, exits 1 on
errors. With `--strict`, warnings also fail.

## Error codes

| Code | Severity | Source |
|---|---|---|
| `UNKNOWN_THEATRE` | warning | coordinate_sanity (no theatre info) |
| `COORD_OUT_OF_BOUNDS` | error | coordinate_sanity |
| `COORD_NEAR_BOUNDS` | warning | coordinate_sanity (within 20% of edge) |
| `FUEL_RANGE_EXCEEDED` | error | fuel_range (route > 2× combat radius) |
| `FUEL_RANGE_TIGHT` | warning | fuel_range (route > 90% of budget) |
| `WEAPONS_NO_PAYLOAD` | warning | weapons_match (combat task without payload) |
| `WEAPONS_TASK_MISMATCH` | warning | weapons_match |
| `ROUTE_COORD_SUSPICIOUS` | warning | route_sanity (|coord| > 1.5M) |
| `ROUTE_ALTITUDE_SPIKE` | warning | route_sanity (>10 km swing) |
| `ROUTE_LANDING_NO_AIRDROME` | warning | route_sanity (landing wp with no airdrome_id) |
| `REF_UNIT_UNKNOWN` | warning | references |
| `REF_GROUP_UNKNOWN` | warning | references |
| `REF_ZONE_UNKNOWN` | warning | references |
| `REF_CARRIER_SHIP_UNKNOWN` | error | references |
| `VALIDATOR_CRASHED` | error | validate() (a validator raised) |

## Adding a new validator

1. Create `validation/<concern>.py` with a top-level `check(spec, report) -> None`.
2. Add the module's `check` function to `_CHECKS` in `validation/__init__.py`.
3. Add a test in `tests/test_validation.py` exercising at least one
   passing and one failing case.

Validators must not import the assembler or any pydcs class — they
operate on the spec only.
