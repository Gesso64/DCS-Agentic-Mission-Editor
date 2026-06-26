"""Naval models: ship groups and carrier operations."""

from typing import List, Optional

from pydantic import BaseModel, Field

from .enums import Skill
from .primitives import Position, Waypoint


class ShipGroup(BaseModel):
    """A ship group."""
    name: str = Field(..., description="Group name")
    ship_type: str = Field(
        ...,
        description="Ship type alias, e.g. 'Arleigh-Burke', 'Kuznetsov'",
    )
    country: str = Field(..., description="Country")
    side: Optional[str] = Field("blue", description="Coalition side")
    position: Position = Field(..., description="Position")
    group_size: Optional[int] = Field(
        1, ge=1, description="Number of ships of this type"
    )
    heading: Optional[float] = Field(0, description="Initial heading in degrees")
    skill: Optional[Skill] = Field(Skill.AVERAGE)
    waypoints: Optional[List[Waypoint]] = Field(None)


class CarrierOps(BaseModel):
    """Carrier operations configuration.

    TACAN, ICLS, BRC, and link-4 settings for a carrier.
    The ship must exist in spec.ships with a carrier-type vessel.
    """
    ship_name: str = Field(
        ..., description="Name of the carrier ship in spec.ships"
    )
    tacan_channel: int = Field(
        ..., ge=1, le=126, description="TACAN channel"
    )
    tacan_mode: Optional[str] = Field(
        "X", description="TACAN mode: X or Y"
    )
    tacan_callsign: Optional[str] = Field(
        "STN", description="TACAN callsign (e.g. 'STN', 'ICL')"
    )
    icls_channel: Optional[int] = Field(
        None, ge=1, le=20, description="ICLS channel"
    )
    base_recovery_course: Optional[float] = Field(
        None, ge=0, lt=360, description="BRC in degrees (ship's landing direction)"
    )
    link4_mhz: Optional[float] = Field(
        None, description="Link-4 data link frequency in MHz"
    )