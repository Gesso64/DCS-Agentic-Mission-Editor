"""Tests for the MCP server dispatch layer.

Tests call _dispatch() directly — no MCP transport needed.
Each test resets the server's in-memory state before running.
"""

import json
import pytest
from pathlib import Path

from dcs_agentic.mcp import server as mcp_server


def _reset():
    """Clear the MCP server's in-memory spec between tests."""
    mcp_server._state["spec"] = None


# ─── Lifecycle tools ──────────────────────────────────────────────────────────

def test_new_mission_creates_spec():
    _reset()
    result = mcp_server._dispatch("new_mission", {"name": "Test Op", "theatre": "Caucasus"})
    assert "Test Op" in result
    assert mcp_server._state["spec"] is not None
    assert mcp_server._state["spec"].name == "Test Op"
    assert mcp_server._state["spec"].theatre == "Caucasus"


def test_new_mission_default_theatre():
    _reset()
    mcp_server._dispatch("new_mission", {"name": "Op Delta"})
    assert mcp_server._state["spec"].theatre == "Caucasus"


def test_open_mission_json(tmp_path):
    _reset()
    from dcs_agentic.schemas import MissionSpec
    spec = MissionSpec(name="Loaded Mission", theatre="Syria")
    json_path = tmp_path / "spec.json"
    json_path.write_text(spec.model_dump_json(), encoding="utf-8")

    result = mcp_server._dispatch("open_mission", {"path": str(json_path)})
    assert "spec.json" in result
    assert mcp_server._state["spec"].name == "Loaded Mission"
    assert mcp_server._state["spec"].theatre == "Syria"


def test_open_mission_missing_file():
    _reset()
    result = mcp_server._dispatch("open_mission", {"path": "/nonexistent/file.miz"})
    assert "Error" in result or "not found" in result.lower()


def test_require_spec_before_tool():
    _reset()
    result = mcp_server._dispatch("build_mission", {"output_path": "out/x.miz"})
    assert "Error" in result


def test_build_mission(tmp_path):
    _reset()
    from dcs_agentic.schemas import MissionSpec, FlightGroup, Waypoint, TaskType, StartType, Skill
    mcp_server._state["spec"] = MissionSpec(
        name="Build Test",
        theatre="Caucasus",
        flights=[
            FlightGroup(
                name="Alpha",
                aircraft_type="F/A-18C",
                country="USA",
                side="blue",
                group_size=1,
                task=TaskType.CAP,
                start_type=StartType.COLD,
                airport="Batumi",
                skill=Skill.AVERAGE,
                waypoints=[Waypoint(x=-255000, y=630000, altitude=5000, speed=480)],
            )
        ],
    )
    out = str(tmp_path / "build_test.miz")
    result = mcp_server._dispatch("build_mission", {"output_path": out})
    assert Path(out).exists(), f"Expected .miz at {out}; server said: {result}"
    assert "build_test.miz" in result


def test_validate_mission_no_issues():
    _reset()
    from dcs_agentic.schemas import MissionSpec
    mcp_server._state["spec"] = MissionSpec(name="Empty", theatre="Caucasus")
    result = mcp_server._dispatch("validate_mission", {})
    assert "no issues" in result.lower() or "passed" in result.lower()


def test_save_spec(tmp_path):
    _reset()
    mcp_server._dispatch("new_mission", {"name": "Save Test"})
    out = str(tmp_path / "saved.json")
    result = mcp_server._dispatch("save_spec", {"output_path": out})
    assert Path(out).exists()
    data = json.loads(Path(out).read_text(encoding="utf-8"))
    assert data["name"] == "Save Test"


# ─── Mutation tools ───────────────────────────────────────────────────────────

def test_add_flight_mutates_spec():
    _reset()
    mcp_server._dispatch("new_mission", {"name": "Mutation Test"})
    result = mcp_server._dispatch("add_flight", {
        "name": "Alpha",
        "aircraft_type": "F/A-18C",
        "country": "USA",
        "side": "blue",
        "group_size": 2,
        "task": "CAP",
        "start_type": "cold",
        "airport": "Batumi",
        "skill": "Average",
        "waypoints": [{"x": -255000, "y": 630000, "altitude": 5000, "speed": 480}],
    })
    spec = mcp_server._state["spec"]
    assert spec.flights is not None
    assert len(spec.flights) == 1
    assert spec.flights[0].name == "Alpha"


def test_add_and_remove_flight():
    _reset()
    mcp_server._dispatch("new_mission", {"name": "Add Remove Test"})
    mcp_server._dispatch("add_flight", {
        "name": "Bravo",
        "aircraft_type": "F-16C_50",
        "country": "USA",
        "side": "blue",
        "group_size": 2,
        "task": "CAP",
        "start_type": "cold",
        "airport": "Batumi",
        "skill": "Average",
        "waypoints": [{"x": -255000, "y": 630000, "altitude": 5000, "speed": 480}],
    })
    assert len(mcp_server._state["spec"].flights) == 1

    result = mcp_server._dispatch("remove_flight", {"name": "Bravo"})
    assert mcp_server._state["spec"].flights == [] or mcp_server._state["spec"].flights is None


def test_get_spec_returns_json():
    _reset()
    mcp_server._dispatch("new_mission", {"name": "JSON Test", "theatre": "Syria"})
    result = mcp_server._dispatch("get_spec", {})
    data = json.loads(result)
    assert data["name"] == "JSON Test"
    assert data["theatre"] == "Syria"


def test_list_aircraft_returns_list():
    _reset()
    mcp_server._dispatch("new_mission", {"name": "Catalog Test"})
    result = mcp_server._dispatch("list_aircraft", {})
    assert len(result) > 0


def test_list_airports_requires_theatre():
    _reset()
    mcp_server._dispatch("new_mission", {"name": "Airport Test", "theatre": "Caucasus"})
    result = mcp_server._dispatch("list_airports", {})
    assert len(result) > 0


def test_unknown_tool_returns_error():
    _reset()
    mcp_server._dispatch("new_mission", {"name": "Unknown Tool Test"})
    result = mcp_server._dispatch("nonexistent_tool", {})
    assert "Error" in result or "unknown" in result.lower()


# ─── Tool surface completeness ────────────────────────────────────────────────

def test_all_tools_are_registered():
    """Every tool in TOOLS must appear in _ALL_TOOLS."""
    from dcs_agentic.agents.tools.mutations import TOOLS
    registered_names = {t.name for t in mcp_server._ALL_TOOLS}
    for tool in TOOLS:
        assert tool["name"] in registered_names, f"Missing tool: {tool['name']}"


def test_lifecycle_tools_are_registered():
    registered_names = {t.name for t in mcp_server._ALL_TOOLS}
    for name in ("new_mission", "open_mission", "build_mission", "validate_mission", "save_spec"):
        assert name in registered_names, f"Missing lifecycle tool: {name}"
