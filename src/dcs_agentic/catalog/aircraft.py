"""Aircraft (planes + helicopters) alias map and capability metadata.

Two kinds of aliases:
  - real        — pydcs has the airframe; alias resolves to that class
  - proxy       — pydcs lacks the airframe; alias resolves to a stand-in.
                  Callers should check is_proxy() and warn via the
                  assembly report so users notice the substitution.

Metadata roles:
  - cap / intercept / sweep : air superiority
  - strike / ground_attack  : air-to-ground bombing
  - sead / dead             : suppression / destruction of air defences
  - cas                     : close air support
  - antiship                : maritime strike
  - recon                   : reconnaissance
  - awacs                   : airborne early warning
  - refueling / tanker      : aerial refuelling
  - transport               : cargo / troop transport
  - helicopter              : rotary-wing (any role)
  - trainer                 : two-seat training aircraft
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import dcs.helicopters as _helicopters
import dcs.planes as _planes


# ─── AircraftInfo ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AircraftInfo:
    """Structured metadata for an aircraft type.

    Attributes:
        alias:            User-facing alias, e.g. "F/A-18C"
        pydcs_class:      The pydcs Plane or Helicopter subclass
        pydcs_attr:       Attribute name on dcs.planes or dcs.helicopters
        role:             Tuple of role tags, e.g. ("multirole", "cap", "strike")
        is_player_flyable: True if this is a flyable module in DCS
        is_helicopter:    True if rotary-wing
        is_proxy:         True if this alias substitutes a different airframe
        proxy_target:     If is_proxy, the pydcs attr name substituted in
        default_country:  Reasonable default home country
        combat_radius_km: Approximate combat radius in km (for fuel-range validation)
        notes:            Additional context
    """
    alias: str
    pydcs_class: type
    pydcs_attr: str
    role: Tuple[str, ...]
    is_player_flyable: bool = False
    is_helicopter: bool = False
    is_proxy: bool = False
    proxy_target: str = ""
    default_country: str = "USA"
    combat_radius_km: int = 500
    notes: str = ""


# ─── Alias map (attribute name per pydcs) ───────────────────────────────────
# NOTE: Keep these dicts as the canonical alias→attr map.
# AircraftInfo entries below derive their pydcs_attr from these.

_PLANE_ALIASES = {
    "FA-18C": "FA_18C_hornet", "F/A-18C": "FA_18C_hornet",
    "FA-18A": "F_A_18A",
    "F-15C": "F_15C", "F-15E": "F_15E",
    "F-16C": "F_16C_50", "F-16A": "F_16A",
    "F-14B": "F_14B", "F-14A": "F_14A",
    "F-5E": "F_5E_3", "F-4E": "F_4E",
    "F-86F": "F_86F_Sabre", "F-117A": "F_117A",
    "A-10C": "A_10C", "A-10C-2": "A_10C_2", "A-10A": "A_10A",
    "A-20G": "A_20G",
    "AV-8B": "AV8BNA",
    "AJS-37": "AJS37",
    "M-2000C": "M_2000C",
    "MiG-21Bis": "MiG_21Bis",
    "MiG-29A": "MiG_29A", "MiG-29S": "MiG_29S",
    "Su-25": "Su_25", "Su-25T": "Su_25T",
    "Su-27": "Su_27", "Su-30": "Su_30", "Su-33": "Su_33",
    "Su-34": "Su_34",
    "JF-17": "JF_17", "J-11A": "J_11A",
    "Hawk": "Hawk",
    "L-39C": "L_39C", "L-39ZA": "L_39ZA",
    "C-101CC": "C_101CC", "C-101EB": "C_101EB",
    "P-51D": "P_51D",
    "Spitfire-LFIX": "SpitfireLFMkIX",
    "Bf-109K": "Bf_109K_4",
    "FW-190A8": "FW_190A8", "FW-190D9": "FW_190D9",
    "B-1B": "B_1B", "B-17G": "B_17G", "B-52H": "B_52H",
    "Ju-88A4": "Ju_88A4",
    "C-130": "C_130", "C-17A": "C_17A", "C-47": "C_47",
    "H-6J": "H_6J",
    "KC-130": "KC130", "KC-135": "KC_135", "KC-135MPRS": "KC135MPRS",
    "E-2C": "E_2C", "E-3A": "E_3A", "KJ-2000": "KJ_2000",
    "A-50": "A_50",
    "IL-76": "IL_76MD", "IL-78": "IL_78M",
    "Tu-160": "Tu_160",
    "An-26": "An_26B", "An-30": "An_30M",
    "I-16": "I_16",
}

_PROXY_ALIASES = {
    "Su-35": "Su_27",
    "Su-57": "Su_30",
}

_HELI_ALIASES = {
    "Ka-50": "Ka_50",
    "Mi-8": "Mi_8MT",
    "Mi-24": "Mi_24V",
    "Mi-24P": "Mi_24P",
    "Mi-26": "Mi_26",
    "Mi-28": "Mi_28N",
    "AH-64D": "AH_64D",
    "AH-1W": "AH_1W",
    "UH-1H": "UH_1H",
    "SH-60": "SH_60B",
    "CH-47": "CH_47D",
    "UH-60": "UH_60A",
    "SA-342": "SA342L",
    "SA-342L": "SA342L",
    "SA-342M": "SA342M",
    "SA-342Mistral": "SA342Mistral",
    "OH-58D": "OH_58D",
    "Ka-27": "Ka_27",
    "CH-53E": "CH_53E",
}


# ─── Lazy-built maps ───────────────────────────────────────────────────────

_MAP: Dict[str, type] = {}               # alias → pydcs class
_INFO: Dict[str, AircraftInfo] = {}       # alias → AircraftInfo


def _build():
    if _MAP:
        return
    _register_plane_aliases()
    _register_proxy_aliases()
    _register_heli_aliases()
    _build_info()


def _register_plane_aliases():
    for alias, attr in _PLANE_ALIASES.items():
        if hasattr(_planes, attr):
            _MAP[alias] = getattr(_planes, attr)


def _register_proxy_aliases():
    for alias, attr in _PROXY_ALIASES.items():
        if hasattr(_planes, attr):
            _MAP[alias] = getattr(_planes, attr)


def _register_heli_aliases():
    for alias, attr in _HELI_ALIASES.items():
        if hasattr(_helicopters, attr):
            _MAP[alias] = getattr(_helicopters, attr)


def _build_info():
    """Build AircraftInfo entries for every alias.

    Derives pydcs_attr from the alias dicts and maps role tags and
    player-flyable status per aircraft type.
    """
    # ── Role mapping per alias ──────────────────────────────────────────
    # (alias, (roles...), is_flyable, default_country, combat_radius_km, notes)
    _INFO_DATA: Dict[str, tuple] = {
        # === Player-flyable ===
        "F/A-18C": (
            ("multirole", "cap", "strike", "sead", "cas", "antiship"),
            True, "USA", 720, "Full-fidelity multirole; AGM-88C, Harpoon, JDAM, Maverick capable",
        ),
        "FA-18C": (
            ("multirole", "cap", "strike", "sead", "cas", "antiship"),
            True, "USA", 720, "Alternative spelling of F/A-18C",
        ),
        "F-16C": (
            ("multirole", "cap", "strike", "sead"),
            True, "USA", 680, "Full-fidelity multirole; HARM, JDAM, Maverick capable",
        ),
        "F-14B": (
            ("cap", "intercept"),
            True, "USA", 800, "Full-fidelity fleet defender; Phoenix/ Sparrow/ Sidewinder",
        ),
        "F-15E": (
            ("strike", "ground_attack"),
            True, "USA", 600, "Full-fidelity Strike Eagle",
        ),
        "A-10C": (
            ("cas", "ground_attack"),
            True, "USA", 450, "Full-fidelity CAS platform; GAU-8, Maverick, JDAM, LGBs",
        ),
        "A-10C-2": (
            ("cas", "ground_attack"),
            True, "USA", 450, "Full-fidelity A-10C II variant",
        ),
        "AV-8B": (
            ("strike", "cas"),
            True, "USA", 500, "Full-fidelity V/STOL Harrier II",
        ),
        "MiG-21Bis": (
            ("cap", "intercept"),
            True, "Russia", 400, "Full-fidelity Cold War interceptor",
        ),
        "MiG-29S": (
            ("cap", "intercept"),
            True, "Russia", 600, "Full-fidelity Fulcrum; R-77 capable",
        ),
        "Su-27": (
            ("cap", "intercept"),
            True, "Russia", 800, "Full-fidelity Flanker",
        ),
        "Su-33": (
            ("cap", "intercept"),
            True, "Russia", 800, "Full-fidelity naval Flanker",
        ),
        "Su-25T": (
            ("cas", "strike"),
            True, "Russia", 400, "Full-fidelity Frogfoot; SEAD capable",
        ),
        "Su-25": (
            ("cas", "ground_attack"),
            True, "Russia", 400, "Frogfoot; low-fidelity cockpit but AFM",
        ),
        "JF-17": (
            ("multirole", "cap", "strike", "sead"),
            True, "China", 600, "Full-fidelity Thunder; good CL-10 SD-10 loadout",
        ),
        "Ka-50": (
            ("helicopter", "cas"),
            True, "Russia", 250, "Full-fidelity Black Shark; single-seat attack helo",
        ),
        "AH-64D": (
            ("helicopter", "cas"),
            True, "USA", 300, "Full-fidelity Apache; Hellfire, rockets, Stinger",
        ),
        "Mi-8": (
            ("helicopter", "transport"),
            True, "Russia", 200, "Full-fidelity Hip; cargo/troop transport",
        ),
        "Mi-24P": (
            ("helicopter", "cas", "transport"),
            True, "Russia", 250, "Full-fidelity Hind; attack + troop transport",
        ),
        "UH-1H": (
            ("helicopter", "transport"),
            True, "USA", 200, "Full-fidelity Huey; utility transport",
        ),
        "SA-342": (
            ("helicopter", "cas"),
            True, "France", 200, "Full-fidelity Gazelle; HOT missile or Mistral",
        ),
        "F-5E": (
            ("cap", "intercept"),
            True, "USA", 400, "Full-fidelity Tiger II; economical fighter",
        ),
        "M-2000C": (
            ("cap", "intercept"),
            True, "France", 600, "Full-fidelity Mirage 2000C",
        ),
        "AJS-37": (
            ("strike", "antiship"),
            True, "Sweden", 500, "Full-fidelity Viggen; strike/ recon",
        ),
        "L-39C": (
            ("trainer", "cas"),
            True, "Russia", 300, "Full-fidelity Albatros; trainer/light attack",
        ),
        "L-39ZA": (
            ("trainer", "cas"),
            True, "Russia", 300, "Full-fidelity Albatros; armed variant",
        ),
        "C-101CC": (
            ("trainer", "cas"),
            True, "Spain", 300, "Full-fidelity; armed variant",
        ),
        "C-101EB": (
            ("trainer",),
            True, "Spain", 300, "Full-fidelity; unarmed trainer",
        ),
        "P-51D": (
            ("cap", "strike"),
            True, "USA", 250, "Full-fidelity Mustang; WWII",
        ),
        "Spitfire-LFIX": (
            ("cap", "strike"),
            True, "UK", 200, "Full-fidelity Spitfire; WWII",
        ),
        "Bf-109K": (
            ("cap", "intercept"),
            True, "Germany", 200, "Full-fidelity 109; WWII",
        ),
        "FW-190A8": (
            ("cap", "strike"),
            True, "Germany", 250, "Full-fidelity Wurger; WWII",
        ),
        "FW-190D9": (
            ("cap", "intercept"),
            True, "Germany", 300, "Full-fidelity Dora; WWII",
        ),
        "I-16": (
            ("cap", "intercept"),
            True, "Russia", 200, "Full-fidelity Ishak; WWII",
        ),
        # Additional flyable helis
        "AH-1W": (
            ("helicopter", "cas"),
            True, "USA", 250, "Full-fidelity Super Cobra",
        ),
        "SA-342L": (
            ("helicopter", "cas"),
            True, "France", 200, "Full-fidelity Gazelle",
        ),
        "SA-342M": (
            ("helicopter", "cas"),
            True, "France", 200, "Full-fidelity Gazelle; HOT missile",
        ),
        "SA-342Mistral": (
            ("helicopter", "cas"),
            True, "France", 200, "Full-fidelity Gazelle; Mistral AAM",
        ),
        # === Non-flyable (AI-only) ===
        "F-15C": (
            ("cap", "intercept"),
            False, "USA", 800, "AI-only Eagle; excellent A2A platform",
        ),
        "F-117A": (
            ("strike",),
            False, "USA", 500, "AI-only Nighthawk; stealth strike",
        ),
        "B-1B": (
            ("strike", "ground_attack"),
            False, "USA", 1200, "AI-only Lancer; heavy bomber",
        ),
        "B-52H": (
            ("strike", "ground_attack"),
            False, "USA", 1400, "AI-only Stratofortress; heavy bomber",
        ),
        "B-17G": (
            ("strike", "ground_attack"),
            False, "USA", 800, "AI-only Flying Fortress; WWII bomber",
        ),
        "Su-30": (
            ("cap", "strike"),
            False, "Russia", 800, "AI-only Flanker-C; multirole",
        ),
        "Su-34": (
            ("strike", "sead"),
            False, "Russia", 800, "AI-only Fullback; strike/SEAD",
        ),
        "Tu-160": (
            ("strike", "ground_attack"),
            False, "Russia", 2000, "AI-only Blackjack; strategic bomber",
        ),
        "E-2C": (
            ("awacs",),
            False, "USA", 500, "AI-only Hawkeye; AEW&C",
        ),
        "E-3A": (
            ("awacs",),
            False, "USA", 800, "AI-only Sentry; AEW&C",
        ),
        "KJ-2000": (
            ("awacs",),
            False, "China", 600, "AI-only; AEW&C",
        ),
        "A-50": (
            ("awacs",),
            False, "Russia", 700, "AI-only Mainstay; AEW&C",
        ),
        "KC-135": (
            ("refueling", "tanker"),
            False, "USA", 1200, "AI-only Stratotanker",
        ),
        "KC-135MPRS": (
            ("refueling", "tanker"),
            False, "USA", 1200, "AI-only; MPRS-equipped",
        ),
        "KC-130": (
            ("refueling", "tanker"),
            False, "USA", 800, "AI-only Hercules tanker",
        ),
        "IL-78": (
            ("refueling", "tanker"),
            False, "Russia", 1000, "AI-only Midas tanker",
        ),
        "C-130": (
            ("transport",),
            False, "USA", 1500, "AI-only Hercules",
        ),
        "C-17A": (
            ("transport",),
            False, "USA", 2000, "AI-only Globemaster III",
        ),
        "C-47": (
            ("transport",),
            False, "USA", 800, "AI-only Skytrain; WWII",
        ),
        "An-26": (
            ("transport",),
            False, "Russia", 800, "AI-only Curl",
        ),
        "An-30": (
            ("recon", "transport"),
            False, "Russia", 800, "AI-only Clank; reconnaissance",
        ),
        "IL-76": (
            ("transport",),
            False, "Russia", 1800, "AI-only Candid",
        ),
        "MiG-29A": (
            ("cap", "intercept"),
            False, "Russia", 500, "AI-only Fulcrum-A",
        ),
        "Ju-88A4": (
            ("strike", "ground_attack"),
            False, "Germany", 400, "AI-only; WWII bomber",
        ),
        "A-20G": (
            ("strike", "ground_attack"),
            False, "USA", 500, "AI-only Havoc; WWII attack bomber",
        ),
        # Helicopters (non-flyable)
        "Mi-24": (
            ("helicopter", "cas"),
            False, "Russia", 250, "AI-only Hind-D",
        ),
        "Mi-26": (
            ("helicopter", "transport"),
            False, "Russia", 300, "AI-only Halo; heavy lift",
        ),
        "Mi-28": (
            ("helicopter", "cas"),
            False, "Russia", 250, "AI-only Havoc; attack helicopter",
        ),
        "CH-47": (
            ("helicopter", "transport"),
            False, "USA", 300, "AI-only Chinook",
        ),
        "SH-60": (
            ("helicopter", "antiship"),
            False, "USA", 200, "AI-only Seahawk; naval utility",
        ),
        "UH-60": (
            ("helicopter", "transport"),
            False, "USA", 200, "AI-only Black Hawk",
        ),
        "Ka-27": (
            ("helicopter", "antiship"),
            False, "Russia", 200, "AI-only Helix; naval ASW",
        ),
        "CH-53E": (
            ("helicopter", "transport"),
            False, "USA", 300, "AI-only Sea Stallion; heavy lift",
        ),
        "OH-58D": (
            ("helicopter", "recon", "scout"),
            False, "USA", 200, "AI-only Kiowa Warrior; scout",
        ),
        "SA-342L": (
            ("helicopter", "cas"),
            False, "France", 200, "AI-only Gazelle; light attack",
        ),
        "SA-342M": (
            ("helicopter", "cas"),
            False, "France", 200, "AI-only Gazelle; HOT missile",
        ),
        "SA-342Mistral": (
            ("helicopter", "cas"),
            False, "France", 200, "AI-only Gazelle; Mistral AAM",
        ),
        # Proxies
        "Su-35": (
            ("cap", "intercept"),
            False, "Russia", 900, "PROXY: Su-27 stands in for Su-35",
        ),
        "Su-57": (
            ("cap", "strike"),
            False, "Russia", 800, "PROXY: Su-30 stands in for Su-57",
        ),
    }

    for alias in _PLANE_ALIASES:
        if alias not in _INFO_DATA or alias not in _MAP:
            continue
        info = _INFO_DATA[alias]
        roles, flyable, country, radius, notes = info
        is_proxy_val = alias in _PROXY_ALIASES
        _INFO[alias] = AircraftInfo(
            alias=alias,
            pydcs_class=_MAP[alias],
            pydcs_attr=_PLANE_ALIASES.get(alias, ""),
            role=roles,
            is_player_flyable=flyable,
            is_proxy=is_proxy_val,
            proxy_target=_PROXY_ALIASES.get(alias, ""),
            default_country=country,
            combat_radius_km=radius,
            notes=notes,
        )

    for alias in _HELI_ALIASES:
        if alias not in _INFO_DATA or alias not in _MAP:
            continue
        info = _INFO_DATA[alias]
        roles, flyable, country, radius, notes = info
        is_proxy_val = alias in _PROXY_ALIASES
        _INFO[alias] = AircraftInfo(
            alias=alias,
            pydcs_class=_MAP[alias],
            pydcs_attr=_HELI_ALIASES.get(alias, ""),
            role=roles,
            is_player_flyable=flyable,
            is_helicopter=True,
            is_proxy=is_proxy_val,
            proxy_target=_PROXY_ALIASES.get(alias, ""),
            default_country=country,
            combat_radius_km=radius,
            notes=notes,
        )


# ─── Public API (preserved + extended) ──────────────────────────────────────

def resolve(name: str):
    """Return the pydcs class for `name`. Raises ValueError if unknown.

    Tries the alias map first, then a sanitized direct lookup on
    dcs.planes (no helicopter direct fallback to avoid surprises).
    """
    _build()
    if name in _MAP:
        return _MAP[name]
    sanitized = name.replace("-", "_").replace("/", "_")
    if hasattr(_planes, sanitized):
        return getattr(_planes, sanitized)
    raise ValueError(
        f"Unknown aircraft type: {name}. "
        f"Known: {sorted(_MAP)[:20]}... ({len(_MAP)} total)"
    )


def is_proxy(name: str) -> bool:
    """True if `name` is substituted with a different airframe in pydcs."""
    _build()
    return name in _PROXY_ALIASES


def proxy_target(name: str) -> str:
    """pydcs attr name being substituted in, e.g. 'Su_27' for 'Su-35'."""
    return _PROXY_ALIASES.get(name, "")


def all_aliases() -> List[str]:
    _build()
    return sorted(_MAP)


def list_by_role(role_tag: str) -> List[str]:
    """Return all aliases matching a given role tag.

    Role tags: cap, intercept, sweep, strike, ground_attack, sead, dead,
    cas, antiship, recon, awacs, refueling, tanker, transport, helicopter,
    trainer, multirole.
    """
    _build()
    return sorted(
        alias for alias, info in _INFO.items()
        if role_tag in info.role
    )


def get_info(alias: str) -> Optional[AircraftInfo]:
    """Return the AircraftInfo for a given alias, or None if unknown."""
    _build()
    return _INFO.get(alias)


def all_flyable() -> List[str]:
    """Return aliases for all player-flyable aircraft."""
    _build()
    return sorted(
        alias for alias, info in _INFO.items()
        if info.is_player_flyable
    )


def list_suitable_for_task(task: str) -> List[str]:
    """Return aliases suitable for a specific task string.

    Task string is case-insensitive and matches against role tags.
    Common tasks: cap, strike, sead, cas, antiship, awacs, refueling,
    transport, recon.
    """
    return list_by_role(task.lower())