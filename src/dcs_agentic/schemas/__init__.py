"""DCS Agentic Mission Editor — Mission Specification Schema.

Public re-exports. Implementations live in topical submodules — edit
those, not this file. New top-level models should be added to a focused
submodule (or a new one) and re-exported here.

Submodules:
  - enums       — TaskType, StartType, Skill, ROE, AlarmState, Modulation
  - primitives  — Position, Waypoint
  - weather     — WindGround, WindHeight, Weather
  - briefing    — Briefing
  - payload     — Pylon, PayloadSpec
  - flight      — FlightGroup
  - ground      — VehicleGroup, StaticObject, FARP
  - naval       — ShipGroup, CarrierOps
  - bullseye    — Bullseye
  - radio       — RadioComms, ATCFrequency, AWACSComms, TankerComms, JTACComms
  - drawing     — Zone, MapMarker
  - triggers    — TriggerKind, ActionKind, TriggerCondition, TriggerAction, Trigger
  - mission     — MissionSpec, Coalition, CustomScript, MissionGoal, SCHEMA_VERSION
  - campaign    — CampaignSpec, CampaignState, MissionLink, AfterAction (NOT YET LIVE)
"""

from .briefing import Briefing
from .bullseye import Bullseye
from .campaign import (
    CAMPAIGN_SCHEMA_VERSION,
    AfterAction,
    CampaignSpec,
    CampaignState,
    MissionLink,
)
from .drawing import MapMarker, Zone
from .enums import AlarmState, Modulation, ROE, Skill, StartType, TaskType
from .flight import FlightGroup
from .ground import FARP, StaticObject, VehicleGroup
from .mission import (
    VALID_THEATRES,
    Coalition,
    CustomScript,
    MissionGoal,
    MissionSpec,
    SCHEMA_VERSION,
)
from .naval import CarrierOps, ShipGroup
from .payload import PayloadSpec, Pylon
from .primitives import Position, Waypoint
from .radio import ATCFrequency, AWACSComms, JTACComms, RadioComms, TankerComms
from .triggers import ActionKind, Trigger, TriggerAction, TriggerCondition, TriggerKind
from .weather import Weather, WindGround, WindHeight

__all__ = [
    # enums
    "TaskType", "StartType", "Skill", "ROE", "AlarmState", "Modulation",
    # primitives
    "Position", "Waypoint",
    # weather
    "WindGround", "WindHeight", "Weather",
    # briefing
    "Briefing",
    # payload
    "Pylon", "PayloadSpec",
    # flight
    "FlightGroup",
    # ground
    "VehicleGroup", "StaticObject", "FARP",
    # naval
    "ShipGroup", "CarrierOps",
    # bullseye
    "Bullseye",
    # radio
    "ATCFrequency", "AWACSComms", "TankerComms", "JTACComms", "RadioComms",
    # drawing
    "Zone", "MapMarker",
    # triggers (v1 closed-union)
    "TriggerKind", "ActionKind", "TriggerCondition", "TriggerAction", "Trigger",
    # mission
    "MissionSpec", "Coalition", "CustomScript", "MissionGoal",
    "SCHEMA_VERSION", "VALID_THEATRES",
    # campaign
    "CampaignSpec", "CampaignState", "MissionLink", "AfterAction",
    "CAMPAIGN_SCHEMA_VERSION",
]