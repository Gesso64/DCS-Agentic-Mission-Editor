"""FARP (Forward Arming and Refuelling Point) builder."""

from dcs import Mission
from dcs.mapping import Point as MapPoint
from dcs.unit import FARP as PydcsFARP, InvisibleFARP

from ...errors import AssemblyReport
from ...schemas import FARP, MissionSpec
from .coalitions import get_or_add_country


def build_farps(mission: Mission, spec: MissionSpec, report: AssemblyReport) -> None:
    if not spec.farps:
        return
    for farp_spec in spec.farps:
        try:
            _build_one(mission, farp_spec, report)
        except Exception as e:
            report.error(
                "FARP_BUILD_FAILED",
                f"{type(e).__name__}: {e}",
                context=farp_spec.name,
            )


def _build_one(mission: Mission, farp_spec: FARP, report: AssemblyReport) -> None:
    country = get_or_add_country(mission, farp_spec.country, farp_spec.side or "blue")
    pos = MapPoint(farp_spec.position.x, farp_spec.position.y, mission.terrain)
    farp_type = InvisibleFARP if farp_spec.invisible else PydcsFARP

    mission.farp(
        country=country,
        name=farp_spec.name,
        position=pos,
        heading=farp_spec.heading or 0,
        farp_type=farp_type,
    )
    report.info(
        "FARP_CREATED",
        f"Created FARP '{farp_spec.name}' at ({pos.x:.0f}, {pos.y:.0f})",
    )
