"""Ship alias map.

Note: 'H-6J' is shared with the aircraft catalog. The ambiguity is
resolved by context — FlightGroup uses aircraft.resolve, ShipGroup uses
this module.
"""

from typing import Any, Dict

import dcs.ships as _ships


_SHIP_ALIASES = {
    "Stennis": "Stennis", "CVN-74": "Stennis",
    "CVN-71": "CVN_71", "CVN-72": "CVN_72",
    "CVN-73": "CVN_73", "CVN-75": "CVN_75",
    "Forrestal": "Forrestal",
    "Vinson": "VINSON",
    "LHA-1": "LHA_Tarawa",
    "Ticonderoga": "TICONDEROG", "CG-Ticonderoga": "TICONDEROG",
    "Arleigh-Burke": "USS_Arleigh_Burke_IIa", "DDG-51": "USS_Arleigh_Burke_IIa",
    "Perry": "PERRY", "FFG-7": "PERRY",
    "Moskva": "MOSCOW",
    "Neustrashimy": "NEUSTRASH",
    "Kuznetsov": "KUZNECOW",
    "Albion": "ALBATROS",
    "Type-45": "USS_Arleigh_Burke_IIa",  # PROXY: British Daring class; closest Western analogue
    "Zubr": "BDK_775", "Ropucha": "BDK_775",
    "Molniya": "MOLNIYA",
    "PIOTR": "PIOTR",
    "Speedboat": "Speedboat",
    "Rezky": "REZKY",
    "H-6J": "Type_052B",
    "Type-054A": "Type_054A",
    "Type-071": "Type_071",
    "HarborTug": "HarborTug",
    "Elnya": "ELNYA",
    "Civ-Container": "Dry_cargo_ship_1",
    "Civ-Cargo": "Dry_cargo_ship_2",
    "Seawise-Giant": "Seawise_Giant",
}


_MAP: Dict[str, Any] = {}


def _build():
    if _MAP:
        return
    for alias, attr in _SHIP_ALIASES.items():
        if hasattr(_ships, attr):
            _MAP[alias] = getattr(_ships, attr)


def resolve(name: str):
    """Return the pydcs ship class for `name`. Raises ValueError if unknown.

    Falls back to a sanitized direct lookup on dcs.ships.
    """
    _build()
    if name in _MAP:
        return _MAP[name]
    sanitized = name.replace("-", "_")
    if hasattr(_ships, sanitized):
        return getattr(_ships, sanitized)
    raise ValueError(f"Unknown ship type: {name}")


def all_aliases() -> list[str]:
    _build()
    return sorted(_MAP)
