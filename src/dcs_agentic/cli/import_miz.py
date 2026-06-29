"""CLI: import a .miz file and emit a JSON MissionSpec."""

import argparse
import json
import sys
from pathlib import Path


def register_subcommand(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "import",
        help="Import a .miz file and write it as a JSON MissionSpec",
    )
    p.add_argument("input", help="Path to the .miz file")
    p.add_argument(
        "-o", "--output",
        help="Output JSON path (default: <input>.json)",
        default=None,
    )
    p.add_argument(
        "--json",
        dest="emit_json",
        action="store_true",
        help="Print JSON to stdout instead of writing a file",
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    from ..importer.miz_reader import import_miz
    from ..errors import Severity

    spec, report = import_miz(args.input)

    for issue in report.issues:
        stream = sys.stderr
        prefix = "WARNING" if issue.severity == Severity.WARNING else "ERROR"
        print(f"{prefix}: [{issue.code}] {issue.message}", file=stream)

    if report.has_errors():
        sys.exit(1)

    payload = spec.model_dump_json(indent=2)

    if args.emit_json:
        print(payload)
        return

    out = Path(args.output) if args.output else Path(args.input).with_suffix(".json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(payload, encoding="utf-8")
    print(f"Spec written to {out}")
