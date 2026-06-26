"""CLI command: inspect -show what's in a .miz file or JSON spec."""

import argparse
import json
import sys
from pathlib import Path


def register_subcommand(subparsers) -> None:
    parser = subparsers.add_parser(
        "inspect",
        help="Show a summary of a .miz file or MissionSpec JSON",
        description="Reads a .miz (via the importer) or a JSON spec, "
                    "prints flights, vehicles, ships, statics, FARPs, "
                    "carrier ops, triggers, and zones.",
    )
    parser.add_argument(
        "input", type=str,
        help="Path to a .miz or .json file",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Print the full spec as JSON instead of a summary",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    from ..schemas import MissionSpec

    path = Path(args.input)
    if not path.exists():
        print(f"ERROR: File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if path.suffix.lower() == ".miz":
        from ..importer.miz_reader import import_miz
        spec, report = import_miz(str(path))
        if report.issues:
            print("Importer report:")
            print(report.format())
            print()
    else:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        spec = MissionSpec.model_validate(data)

    if args.json:
        print(spec.model_dump_json(indent=2))
        return

    _print_summary(spec)


def _print_summary(spec) -> None:
    print(f"Mission:  {spec.name}")
    print(f"Theatre:  {spec.theatre}")
    if spec.sortie:
        print(f"Sortie:   {spec.sortie}")
    if spec.start_time is not None:
        print(f"Start:    unix {spec.start_time}")

    _section("Coalitions", spec.coalitions,
             lambda c: f"{c.side}: {c.country}")
    _section("Flights", spec.flights,
             lambda f: f"{f.name} -{f.aircraft_type} x{f.group_size or 1} "
                       f"({f.task.value if f.task else '?'}) from {f.airport or 'inflight'}")
    _section("Vehicles", spec.vehicles,
             lambda v: f"{v.name} -{v.vehicle_type} x{v.group_size or 1} ({v.side})")
    _section("Ships", spec.ships,
             lambda s: f"{s.name} -{s.ship_type} x{s.group_size or 1} ({s.side})")
    _section("Statics", spec.statics,
             lambda s: f"{s.name} -{s.type} ({s.side})")
    _section("FARPs", spec.farps,
             lambda f: f"{f.name} ({'invisible' if f.invisible else 'visible'}) at "
                       f"({f.position.x:.0f}, {f.position.y:.0f})")
    _section("Carrier ops", spec.carrier_ops,
             lambda c: f"{c.ship_name}: TACAN ch {c.tacan_channel}{c.tacan_mode or 'X'} "
                       f"'{c.tacan_callsign or 'STN'}'")
    _section("Triggers", spec.triggers,
             lambda t: f"{t.name}: {len(t.conditions)} cond → {len(t.actions)} act")
    _section("Zones", spec.zones,
             lambda z: f"{z.name}: r={z.radius:.0f}m at ({z.center.x:.0f}, {z.center.y:.0f})")
    _section("Markers", spec.markers,
             lambda m: f"{m.name} [{m.coalition}]: {m.text[:40]}")


def _section(title, items, fmt):
    items = items or []
    print(f"\n{title} ({len(items)}):")
    if not items:
        print("  (none)")
    for it in items:
        print(f"  - {fmt(it)}")
