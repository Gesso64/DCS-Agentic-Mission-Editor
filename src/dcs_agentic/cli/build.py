"""CLI command: build — assemble a .miz from a JSON spec file.

Usage:
    dcs-agentic build spec.json [--output mission.miz] [--strict]
"""

import argparse
import json
import sys
from pathlib import Path

from ..pipeline import MissionAssembler
from ..schemas import MissionSpec


def register_subcommand(subparsers) -> None:
    """Register the 'build' subcommand."""
    parser = subparsers.add_parser(
        "build",
        help="Build a .miz from a JSON spec file",
        description="Read a MissionSpec JSON file, assemble it into a .miz, "
                    "and save the result.",
    )
    parser.add_argument(
        "spec_file", type=str,
        help="Path to JSON mission spec file",
    )
    parser.add_argument(
        "-o", "--output", type=str, default="output/mission.miz",
        help="Output .miz file path (default: output/mission.miz)",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit non-zero if any assembly error occurred",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    """Execute the build command."""
    spec_path = Path(args.spec_file)
    if not spec_path.exists():
        print(f"Error: spec file not found: {spec_path}", file=sys.stderr)
        sys.exit(1)
    with open(spec_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    spec = MissionSpec.model_validate(data)

    print(f"\nAssembling mission: {spec.name}")
    print(f"  Theatre: {spec.theatre}")
    print(f"  Flights: {len(spec.flights or [])}")
    print(f"  Vehicles: {len(spec.vehicles or [])}")
    print(f"  Ships: {len(spec.ships or [])}")
    print()

    assembler = MissionAssembler(spec, strict=args.strict)
    try:
        output_path = assembler.save(args.output)
    except Exception:
        print("\nAssembly report:")
        print(assembler.report.format())
        raise

    print("Assembly report:")
    print(assembler.report.format())
    print(f"\nDone! Mission saved to: {output_path}")
    if assembler.report.has_errors():
        print(f"  ({len(assembler.report.errors)} error(s), "
              f"{len(assembler.report.warnings)} warning(s) — see report above)")
        sys.exit(0 if not args.strict else 1)