"""Radio communication models: ATC, AWACS, tanker, and JTAC."""

from typing import Optional

from pydantic import BaseModel, Field

from .enums import Modulation


class ATCFrequency(BaseModel):
    """Airport / airbase radio frequencies."""
    airport: str = Field(..., description="Airport name on the theatre")
    tower_mhz: Optional[float] = Field(
        None, description="Tower/approach frequency in MHz"
    )
    ground_mhz: Optional[float] = Field(
        None, description="Ground frequency in MHz"
    )
    approach_mhz: Optional[float] = Field(
        None, description="Approach/departure frequency in MHz"
    )


class AWACSComms(BaseModel):
    """AWACS (airborne early warning) radio configuration."""
    flight_name: str = Field(
        ..., description="Name of the AWACS flight in spec.flights"
    )
    callsign: Optional[str] = Field("Magic", description="AWACS radio callsign")
    frequency_mhz: float = Field(..., description="Primary frequency in MHz")
    modulation: Modulation = Field(
        Modulation.AM, description="Radio modulation"
    )


class TankerComms(BaseModel):
    """Aerial tanker radio configuration."""
    flight_name: str = Field(
        ..., description="Name of the tanker flight in spec.flights"
    )
    callsign: Optional[str] = Field("Texaco", description="Tanker radio callsign")
    frequency_mhz: float = Field(..., description="Primary frequency in MHz")
    tacan_channel: Optional[int] = Field(
        None, ge=1, le=126, description="TACAN channel"
    )
    tacan_mode: Optional[str] = Field(
        "X", description="TACAN mode: X or Y"
    )


class JTACComms(BaseModel):
    """JTAC (ground-based forward air controller) radio configuration."""
    unit_name: str = Field(
        ..., description="Name of the JTAC ground unit in spec.vehicles"
    )
    callsign: Optional[str] = Field(
        "Warrior", description="JTAC radio callsign"
    )
    frequency_mhz: float = Field(..., description="Primary frequency in MHz")
    code: Optional[int] = Field(
        1688, description="Laser target designation code"
    )


class RadioComms(BaseModel):
    """Aggregate radio communication settings for the mission."""
    atc: Optional[list[ATCFrequency]] = Field(
        None, description="Airport ATC frequency overrides"
    )
    awacs: Optional[list[AWACSComms]] = Field(
        None, description="AWACS flights"
    )
    tankers: Optional[list[TankerComms]] = Field(
        None, description="Tanker flights"
    )
    jtac: Optional[list[JTACComms]] = Field(
        None, description="JTAC ground units"
    )