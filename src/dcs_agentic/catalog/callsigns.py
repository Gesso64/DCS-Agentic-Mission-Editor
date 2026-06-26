"""Callsign name ↔ numeric ID maps for AWACS, tanker, JTAC.

Verified against pydcs's Country class definitions in dcs/countries.py (USA
nested classes CallsignAWACS, CallsignTankers, CallsignGroundUnits).

Numeric IDs are the 0-based index into each callsign category's list.
These are used when calling Country.next_callsign_category(category) in
pydcs, or when setting callsign_dict["name"] on a unit.

Usage:
    get_awacs_id("Magic")       -> 1
    get_tanker_id("Texaco")     -> 0
    get_jtac_id("Warrior")     -> 2
    all_awacs()                 -> ["Overlord", "Magic", ...]
"""

from typing import Dict, List, Optional

# ── AWACS callsigns ─────────────────────────────────────────────────────────
# Source: dcs/countries.py, USA.CallsignAWACS (line ~371)
AWACS_CALLSIGNS: Dict[str, int] = {
    "Overlord": 0,
    "Magic": 1,
    "Wizard": 2,
    "Focus": 3,
    "Darkstar": 4,
}

# ── Tanker callsigns ────────────────────────────────────────────────────────
# Source: dcs/countries.py, USA.CallsignTankers (line ~378)
TANKER_CALLSIGNS: Dict[str, int] = {
    "Texaco": 0,
    "Arco": 1,
    "Shell": 2,
}

# ── JTAC / FAC / ground unit callsigns ─────────────────────────────────────
# Source: dcs/countries.py, USA.CallsignGroundUnits (line ~405)
JTAC_CALLSIGNS: Dict[str, int] = {
    "Axeman": 0,
    "Darknight": 1,
    "Warrior": 2,
    "Pointer": 3,
    "Eyeball": 4,
    "Moonbeam": 5,
    "Whiplash": 6,
    "Finger": 7,
    "Pinpoint": 8,
    "Ferret": 9,
    "Shaba": 10,
    "Playboy": 11,
    "Hammer": 12,
    "Jaguar": 13,
    "Deathstar": 14,
    "Firefly": 15,
    "Mantis": 16,
    "Badger": 17,
}


# ── Lookup functions ────────────────────────────────────────────────────────

def get_awacs_id(name: str) -> Optional[int]:
    """Return the numeric AWACS callsign ID, or None if unknown."""
    return AWACS_CALLSIGNS.get(name)


def get_tanker_id(name: str) -> Optional[int]:
    """Return the numeric tanker callsign ID, or None if unknown."""
    return TANKER_CALLSIGNS.get(name)


def get_jtac_id(name: str) -> Optional[int]:
    """Return the numeric JTAC callsign ID, or None if unknown."""
    return JTAC_CALLSIGNS.get(name)


def all_awacs() -> List[str]:
    """Return sorted list of all known AWACS callsign names."""
    return sorted(AWACS_CALLSIGNS)


def all_tankers() -> List[str]:
    """Return sorted list of all known tanker callsign names."""
    return sorted(TANKER_CALLSIGNS)


def all_jtac() -> List[str]:
    """Return sorted list of all known JTAC callsign names."""
    return sorted(JTAC_CALLSIGNS)