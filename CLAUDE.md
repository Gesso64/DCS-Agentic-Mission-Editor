# CLAUDE.md — project conventions

This file is read automatically by Claude Code sessions in this repo.

## What this project is

A tool that turns declarative JSON specs (and natural-language prompts)
into DCS World `.miz` mission files, and orchestrates multi-mission
campaigns. See `PLAN.md` for the full architecture and build plan — read
it before starting non-trivial work.

## Hard rules

1. **No silent failures.** Inside `pipeline/`, `catalog/`, `validation/`,
   `importer/`, `campaign/`: never `print()`. Use `self.report.warn(...)`,
   `self.report.error(...)`, or `self.report.info(...)`. Only `cli/`
   prints to stdout/stderr.

2. **Speed values at the schema boundary are km/h** (matches pydcs).
   If a value is in knots somewhere, convert it via
   `dcs_agentic.units.kt_to_kmh()` at the boundary — never inline.

3. **Coordinates use pydcs's convention.** `Point(x, y)` where x is
   north-south and y is east-west. The DCS editor calls these "X-coord"
   and "Z-coord". Don't invent a third name.

4. **Schema + builder + importer + test in the same commit.** Adding a
   field to a Pydantic model without populating it in the .miz = silent
   data loss. Adding it without an importer = lossy round-trip.

5. **No bare `except:`.** Catch named exceptions. `Exception` is
   acceptable only at builder top-level where you immediately
   `report.error(...)` and continue.

6. **Pydantic doesn't validate references.** Cross-spec checks
   ("trigger references unknown flight") belong in `validation/`, not
   in `field_validator`s.

7. **When pydcs's API is unclear, read its source** at
   `.venv/Lib/site-packages/dcs/`. It's the only authoritative reference.

## Common gotchas (real bugs we've already hit)

- `Mission.start_time` wants a **naive** `datetime`, not tz-aware.
- `Weather.Preceptions` is not a typo — pydcs spells it that way.
- The fallback path in `flights.py` (when DCS payloads aren't installed)
  must set `group.task` explicitly. Otherwise every flight ships as CAS.
- `vehicles.add_waypoint(pos, speed=N)` treats N as km/h, not knots.
- `FlightGroup.modulation` is typed as `Optional[Modulation]` (the enum),
  not `int`. Use `Modulation.AM` / `Modulation.FM`, not 0/1.
- `AlarmState` on VehicleGroup is a string enum (`"Green"`/`"Red"`/`"Auto"`).
  The Phase 4 builder must convert to int (0/1/2) when constructing
  `OptAlarmState(value=...)` — pydcs expects an integer.
- `ROE` maps 1:1 to `OptROE.Values` attribute names. Use
  `getattr(OptROE.Values, roe_value)` in the builder, not a hand-written
  lookup table.

## Where things live

| Need to... | Look in... |
|---|---|
| Add a new aircraft alias | `catalog/aircraft.py` |
| Add a payload preset | `catalog/payloads.py` |
| Add a radio model (ATC/AWACS/tanker/JTAC) | `schemas/radio.py` |
| Add a trigger kind or action | `schemas/triggers.py` |
| Add a drawing/zone/marker model | `schemas/drawing.py` |
| Add carrier ops fields | `schemas/naval.py` |
| Add a FARP model | `schemas/ground.py` |
| Add a bullseye field | `schemas/bullseye.py` |
| Change how flights are built | `pipeline/builders/flights.py` |
| Add a schema field | `schemas/<concern>.py`, then update the builder + importer |
| Add a CLI command | `cli/<name>.py`, wire from `__main__.py` |
| Add a validation check | `validation/<check>.py` |

## Tests

`pytest tests/` runs everything. The package must be installed editable
(`pip install -e .[dev]`) before tests work — do not add a `sys.path`
hack to fix a missing install.

## When in doubt

Read `PLAN.md`. It's verbose for a reason — the architectural decisions
are documented with rationale.
