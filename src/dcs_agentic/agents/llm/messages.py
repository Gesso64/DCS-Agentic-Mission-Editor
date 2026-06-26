"""Message formatting utilities for the LLM client.

Handles construction of system prompts with injected schema and catalog data,
plus message history formatting for multi-turn conversations.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...catalog import aircraft, payloads, theatres, vehicles, ships, callsigns
from ...schemas import MissionSpec


_AGENTS_ROOT = Path(__file__).resolve().parent.parent  # …/dcs_agentic/agents


def _resolve_template_path(template_path: str) -> Path:
    """Resolve a template path: absolute paths pass through; relative paths
    starting with 'agents/' are resolved against the package root so callers
    don't have to know cwd."""
    p = Path(template_path)
    if p.is_absolute() and p.exists():
        return p
    if template_path.startswith("agents/"):
        rel = template_path[len("agents/"):]
        return _AGENTS_ROOT / rel
    return p


def build_system_prompt(
    template_path: str,
    theatre: str = "Caucasus",
    spec: Optional[MissionSpec] = None,
) -> str:
    """Load a system prompt template and inject runtime values.

    Args:
        template_path: Path to the .md template file
        theatre: Theatre name for catalog summaries
        spec: Optional existing MissionSpec for patch-mode editing

    Returns:
        Rendered system prompt string with {{ VARIABLES }} replaced.
    """
    with open(_resolve_template_path(template_path), "r", encoding="utf-8") as f:
        template = f.read()

    # Inject schema
    schema_json = MissionSpec.model_json_schema()
    template = template.replace("{{ SCHEMA_JSON }}", json.dumps(schema_json, indent=2))

    # Inject theatre-specific catalog info
    theatre_info = theatres.get_info(theatre)
    if theatre_info:
        airports_str = "\n".join(
            f"  - {a}" for a in theatre_info.notable_airports
        )
        bullseye_str = (
            f"  ({theatre_info.default_bullseye.x}, "
            f"{theatre_info.default_bullseye.y}) "
            f"— shared default; set per-side via MissionSpec.bullseye if needed"
        )
    else:
        airports_str = "  (unknown theatre)"
        bullseye_str = "  (unknown theatre)"

    template = template.replace("{{ THEATRE_AIRPORTS }}", airports_str)
    template = template.replace("{{ THEATRE_BULLSEYE }}", bullseye_str)

    # Inject aircraft by role summaries
    aircraft_by_role = {}
    for role in ("cap", "strike", "sead", "cas", "recon", "awacs", "tanker", "transport", "helicopter"):
        names = aircraft.list_by_role(role)
        if names:
            aircraft_by_role[role] = ", ".join(names[:20])  # limit to 20 per role

    aircraft_str = "\n".join(
        f"  **{role.upper()}**: {names}" for role, names in aircraft_by_role.items()
    )
    template = template.replace("{{ AIRCRAFT_BY_ROLE }}", aircraft_str)

    # Inject vehicle by role summaries
    vehicle_by_role = {}
    for role in ("sam", "aaa", "ewr", "artillery", "armor", "infantry"):
        names = vehicles.list_by_role(role)
        if names:
            vehicle_by_role[role] = ", ".join(names[:20])

    vehicle_str = "\n".join(
        f"  **{role.upper()}**: {names}" for role, names in vehicle_by_role.items()
    )
    template = template.replace("{{ VEHICLE_BY_ROLE }}", vehicle_str)

    # Inject ship list
    ship_list = ships.all_aliases()
    template = template.replace("{{ SHIP_LIST }}", ", ".join(ship_list[:30]))

    # Inject payload presets for top aircraft
    top_aircraft = ["F/A-18C", "F-16C", "F-15C", "F-15E", "A-10C", "AH-64D", "F-14B", "Su-27", "MiG-29S", "Ka-50"]
    preset_lines = []
    for ac in top_aircraft:
        presets = payloads.list_for_aircraft(ac)
        if presets:
            preset_lines.append(f"  **{ac}**: {', '.join(presets)}")
    template = template.replace("{{ PAYLOAD_PRESETS }}", "\n".join(preset_lines))

    # Inject theatre bounds for coordinate sanity checking
    theatre_info = theatres.get_info(theatre)
    if theatre_info:
        b = theatre_info.bounds
        bounds_str = (
            f"x ∈ [{b.left}, {b.right}], "
            f"y ∈ [{b.bottom}, {b.top}]"
        )
    else:
        bounds_str = "x ∈ [-500000, 500000], y ∈ [-500000, 500000]"
    template = template.replace("{{ THEATRE_BOUNDS }}", bounds_str)

    return template


def build_editor_prompt(
    template_path: str,
    theatre: str = "Caucasus",
) -> str:
    """Build the editor agent's system prompt.

    Simpler than the designer prompt — the editor works via tool calls,
    so the system prompt is mostly rules and tool descriptions.
    """
    with open(_resolve_template_path(template_path), "r", encoding="utf-8") as f:
        template = f.read()

    # Inject tool list summary
    from ..tools.mutations import TOOLS
    tool_lines = [f"  - `{t['name']}`: {t['description']}" for t in TOOLS]
    template = template.replace("{{ TOOL_LIST }}", "\n".join(tool_lines))

    return template


def build_campaign_prompt(
    template_path: str,
    theatre: str = "Caucasus",
) -> str:
    """Build the campaign architect's system prompt.

    Similar to the designer prompt but outputs CampaignSpec with templates.
    """
    with open(_resolve_template_path(template_path), "r", encoding="utf-8") as f:
        template = f.read()

    schema_json = MissionSpec.model_json_schema()
    template = template.replace("{{ SCHEMA_JSON }}", json.dumps(schema_json, indent=2))

    theatre_info = theatres.get_info(theatre)
    if theatre_info:
        airports_str = "\n".join(f"  - {a}" for a in theatre_info.notable_airports)
    else:
        airports_str = "  (unknown theatre)"
    template = template.replace("{{ THEATRE_AIRPORTS }}", airports_str)

    return template


def format_user_message(prompt: str, spec: Optional[MissionSpec] = None) -> str:
    """Format the user's message, optionally including an existing spec for patching.

    Args:
        prompt: The user's natural-language instruction
        spec: Optional existing MissionSpec to patch

    Returns:
        Formatted user message string
    """
    if spec is None:
        return prompt
    return (
        f"Here is the current mission specification:\n\n"
        f"```json\n{spec.model_dump_json(indent=2)}\n```\n\n"
        f"Now modify it per this instruction: {prompt}"
    )
