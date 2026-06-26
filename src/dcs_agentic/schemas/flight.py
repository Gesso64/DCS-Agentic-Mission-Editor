"""Aircraft flight group model."""

from typing import List, Optional

from pydantic import BaseModel, Field

from .enums import Modulation, Skill, StartType, TaskType
from .payload import PayloadSpec
from .primitives import Position, Waypoint


class FlightGroup(BaseModel):
    """An aircraft group (flight)."""
    name: str = Field(..., description="Group name (e.g. 'Strike 1', 'CAP 1')")
    aircraft_type: str = Field(
        ..., description="Aircraft type alias, e.g. 'F/A-18C', 'Su-27', 'AH-64D'"
    )
    country: str = Field(..., description="Country, e.g. 'USA', 'Russia'")
    side: Optional[str] = Field("blue", description="Coalition side: 'blue' or 'red'")
    group_size: Optional[int] = Field(
        1, ge=1, le=4, description="Number of aircraft in the flight (1-4)"
    )
    task: Optional[TaskType] = Field(None, description="Primary mission task")
    start_type: Optional[StartType] = Field(
        StartType.COLD, description="Start type: cold, warm, or runway"
    )
    airport: Optional[str] = Field(None, description="Airport name for takeoff")
    position: Optional[Position] = Field(
        None, description="Position for inflight spawn (if no airport)"
    )
    altitude: Optional[int] = Field(None, description="Cruise altitude in meters")
    speed: Optional[float] = Field(None, description="Cruise speed in km/h")
    skill: Optional[Skill] = Field(Skill.AVERAGE, description="AI skill level")
    waypoints: Optional[List[Waypoint]] = Field(None, description="Route waypoints")
    late_activation: Optional[bool] = Field(
        False, description="Late activation (spawn on trigger)"
    )
    livery: Optional[str] = Field(None, description="Aircraft livery/skin")
    callsign: Optional[List[str]] = Field(None, description="Callsigns for each unit")
    radio_frequency: Optional[float] = Field(None, description="Radio frequency in MHz")
    modulation: Optional[Modulation] = Field(
        Modulation.AM, description="Radio modulation: AM or FM"
    )
    payload: Optional[PayloadSpec] = Field(
        None, description="Weapons, fuel, and countermeasures configuration"
    )
