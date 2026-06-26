"""Drawing, zone, and map marker models for mission visual elements."""

from typing import Optional

from pydantic import BaseModel, Field

from .primitives import Position


class Zone(BaseModel):
    """A circular zone on the map (combat zone, no-fly zone, etc.)."""
    name: str = Field(..., description="Zone name (referenced by triggers)")
    center: Position = Field(..., description="Center position in meters")
    radius: float = Field(..., ge=0, description="Radius in meters")
    color: Optional[str] = Field(
        "rgba(255,0,0,0.3)", description="Color string e.g. 'rgba(r,g,b,a)'"
    )


class MapMarker(BaseModel):
    """A text marker on the map (F10 map marker)."""
    name: str = Field(..., description="Marker label")
    position: Position = Field(..., description="Marker position")
    text: str = Field(..., description="Marker text content")
    coalition: Optional[str] = Field(
        "all", description="Visible to: 'blue', 'red', or 'all'"
    )