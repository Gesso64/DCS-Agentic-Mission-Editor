"""CLI command: design — AI-driven mission creation from prompts.

Usage:
    dcs-agentic design --prompt "..." [--theatre Caucasus] [--output mission.miz]
"""

import argparse
import sys

from ..agents.mission_agent import design_mission
from ..pipeline import MissionAssembler


def register_subcommand(subparsers) -> None:
    """Register the 'design' subcommand."""
    parser = subparsers.add_parser(
        "design",
        help="Create a mission from a natural-language prompt",
        description="Use an LLM to design a mission from a text description. "
                    "The output is a fully assembled .miz file.",
    )
    parser.add_argument(
        "-p", "--prompt", type=str, required=True,
        help="Natural-language mission description",
    )
    parser.add_argument(
        "-t", "--theatre", type=str, default="Caucasus",
        help="Theatre/map (default: Caucasus)",
    )
    parser.add_argument(
        "-o", "--output", type=str, default="output/mission.miz",
        help="Output .miz file path (default: output/mission.miz)",
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help="Override the LLM model alias (e.g. 'claude-sonnet-4-6' for GLM)",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit non-zero if any assembly error occurs",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    """Execute the design command."""
    print(f"\n🧠 Designing mission from prompt...")
    print(f"  Prompt: {args.prompt}")
    print(f"  Theatre: {args.theatre}")
    print()

    spec = design_mission(
        prompt=args.prompt,
        theatre=args.theatre,
        model=args.model,
    )

    print(f"✅ Mission designed: {spec.name}")
    print(f"  Flights: {len(spec.flights or [])}")
    print(f"  Vehicles: {len(spec.vehicles or [])}")
    print(f"  Ships: {len(spec.ships or [])}")
    print()

    print(f"🔧 Assembling mission...")
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