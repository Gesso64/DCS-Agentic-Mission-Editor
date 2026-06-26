"""Weather models."""

from typing import Optional

from pydantic import BaseModel, Field


class WindGround(BaseModel):
    speed: float = Field(0, description="Wind speed at ground level (m/s)")
    dir: float = Field(0, description="Wind direction in degrees (0-360)")


class WindHeight(BaseModel):
    speed: float = Field(0, description="Wind speed at altitude (m/s)")
    dir: float = Field(0, description="Wind direction in degrees (0-360)")


class Weather(BaseModel):
    """Mission weather configuration."""
    season: Optional[str] = Field(
        None,
        description="Season: 'Summer', 'Winter', 'Autumn', 'Spring' "
                    "(currently a no-op in the assembler)",
    )
    qnh: Optional[int] = Field(None, description="QNH pressure in mmHg")
    temperature: Optional[float] = Field(
        None, description="Temperature at ground level (°C)"
    )
    fog_enabled: Optional[bool] = Field(False)
    fog_visibility: Optional[float] = Field(None, description="Fog visibility in meters")
    clouds_thickness: Optional[int] = Field(None, description="Cloud thickness (0-10)")
    clouds_density: Optional[int] = Field(None, description="Cloud density (0-10)")
    clouds_base: Optional[int] = Field(None, description="Cloud base altitude in meters")
    clouds_iprecptns: Optional[int] = Field(
        None, description="Precipitation type (0=none)"
    )
    wind_at_ground: Optional[WindGround] = None
    wind_at_height: Optional[WindHeight] = None
    enable_dust: Optional[bool] = Field(False, description="Enable dust/sandstorms")
