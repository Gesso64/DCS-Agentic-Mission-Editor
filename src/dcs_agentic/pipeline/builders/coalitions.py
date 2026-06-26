"""Coalition / country builder.

Also exposes get_or_add_country() — the helper every group builder
calls to resolve a (country, side) pair to a pydcs country instance,
adding it to the coalition if not already present.
"""

from dcs import Mission

from ...catalog import countries as catalog_countries
from ...errors import AssemblyReport
from ...schemas import MissionSpec


def build_coalitions(mission: Mission, spec: MissionSpec, report: AssemblyReport) -> None:
    """Pre-add every country declared in spec.coalitions.

    Group builders also call get_or_add_country() to ensure the country
    exists before placing a group in it — this pass is for explicitly
    declared coalitions that have no groups.
    """
    if not spec.coalitions:
        return
    for coalition_spec in spec.coalitions:
        side = coalition_spec.side.lower()
        if side not in ("blue", "red"):
            report.warn(
                "COALITION_SIDE_INVALID",
                f"Coalition side must be 'blue' or 'red', got '{coalition_spec.side}'",
                context=coalition_spec.country,
            )
            continue
        try:
            country_cls = catalog_countries.resolve(coalition_spec.country)
        except ValueError as e:
            report.error(
                "UNKNOWN_COUNTRY",
                str(e),
                context=coalition_spec.country,
            )
            continue
        col_obj = mission.coalition[side]
        col_obj.add_country(country_cls())


def get_or_add_country(mission: Mission, country_name: str, side: str):
    """Look up or add a country in the given coalition side. Returns the
    pydcs country instance. Raises ValueError on unknown name/side."""
    side = (side or "blue").lower()
    col_obj = mission.coalition.get(side)
    if col_obj is None:
        raise ValueError(f"Unknown coalition side: {side}")
    country_cls = catalog_countries.resolve(country_name)
    country_instance = country_cls()
    existing = col_obj.country(country_instance.name)
    if existing is not None:
        return existing
    return col_obj.add_country(country_instance)
