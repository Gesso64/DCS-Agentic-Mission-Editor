"""CLI: register dcs-agentic as an MCP server with your AI coding host.

Supported hosts
---------------
    claude-desktop          Claude Desktop app (default)
    claude-code             Claude Code — global (~/.claude.json)
    claude-code-project     Claude Code — this project (.mcp.json)
    cursor                  Cursor — global (~/.cursor/mcp.json)
    cursor-project          Cursor — this project (.cursor/mcp.json)
    windsurf                Windsurf by Codeium
    zed                     Zed editor

Usage
-----
    python -m dcs_agentic setup                       # Claude Desktop
    python -m dcs_agentic setup --host cursor
    python -m dcs_agentic setup --host zed
    python -m dcs_agentic setup --host claude-code
    python -m dcs_agentic setup --dry-run             # preview without writing

The command uses sys.executable (the current Python) so it works regardless
of whether dcs-agentic-mcp is on PATH.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Callable


# ─── Per-host metadata ────────────────────────────────────────────────────────
# config_key: the top-level JSON key that holds the server map.
#   Most hosts: "mcpServers"
#   Zed:        "context_servers"

def _claude_desktop_path() -> Path:
    if sys.platform == "win32":
        return Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def _windsurf_path() -> Path:
    if sys.platform == "win32":
        return Path.home() / ".codeium" / "windsurf" / "mcp_config.json"
    return Path.home() / ".codeium" / "windsurf" / "mcp_config.json"


_HOST_META: dict[str, dict] = {
    "claude-desktop": {
        "path": _claude_desktop_path,
        "config_key": "mcpServers",
        "next": "Fully quit and relaunch Claude Desktop (Ctrl+Q / Cmd+Q).",
    },
    "claude-code": {
        # Global Claude Code config — NOT ~/.claude/settings.json (that's for
        # other Claude Code settings, not MCP). The MCP config lives in ~/.claude.json.
        "path": lambda: Path.home() / ".claude.json",
        "config_key": "mcpServers",
        "next": "Run: claude mcp list   to verify.",
    },
    "claude-code-project": {
        # Project-scoped Claude Code MCP config (checked into repo).
        "path": lambda: Path(".mcp.json"),
        "config_key": "mcpServers",
        "next": "Run: claude mcp list   inside this project to verify.",
    },
    "cursor": {
        "path": lambda: Path.home() / ".cursor" / "mcp.json",
        "config_key": "mcpServers",
        "next": "Cursor picks up changes automatically. Check Settings → MCP.",
    },
    "cursor-project": {
        "path": lambda: Path(".cursor") / "mcp.json",
        "config_key": "mcpServers",
        "next": "Cursor picks up changes automatically.",
    },
    "windsurf": {
        "path": _windsurf_path,
        "config_key": "mcpServers",
        "next": "Windsurf picks up MCP changes automatically (Settings → Cascade → MCP).",
    },
    "zed": {
        # Zed uses "context_servers" (not "mcpServers") — unique among major hosts.
        "path": lambda: Path.home() / ".config" / "zed" / "settings.json",
        "config_key": "context_servers",
        "next": "Zed auto-restarts the server on settings.json save — no restart needed.",
    },
}


# ─── MCP server entry ─────────────────────────────────────────────────────────

def _mcp_entry() -> dict:
    """Build the server entry using the current Python interpreter.

    sys.executable avoids PATH issues during local/editable installs.
    If you publish to PyPI and install globally, `dcs-agentic-mcp` will be
    on PATH and you can simplify to {"command": "dcs-agentic-mcp", "args": []}.
    """
    return {
        "command": sys.executable,
        "args": ["-m", "dcs_agentic", "mcp"],
    }


# ─── Read / write helpers ─────────────────────────────────────────────────────

def _read_config(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"WARNING: {path} contains invalid JSON ({exc}).")
            print("         A backup will be made before writing.")
    return {}


def _backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    backup = path.with_suffix(".json.bak")
    shutil.copy2(path, backup)
    return backup


def _write_config(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ─── Merge logic ──────────────────────────────────────────────────────────────

def _merge(config: dict, entry: dict, config_key: str) -> tuple[dict, bool]:
    """Insert the dcs-agentic entry under config_key. Returns (updated, changed)."""
    servers = config.setdefault(config_key, {})
    if servers.get("dcs-agentic") == entry:
        return config, False
    servers["dcs-agentic"] = entry
    return config, True


# ─── Core ─────────────────────────────────────────────────────────────────────

def _run_setup(host: str, dry_run: bool) -> int:
    meta = _HOST_META[host]
    config_path: Path = meta["path"]()
    config_key: str = meta["config_key"]
    entry = _mcp_entry()

    print(f"Host       : {host}")
    print(f"Config     : {config_path}")
    print(f"Config key : {config_key}")
    print(f"Command    : {entry['command']}")
    print(f"Args       : {entry['args']}")
    print()

    config = _read_config(config_path)
    updated, changed = _merge(config, entry, config_key)

    if not changed:
        print("Already registered — no changes needed.")
        return 0

    if dry_run:
        print("Dry run — would write:")
        print(json.dumps({config_key: {"dcs-agentic": entry}}, indent=2))
        return 0

    backup = _backup(config_path)
    if backup:
        print(f"Backed up existing config → {backup}")

    _write_config(config_path, updated)
    print(f"Written → {config_path}")
    print()
    print("Next step:", meta["next"])
    return 0


# ─── CLI wiring ───────────────────────────────────────────────────────────────

def register_subcommand(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "setup",
        help="Register dcs-agentic as an MCP server with your AI coding host",
    )
    p.add_argument(
        "--host",
        choices=list(_HOST_META),
        default="claude-desktop",
        metavar="HOST",
        help=(
            "Host to configure (default: claude-desktop). "
            "Choices: " + ", ".join(_HOST_META)
        ),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be written without modifying any files",
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    sys.exit(_run_setup(args.host, args.dry_run))
