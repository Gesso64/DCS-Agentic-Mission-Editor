"""Enums used across the schema."""

from enum import Enum


class TaskType(str, Enum):
    CAP = "CAP"
    CAS = "CAS"
    SEAD = "SEAD"
    DEAD = "DEAD"
    STRIKE = "STRIKE"
    SWEEP = "SWEEP"
    INTERCEPT = "INTERCEPT"
    ESCORT = "ESCORT"
    AWACS = "AWACS"
    REFUELING = "REFUELING"
    TRANSPORT = "TRANSPORT"
    RECON = "RECON"
    ANTISHIP = "ANTISHIP"
    GROUND_ATTACK = "GROUND_ATTACK"
    AFAC = "AFAC"
    EWR = "EWR"
    PATROL = "PATROL"


class StartType(str, Enum):
    COLD = "cold"
    WARM = "warm"
    RUNWAY = "runway"


class Skill(str, Enum):
    PLAYER = "Player"
    CLIENT = "Client"
    EXCELLENT = "Excellent"
    GOOD = "Good"
    HIGH = "High"
    AVERAGE = "Average"
    RANDOM = "Random"


class ROE(str, Enum):
    """Rules of Engagement for AI groups."""
    WEAPON_FREE = "WeaponFree"
    OPEN_FIRE_WEAPON_FREE = "OpenFireWeaponFree"
    OPEN_FIRE = "OpenFire"
    RETURN_FIRE = "ReturnFire"
    WEAPON_HOLD = "WeaponHold"


class AlarmState(str, Enum):
    """Alarm state for ground/air defense units."""
    GREEN = "Green"
    RED = "Red"
    AUTO = "Auto"


class Modulation(str, Enum):
    """Radio modulation: AM or FM."""
    AM = "AM"
    FM = "FM"
