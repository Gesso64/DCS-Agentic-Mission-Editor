"""Trigger models (v1 closed-union design).

Replaces the v0 loose placeholder. Each trigger has a typed condition
kind and action kind with validated fields. Cross-references (e.g.
trigger references an unknown flight name) are NOT validated here —
that belongs in validation/.
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class TriggerKind(str, Enum):
    """Trigger condition types supported in v1."""
    TIME_REACHED = "time_reached"
    UNIT_DEAD = "unit_dead"
    GROUP_DEAD = "group_dead"
    UNIT_IN_ZONE = "unit_in_zone"
    FLAG_TRUE = "flag_true"


class ActionKind(str, Enum):
    """Trigger action types supported in v1."""
    SHOW_MESSAGE = "show_message"
    PLAY_SOUND = "play_sound"
    SET_FLAG = "set_flag"
    ACTIVATE_GROUP = "activate_group"
    END_MISSION = "end_mission"
    SET_GOAL_SCORE = "set_goal_score"


class TriggerCondition(BaseModel):
    """A single trigger condition.

    One of the optional fields is populated based on `kind`.
    The `params` dict allows future extensibility for condition types
    not yet added to TriggerKind.
    """
    kind: TriggerKind = Field(..., description="Condition type")
    time_seconds: Optional[float] = Field(
        None, ge=0, description="Seconds since mission start (TIME_REACHED)"
    )
    unit_name: Optional[str] = Field(
        None, description="Unit name (UNIT_DEAD, UNIT_IN_ZONE)"
    )
    group_name: Optional[str] = Field(
        None, description="Group name (GROUP_DEAD)"
    )
    zone_name: Optional[str] = Field(
        None, description="Zone name (UNIT_IN_ZONE)"
    )
    flag_name: Optional[str] = Field(
        None, description="Flag name or index (FLAG_TRUE)"
    )
    params: Optional[Dict[str, Any]] = Field(
        None, description="Additional/extensible condition parameters"
    )

    @model_validator(mode="after")
    def validate_condition_fields(self):
        kind = self.kind
        if kind == TriggerKind.TIME_REACHED and self.time_seconds is None:
            raise ValueError("time_seconds is required for TIME_REACHED condition")
        if kind in (TriggerKind.UNIT_DEAD, TriggerKind.UNIT_IN_ZONE) and self.unit_name is None:
            raise ValueError(f"unit_name is required for {kind} condition")
        if kind == TriggerKind.UNIT_IN_ZONE and self.zone_name is None:
            raise ValueError("zone_name is required for UNIT_IN_ZONE condition")
        if kind == TriggerKind.GROUP_DEAD and self.group_name is None:
            raise ValueError("group_name is required for GROUP_DEAD condition")
        if kind == TriggerKind.FLAG_TRUE and self.flag_name is None:
            raise ValueError("flag_name is required for FLAG_TRUE condition")
        return self


class TriggerAction(BaseModel):
    """A single trigger action.

    One of the optional fields is populated based on `kind`.
    """
    kind: ActionKind = Field(..., description="Action type")
    message: Optional[str] = Field(
        None, description="Message text (SHOW_MESSAGE)"
    )
    duration_seconds: Optional[float] = Field(
        10, ge=0, description="Message/sound duration in seconds"
    )
    sound_file: Optional[str] = Field(
        None, description="Sound file path (PLAY_SOUND)"
    )
    flag_name: Optional[str] = Field(
        None, description="Flag name to set (SET_FLAG)"
    )
    flag_value: Optional[int] = Field(
        1, description="Flag value to set (SET_FLAG)"
    )
    group_name: Optional[str] = Field(
        None, description="Group to activate (ACTIVATE_GROUP)"
    )
    winner: Literal["blue", "red", "draw"] | None = Field(
        None, description="Winner for END_MISSION: 'blue', 'red', or 'draw'"
    )
    score: Optional[int] = Field(
        None, description="Score value (SET_GOAL_SCORE)"
    )

    @model_validator(mode="after")
    def validate_action_fields(self):
        if self.kind == ActionKind.SHOW_MESSAGE and self.message is None:
            raise ValueError("message is required for SHOW_MESSAGE action")
        if self.kind == ActionKind.PLAY_SOUND and self.sound_file is None:
            raise ValueError("sound_file is required for PLAY_SOUND action")
        if self.kind == ActionKind.SET_FLAG and self.flag_name is None:
            raise ValueError("flag_name is required for SET_FLAG action")
        if self.kind == ActionKind.ACTIVATE_GROUP and self.group_name is None:
            raise ValueError("group_name is required for ACTIVATE_GROUP action")
        if self.kind == ActionKind.END_MISSION and self.winner is None:
            raise ValueError("winner is required for END_MISSION action")
        return self


class Trigger(BaseModel):
    """A mission trigger: list of conditions AND-ed together, list of actions."""
    name: str = Field(..., description="Trigger name")
    once: Optional[bool] = Field(
        True, description="Fire once (True) or continuously (False)"
    )
    coalition: Optional[str] = Field(
        None, description="'blue', 'red', or None for all coalitions"
    )
    conditions: List[TriggerCondition] = Field(
        ..., description="Conditions (AND-ed together)"
    )
    actions: List[TriggerAction] = Field(
        ..., description="Actions to execute when conditions fire"
    )
    params: Optional[Dict[str, Any]] = Field(
        None, description="Additional/extensible trigger parameters"
    )