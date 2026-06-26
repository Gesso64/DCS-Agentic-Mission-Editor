"""Phase 4 tail tests: ROE/AlarmState, FARPs, carrier ops, drawings."""
from dcs.drawing.drawings import StandardLayer
from dcs.task import OptAlarmState, OptROE

from dcs_agentic.pipeline import MissionAssembler
from dcs_agentic.schemas import (
    CarrierOps,
    Coalition,
    FARP,
    MapMarker,
    MissionSpec,
    Position,
    ShipGroup,
    VehicleGroup,
    Zone,
)
from dcs_agentic.schemas.enums import AlarmState, ROE


def _spec(**overrides) -> MissionSpec:
    base = dict(
        name="P4Tail",
        theatre="Caucasus",
        coalitions=[
            Coalition(side="blue", country="USA"),
            Coalition(side="red", country="Russia"),
        ],
    )
    base.update(overrides)
    return MissionSpec(**base)


def test_vehicle_roe_and_alarm_state_applied():
    spec = _spec(vehicles=[
        VehicleGroup(
            name="SAM Alpha", vehicle_type="SA-11-LN", country="Russia",
            side="red", position=Position(x=-272000, y=614000), group_size=1,
            roe=ROE.WEAPON_FREE, alarm_state=AlarmState.RED,
        ),
    ])
    asm = MissionAssembler(spec)
    asm.assemble()
    assert not asm.report.has_errors()
    country = asm.mission.country("Russia")
    vg = list(country.vehicle_group)[0]
    roe_tasks = [t for t in vg.tasks if isinstance(t, OptROE)]
    alarm_tasks = [t for t in vg.tasks if isinstance(t, OptAlarmState)]
    assert len(roe_tasks) == 1
    assert roe_tasks[0].params["action"]["params"]["value"] == OptROE.Values.WeaponFree
    assert len(alarm_tasks) == 1
    assert alarm_tasks[0].params["action"]["params"]["value"] == 2  # RED


def test_farp_creates_static_group():
    spec = _spec(farps=[
        FARP(
            name="FARP Bravo", country="USA", side="blue",
            position=Position(x=-280000, y=620000), heading=90,
        ),
    ])
    asm = MissionAssembler(spec)
    asm.assemble()
    assert not asm.report.has_errors()
    codes = [i.code for i in asm.report.issues]
    assert "FARP_CREATED" in codes


def test_invisible_farp_uses_invisible_type():
    spec = _spec(farps=[
        FARP(
            name="FARP Hidden", country="USA", side="blue",
            position=Position(x=-280000, y=620000), invisible=True,
        ),
    ])
    asm = MissionAssembler(spec)
    asm.assemble()
    country = asm.mission.country("USA")
    static_groups = list(country.static_group)
    assert any(sg.name == "FARP Hidden" for sg in static_groups)


def test_carrier_ops_adds_tacan_beacon():
    spec = _spec(
        ships=[
            ShipGroup(
                name="CVN-73", ship_type="CV_1143_5", country="USA",
                side="blue", position=Position(x=-290000, y=590000), group_size=1,
            ),
        ],
        carrier_ops=[
            CarrierOps(
                ship_name="CVN-73", tacan_channel=72, tacan_mode="X",
                tacan_callsign="WSH",
            ),
        ],
    )
    asm = MissionAssembler(spec)
    asm.assemble()
    codes = [i.code for i in asm.report.issues]
    assert "CARRIER_OPS_CREATED" in codes
    country = asm.mission.country("USA")
    sg = next(s for s in country.ship_group if s.name == "CVN-73")
    beacon_tasks = [t for t in sg.points[0].tasks if t.params.get("action", {}).get("id") == "ActivateBeacon"]
    assert len(beacon_tasks) == 1
    assert beacon_tasks[0].params["action"]["params"]["channel"] == 72


def test_carrier_ops_unknown_ship_errors():
    spec = _spec(
        carrier_ops=[CarrierOps(ship_name="Ghost Boat", tacan_channel=10)],
    )
    asm = MissionAssembler(spec)
    asm.assemble()
    codes = [i.code for i in asm.report.issues]
    assert "CARRIER_NOT_FOUND" in codes


def test_carrier_ops_partial_features_warn():
    spec = _spec(
        ships=[
            ShipGroup(
                name="CVN-73", ship_type="CV_1143_5", country="USA",
                side="blue", position=Position(x=-290000, y=590000), group_size=1,
            ),
        ],
        carrier_ops=[
            CarrierOps(
                ship_name="CVN-73", tacan_channel=72,
                icls_channel=11, base_recovery_course=180.0,
            ),
        ],
    )
    asm = MissionAssembler(spec)
    asm.assemble()
    codes = [i.code for i in asm.report.issues]
    assert "CARRIER_OPS_PARTIAL" in codes


def test_zone_creates_circle_on_common_layer():
    spec = _spec(zones=[
        Zone(name="Zone Alpha", center=Position(x=-250000, y=620000),
             radius=20000.0, color="rgba(0,255,0,0.5)"),
    ])
    asm = MissionAssembler(spec)
    asm.assemble()
    codes = [i.code for i in asm.report.issues]
    assert "ZONE_CREATED" in codes
    common = asm.mission.drawings.get_layer(StandardLayer.Common)
    assert len(common.objects) >= 2  # circle + label


def test_marker_routes_to_coalition_layer():
    spec = _spec(markers=[
        MapMarker(name="M1", position=Position(x=-250000, y=620000),
                  text="hi", coalition="blue"),
    ])
    asm = MissionAssembler(spec)
    asm.assemble()
    codes = [i.code for i in asm.report.issues]
    assert "MARKER_CREATED" in codes
    blue = asm.mission.drawings.get_layer(StandardLayer.Blue)
    assert len(blue.objects) == 1
