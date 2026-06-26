"""Country alias map."""

from typing import Any, Dict

from dcs import countries as _dcs_countries


COUNTRY_MAP: Dict[str, Any] = {
    "USA": _dcs_countries.USA,
    "UK": _dcs_countries.UK,
    "Russia": _dcs_countries.Russia,
    "China": _dcs_countries.China,
    "Iran": _dcs_countries.Iran,
    "Syria": _dcs_countries.Syria,
    "Germany": _dcs_countries.Germany,
    "France": _dcs_countries.France,
    "Italy": _dcs_countries.Italy,
    "Turkey": _dcs_countries.Turkey,
    "Israel": _dcs_countries.Israel,
    "Georgia": _dcs_countries.Georgia,
    "Ukraine": _dcs_countries.Ukraine,
    "Australia": _dcs_countries.Australia,
    "Canada": _dcs_countries.Canada,
    "Spain": _dcs_countries.Spain,
    "Netherlands": _dcs_countries.TheNetherlands,
    "Poland": _dcs_countries.Poland,
    "Norway": _dcs_countries.Norway,
    "Denmark": _dcs_countries.Denmark,
    "Belgium": _dcs_countries.Belgium,
    "SouthKorea": _dcs_countries.SouthKorea,
    "Japan": _dcs_countries.Japan,
    "Abkhazia": _dcs_countries.Abkhazia,
    "Belarus": _dcs_countries.Belarus,
    "Serbia": _dcs_countries.Serbia,
    "Kazakhstan": _dcs_countries.Kazakhstan,
    "NorthKorea": _dcs_countries.NorthKorea,
    "Croatia": _dcs_countries.Croatia,
    "CzechRepublic": _dcs_countries.CzechRepublic,
}


def resolve(name: str):
    """Look up a country class by alias. Raises ValueError on unknown name."""
    cls = COUNTRY_MAP.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown country: {name}. Valid: {sorted(COUNTRY_MAP)}"
        )
    return cls


def all_aliases() -> list[str]:
    return sorted(COUNTRY_MAP)
