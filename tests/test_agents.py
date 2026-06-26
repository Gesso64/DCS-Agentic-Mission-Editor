"""Offline tests for the agent/LLM layer (Phases 8-10).

These tests do NOT call a real LLM. They exercise:
  - the editor tool surface (apply_tool dispatch + per-tool semantics)
  - prompt template rendering with catalog injection
  - agent-loop control flow with a stub LLM

Anything that needs a live model goes elsewhere.
"""
import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from dcs_agentic.agents.editor_agent import edit_mission
from dcs_agentic.agents.llm.messages import (
    build_campaign_prompt,
    build_editor_prompt,
    build_system_prompt,
    format_user_message,
)
from dcs_agentic.agents.mission_agent import design_mission
from dcs_agentic.agents.tools.mutations import TOOLS, apply_tool
from dcs_agentic.schemas import (
    Briefing,
    Coalition,
    FlightGroup,
    MissionSpec,
    PayloadSpec,
    Position,
    Skill,
    StartType,
    TaskType,
    VehicleGroup,
    Waypoint,
)


PROMPT_DIR = (
    Path(__file__).parent.parent / "src" / "dcs_agentic" / "agents" / "prompts"
)


def _base_spec() -> MissionSpec:
    return MissionSpec(
        name="Agent Test",
        theatre="Caucasus",
        coalitions=[Coalition(side="blue", country="USA")],
        flights=[
            FlightGroup(
                name="Alpha",
                aircraft_type="F/A-18C",
                country="USA",
                side="blue",
                group_size=2,
                task=TaskType.CAP,
                start_type=StartType.COLD,
                airport="Batumi",
                skill=Skill.EXCELLENT,
                waypoints=[
                    Waypoint(x=-255000, y=630000, altitude=5000, speed=480, name="WP1"),
                ],
            ),
        ],
    )


# ─── TOOLS surface ──────────────────────────────────────────────────────────


def test_tools_schemas_are_serializable():
    """Every tool's input_schema must be a JSON-serializable dict, not a callable.

    The Anthropic API rejects function references; the schemas must be
    materialized at module load.
    """
    assert len(TOOLS) == 19
    for tool in TOOLS:
        assert "name" in tool and "description" in tool and "input_schema" in tool
        assert isinstance(tool["input_schema"], dict), (
            f"{tool['name']} input_schema must be a dict, got {type(tool['input_schema'])}"
        )
        json.dumps(tool["input_schema"])


def test_apply_tool_unknown_name_returns_error():
    spec = _base_spec()
    new_spec, msg = apply_tool(spec, "no_such_tool", {})
    assert new_spec is spec
    assert "unknown tool" in msg


# ─── Mutations: flights ─────────────────────────────────────────────────────


def test_add_flight():
    spec = _base_spec()
    new_flight = FlightGroup(
        name="Bravo", aircraft_type="F-16C", country="USA",
        side="blue", group_size=2, task=TaskType.SEAD,
        start_type=StartType.COLD, airport="Batumi",
    )
    new_spec, msg = apply_tool(spec, "add_flight", new_flight.model_dump(mode="json"))
    assert msg.startswith("ok")
    assert len(new_spec.flights) == 2
    assert spec.flights == _base_spec().flights  # original untouched


def test_add_flight_duplicate_name_errors():
    spec = _base_spec()
    dupe = spec.flights[0].model_dump(mode="json")
    _, msg = apply_tool(spec, "add_flight", dupe)
    assert "already exists" in msg


def test_remove_flight_missing_errors():
    spec = _base_spec()
    _, msg = apply_tool(spec, "remove_flight", {"name": "Ghost"})
    assert "not found" in msg


def test_remove_flight_ok():
    spec = _base_spec()
    new_spec, msg = apply_tool(spec, "remove_flight", {"name": "Alpha"})
    assert msg.startswith("ok")
    assert new_spec.flights == []


def test_move_waypoint():
    spec = _base_spec()
    new_spec, msg = apply_tool(spec, "move_waypoint", {
        "flight_name": "Alpha",
        "waypoint_index": 0,
        "x": -100000.0,
        "y": 700000.0,
        "altitude": 7000,
    })
    assert msg.startswith("ok")
    wp = new_spec.flights[0].waypoints[0]
    assert wp.x == -100000.0
    assert wp.y == 700000.0
    assert wp.altitude == 7000


def test_move_waypoint_bad_index():
    spec = _base_spec()
    _, msg = apply_tool(spec, "move_waypoint", {
        "flight_name": "Alpha", "waypoint_index": 99, "x": 0.0, "y": 0.0,
    })
    assert "out of range" in msg


def test_add_waypoint_appends():
    spec = _base_spec()
    new_spec, msg = apply_tool(spec, "add_waypoint", {
        "flight_name": "Alpha", "x": -260000.0, "y": 625000.0,
        "altitude": 4500, "speed": 450, "name": "Egress",
    })
    assert msg.startswith("ok")
    assert len(new_spec.flights[0].waypoints) == 2
    assert new_spec.flights[0].waypoints[-1].name == "Egress"


def test_set_payload_preset_resolves():
    spec = _base_spec()
    new_spec, msg = apply_tool(spec, "set_payload", {
        "flight_name": "Alpha", "preset_name": "CAP A-A",
    })
    assert msg.startswith("ok")
    assert new_spec.flights[0].payload.preset_name == "CAP A-A"


def test_set_payload_unknown_preset_errors():
    spec = _base_spec()
    _, msg = apply_tool(spec, "set_payload", {
        "flight_name": "Alpha", "preset_name": "NOT A REAL PRESET",
    })
    assert "Error" in msg


def test_set_payload_needs_preset_or_pylons():
    spec = _base_spec()
    _, msg = apply_tool(spec, "set_payload", {"flight_name": "Alpha"})
    assert "preset_name or pylons" in msg


# ─── Mutations: ground, naval, mission-level ────────────────────────────────


def test_add_and_remove_vehicle_group():
    spec = _base_spec()
    vg = VehicleGroup(
        name="SAM-1", vehicle_type="SA-11-LN", country="Russia",
        side="red", position=Position(x=-272000, y=614000), group_size=1,
    )
    new_spec, msg = apply_tool(spec, "add_vehicle_group", vg.model_dump(mode="json"))
    assert msg.startswith("ok")
    assert len(new_spec.vehicles) == 1
    new_spec2, msg2 = apply_tool(new_spec, "remove_vehicle_group", {"name": "SAM-1"})
    assert msg2.startswith("ok")
    assert new_spec2.vehicles == []


def test_set_briefing_replaces():
    spec = _base_spec()
    briefing = Briefing(description="d", blue_task="b", red_task="r")
    new_spec, msg = apply_tool(spec, "set_briefing", briefing.model_dump(mode="json"))
    assert msg.startswith("ok")
    assert new_spec.briefing.description == "d"


def test_set_start_time():
    spec = _base_spec()
    new_spec, msg = apply_tool(spec, "set_start_time", {"start_time": 1700000000.0})
    assert msg.startswith("ok")
    assert new_spec.start_time == 1700000000.0


# ─── Read-only lookups ─────────────────────────────────────────────────────


def test_get_spec_returns_json():
    spec = _base_spec()
    _, payload = apply_tool(spec, "get_spec", {})
    parsed = json.loads(payload)
    assert parsed["name"] == "Agent Test"


def test_list_airports_uses_spec_theatre():
    spec = _base_spec()
    _, msg = apply_tool(spec, "list_airports", {})
    assert "Batumi" in msg


def test_list_aircraft_role_filter():
    spec = _base_spec()
    _, msg = apply_tool(spec, "list_aircraft", {"role": "cap"})
    assert "F/A-18C" in msg or "F-15C" in msg


def test_list_payload_presets_for_aircraft():
    spec = _base_spec()
    _, msg = apply_tool(spec, "list_payload_presets", {"aircraft_alias": "F/A-18C"})
    assert "CAP A-A" in msg


def test_validate_spec_runs_without_errors():
    spec = _base_spec()
    _, msg = apply_tool(spec, "validate_spec", {})
    assert isinstance(msg, str)


# ─── Prompt rendering ───────────────────────────────────────────────────────


def test_build_system_prompt_substitutes_catalog():
    """All {{ VARIABLES }} in the template must be replaced after rendering."""
    out = build_system_prompt(
        str(PROMPT_DIR / "mission_designer.md"),
        theatre="Caucasus",
    )
    assert "{{ SCHEMA_JSON }}" not in out
    assert "{{ THEATRE_AIRPORTS }}" not in out
    assert "{{ AIRCRAFT_BY_ROLE }}" not in out
    assert "{{ PAYLOAD_PRESETS }}" not in out
    assert "Batumi" in out
    assert "F/A-18C" in out


def test_build_editor_prompt_lists_tools():
    out = build_editor_prompt(str(PROMPT_DIR / "editor.md"))
    assert "{{ TOOL_LIST }}" not in out
    assert "add_flight" in out
    assert "set_payload" in out


def test_build_campaign_prompt_substitutes_schema():
    out = build_campaign_prompt(str(PROMPT_DIR / "campaign_architect.md"))
    assert "{{ SCHEMA_JSON }}" not in out


def test_format_user_message_with_spec_embeds_json():
    spec = _base_spec()
    out = format_user_message("add an AWACS", spec=spec)
    assert "add an AWACS" in out
    assert '"Agent Test"' in out


# ─── Agent loops with stubbed LLM ───────────────────────────────────────────


class _StubResponse:
    """Minimal stand-in for an Anthropic Message response."""

    class _Block:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class _Usage:
        input_tokens = 0
        output_tokens = 0

    def __init__(self, content_blocks, stop_reason="end_turn"):
        self.content = content_blocks
        self.stop_reason = stop_reason
        self.usage = self._Usage()


def _text_block(text: str):
    return _StubResponse._Block(type="text", text=text)


def _tool_use_block(id_: str, name: str, input_: Dict[str, Any]):
    return _StubResponse._Block(type="tool_use", id=id_, name=name, input=input_)


def test_design_mission_parses_json_response(monkeypatch):
    """design_mission must accept a valid JSON spec from the LLM."""
    spec_json = json.dumps(_base_spec().model_dump(mode="json"))
    stub = _StubResponse([_text_block(f"```json\n{spec_json}\n```")])
    with patch(
        "dcs_agentic.agents.llm.client.Anthropic"
    ) as MockAnthropic:
        instance = MockAnthropic.return_value
        instance.messages.create.return_value = stub
        result = design_mission("anything", theatre="Caucasus", max_retries=0)
    assert result.name == "Agent Test"


def test_design_mission_retries_on_invalid_json(monkeypatch):
    spec_json = json.dumps(_base_spec().model_dump(mode="json"))
    bad = _StubResponse([_text_block("not json")])
    good = _StubResponse([_text_block(spec_json)])
    with patch("dcs_agentic.agents.llm.client.Anthropic") as MockAnthropic:
        instance = MockAnthropic.return_value
        instance.messages.create.side_effect = [bad, good]
        result = design_mission("anything", max_retries=1)
    assert result.name == "Agent Test"


def test_editor_applies_tool_calls_then_ends(monkeypatch):
    """Editor must invoke apply_tool when the model emits tool_use blocks
    and stop when stop_reason switches to end_turn."""
    spec = _base_spec()
    new_wp = {"flight_name": "Alpha", "x": -260000.0, "y": 620000.0,
              "altitude": 5000, "speed": 450, "name": "Added"}
    first = _StubResponse(
        [_tool_use_block("tu1", "add_waypoint", new_wp)],
        stop_reason="tool_use",
    )
    final = _StubResponse([_text_block("done")], stop_reason="end_turn")
    with patch("dcs_agentic.agents.llm.client.Anthropic") as MockAnthropic:
        instance = MockAnthropic.return_value
        instance.messages.create.side_effect = [first, final]
        out = edit_mission(spec, "add a waypoint", max_turns=4)
    assert len(out.flights[0].waypoints) == 2
    assert out.flights[0].waypoints[-1].name == "Added"
