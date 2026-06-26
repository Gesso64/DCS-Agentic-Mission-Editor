"""Smoke tests for the mission assembler. Requires `pip install -e .`."""
import os

import pytest

from dcs_agentic.schemas import (
    MissionSpec, FlightGroup, VehicleGroup, Coalition, Waypoint,
    Position, TaskType, StartType, Skill, Briefing, PayloadSpec, Pylon
)
from dcs_agentic.pipeline import MissionAssembler
from dcs_agentic.errors import AssemblyError, Severity


def test_simple_cap():
    """Test: Create a simple CAP mission."""
    spec = MissionSpec(
        name="Simple CAP Test",
        theatre="Caucasus",
        sortie="CAP-01",
        coalitions=[
            Coalition(side="blue", country="USA"),
            Coalition(side="red", country="Russia"),
        ],
        briefing=Briefing(
            description="Test mission: 2-ship CAP over Batumi",
            blue_task="Establish CAP over Batumi. Engage any hostile aircraft entering the zone.",
            red_task="Air defense alert.",
        ),
        flights=[
            FlightGroup(
                name="CAP Alpha",
                aircraft_type="F/A-18C",
                country="USA",
                side="blue",
                group_size=2,
                task=TaskType.CAP,
                start_type=StartType.COLD,
                airport="Batumi",
                skill=Skill.EXCELLENT,
                waypoints=[
                    Waypoint(x=-255000, y=630000, altitude=5000, speed=480, name="Batumi CAP North"),
                    Waypoint(x=-265000, y=620000, altitude=5000, speed=480, name="Batumi CAP South"),
                ],
            ),
            FlightGroup(
                name="Red Bandit",
                aircraft_type="Su-27",
                country="Russia",
                side="red",
                group_size=2,
                task=TaskType.CAP,
                start_type=StartType.COLD,
                airport="Sochi-Adler",
                skill=Skill.GOOD,
                waypoints=[
                    Waypoint(x=-230000, y=660000, altitude=4500, speed=450, name="Patrol North"),
                ],
            ),
        ],
        vehicles=None,
        ships=None,
    )

    assembler = MissionAssembler(spec)
    output = assembler.save("output/test_simple_cap.miz")
    assert os.path.exists(output), f"miz file not written: {output}"
    assert os.path.getsize(output) > 0, "miz file is empty"
    print(f"  OK: {output}")


def test_strike_mission():
    """Test: Create a strike mission with SEAD support."""
    spec = MissionSpec(
        name="Strike Package Test",
        theatre="Caucasus",
        sortie="STRIKE-01",
        coalitions=[
            Coalition(side="blue", country="USA"),
            Coalition(side="red", country="Russia"),
        ],
        flights=[
            FlightGroup(
                name="Strike Lead",
                aircraft_type="F/A-18C",
                country="USA",
                side="blue",
                group_size=2,
                task=TaskType.STRIKE,
                start_type=StartType.COLD,
                airport="Batumi",
                skill=Skill.EXCELLENT,
                waypoints=[
                    Waypoint(x=-250000, y=625000, altitude=5000, speed=420, name="IP"),
                    Waypoint(x=-270000, y=615000, altitude=4500, speed=420, name="Target Area"),
                    Waypoint(x=-260000, y=620000, altitude=3000, speed=420, name="Egress"),
                ],
            ),
            FlightGroup(
                name="SEAD Escort",
                aircraft_type="F-16C",
                country="USA",
                side="blue",
                group_size=2,
                task=TaskType.SEAD,
                start_type=StartType.COLD,
                airport="Batumi",
                skill=Skill.EXCELLENT,
                waypoints=[
                    Waypoint(x=-250000, y=625000, altitude=5000, speed=480, name="IP"),
                    Waypoint(x=-270000, y=615000, altitude=4500, speed=480, name="SAM Suppression"),
                ],
            ),
        ],
        vehicles=[
            VehicleGroup(
                name="SA-11 Site Alpha",
                vehicle_type="SA-11-LN",
                country="Russia",
                side="red",
                position=Position(x=-272000, y=614000),
                group_size=2,
                heading=45,
                skill=Skill.HIGH,
            ),
            VehicleGroup(
                name="SA-11 Radar",
                vehicle_type="SA-11-SR",
                country="Russia",
                side="red",
                position=Position(x=-271000, y=614500),
                group_size=1,
                heading=0,
                skill=Skill.HIGH,
            ),
            VehicleGroup(
                name="SA-11 CP",
                vehicle_type="SA-11-CP",
                country="Russia",
                side="red",
                position=Position(x=-272500, y=614000),
                group_size=1,
                heading=0,
                skill=Skill.HIGH,
            ),
        ],
    )

    assembler = MissionAssembler(spec)
    output = assembler.save("output/test_strike.miz")
    assert os.path.exists(output), f"miz file not written: {output}"
    assert os.path.getsize(output) > 0, "miz file is empty"
    print(f"  OK: {output}")


def test_report_records_creation():
    """The assembler should record an INFO entry per group created."""
    spec = MissionSpec(
        name="Report Smoke",
        theatre="Caucasus",
        coalitions=[Coalition(side="blue", country="USA")],
        flights=[
            FlightGroup(
                name="Solo", aircraft_type="F/A-18C", country="USA",
                side="blue", group_size=1, task=TaskType.CAP,
                start_type=StartType.COLD, airport="Batumi",
            ),
        ],
    )
    asm = MissionAssembler(spec)
    asm.assemble()
    codes = [i.code for i in asm.report.issues]
    assert "FLIGHT_CREATED" in codes
    assert not asm.report.has_errors()


def test_strict_mode_raises_on_unknown_aircraft():
    """An unknown aircraft type should produce an error and --strict should raise."""
    spec = MissionSpec(
        name="Bad Aircraft",
        theatre="Caucasus",
        coalitions=[Coalition(side="blue", country="USA")],
        flights=[
            FlightGroup(
                name="Ghost", aircraft_type="NotARealJet", country="USA",
                side="blue", group_size=1, task=TaskType.CAP,
                start_type=StartType.COLD, airport="Batumi",
            ),
        ],
    )
    asm = MissionAssembler(spec, strict=True)
    with pytest.raises(AssemblyError):
        asm.assemble()
    assert any(i.code == "FLIGHT_BUILD_FAILED" for i in asm.report.issues)


def test_non_strict_mode_collects_errors_without_raising():
    spec = MissionSpec(
        name="Bad Aircraft Soft",
        theatre="Caucasus",
        coalitions=[Coalition(side="blue", country="USA")],
        flights=[
            FlightGroup(
                name="Ghost", aircraft_type="NotARealJet", country="USA",
                side="blue", group_size=1, task=TaskType.CAP,
                start_type=StartType.COLD, airport="Batumi",
            ),
        ],
    )
    asm = MissionAssembler(spec, strict=False)
    asm.assemble()  # must not raise
    assert asm.report.has_errors()


def test_payload_preset_applied():
    """A FlightGroup with PayloadSpec(preset_name=...) gets the preset's pylons."""
    from dcs_agentic.catalog import payloads as cp
    preset = cp.resolve("F/A-18C", "CAP A-A")
    spec = MissionSpec(
        name="Payload Preset",
        theatre="Caucasus",
        coalitions=[Coalition(side="blue", country="USA")],
        flights=[
            FlightGroup(
                name="CAP", aircraft_type="F/A-18C", country="USA",
                side="blue", group_size=1, task=TaskType.CAP,
                start_type=StartType.COLD, airport="Batumi",
                payload=PayloadSpec(preset_name="CAP A-A"),
            ),
        ],
    )
    asm = MissionAssembler(spec)
    asm.assemble()
    assert not asm.report.has_errors()
    flight_group = list(asm.mission.country("USA").plane_group)[0]
    unit = flight_group.units[0]
    expected_stations = {station for (station, _, _) in preset.pylons}
    assert set(unit.pylons.keys()) == expected_stations
    for station, clsid, _ in preset.pylons:
        assert unit.pylons[station]["CLSID"] == clsid


def test_payload_unknown_preset_records_error():
    spec = MissionSpec(
        name="Bad Preset",
        theatre="Caucasus",
        coalitions=[Coalition(side="blue", country="USA")],
        flights=[
            FlightGroup(
                name="CAP", aircraft_type="F/A-18C", country="USA",
                side="blue", group_size=1, task=TaskType.CAP,
                start_type=StartType.COLD, airport="Batumi",
                payload=PayloadSpec(preset_name="NOT A REAL PRESET"),
            ),
        ],
    )
    asm = MissionAssembler(spec)
    asm.assemble()
    codes = [i.code for i in asm.report.issues]
    assert "PAYLOAD_PRESET_UNKNOWN" in codes


if __name__ == "__main__":
    print("=== Testing Mission Assembler ===\n")

    tests = [
        ("Simple CAP", test_simple_cap),
        ("Strike with SEAD and SAMs", test_strike_mission),
    ]

    passed = 0
    for name, test_fn in tests:
        print(f"Test: {name}")
        try:
            result = test_fn()
            if result:
                passed += 1
                print(f"  PASS\n")
        except Exception as e:
            import traceback
            print(f"  FAIL: {e}")
            traceback.print_exc()
            print()

    print(f"=== Done - {passed}/{len(tests)} passed ===")