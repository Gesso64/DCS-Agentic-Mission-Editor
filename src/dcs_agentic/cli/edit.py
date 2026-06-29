"""CLI command: edit — AI-driven mission editing via tool calls.

Usage:
    dcs-agentic edit input.miz --instruction "add an AWACS" [--output output.miz]
"""

import argparse
import json
import sys
from pathlib import Path

from ..pipeline import MissionAssembler
from ..schemas import MissionSpec


def register_subcommand(subparsers) -> None:
    """Register the 'edit' subcommand."""
    parser = subparsers.add_parser(
        "edit",
        help="Edit an existing mission using natural language",
        description="Load a .miz or spec.json, apply edits via AI tool calls, "
                    "and save the result as a new .miz file.",
    )
    parser.add_argument(
        "input", type=str,
        help="Input .miz file or spec.json to edit",
    )
    parser.add_argument(
        "-i", "--instruction", type=str, required=True,
        help="Natural-language edit instruction",
    )
    parser.add_argument(
        "-o", "--output", type=str, default="output/edited_mission.miz",
        help="Output .miz file path (default: output/edited_mission.miz)",
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help="Override the LLM model alias",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit non-zero if any assembly error occurs",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    """Execute the edit command."""
    input_path = Path(args.input)

    # Load the spec
    if input_path.suffix.lower() == ".miz":
        # Import from .miz file
        from ..importer.miz_reader import import_miz
        spec, import_report = import_miz(str(input_path))
        if any(i.code == "IMPORTER_NOT_IMPLEMENTED" for i in import_report.issues):
            print(
                f"❌ .miz import is not yet implemented (Phase 6). "
                f"Editing '{input_path}' would silently throw away its contents.\n"
                f"Workaround: convert the .miz to a JSON spec first, then pass that.",
                file=sys.stderr,
            )
            sys.exit(2)
        print(f"📂 Loaded mission from .miz: {spec.name}")
        print(import_report.format())
    else:
        # Load from JSON spec
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        spec = MissionSpec.model_validate(data)
        print(f"📂 Loaded mission spec: {spec.name}")

    print(f"  Flights: {len(spec.flights or [])}")
    print(f"  Vehicles: {len(spec.vehicles or [])}")
    print(f"  Ships: {len(spec.ships or [])}")
    print()

    print(f"🧠 Editing mission...")
    print(f"  Instruction: {args.instruction}")
    print()

    from ..agents.editor_agent import edit_mission
    edited_spec = edit_mission(
        spec=spec,
        instruction=args.instruction,
        theatre=spec.theatre or "Caucasus",
        model=args.model,
    )

    print(f"✅ Edit complete: {edited_spec.name}")
    print()

    print(f"🔧 Assembling mission...")
    assembler = MissionAssembler(edited_spec, strict=args.strict)
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