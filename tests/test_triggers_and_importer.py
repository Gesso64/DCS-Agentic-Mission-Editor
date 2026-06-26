"""Phase 5 trigger builder + Phase 6 importer tests."""
import os
from pathlib import Path

import pytest

from dcs_agentic.importer.miz_reader import import_miz
from dcs_agentic.pipeline import MissionAssembler
from dcs_agentic.schemas import (
    Briefing,
    Coalition,
    FlightGroup,
    MissionSpec,
    Position,
    StartType,
    TaskType,
    VehicleGroup,
    Waypoint,
)
from dcs_agentic.schemas.triggers import (
    ActionKind,
    Trigger,
    TriggerAction,
    TriggerCondition,
    TriggerKind,
)


def _spec_with_triggers() -> MissionSpec:
    return MissionSpec(
        name="Trigger Test",
        theatre="Caucasus",
        coalitions=[
            Coalition(side="blue", country="USA"),
            Coalition(side="red", country="Russia"),
        ],
        flights=[
            FlightGroup(
                name="Alpha", aircraft_type="F/A-18C", country="USA", side="blue",
                group_size=1, task=TaskType.CAP, start_type=StartType.COLD, airport="Batumi",
            ),
        ],
        triggers=[
            Trigger(
                name="hello-at-60",
                conditions=[TriggerCondition(kind=TriggerKind.TIME_REACHED, time_seconds=60)],
                actions=[TriggerAction(kind=ActionKind.SHOW_MESSAGE, message="Hello", duration_seconds=10)],
            ),
            Trigger(
                name="end-when-alpha-dies",
                conditions=[TriggerCondition(kind=TriggerKind.GROUP_DEAD, group_name="Alpha")],
                actions=[TriggerAction(kind=ActionKind.END_MISSION, winner="red")],
            ),
            Trigger(
                name="flag-flip",
                conditions=[TriggerCondition(kind=TriggerKind.FLAG_TRUE, flag_name="ready")],
                actions=[TriggerAction(kind=ActionKind.SET_FLAG, flag_name="done", flag_value=1)],
            ),
        ],
    )


# ─── Phase 5: triggers ──────────────────────────────────────────────────────


def test_triggers_attached_to_mission():
    asm = MissionAssembler(_spec_with_triggers())
    asm.assemble()
    assert len(asm.mission.triggerrules.triggers) == 3
    codes = [i.code for i in asm.report.issues]
    assert codes.count("TRIGGER_CREATED") == 3
    assert "TRIGGER_BUILD_FAILED" not in codes


def test_trigger_unknown_group_warns_not_raises():
    """A trigger referencing a missing group should warn and skip, not crash."""
    spec = _spec_with_triggers()
    spec.triggers.append(Trigger(
        name="bad-ref",
        conditions=[TriggerCondition(kind=TriggerKind.GROUP_DEAD, group_name="Ghost")],
        actions=[TriggerAction(kind=ActionKind.END_MISSION, winner="blue")],
    ))
    asm = MissionAssembler(spec)
    asm.assemble()
    codes = [i.code for i in asm.report.issues]
    assert "TRIGGER_GROUP_UNKNOWN" in codes
    assert "TRIGGER_NO_VALID_CONDITIONS" in codes
    # The other 3 valid triggers should still have landed.
    assert len(asm.mission.triggerrules.triggers) == 3


def test_trigger_coalition_filter_routes_to_messagetocoalition():
    spec = MissionSpec(
        name="Coalition msg",
        theatre="Caucasus",
        coalitions=[Coalition(side="blue", country="USA")],
        triggers=[Trigger(
            name="blue-only",
            coalition="blue",
            conditions=[TriggerCondition(kind=TriggerKind.TIME_REACHED, time_seconds=1)],
            actions=[TriggerAction(kind=ActionKind.SHOW_MESSAGE, message="Hi blue")],
        )],
    )
    asm = MissionAssembler(spec)
    asm.assemble()
    from dcs.action import MessageToCoalition
    rule = asm.mission.triggerrules.triggers[0]
    assert isinstance(rule.actions[0], MessageToCoalition)


# ─── Phase 6: importer ──────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def round_trip_miz(tmp_path_factory):
    """Build a real .miz so the importer has something to read back."""
    spec = MissionSpec(
        name="Round Trip",
        theatre="Caucasus",
        coalitions=[
            Coalition(side="blue", country="USA"),
            Coalition(side="red", country="Russia"),
        ],
        briefing=Briefing(description="d", blue_task="bt", red_task="rt"),
        flights=[
            FlightGroup(
                name="Alpha", aircraft_type="F/A-18C", country="USA", side="blue",
                group_size=2, task=TaskType.CAP, start_type=StartType.COLD, airport="Batumi",
                waypoints=[
                    Waypoint(x=-255000, y=630000, altitude=5000, speed=480, name="WP1"),
                    Waypoint(x=-265000, y=620000, altitude=5000, speed=480, name="WP2"),
                ],
            ),
        ],
        vehicles=[
            VehicleGroup(
                name="SAM", vehicle_type="SA-11-LN", country="Russia", side="red",
                position=Position(x=-272000, y=614000), group_size=1, heading=45,
            ),
        ],
    )
    asm = MissionAssembler(spec)
    out = tmp_path_factory.mktemp("miz") / "rt.miz"
    asm.save(str(out))
    return out


def test_import_theatre_and_briefing(round_trip_miz):
    spec, report = import_miz(str(round_trip_miz))
    assert spec.theatre == "Caucasus"
    assert not report.has_errors()


def test_import_flights_round_trip(round_trip_miz):
    spec, _ = import_miz(str(round_trip_miz))
    flights = spec.flights or []
    assert len(flights) == 1
    f = flights[0]
    assert f.name == "Alpha"
    assert f.aircraft_type == "F/A-18C"
    assert f.country == "USA"
    assert f.side == "blue"
    assert f.group_size == 2
    assert f.waypoints and len(f.waypoints) >= 2


def test_import_vehicles_round_trip(round_trip_miz):
    spec, _ = import_miz(str(round_trip_miz))
    vehicles = spec.vehicles or []
    assert len(vehicles) == 1
    v = vehicles[0]
    assert v.name == "SAM"
    assert v.country == "Russia"
    assert v.side == "red"
    # heading drift from float round-trip via radians
    assert 44.9 < v.heading < 45.1


def test_import_coalitions_only_used_countries(round_trip_miz):
    """The importer must emit only countries that actually own units,
    not every country pydcs wires up by default."""
    spec, _ = import_miz(str(round_trip_miz))
    pairs = {(c.side, c.country) for c in (spec.coalitions or [])}
    assert pairs == {("blue", "USA"), ("red", "Russia")}


def test_import_missing_file_reports_error(tmp_path):
    spec, report = import_miz(str(tmp_path / "nope.miz"))
    assert report.has_errors()
    assert any(i.code == "MIZ_NOT_FOUND" for i in report.issues)
