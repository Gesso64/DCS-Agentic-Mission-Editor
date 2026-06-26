"""Ground unit models: vehicles, static objects, and FARPs."""

from typing import List, Optional

from pydantic import BaseModel, Field

from .enums import AlarmState, ROE, Skill
from .primitives import Position, Waypoint


class VehicleGroup(BaseModel):
    """A ground vehicle group."""
    name: str = Field(..., description="Group name")
    vehicle_type: str = Field(
        ...,
        description="Vehicle type alias, e.g. 'SA-11-LN', 'M-1-ABRAMS', 'BMP-2'",
    )
    country: str = Field(..., description="Country")
    side: Optional[str] = Field("red", description="Coalition side")
    position: Position = Field(..., description="Position")
    group_size: Optional[int] = Field(
        1, ge=1, description="Number of vehicles in the group"
    )
    heading: Optional[float] = Field(0, description="Initial heading in degrees")
    skill: Optional[Skill] = Field(Skill.AVERAGE, description="AI skill level")
    waypoints: Optional[List[Waypoint]] = Field(None, description="Route waypoints")
    late_activation: Optional[bool] = Field(False)
    visible: Optional[bool] = Field(True, description="Visible before mission start")
    roe: Optional[ROE] = Field(
        None, description="Rules of engagement for this group"
    )
    alarm_state: Optional[AlarmState] = Field(
        None, description="Alarm state (alert level)"
    )


class FARP(BaseModel):
    """A forward arming and refuelling point."""
    name: str = Field(..., description="FARP name")
    country: str = Field(..., description="Country")
    side: Optional[str] = Field("blue", description="Coalition side")
    position: Position = Field(..., description="Position")
    heading: Optional[float] = Field(0, description="Heading in degrees")
    invisible: Optional[bool] = Field(
        False, description="Invisible FARP (not rendered)"
    )
    has_fuel: Optional[bool] = Field(True, description="Provides fuel")
    has_ammo: Optional[bool] = Field(True, description="Provides ammunition")
    has_repair: Optional[bool] = Field(True, description="Provides repairs")


class StaticObject(BaseModel):
    """A static object (building, container, etc.).

    `type` is resolved against pydcs's dcs.statics.{Fortification,
    GroundObject, Warehouse, Cargo} containers — see catalog/statics.py.
    """
    name: str = Field(..., description="Object name")
    type: str = Field(
        ...,
        description="Static type, e.g. 'FARP', 'container_red', 'house'",
    )
    country: str = Field(..., description="Country")
    side: Optional[str] = Field("neutrals")
    position: Position = Field(..., description="Position")
    heading: Optional[float] = Field(0, description="Heading in degrees")
    dead: Optional[bool] = Field(False, description="Render as destroyed")
