"""Phase 11 after-action parser tests."""
import json
from pathlib import Path

import pytest

from dcs_agentic.campaign.after_action import (
    LUA_HOOK_SCRIPT,
    AfterAction,
    load_outcome,
    parse_lua_callback,
    parse_tacview,
)


def test_lua_callback_basic(tmp_path):
    data = {
        "mission_name": "Op Lion D-Day",
        "winner": "blue",
        "blue_score": 1000,
        "red_score": 200,
        "blue_losses": ["Hornet 1-1"],
        "red_losses": ["Bandit 2-1", "Bandit 2-2"],
        "captured": {"Sochi-Adler": "blue"},
        "flags_set": {"sam_destroyed": True},
        "duration": 1800.5,
    }
    out = parse_lua_callback(data)
    assert isinstance(out, AfterAction)
    assert out.mission_name == "Op Lion D-Day"
    assert out.winner == "blue"
    assert out.blue_losses == ["Hornet 1-1"]
    assert len(out.red_losses) == 2
    assert out.captured == {"Sochi-Adler": "blue"}
    assert out.flags_set == {"sam_destroyed": True}
    assert out.duration_seconds == 1800.5


def test_lua_callback_mission_name_override():
    out = parse_lua_callback({}, mission_name="Default")
    assert out.mission_name == "Default"


def test_lua_callback_empty_dict_safe():
    out = parse_lua_callback({}, mission_name="X")
    assert out.blue_losses == []
    assert out.captured == {}
    assert out.blue_score == 0


def test_lua_hook_script_contains_event_handler():
    """Sanity check the Lua hook string carries the event names we depend on."""
    assert "S_EVENT_DEAD" in LUA_HOOK_SCRIPT
    assert "S_EVENT_MISSION_END" in LUA_HOOK_SCRIPT
    assert "S_EVENT_BASE_CAPTURED" in LUA_HOOK_SCRIPT
    assert "world.addEventHandler" in LUA_HOOK_SCRIPT


def _write_tacview(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "test.acmi"
    p.write_text(body, encoding="utf-8")
    return p


def test_tacview_destroyed_events_route_by_coalition(tmp_path):
    body = (
        "FileType=text/acmi/tacview\n"
        "FileVersion=2.2\n"
        "0,ReferenceTime=2024-01-01T00:00:00Z\n"
        "0,Title=Op Lion D-Day\n"
        "#0\n"
        "a1,T=37.5|45.0|2000,Type=Plane,Name=Hornet 1-1,Coalition=Allies\n"
        "b1,T=37.6|45.1|2000,Type=Plane,Name=Bandit 2-1,Coalition=Enemies\n"
        "#60.5\n"
        "0,Event=Destroyed|b1|a1\n"
        "#120.0\n"
        "0,Event=Destroyed|a1|b1\n"
    )
    p = _write_tacview(tmp_path, body)
    out = parse_tacview(str(p))
    assert "Bandit 2-1" in out.red_losses
    assert "Hornet 1-1" in out.blue_losses
    assert out.mission_name == "Op Lion D-Day"
    assert out.duration_seconds == 120.0


def test_tacview_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_tacview(str(tmp_path / "nope.acmi"))


def test_tacview_empty_file_returns_empty(tmp_path):
    p = _write_tacview(tmp_path, "")
    out = parse_tacview(str(p), mission_name="X")
    assert out.blue_losses == []
    assert out.red_losses == []


def test_load_outcome_dispatches_by_extension(tmp_path):
    j = tmp_path / "x.json"
    j.write_text(json.dumps({"mission_name": "J", "winner": "blue"}), encoding="utf-8")
    out = load_outcome(str(j))
    assert out.winner == "blue"

    a = _write_tacview(
        tmp_path,
        "FileType=text/acmi/tacview\n0,Title=A\n#1\n",
    )
    out2 = load_outcome(str(a))
    assert out2.mission_name == "A"


def test_load_outcome_unknown_ext_raises(tmp_path):
    p = tmp_path / "x.xyz"
    p.write_text("nope")
    with pytest.raises(ValueError):
        load_outcome(str(p))
