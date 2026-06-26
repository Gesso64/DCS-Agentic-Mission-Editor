"""Static object builder."""

from dcs import Mission
from dcs.mapping import Point as MapPoint

from ...catalog import statics as catalog_statics
from ...errors import AssemblyReport
from ...schemas import MissionSpec, StaticObject
from .coalitions import get_or_add_country


def build_statics(mission: Mission, spec: MissionSpec, report: AssemblyReport) -> None:
    if not spec.statics:
        return
    for static_spec in spec.statics:
        try:
            _build_one(mission, static_spec, report)
        except Exception as e:
            report.error(
                "STATIC_BUILD_FAILED",
                f"{type(e).__name__}: {e}",
                context=static_spec.name,
            )


def _build_one(mission: Mission, static_spec: StaticObject, report: AssemblyReport) -> None:
    country = get_or_add_country(
        mission, static_spec.country, static_spec.side or "neutrals",
    )
    pos = MapPoint(static_spec.position.x, static_spec.position.y, mission.terrain)
    stype = catalog_statics.resolve(static_spec.type)

    mission.static_group(
        country=country,
        name=static_spec.name,
        _type=stype,
        position=pos,
        heading=static_spec.heading or 0,
        dead=static_spec.dead or False,
    )

    report.info(
        "STATIC_CREATED",
        f"Created static '{static_spec.name}': {static_spec.type}",
    )
