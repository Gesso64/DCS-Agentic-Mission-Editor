"""Payload / weapons models for aircraft flights."""

from typing import List, Optional

from pydantic import BaseModel, Field


class Pylon(BaseModel):
    """A single pylon station with a weapon loadout."""
    station: int = Field(..., ge=1, le=20, description="Pylon station number")
    clsid: str = Field(..., description="DCS CLSID, e.g. '{AIM-9X}'")
    quantity: Optional[int] = Field(1, ge=1, description="Number of weapons on this station")


class PayloadSpec(BaseModel):
    """Weapons and fuel configuration for a flight.

    Named presets (from catalog/payloads.py) may be referenced by name.
    Explicit pylons override the preset. If neither is set, the aircraft
    spawns with its DCS-default loadout.
    """

    preset_name: Optional[str] = Field(
        None, description="Named preset from catalog/payloads.py; "
                         "if set, pylons may be omitted"
    )
    pylons: Optional[List[Pylon]] = Field(
        None, description="Explicit pylon assignments; override preset"
    )
    fuel: Optional[float] = Field(
        None, ge=0, le=1, description="Fuel fraction 0..1"
    )
    chaff: Optional[int] = Field(None, ge=0, description="Chaff dispenser count")
    flare: Optional[int] = Field(None, ge=0, description="Flare dispenser count")
    gun: Optional[int] = Field(
        None, ge=0, le=100, description="Gun ammo percentage"
    )