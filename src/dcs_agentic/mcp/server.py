"""DCS Agentic Mission Editor — MCP server.

Exposes the mission tool surface over the Model Context Protocol (stdio
transport) so any MCP host (Claude Desktop, Claude Code, Cursor, …) can
drive mission creation without using the bundled agent.

Session model: one in-memory MissionSpec per stdio session. Call
``new_mission`` or ``open_mission`` first, then use the edit/lookup
tools, then ``build_mission`` to write the .miz.

Usage
-----
    dcs-agentic-mcp                     # console script
    python -m dcs_agentic mcp           # via CLI
"""

import asyncio
import json
from pathlib import Path
from typing import Any

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from ..schemas.mission import MissionSpec
from ..agents.tools.mutations import TOOLS, apply_tool
from ..pipeline.assembler import MissionAssembler
from ..importer.miz_reader import import_miz
from ..validation import validate

# ─── Session state ────────────────────────────────────────────────────────────
# One MissionSpec per stdio session. All tools read/write _state["spec"].
_state: dict[str, Any] = {"spec": None}


def _require_spec() -> MissionSpec:
    if _state["spec"] is None:
        raise ValueError(
            "No mission loaded. Call new_mission or open_mission first."
        )
    return _state["spec"]


# ─── Tool definitions ─────────────────────────────────────────────────────────

_LIFECYCLE_TOOLS: list[types.Tool] = [
    types.Tool(
        name="new_mission",
        description=(
            "Create a new empty mission and set it as the working spec for this "
            "session. Must be called before any edit tools. The mission starts with "
            "no flights, vehicles, or weather — add them with the edit tools."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Mission name"},
                "theatre": {
                    "type": "string",
                    "default": "Caucasus",
                    "description": (
                        "Map name: Caucasus, Syria, PersianGulf, Nevada, "
                        "Normandy, TheChannel, MarianaIslands, Falklands"
                    ),
                },
            },
            "required": ["name"],
        },
    ),
    types.Tool(
        name="open_mission",
        description=(
            "Load an existing .miz file or JSON spec file as the working mission. "
            "Accepts absolute or relative paths. Returns an import report with any "
            "warnings about fields that could not be imported."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to a .miz file or a JSON MissionSpec file",
                },
            },
            "required": ["path"],
        },
    ),
    types.Tool(
        name="build_mission",
        description=(
            "Assemble the current working spec into a .miz file and save it to disk. "
            "Returns a build report (warnings, errors). The file is ready to load in "
            "DCS World immediately after a successful build."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "output_path": {
                    "type": "string",
                    "description": "Destination path for the .miz file (e.g. output/my_mission.miz)",
                },
            },
            "required": ["output_path"],
        },
    ),
    types.Tool(
        name="validate_mission",
        description=(
            "Run the validation layer over the current working spec without building "
            "it. Checks coordinate sanity, weapons compatibility, route logic, and "
            "cross-spec references. Returns a list of issues."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="save_spec",
        description=(
            "Save the current working spec as a human-readable JSON file. Useful for "
            "inspection, version control, or passing to 'python -m dcs_agentic build'."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "output_path": {
                    "type": "string",
                    "description": "Destination path for the JSON spec file",
                },
            },
            "required": ["output_path"],
        },
    ),
]

# Convert the existing TOOLS list (Anthropic tool-use format) to mcp.types.Tool.
# The input_schema is already a valid JSON Schema — reuse it directly.
_MUTATION_TOOLS: list[types.Tool] = [
    types.Tool(
        name=t["name"],
        description=t["description"],
        inputSchema=t["input_schema"],
    )
    for t in TOOLS
]

_ALL_TOOLS = _LIFECYCLE_TOOLS + _MUTATION_TOOLS
_MUTATION_NAMES = {t["name"] for t in TOOLS}

# ─── MCP server ───────────────────────────────────────────────────────────────

app = Server("dcs-agentic")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return _ALL_TOOLS


@app.call_tool()
async def call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    args = arguments or {}
    try:
        result = _dispatch(name, args)
    except Exception as exc:
        result = f"Error: {type(exc).__name__}: {exc}"
    return [types.TextContent(type="text", text=result)]


# ─── Dispatcher ───────────────────────────────────────────────────────────────

def _dispatch(name: str, args: dict) -> str:  # noqa: C901
    # ── Lifecycle ──────────────────────────────────────────────────────────
    if name == "new_mission":
        mission_name = args["name"]
        theatre = args.get("theatre", "Caucasus")
        _state["spec"] = MissionSpec(name=mission_name, theatre=theatre)
        return f"New mission '{mission_name}' created for theatre {theatre}."

    if name == "open_mission":
        path = Path(args["path"])
        if not path.exists():
            return f"Error: file not found: {path}"
        if path.suffix.lower() == ".miz":
            spec, report = import_miz(str(path))
            _state["spec"] = spec
            summary = report.format() if report.issues else "No import issues."
            return f"Loaded {path.name}.\n{summary}"
        raw = path.read_text(encoding="utf-8")
        _state["spec"] = MissionSpec.model_validate_json(raw)
        return f"Loaded spec from {path.name}."

    _no_spec = "Error: No mission loaded. Call new_mission or open_mission first."

    if name == "build_mission":
        if _state["spec"] is None:
            return _no_spec
        out = args["output_path"]
        assembler = MissionAssembler(_state["spec"])
        assembler.save(out)
        summary = assembler.report.format() if assembler.report.issues else "No issues."
        return f"Saved to {out}.\n{summary}"

    if name == "validate_mission":
        if _state["spec"] is None:
            return _no_spec
        report = validate(_state["spec"])
        return report.format() if report.issues else "Validation passed with no issues."

    if name == "save_spec":
        if _state["spec"] is None:
            return _no_spec
        out = Path(args["output_path"])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(_state["spec"].model_dump_json(indent=2), encoding="utf-8")
        return f"Spec saved to {out}."

    # ── Mutations + lookups (existing tool surface) ────────────────────────
    if name in _MUTATION_NAMES:
        if _state["spec"] is None:
            return "Error: No mission loaded. Call new_mission or open_mission first."
        updated, message = apply_tool(_state["spec"], name, args)
        _state["spec"] = updated
        return message

    return f"Error: unknown tool '{name}'"


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    """Start the MCP server on stdio."""
    async def _run() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options(),
            )

    asyncio.run(_run())


if __name__ == "__main__":
    main()
