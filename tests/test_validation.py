"""Validation layer tests (Phase 7)."""
import json
from pathlib import Path

import pytest

from dcs_agentic.pipeline import MissionAssembler
from dcs_agentic.schemas import (
    CarrierOps,
    Coalition,
    FlightGroup,
    MissionSpec,
    PayloadSpec,
    Position,
    Pylon,
    ShipGroup,
    StartType,
    TaskType,
    Trigger,
    VehicleGroup,
    Waypoint,
)
from dcs_agentic.schemas.triggers import (
    ActionKind,
    TriggerAction,
    TriggerCondition,
    TriggerKind,
)
from dcs_agentic.validation import validate


def _base() -> MissionSpec:
    return MissionSpec(
        name="V", theatre="Caucasus",
        coalitions=[Coalition(side="blue", country="USA")],
        flights=[
            FlightGroup(
                name="Alpha", aircraft_type="F/A-18C", country="USA",
                side="blue", group_size=1, task=TaskType.CAP,
                start_type=StartType.COLD, airport="Batumi",
            ),
        ],
    )


# ─── coordinate_sanity ──────────────────────────────────────────────────────


def test_coords_in_bounds_no_warnings():
    spec = _base()
    spec.flights[0].waypoints = [
        Waypoint(x=-255000, y=630000, altitude=5000, speed=480, name="WP1"),
    ]
    report = validate(spec)
    assert not any(i.code in ("COORD_OUT_OF_BOUNDS", "COORD_NEAR_BOUNDS") for i in report.issues)


def test_coords_far_outside_errors():
    spec = _base()
    spec.flights[0].waypoints = [
        Waypoint(x=99_999_999, y=99_999_999, name="WP1"),
    ]
    report = validate(spec)
    assert any(i.code == "COORD_OUT_OF_BOUNDS" for i in report.issues)


# ─── fuel_range ─────────────────────────────────────────────────────────────


def test_fuel_range_tight_warns():
    """F/A-18C combat radius is ~720 km — give it a 1300 km round-trip."""
    spec = _base()
    spec.flights[0].waypoints = [
        Waypoint(x=0, y=0, altitude=5000, speed=480, name="A"),
        Waypoint(x=650_000, y=0, altitude=5000, speed=480, name="B"),
        Waypoint(x=0, y=0, altitude=5000, speed=480, name="A2"),
    ]
    report = validate(spec)
    codes = {i.code for i in report.issues}
    fuel_codes = codes & {"FUEL_RANGE_TIGHT", "FUEL_RANGE_EXCEEDED"}
    assert fuel_codes, f"Expected a fuel-range code, got: {codes}"


def test_fuel_range_exceeded_errors():
    spec = _base()
    spec.flights[0].waypoints = [
        Waypoint(x=0, y=0, name="A"),
        Waypoint(x=5_000_000, y=0, name="B"),
    ]
    report = validate(spec)
    assert any(i.code == "FUEL_RANGE_EXCEEDED" for i in report.issues)


# ─── weapons_match ──────────────────────────────────────────────────────────


def test_cap_with_aa_missiles_passes():
    spec = _base()
    spec.flights[0].payload = PayloadSpec(preset_name="CAP A-A")
    report = validate(spec)
    assert not any(i.code == "WEAPONS_TASK_MISMATCH" for i in report.issues)


def test_strike_task_without_bombs_warns():
    spec = _base()
    spec.flights[0].task = TaskType.STRIKE
    spec.flights[0].payload = PayloadSpec(
        pylons=[Pylon(station=1, clsid="{AIM-9X}", quantity=1)],
    )
    report = validate(spec)
    assert any(i.code == "WEAPONS_TASK_MISMATCH" for i in report.issues)


def test_no_payload_for_combat_task_warns():
    spec = _base()
    spec.flights[0].task = TaskType.CAP
    spec.flights[0].payload = None
    report = validate(spec)
    assert any(i.code == "WEAPONS_NO_PAYLOAD" for i in report.issues)


# ─── route_sanity ──────────────────────────────────────────────────────────


def test_extreme_coords_warn_xy_swap():
    spec = _base()
    spec.flights[0].waypoints = [
        Waypoint(x=2_000_000, y=-3_000_000, name="WP1"),
    ]
    report = validate(spec)
    assert any(i.code == "ROUTE_COORD_SUSPICIOUS" for i in report.issues)


def test_altitude_spike_warns():
    spec = _base()
    spec.flights[0].waypoints = [
        Waypoint(x=0, y=0, altitude=100, name="WP1"),
        Waypoint(x=100, y=0, altitude=15000, name="WP2"),
    ]
    report = validate(spec)
    assert any(i.code == "ROUTE_ALTITUDE_SPIKE" for i in report.issues)


# ─── references ────────────────────────────────────────────────────────────


def test_trigger_unknown_group_warns():
    spec = _base()
    spec.triggers = [Trigger(
        name="T1",
        conditions=[TriggerCondition(kind=TriggerKind.GROUP_DEAD, group_name="Ghost")],
        actions=[TriggerAction(kind=ActionKind.SHOW_MESSAGE, message="hi")],
    )]
    report = validate(spec)
    assert any(i.code == "REF_GROUP_UNKNOWN" for i in report.issues)


def test_carrier_ops_unknown_ship_errors():
    spec = _base()
    spec.carrier_ops = [CarrierOps(ship_name="Phantom Carrier", tacan_channel=10)]
    report = validate(spec)
    assert any(i.code == "REF_CARRIER_SHIP_UNKNOWN" for i in report.issues)


# ─── assembler integration ────────────────────────────────────────────────


def test_assembler_validate_true_prepends_issues():
    spec = _base()
    spec.flights[0].waypoints = [Waypoint(x=99_999_999, y=99_999_999, name="Z")]
    asm = MissionAssembler(spec, validate=True)
    asm.assemble()
    codes = {i.code for i in asm.report.issues}
    assert "COORD_OUT_OF_BOUNDS" in codes


def test_validator_crash_is_caught():
    """A buggy validator must surface as VALIDATOR_CRASHED, not crash validate()."""
    from dcs_agentic.validation import _CHECKS
    # Inject a bomb into the local _CHECKS tuple via patching the module
    import dcs_agentic.validation as v
    original = v._CHECKS
    def boom(spec, report):
        raise RuntimeError("kaboom")
    v._CHECKS = (boom,)
    try:
        report = v.validate(_base())
        assert any(i.code == "VALIDATOR_CRASHED" for i in report.issues)
    finally:
        v._CHECKS = original
