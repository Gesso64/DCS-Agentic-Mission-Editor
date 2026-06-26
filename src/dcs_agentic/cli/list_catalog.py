"""CLI command: list — browse the catalog (aircraft/vehicles/payloads/theatres)."""

import argparse


def register_subcommand(subparsers) -> None:
    parser = subparsers.add_parser(
        "list",
        help="List catalog entries (aircraft, vehicles, payloads, theatres, …)",
        description="Browse the bundled domain catalog. Use this to discover "
                    "valid aliases when writing a MissionSpec by hand.",
    )
    parser.add_argument(
        "what", type=str,
        choices=["aircraft", "vehicles", "ships", "statics", "payloads",
                 "theatres", "airports", "callsigns"],
        help="Catalog dimension to list",
    )
    parser.add_argument(
        "--role", type=str, default=None,
        help="Filter aircraft/vehicles by role (cap, strike, sead, sam, …)",
    )
    parser.add_argument(
        "--aircraft", type=str, default=None,
        help="Filter payloads by aircraft alias",
    )
    parser.add_argument(
        "--theatre", type=str, default=None,
        help="Filter airports by theatre",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    from ..catalog import aircraft, callsigns, payloads, ships, statics, theatres, vehicles

    if args.what == "aircraft":
        names = aircraft.list_by_role(args.role) if args.role else aircraft.all_aliases()
        _print(f"Aircraft ({args.role or 'all roles'})", names)

    elif args.what == "vehicles":
        names = vehicles.list_by_role(args.role) if args.role else vehicles.all_aliases()
        _print(f"Vehicles ({args.role or 'all roles'})", names)

    elif args.what == "ships":
        _print("Ships", ships.all_aliases())

    elif args.what == "statics":
        _print("Statics", statics.all_aliases())

    elif args.what == "payloads":
        if args.aircraft:
            presets = payloads.list_for_aircraft(args.aircraft)
            _print(f"Payload presets for {args.aircraft}", presets)
        else:
            for alias in payloads.list_aircraft_with_presets():
                presets = payloads.list_for_aircraft(alias)
                print(f"\n{alias}:")
                for p in presets:
                    print(f"  • {p}")

    elif args.what == "theatres":
        _print("Theatres", theatres.all_aliases())

    elif args.what == "airports":
        target_theatres = [args.theatre] if args.theatre else theatres.all_aliases()
        for t in target_theatres:
            info = theatres.get_info(t)
            if not info:
                continue
            print(f"\n{t}:")
            for a in info.notable_airports:
                print(f"  • {a}")

    elif args.what == "callsigns":
        print("\nAWACS:")
        for name, idx in callsigns.AWACS_CALLSIGNS.items():
            print(f"  {idx:3d}  {name}")
        print("\nTanker:")
        for name, idx in callsigns.TANKER_CALLSIGNS.items():
            print(f"  {idx:3d}  {name}")
        print("\nJTAC:")
        for name, idx in callsigns.JTAC_CALLSIGNS.items():
            print(f"  {idx:3d}  {name}")


def _print(header, items):
    items = list(items)
    print(f"\n{header} ({len(items)}):")
    if not items:
        print("  (none)")
    for it in items:
        print(f"  - {it}")
