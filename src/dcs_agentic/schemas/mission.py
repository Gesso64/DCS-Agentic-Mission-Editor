"""Top-level MissionSpec, Coalition, CustomScript, and MissionGoal."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from .briefing import Briefing
from .bullseye import Bullseye
from .drawing import MapMarker, Zone
from .flight import FlightGroup
from .ground import FARP, StaticObject, VehicleGroup
from .naval import CarrierOps, ShipGroup
from .radio import RadioComms
from .triggers import Trigger
from .weather import Weather


SCHEMA_VERSION = "0.2.0"

VALID_THEATRES = frozenset({
    "Caucasus", "PersianGulf", "Syria", "Nevada",
    "Normandy", "TheChannel", "MarianaIslands", "Falklands",
})


_VALID_SIDES = {"blue", "red", "neutrals"}


class Coalition(BaseModel):
    """A coalition side with its countries."""
    side: str = Field(..., description="'blue', 'red', or 'neutrals'")
    country: str = Field(..., description="Country name, e.g. 'USA', 'Russia'")

    @field_validator("side")
    @classmethod
    def _validate_side(cls, v: str) -> str:
        lower = v.lower()
        if lower not in _VALID_SIDES:
            raise ValueError(f"side must be one of {_VALID_SIDES}, got '{v}'")
        return lower


class MissionGoal(BaseModel):
    """A mission goal / victory condition.

    These map to DCS's scoring system. Cross-references to specific
    flights or zones are not validated here — that belongs in validation/.
    """
    description: str = Field(..., description="Goal description")
    score_target: Optional[int] = Field(
        None, ge=0, description="Target score for this goal"
    )
    coalition: Optional[str] = Field(
        None, description="Which coalition this goal applies to: 'blue' or 'red'"
    )
    category: Optional[str] = Field(
        None, description="Goal category, e.g. 'intercept', 'destroy', 'capture'"
    )
    params: Optional[Dict[str, Any]] = Field(
        None, description="Additional goal parameters"
    )


class CustomScript(BaseModel):
    """Custom Lua script to embed in the mission."""
    name: str = Field(..., description="Script name")
    content: Optional[str] = Field(None, description="Inline script content")
    file_path: Optional[str] = Field(None, description="Path to external script file")
    language: Optional[str] = Field("Lua", description="Script language")


class MissionSpec(BaseModel):
    """Complete declarative mission specification."""

    # Core info
    name: str = Field(..., description="Mission name")
    theatre: str = Field(
        "Caucasus",
        description="Map/theatre. See VALID_THEATRES.",
    )
    sortie: Optional[str] = Field(None, description="Sortie identifier text")
    version: Optional[int] = Field(20, description="MIZ version")

    # Timing
    start_time: Optional[float] = Field(
        None, description="Start time as unix timestamp"
    )

    # Sides and coalitions
    coalitions: Optional[List[Coalition]] = Field(
        None, description="Which countries are on which side"
    )

    # Briefing
    briefing: Optional[Briefing] = Field(None, description="Mission briefing")

    # Weather
    weather: Optional[Weather] = Field(None, description="Weather conditions")

    # Forces
    flights: Optional[List[FlightGroup]] = Field(None, description="Aircraft groups")
    vehicles: Optional[List[VehicleGroup]] = Field(
        None, description="Ground vehicle groups"
    )
    ships: Optional[List[ShipGroup]] = Field(None, description="Ship groups")
    statics: Optional[List[StaticObject]] = Field(
        None, description="Static objects"
    )

    # FARP (forward arming and refuelling points)
    farps: Optional[List[FARP]] = Field(
        None, description="Forward arming and refuelling points"
    )

    # Carrier operations
    carrier_ops: Optional[List[CarrierOps]] = Field(
        None, description="Carrier-based operations (TACAN, ICLS, etc.)"
    )

    # Triggers
    triggers: Optional[List[Trigger]] = Field(None, description="Mission triggers")

    # Drawings, zones, and map markers
    zones: Optional[List[Zone]] = Field(
        None, description="Map zones (combat zones, no-fly zones, etc.)"
    )
    markers: Optional[List[MapMarker]] = Field(
        None, description="F10 map markers"
    )

    # Bullseye reference points
    bullseye: Optional[Bullseye] = Field(
        None, description="Bullseye reference points per coalition"
    )

    # Radio communications (ATC, AWACS, tanker, JTAC)
    radios: Optional[RadioComms] = Field(
        None, description="Radio communications configuration"
    )

    # Mission goals
    mission_goals: Optional[List[MissionGoal]] = Field(
        None, description="Mission goals / victory conditions"
    )

    # Custom Lua scripts
    custom_scripts: Optional[List[CustomScript]] = Field(
        None, description="Custom Lua scripts"
    )

    # Metadata for agent tracking
    agent_notes: Optional[str] = Field(
        None, description="Notes from the AI agent about design decisions"
    )

    @field_validator("theatre")
    @classmethod
    def validate_theatre(cls, v):
        if v not in VALID_THEATRES:
            raise ValueError(f"Unknown theatre: {v}. Valid: {sorted(VALID_THEATRES)}")
        return v