"""Briefing models."""

from typing import List, Optional

from pydantic import BaseModel, Field


class Briefing(BaseModel):
    """Mission briefing information."""
    description: Optional[str] = Field(None, description="General mission description")
    blue_task: Optional[str] = Field(None, description="Blue coalition task description")
    red_task: Optional[str] = Field(None, description="Red coalition task description")
    images_blue: Optional[List[str]] = Field(
        None, description="Blueprint image file paths for blue"
    )
    images_red: Optional[List[str]] = Field(
        None, description="Blueprint image file paths for red"
    )
