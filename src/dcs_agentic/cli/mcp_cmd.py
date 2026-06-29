"""CLI: launch the MCP server (stdio transport)."""

import argparse


def register_subcommand(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "mcp",
        help="Start the MCP server (stdio transport) — connect any MCP host",
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:  # noqa: ARG001
    try:
        from ..mcp.server import main
    except ImportError:
        import sys
        print(
            "The MCP server requires the 'mcp' extra.\n"
            "Install it with:  pip install -e .[mcp]",
            file=sys.stderr,
        )
        sys.exit(1)
    main()
