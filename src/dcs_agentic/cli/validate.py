"""CLI command: validate — run the validation layer over a spec."""

import argparse
import json
import sys

from ..schemas import MissionSpec
from ..validation import validate


def register_subcommand(subparsers) -> None:
    parser = subparsers.add_parser(
        "validate",
        help="Run validation checks over a MissionSpec without assembling",
        description="Reads a JSON spec, runs all registered validators, "
                    "and prints any issues. Exits non-zero on errors.",
    )
    parser.add_argument(
        "spec_file", type=str,
        help="Path to JSON mission spec file",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit non-zero on warnings too (default: only errors fail)",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with open(args.spec_file, "r") as f:
        data = json.load(f)
    spec = MissionSpec.model_validate(data)

    print(f"Validating: {spec.name} ({spec.theatre})")
    report = validate(spec)
    print(report.format())

    if report.has_errors():
        print(f"\n{len(report.errors)} error(s).")
        sys.exit(1)
    if args.strict and report.warnings:
        print(f"\n{len(report.warnings)} warning(s) (strict mode).")
        sys.exit(1)
    print(f"\n✅ Validation passed ({len(report.warnings)} warning(s)).")
