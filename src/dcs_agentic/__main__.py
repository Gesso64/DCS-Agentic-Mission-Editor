"""
DCS Agentic Mission Editor - CLI Entry Point

Run: python -m dcs_agentic [command] [options]

Commands:
  build     Build a .miz from a JSON spec file
  design    Create a mission from a natural-language prompt
  edit      Edit an existing mission using natural language
  inspect   Show what's in a .miz file
  validate  Validate a mission spec without building
  campaign  Manage multi-mission campaigns

Use "python -m dcs_agentic <command> --help" for command-specific help.
"""

import argparse
import sys


def _version() -> str:
    try:
        from importlib.metadata import version
        return version("dcs-agentic")
    except Exception:
        return "0.0.0+unknown"


def main():
    parser = argparse.ArgumentParser(
        description="DCS Agentic Mission Editor - Generate .miz files from mission specs"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Import and register subcommands
    from .cli import design as design_module
    from .cli import edit as edit_module
    from .cli import campaign as campaign_module

    design_module.register_subcommand(subparsers)
    edit_module.register_subcommand(subparsers)
    campaign_module.register_subcommand(subparsers)

    # Built-in commands
    from .cli import build as build_module
    from .cli import inspect as inspect_module
    from .cli import list_catalog as list_catalog_module
    from .cli import validate as validate_module
    from .cli import import_miz as import_miz_module
    from .cli import mcp_cmd as mcp_cmd_module
    from .cli import setup_cmd as setup_cmd_module
    build_module.register_subcommand(subparsers)
    validate_module.register_subcommand(subparsers)
    inspect_module.register_subcommand(subparsers)
    list_catalog_module.register_subcommand(subparsers)
    import_miz_module.register_subcommand(subparsers)
    mcp_cmd_module.register_subcommand(subparsers)
    setup_cmd_module.register_subcommand(subparsers)

    parser.add_argument(
        "--version", action="version",
        version=f"dcs-agentic {_version()}",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()