"""Coordinate primitives used by every group type."""

from typing import List, Optional

from pydantic import BaseModel, Field

from .enums import TaskType


class Position(BaseModel):
    """Map coordinate position in meters (DCS coordinate system).

    pydcs uses Point(x, y) where x is north-south, y is east-west.
    Coordinates are negative on most theatres (Caucasus, Syria, etc.).
    """
    x: float = Field(..., description="X coordinate in meters (map-projected)")
    y: float = Field(..., description="Y coordinate in meters (map-projected)")


class Waypoint(BaseModel):
    """A waypoint along a group's route.

    Speed is km/h (pydcs convention). The assembler converts to m/s
    internally via dcs_agentic.units.kmh_to_ms.
    """
    x: float = Field(..., description="X coordinate in meters")
    y: float = Field(..., description="Y coordinate in meters")
    altitude: Optional[int] = Field(None, description="Altitude in meters (MSL)")
    speed: Optional[float] = Field(
        None,
        description="Speed in km/h (pydcs convention; converted to m/s internally)",
    )
    name: Optional[str] = Field(None, description="Waypoint name")
    type: Optional[str] = Field(
        None,
        description="Waypoint type: 'Turning Point', 'Land', 'TakeOff', etc.",
    )
    action: Optional[str] = Field(
        None,
        description="Point action: 'TURNING_POINT', 'LANDING', 'FLY_OVER_POINT', etc.",
    )
    tasks: Optional[List[TaskType]] = Field(
        None, description="Tasks to execute at this waypoint"
    )
    eta_locked: Optional[bool] = Field(False, description="Lock ETA at this waypoint")
    airdrome_id: Optional[int] = Field(
        None, description="Airport ID for landing/takeoff waypoints"
    )
