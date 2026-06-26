"""Bullseye reference point models.

Bullseye is a navigation reference point used for threat callouts
and coordinate-relative positioning. DCS missions typically define
separate bullseye positions for each coalition.
"""

from typing import Optional

from pydantic import BaseModel, Field

from .primitives import Position


class Bullseye(BaseModel):
    """Bullseye (navigation reference point) for each coalition.

    If absent from a MissionSpec, the assembler falls back to the
    theatre default from catalog/theatres.py.
    """

    blue: Optional[Position] = Field(
        None, description="Blue-coalition bullseye position"
    )
    red: Optional[Position] = Field(
        None, description="Red-coalition bullseye position"
    )