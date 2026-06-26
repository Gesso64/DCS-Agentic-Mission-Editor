"""Vehicle (air defence, artillery, armor) alias map with role metadata.

Each alias resolves to a pydcs vehicle class. Structured metadata
categorises each vehicle by role (sam, aaa, ewr, artillery, armor,
infantry, etc.) for agent lookup tools.

Usage:
    from dcs_agentic.catalog import vehicles

    vehicles.resolve("SA-11-LN")     # -> pydcs class
    vehicles.list_by_role("sam")     # -> ["SA-2-LN", "SA-3-LN", ...]
    vehicles.get_info("M1-Abrams")   # -> VehicleInfo(...)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import dcs.vehicles as _vehicles


# ─── VehicleInfo ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class VehicleInfo:
    """Structured metadata for a vehicle type.

    Attributes:
        alias:       User-facing alias, e.g. "SA-11-LN", "M1-Abrams"
        pydcs_attr:  Attribute name on the pydcs vehicle container class
        role:        Tuple of role tags, e.g. ("sam", "ln")
        country:     Default home country
        notes:       Additional context
    """
    alias: str
    pydcs_attr: str
    role: Tuple[str, ...]
    notes: str = ""


# ─── Air Defence aliases with role metadata ─────────────────────────────────
_AD_ALIASES: Dict[str, Tuple[str, ...]] = {
    # SAM launchers
    "SA-2-LN":    ("sam", "ln", "mrsam", "strategic"),      # S-75 Dvina — long-range, strategic
    "SA-3-LN":    ("sam", "ln", "mrsam"),                   # S-125 Neva — medium-range
    "SA-6-LN":    ("sam", "ln", "mrsam"),                   # Kub — mobile medium-range
    "SA-8":       ("sam", "shorad"),                         # Osa — mobile short-range
    "SA-9":       ("sam", "shorad"),                         # Strela-1 — mobile short-range
    "SA-10-LN":   ("sam", "ln", "lrsam", "strategic"),       # S-300PS — long-range strategic
    "SA-11-LN":   ("sam", "ln", "mrsam"),                   # Buk — mobile medium-range
    "SA-15":      ("sam", "shorad"),                         # Tor — mobile short-range
    "SA-17":      ("sam", "ln", "mrsam"),                   # Buk-M1 — mobile medium-range
    "SA-19":      ("sam", "aaa", "shorad"),                 # Tunguska — SAM + AAA hybrid
    "SA-13":      ("sam", "shorad"),                         # Strela-10M — mobile short-range
    "SA-18":      ("sam", "infantry"),                      # Igla MANPADS
    "SA-24":      ("sam", "infantry"),                      # Igla-S MANPADS (insurgent)
    "Hawk-LN":    ("sam", "ln", "mrsam"),                   # MIM-23 Hawk — medium-range
    "Patriot-LN": ("sam", "ln", "lrsam", "strategic"),       # MIM-104 — long-range
    "Roland-ADS": ("sam", "shorad"),                         # Roland — mobile short-range
    "NASAMS-LN":  ("sam", "ln", "mrsam"),                   # NASAMS — medium-range
    "Avenger":    ("sam", "shorad"),                         # M1097 Avenger — short-range
    "Chaparral":  ("sam", "shorad"),                         # M48 Chaparral — short-range
    "Rapier-LN":  ("sam", "ln", "shorad"),                  # Rapier — short-range
    "HQ-7-LN":    ("sam", "ln", "shorad"),                   # HQ-7 — short-range
    "S-200":      ("sam", "ln", "lrsam", "strategic"),       # S-200 Angara — very-long-range

    # SAM search / tracking radars
    "SA-2-TR":    ("sam", "radar", "tracking"),
    "SA-2-SR":    ("sam", "radar", "search"),  # Not in aliases yet but keeping for reference
    "SA-3-SR":    ("sam", "radar", "search"),
    "SA-3-TR":    ("sam", "radar", "tracking"),
    "SA-6-SR":    ("sam", "radar", "search"),  # 1S91 — search + track combined
    "SA-10-SR":   ("sam", "radar", "search"),
    "SA-10-TR":   ("sam", "radar", "tracking"),
    "SA-10-CP":   ("sam", "command"),
    "SA-11-SR":   ("sam", "radar", "search"),
    "SA-11-CP":   ("sam", "command"),
    "Hawk-SR":    ("sam", "radar", "search"),
    "Hawk-TR":    ("sam", "radar", "tracking"),
    "Hawk-PCP":   ("sam", "command"),
    "Hawk-CWAR":  ("sam", "radar", "search"),
    "Patriot-CP":      ("sam", "command"),
    "Patriot-SR":      ("sam", "radar", "search"),
    "Patriot-TR":      ("sam", "radar", "tracking"),
    "Patriot-STR":     ("sam", "radar", "search"),
    "Patriot-AMG":     ("sam", "radar", "tracking"),  # Patriot AMG is actually TR
    "Roland-Radar":    ("sam", "radar"),
    "NASAMS-Radar":    ("sam", "radar", "search"),
    "NASAMS-CP":       ("sam", "command"),
    "Rapier-Radar":    ("sam", "radar", "tracking"),
    "Rapier-Optical":  ("sam", "optical", "tracking"),
    "HQ-7-SR":         ("sam", "radar", "search"),

    # AAA (anti-aircraft artillery)
    "ZSU-23-4":   ("aaa", "shorad", "mobile"),
    "ZSU-57-2":   ("aaa", "mobile"),
    "Gepard":     ("aaa", "shorad", "mobile"),
    "Vulcan":     ("aaa", "shorad"),

    # EWR (early warning radar)
    "Dog-Ear":    ("ewr", "radar"),
    "FPS-117":    ("ewr", "radar"),   # Fixed long-range radar
    "FPS-117-Dome": ("ewr", "radar"),
    "1L13-EWR":   ("ewr", "radar"),
    "55G6-EWR":   ("ewr", "radar"),

    # Support
    "Generator":  ("support", "power"),
    "SA-18":      ("sam", "infantry"),     # duplicated intentionally for role lookups
    "SA-24":      ("sam", "infantry"),
}

# Need to figure out the pydcs attr names for lookup
_AD_ATTR_MAP: Dict[str, str] = {
    "SA-2-LN": "S_75M_Volhov", "SA-2-TR": "SNR_75V",
    "SA-3-LN": "X_5p73_s_125_ln", "SA-3-SR": "P_19_s_125_sr", "SA-3-TR": "Snr_s_125_tr",
    "SA-6-SR": "Kub_1S91_str", "SA-6-LN": "Kub_2P25_ln",
    "SA-8": "Osa_9A33_ln",
    "SA-9": "Strela_1_9P31",
    "SA-10-SR": "S_300PS_64H6E_sr", "SA-10-TR": "S_300PS_40B6M_tr",
    "SA-10-CP": "S_300PS_54K6_cp", "SA-10-LN": "S_300PS_5P85C_ln",
    "SA-11-SR": "SA_11_Buk_SR_9S18M1", "SA-11-CP": "SA_11_Buk_CC_9S470M1",
    "SA-11-LN": "SA_11_Buk_LN_9A310M1",
    "SA-15": "Tor_9A331",
    "SA-19": "X_2S6_Tunguska",
    "SA-13": "Strela_10M3", "SA-17": "SA_11_Buk_LN_9A310M1",
    "SA-18": "SA_18_Igla_comm", "SA-24": "Igla_manpad_INS",
    "ZSU-23-4": "ZSU_23_4_Shilka", "ZSU-57-2": "ZSU_57_2",
    "Gepard": "Gepard", "Vulcan": "Vulcan",
    "Hawk-LN": "Hawk_ln", "Hawk-SR": "Hawk_sr", "Hawk-TR": "Hawk_tr",
    "Hawk-PCP": "Hawk_pcp", "Hawk-CWAR": "Hawk_cwar",
    "Patriot-CP": "Patriot_cp", "Patriot-LN": "Patriot_ln",
    "Patriot-SR": "Patriot_ECS",
    "Patriot-TR": "Patriot_AMG", "Patriot-STR": "Patriot_str",
    "Roland-ADS": "Roland_ADS", "Roland-Radar": "Roland_Radar",
    "NASAMS-CP": "NASAMS_Command_Post", "NASAMS-LN": "NASAMS_LN_B",
    "NASAMS-Radar": "NASAMS_Radar_MPQ64F1",
    "Avenger": "M1097_Avenger", "Chaparral": "M48_Chaparral",
    "Rapier-LN": "Rapier_fsa_launcher",
    "Rapier-Radar": "Rapier_fsa_blindfire_radar",
    "Rapier-Optical": "Rapier_fsa_optical_tracker_unit",
    "HQ-7-LN": "HQ_7_LN_SP", "HQ-7-SR": "HQ_7_STR_SP",
    "S-200": "S_200_Launcher",
    "Dog-Ear": "Dog_Ear_radar", "FPS-117": "FPS_117", "FPS-117-Dome": "FPS_117_Dome",
    "1L13-EWR": "X_1L13_EWR", "55G6-EWR": "X_55G6_EWR",
    "Generator": "Generator_5i57",
}

_ARTILLERY_ATTR_MAP: Dict[str, str] = {
    "M-109": "M_109", "MLRS": "MLRS",
    "2S1": "SAU_Gvozdika", "2S3": "SAU_Akatsia", "2S9": "SAU_2_C9",
    "2S19": "SAU_Msta",
    "BM-21": "Grad_URAL", "BM-27": "Uragan_BM_27", "BM-30": "Smerch",
    "D-30": "M2A1_105", "M-12": "M12_GMC",
    "Dana": "SpGH_Dana", "PLZ-05": "PLZ05",
}

_ARMOR_ATTR_MAP: Dict[str, str] = {
    "BMP-1": "BMP_1", "BMP-2": "BMP_2", "BMP-3": "BMP_3",
    "BTR-80": "BTR_80", "BTR-82A": "BTR_82A", "BTR-D": "BTR_D",
    "M2-Bradley": "M_2_Bradley", "M-113": "M_113",
    "M-1045": "M1045_HMMWV_TOW", "M-1043": "M1043_HMMWV_Armament",
    "LAV-25": "LAV_25",
    "M1-Abrams": "M_1_Abrams", "M-60": "M_60",
    "T-55": "T_55", "T-72B": "T_72B", "T-72B3": "T_72B3",
    "T-80U": "T_80UD", "T-90": "T_90",
    "Leopard-2": "Leopard_2", "Leopard-2A4": "Leopard_2A4",
    "Leopard-2A5": "Leopard_2A5",
    "Leopard-1": "Leopard1A3",
    "Challenger-2": "Challenger2", "Merkava-IV": "Merkava_Mk4",
    "Stryker-ICV": "M1126_Stryker_ICV", "Stryker-MGS": "M1128_Stryker_MGS",
    "Stryker-ATGM": "M1134_Stryker_ATGM",
    "ZBD-04A": "ZBD04A", "Type-96": "ZTZ96B", "Type-59": "TYPE_59",
    "MT-LB": "MTLB", "BMD-1": "BMD_1", "BRDM-2": "BRDM_2", "PT-76": "PT_76",
    "Marder": "Marder", "VAB": "VAB_Mephisto", "Leclerc": "Leclerc",
    "AAV7": "AAV7",
}

_ARTILLERY_ALIASES: Dict[str, Tuple[str, ...]] = {
    "M-109":  ("artillery", "howitzer", "155mm"),
    "MLRS":   ("artillery", "mlrs", "rocket"),
    "2S1":    ("artillery", "howitzer", "122mm"),
    "2S3":    ("artillery", "howitzer", "152mm"),
    "2S9":    ("artillery", "mortar", "120mm"),
    "2S19":   ("artillery", "howitzer", "152mm"),
    "BM-21":  ("artillery", "mlrs", "rocket"),
    "BM-27":  ("artillery", "mlrs", "rocket"),
    "BM-30":  ("artillery", "mlrs", "rocket"),
    "D-30":   ("artillery", "howitzer", "towed"),
    "M-12":   ("artillery", "howitzer", "155mm"),
    "Dana":   ("artillery", "howitzer", "wheeled"),
    "PLZ-05": ("artillery", "howitzer", "155mm"),
}

_ARMOR_ALIASES: Dict[str, Tuple[str, ...]] = {
    "BMP-1":          ("armor", "ifv"),
    "BMP-2":          ("armor", "ifv"),
    "BMP-3":          ("armor", "ifv"),
    "BTR-80":         ("armor", "apc"),
    "BTR-82A":        ("armor", "apc"),
    "BTR-D":          ("armor", "apc"),
    "M2-Bradley":     ("armor", "ifv"),
    "M-113":          ("armor", "apc"),
    "M-1045":         ("armor", "atgm"),
    "M-1043":         ("armor", "scout"),
    "LAV-25":         ("armor", "recce"),
    "M1-Abrams":      ("armor", "mbt"),
    "M-60":           ("armor", "mbt"),
    "T-55":           ("armor", "mbt"),
    "T-72B":          ("armor", "mbt"),
    "T-72B3":         ("armor", "mbt"),
    "T-80U":          ("armor", "mbt"),
    "T-90":           ("armor", "mbt"),
    "Leopard-2":       ("armor", "mbt"),
    "Leopard-2A4":     ("armor", "mbt"),
    "Leopard-2A5":     ("armor", "mbt"),
    "Leopard-1":       ("armor", "mbt"),
    "Challenger-2":    ("armor", "mbt"),
    "Merkava-IV":      ("armor", "mbt"),
    "Stryker-ICV":     ("armor", "apc"),
    "Stryker-MGS":     ("armor", "stryker"),
    "Stryker-ATGM":    ("armor", "atgm"),
    "ZBD-04A":         ("armor", "ifv"),
    "Type-96":         ("armor", "mbt"),
    "Type-59":         ("armor", "mbt"),
    "MT-LB":           ("armor", "apc"),
    "BMD-1":           ("armor", "ifv", "airborne"),
    "BRDM-2":          ("armor", "recce", "scout"),
    "PT-76":           ("armor", "light"),
    "Marder":          ("armor", "ifv"),
    "VAB":             ("armor", "atgm"),
    "Leclerc":         ("armor", "mbt"),
    "AAV7":            ("armor", "apc", "amphibious"),
    "HMMWV":           ("armor", "scout"),
    "Ural-375":        ("support", "aaa", "truck"),
}


# ─── Lazy-built maps ───────────────────────────────────────────────────────

_MAP: Dict[str, Any] = {}
_INFO: Dict[str, VehicleInfo] = {}


def _build():
    if _MAP:
        return
    ad = _vehicles.AirDefence
    for alias, attr in _AD_ATTR_MAP.items():
        if hasattr(ad, attr):
            _MAP[alias] = getattr(ad, attr)
    art = _vehicles.Artillery
    for alias, attr in _ARTILLERY_ATTR_MAP.items():
        if hasattr(art, attr):
            _MAP[alias] = getattr(art, attr)
    arm = _vehicles.Armor
    for alias, attr in _ARMOR_ATTR_MAP.items():
        if hasattr(arm, attr):
            _MAP[alias] = getattr(arm, attr)
    # Extra friendly aliases
    if hasattr(arm, "M1043_HMMWV_Armament"):
        _MAP["HMMWV"] = arm.M1043_HMMWV_Armament
    if hasattr(ad, "Ural_375_ZU_23"):
        _MAP["Ural-375"] = ad.Ural_375_ZU_23
    _build_info()


def _build_info():
    for alias in _AD_ATTR_MAP:
        roles = _AD_ALIASES.get(alias, ("sam",))
        _INFO[alias] = VehicleInfo(
            alias=alias,
            pydcs_attr=_AD_ATTR_MAP[alias],
            role=roles,
        )
    for alias in _ARTILLERY_ATTR_MAP:
        roles = _ARTILLERY_ALIASES.get(alias, ("artillery",))
        _INFO[alias] = VehicleInfo(
            alias=alias,
            pydcs_attr=_ARTILLERY_ATTR_MAP[alias],
            role=roles,
        )
    for alias in _ARMOR_ATTR_MAP:
        roles = _ARMOR_ALIASES.get(alias, ("armor",))
        _INFO[alias] = VehicleInfo(
            alias=alias,
            pydcs_attr=_ARMOR_ATTR_MAP[alias],
            role=roles,
        )
    # Extra aliases
    if "HMMWV" in _MAP:
        _INFO["HMMWV"] = VehicleInfo(
            alias="HMMWV",
            pydcs_attr="M1043_HMMWV_Armament",
            role=("armor", "scout"),
        )
    if "Ural-375" in _MAP:
        _INFO["Ural-375"] = VehicleInfo(
            alias="Ural-375",
            pydcs_attr="Ural_375_ZU_23",
            role=("support", "aaa", "truck"),
        )


# ─── Public API ─────────────────────────────────────────────────────────────

def resolve(name: str):
    """Return the pydcs vehicle class for `name`. Raises ValueError if unknown."""
    _build()
    if name in _MAP:
        return _MAP[name]
    raise ValueError(f"Unknown vehicle type: {name}")


def all_aliases() -> List[str]:
    _build()
    return sorted(_MAP)


def list_by_role(role_tag: str) -> List[str]:
    """Return all aliases matching a given role tag.

    Role tags: sam, aaa, ewr, radar, search, tracking, command, shorad,
    mrsam, lrsam, strategic, shortrange, artillery, howitzer, mlrs,
    armor, mbt, ifv, apc, recce, atgm, scout, support, infantry,
    mobile, towed.
    """
    _build()
    return sorted(
        alias for alias, info in _INFO.items()
        if role_tag in info.role
    )


def get_info(alias: str) -> Optional[VehicleInfo]:
    """Return the VehicleInfo for a given alias, or None if unknown."""
    _build()
    return _INFO.get(alias)