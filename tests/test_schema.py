"""Schema drift test: verifies the committed JSON schema is up to date."""
import json
from pathlib import Path

from dcs_agentic.schemas import MissionSpec

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "src" / "dcs_agentic" / "schemas" / "mission.schema.json"


def test_schema_on_disk_matches_generated():
    """The committed mission.schema.json must match MissionSpec.model_json_schema().
    If this fails, run: python scripts/dump_schema.py"""
    generated = MissionSpec.model_json_schema()
    on_disk = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert generated == on_disk, (
        "schema drift detected. Run: python scripts/dump_schema.py"
    )


def test_demo_cap_full_fixture_loads():
    """Verify the full demo fixture loads cleanly with all new fields."""
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "demo_cap_full.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    spec = MissionSpec.model_validate(data)
    assert spec.bullseye is not None
    assert spec.bullseye.blue is not None
    assert spec.radios is not None
    assert len(spec.radios.awacs or []) == 1
    assert len(spec.zones or []) == 1
    assert len(spec.markers or []) == 1
    assert len(spec.mission_goals or []) == 1
    assert spec.flights[0].payload is not None
    assert spec.flights[0].payload.preset_name == "CAP A-A"
    assert spec.vehicles[0].roe is not None
    assert spec.vehicles[0].alarm_state is not None
    assert len(spec.farps or []) == 1
    assert len(spec.triggers or []) == 1
    print(f"  OK: demo_cap_full loaded ({spec.name})")


def test_minimal_carrier_fixture_loads():
    """Verify carrier ops fixture loads cleanly."""
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "minimal_carrier.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    spec = MissionSpec.model_validate(data)
    assert len(spec.carrier_ops or []) == 1
    assert spec.carrier_ops[0].tacan_channel == 74
    assert len(spec.ships or []) == 1
    print(f"  OK: minimal_carrier loaded ({spec.name})")


def test_trigger_validation():
    """Valid trigger creates OK; invalid ones raise."""
    from dcs_agentic.schemas.triggers import (
        ActionKind, Trigger, TriggerAction, TriggerCondition, TriggerKind,
    )

    # Valid
    cond = TriggerCondition(kind=TriggerKind.TIME_REACHED, time_seconds=30)
    act = TriggerAction(kind=ActionKind.SHOW_MESSAGE, message="hello")
    trig = Trigger(name="test", conditions=[cond], actions=[act])
    assert trig.once is True
    assert len(trig.conditions) == 1

    # Invalid: TIME_REACHED without time_seconds
    import pytest
    with pytest.raises(ValueError, match="time_seconds is required"):
        TriggerCondition(kind=TriggerKind.TIME_REACHED)

    # Invalid: SHOW_MESSAGE without message
    with pytest.raises(ValueError, match="message is required"):
        TriggerAction(kind=ActionKind.SHOW_MESSAGE)