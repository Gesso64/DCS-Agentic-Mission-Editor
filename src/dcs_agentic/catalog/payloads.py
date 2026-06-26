"""Named payload (loadout) presets per aircraft.

Each preset is a named weapon configuration that can be referenced from a
FlightGroup's PayloadSpec by preset_name. CLSIDs are extracted from
pydcs's weapons_data.py at load time, so they stay consistent with
whatever version of pydcs is installed.

Usage:
    from dcs_agentic.catalog import payloads

    preset = payloads.resolve("F/A-18C", "CAP A-A")
    # -> PayloadPreset with pylons=[(1, clsid, 1), ...]

    payloads.list_for_aircraft("F/A-18C")
    # -> ["CAP A-A", "STRIKE GBU-38", "SEAD HARM", ...]
"""

import re

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from dcs.weapons_data import Weapons

from ..schemas import Pylon


# ── Fuzzy weapon lookup ────────────────────────────────────────────────────
# pydcs weapons attributes use underscore-heavy names like
# "AIM_9X_Sidewinder_IR_AAM". We match on the *normalized* form
# (alphanumeric + spaces only) so callers can pass "AIM-9X", "AGM-88C HARM",
# "R-27R", or "GBU-38" and get the right attribute.

_ATTR_CACHE: Dict[str, str] = {}


def _normalize(s: str) -> str:
    """Lowercase, strip non-alphanumeric except spaces, collapse whitespace."""
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    return " ".join(s.split())


def _build_attr_cache():
    if _ATTR_CACHE:
        return
    # Build cache from the "name" field of each weapon (human-readable)
    # AND from the attribute name itself
    for name in dir(Weapons):
        if name.startswith("_"):
            continue
        val = getattr(Weapons, name)
        # Normalized attribute name as fallback
        norm_attr = _normalize(name)
        _ATTR_CACHE[norm_attr] = name
        # Normalized "name" field as primary match target
        display_name = val.get("name", "")
        norm_display = _normalize(display_name)
        if norm_display and norm_display != norm_attr:
            _ATTR_CACHE[norm_display] = name


def _find_attr(substring: str) -> str:
    """Find a Weapons attribute by case-insensitive normalized substring match."""
    _build_attr_cache()
    key = _normalize(substring)
    for cached_key, attr in _ATTR_CACHE.items():
        if key in cached_key:
            return attr
    # Last-resort: try the attribute name directly
    if hasattr(Weapons, substring):
        return substring
    raise KeyError(
        f"No weapon attribute matching '{substring}' found in pydcs Weapons. "
        f"Try a simpler substring like 'AIM-9X', 'AGM-88', or 'GBU-38'."
    )


def _clsid(substring: str) -> str:
    """Extract CLSID for the weapon matching `substring`."""
    attr = _find_attr(substring)
    return getattr(Weapons, attr)["clsid"]


# ── PayloadPreset data class ───────────────────────────────────────────────

@dataclass(frozen=True)
class PayloadPreset:
    """A named loadout configuration.

    Attributes:
        name:            Human-readable name (e.g. "CAP A-A", "STRIKE GBU-38")
        aircraft_alias:  Aircraft type alias this preset applies to
        pylons:          List of (station, clsid, quantity) tuples
        fuel:            Fuel fraction 0..1 (1.0 = full)
        description:     Short description of what this loadout is for
    """
    name: str
    aircraft_alias: str
    pylons: Tuple[Tuple[int, str, int], ...] = field(default_factory=tuple)
    fuel: float = 1.0
    description: str = ""


# ── Preset definitions ─────────────────────────────────────────────────────
# Each preset defines per-pylon weapon loads. CLSID strings are resolved
# at import time via the _clsid() fuzzy lookup.
# Station numbers are 1-based, matching pydcs / DCS editor convention.

# ──────────── F/A-18C ────────────
# Hornet pylons: 1(L-wing-A2A), 2(L-out), 3(L-in), 4(L-fuse-A2A),
#                 5(center), 6(R-fuse-A2A), 7(R-in), 8(R-out), 9(R-wing-A2A)

FA18_CAP_AA = PayloadPreset(
    name="CAP A-A",
    aircraft_alias="F/A-18C",
    pylons=(
        (1, _clsid("AIM-9X"), 1),
        (2, "{LAU-115 - AIM-120B}", 1),
        (3, "{LAU-115 - AIM-120B}", 1),
        (4, _clsid("AIM-120B"), 1),
        (6, _clsid("AIM-120B"), 1),
        (7, "{LAU-115 - AIM-120B}", 1),
        (8, "{LAU-115 - AIM-120B}", 1),
        (9, _clsid("AIM-9X"), 1),
    ),
    fuel=1.0,
    description="8x AAM (2x AIM-9X, 6x AIM-120B) — standard CAP loadout",
)

FA18_STRIKE_GBU38 = PayloadPreset(
    name="STRIKE GBU-38",
    aircraft_alias="F/A-18C",
    pylons=(
        (1, _clsid("AIM-9X"), 1),
        (2, "{LAU-115 - AIM-120B}", 1),
        (3, _clsid("BRU 55 with 2 x GBU 38"), 2),
        (4, _clsid("AIM-120B"), 1),
        (5, _clsid("FPU 8A Fuel Tank"), 1),
        (6, _clsid("AIM-120B"), 1),
        (7, _clsid("BRU 55 with 2 x GBU 38"), 2),
        (8, "{LAU-115 - AIM-120B}", 1),
        (9, _clsid("AIM-9X"), 1),
    ),
    fuel=0.8,
    description="4x GBU-38 JDAM (BRU-55 twin rack), 4x AMRAAM, 2x AIM-9X, centerline tank — precision strike",
)

FA18_SEAD_HARM = PayloadPreset(
    name="SEAD HARM",
    aircraft_alias="F/A-18C",
    pylons=(
        (1, _clsid("AIM-9X"), 1),
        (2, _clsid("AGM-88C HARM"), 1),
        (3, _clsid("AGM-88C HARM"), 1),
        (4, _clsid("AIM-120B"), 1),
        (5, _clsid("FPU_8A_FUEL_TANK"), 1),
        (6, _clsid("AIM-120B"), 1),
        (7, _clsid("AGM-88C HARM"), 1),
        (8, _clsid("AGM-88C HARM"), 1),
        (9, _clsid("AIM-9X"), 1),
    ),
    fuel=0.9,
    description="4x AGM-88C HARM, 2x AMRAAM, 2x AIM-9X, centerline tank — SEAD/DEAD escort",
)

FA18_CAS_MAVERICK = PayloadPreset(
    name="CAS Maverick",
    aircraft_alias="F/A-18C",
    pylons=(
        (1, _clsid("AIM-9X"), 1),
        (2, _clsid("AGM-65E"), 1),
        (3, _clsid("AGM-65E"), 1),
        (4, _clsid("AIM-120B"), 1),
        (5, _clsid("FPU_8A_FUEL_TANK"), 1),
        (6, _clsid("AIM-120B"), 1),
        (7, _clsid("AGM-65E"), 1),
        (8, _clsid("AGM-65E"), 1),
        (9, _clsid("AIM-9X"), 1),
    ),
    fuel=1.0,
    description="4x AGM-65E Laser Maverick, 2x AMRAAM, 2x AIM-9X, centerline tank — CAS/precision strike",
)

FA18_ANTISHIP_HARPOON = PayloadPreset(
    name="ANTISHIP Harpoon",
    aircraft_alias="F/A-18C",
    pylons=(
        (1, _clsid("AIM-9X"), 1),
        (2, _clsid("AGM-84A Harpoon"), 1),
        (3, _clsid("FPU_8A_FUEL_TANK"), 1),
        (4, _clsid("AIM-120B"), 1),
        (5, _clsid("FPU_8A_FUEL_TANK"), 1),
        (6, _clsid("AIM-120B"), 1),
        (7, _clsid("FPU_8A_FUEL_TANK"), 1),
        (8, _clsid("AGM-84A Harpoon"), 1),
        (9, _clsid("AIM-9X"), 1),
    ),
    fuel=1.0,
    description="2x AGM-84A Harpoon, 2x AMRAAM, 2x AIM-9X, 3x fuel tanks — antiship strike",
)

# ──────────── F-16C ────────────

F16_CAP_AA = PayloadPreset(
    name="CAP A-A",
    aircraft_alias="F-16C",
    pylons=(
        (1, _clsid("AIM-9X"), 1),
        (2, _clsid("AIM-120B"), 1),
        (3, _clsid("AIM-120B"), 1),
        (4, _clsid("AIM-120B"), 1),
        (6, _clsid("AIM-120B"), 1),
        (7, _clsid("AIM-120B"), 1),
        (8, _clsid("AIM-120B"), 1),
        (9, _clsid("AIM-9X"), 1),
    ),
    fuel=1.0,
    description="8x AAM (2x AIM-9X, 6x AIM-120B) — standard CAP",
)

F16_STRIKE_GBU38 = PayloadPreset(
    name="STRIKE GBU-38",
    aircraft_alias="F-16C",
    pylons=(
        (1, _clsid("AIM-9X"), 1),
        (3, _clsid("GBU-38"), 1),
        (4, _clsid("GBU-38"), 1),
        (7, _clsid("GBU-38"), 1),
        (8, _clsid("GBU-38"), 1),
        (9, _clsid("AIM-9X"), 1),
    ),
    fuel=0.9,
    description="4x GBU-38 JDAM, 2x AIM-9X — precision strike",
)

F16_CAS_LGB = PayloadPreset(
    name="CAS LGB",
    aircraft_alias="F-16C",
    pylons=(
        (1, _clsid("AIM-9X"), 1),
        (3, _clsid("GBU-12"), 1),
        (4, _clsid("GBU-12"), 1),
        (7, _clsid("GBU-12"), 1),
        (8, _clsid("GBU-12"), 1),
        (9, _clsid("AIM-9X"), 1),
    ),
    fuel=1.0,
    description="4x GBU-12 LGB, 2x AIM-9X — CAS with laser-guided bombs",
)

# ──────────── F-15C ────────────

F15C_CAP_AA = PayloadPreset(
    name="CAP A-A",
    aircraft_alias="F-15C",
    pylons=(
        (1, _clsid("AIM-120B"), 1),
        (2, _clsid("AIM-9M"), 1),
        (3, _clsid("AIM-120B"), 1),
        (4, _clsid("AIM-120B"), 1),
        (5, _clsid("AIM-120B"), 1),
        (6, _clsid("AIM-120B"), 1),
        (7, _clsid("AIM-120B"), 1),
        (8, _clsid("AIM-9M"), 1),
        (9, _clsid("AIM-120B"), 1),
    ),
    fuel=1.0,
    description="8x AIM-120B, 2x AIM-9M — maximum A2A loadout",
)

# ──────────── A-10C ────────────

A10C_CAS = PayloadPreset(
    name="CAS",
    aircraft_alias="A-10C",
    pylons=(
        (2, _clsid("AIM-9M"), 1),
        (4, _clsid("AGM-65D"), 1),
        (5, _clsid("AGM-65D"), 1),
        (6, _clsid("GBU-12"), 1),
        (7, _clsid("GBU-12"), 1),
        (8, _clsid("AGM-65D"), 1),
        (9, _clsid("AGM-65D"), 1),
        (10, _clsid("ALQ-131"), 1),
        (11, _clsid("AIM-9M"), 1),
    ),
    fuel=1.0,
    description="4x AGM-65D Maverick, 2x GBU-12 LGB, 2x AIM-9M, ECM pod",
)

# ──────────── AH-64D ────────────

AH64D_CAS = PayloadPreset(
    name="CAS Hellfire",
    aircraft_alias="AH-64D",
    pylons=(
        (1, _clsid("AGM-114K"), 4),
        (3, _clsid("AGM-114K"), 4),
    ),
    fuel=1.0,
    description="8x AGM-114K Hellfire — standard CAS loadout",
)

# ──────────── Su-27 ────────────

SU27_CAP_AA = PayloadPreset(
    name="CAP A-A",
    aircraft_alias="Su-27",
    pylons=(
        (1, _clsid("R-27R"), 1),
        (2, _clsid("R-73"), 1),
        (3, _clsid("R-27R"), 1),
        (4, _clsid("R-27R"), 1),
        (6, _clsid("R-27R"), 1),
        (7, _clsid("R-27R"), 1),
        (8, _clsid("R-73"), 1),
        (9, _clsid("R-73"), 1),
    ),
    fuel=1.0,
    description="6x R-27R, 3x R-73 — standard Su-27 A2A loadout",
)

# ──────────── MiG-29S ────────────

MIG29S_CAP_AA = PayloadPreset(
    name="CAP A-A",
    aircraft_alias="MiG-29S",
    pylons=(
        (1, _clsid("R-77"), 1),
        (2, _clsid("R-73"), 1),
        (3, _clsid("R-77"), 1),
        (4, _clsid("R-77"), 1),
        (6, _clsid("R-77"), 1),
        (7, _clsid("R-77"), 1),
        (8, _clsid("R-73"), 1),
    ),
    fuel=1.0,
    description="6x R-77, 2x R-73 — standard MiG-29S A2A loadout",
)

# ──────────── Ka-50 ────────────

KA50_CAS = PayloadPreset(
    name="CAS",
    aircraft_alias="Ka-50",
    pylons=(
        (1, _clsid("Vikhr"), 6),
        (2, _clsid("Vikhr"), 6),
        (3, _clsid("S-13"), 1),
        (4, _clsid("S-13"), 1),
    ),
    fuel=1.0,
    description="12x Vikhr ATGM, 2x S-13 rocket pods",
)


# ─── Registry ───────────────────────────────────────────────────────────────
# Keyed by (aircraft_alias, preset_name)
_PRESETS: Dict[Tuple[str, str], PayloadPreset] = {}

_all_presets = [
    FA18_CAP_AA, FA18_STRIKE_GBU38, FA18_SEAD_HARM, FA18_CAS_MAVERICK,
    FA18_ANTISHIP_HARPOON,
    F16_CAP_AA, F16_STRIKE_GBU38, F16_CAS_LGB,
    F15C_CAP_AA,
    A10C_CAS,
    AH64D_CAS,
    SU27_CAP_AA,
    MIG29S_CAP_AA,
    KA50_CAS,
]


def _build():
    if _PRESETS:
        return
    for preset in _all_presets:
        key = (preset.aircraft_alias, preset.name)
        _PRESETS[key] = preset


# ─── Public API ─────────────────────────────────────────────────────────────

def resolve(aircraft_alias: str, preset_name: str) -> PayloadPreset:
    """Look up a payload preset by aircraft type and preset name.

    Raises ValueError if not found.
    """
    _build()
    key = (aircraft_alias, preset_name)
    if key not in _PRESETS:
        raise ValueError(
            f"No payload preset '{preset_name}' for aircraft '{aircraft_alias}'. "
            f"Available: {list_for_aircraft(aircraft_alias) or 'no presets for this aircraft'}"
        )
    return _PRESETS[key]


def list_for_aircraft(aircraft_alias: str) -> List[str]:
    """Return all preset names available for a given aircraft, sorted."""
    _build()
    return sorted(
        name for (alias, name) in _PRESETS
        if alias == aircraft_alias
    )


def all_presets() -> Dict[Tuple[str, str], PayloadPreset]:
    """Return the full registry."""
    _build()
    return dict(_PRESETS)


def list_aircraft_with_presets() -> List[str]:
    """Return all aircraft aliases that have at least one preset."""
    _build()
    return sorted(set(alias for (alias, _) in _PRESETS))