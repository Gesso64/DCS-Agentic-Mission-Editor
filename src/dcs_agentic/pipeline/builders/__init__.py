"""Per-concern mission builders.

Every public function in a builder module has the same signature:

    def build_<concern>(mission, spec, report) -> None

Builders accumulate issues in `report` and do not raise — except where
the failure of one element should not silently lose the rest of the
mission. The top-level pattern is:

    for item in spec.<concern> or []:
        try:
            _build_one(mission, item, report)
        except Exception as e:
            report.error("<CONCERN>_BUILD_FAILED",
                         f"{type(e).__name__}: {e}",
                         context=item.name)

This module also exposes the shared enum mappers used by multiple
builders (skill, start_type, task, waypoint action).
"""

from dcs import task as dcs_task
from dcs.mission import StartType as PydcsStartType
from dcs.point import PointAction
from dcs.unit import Skill as PydcsSkill

from ...schemas import Skill, StartType, TaskType, Waypoint


def skill_to_pydcs(skill: Skill) -> PydcsSkill:
    return {
        Skill.PLAYER: PydcsSkill.Player,
        Skill.CLIENT: PydcsSkill.Client,
        Skill.EXCELLENT: PydcsSkill.Excellent,
        Skill.GOOD: PydcsSkill.Good,
        Skill.HIGH: PydcsSkill.High,
        Skill.AVERAGE: PydcsSkill.Average,
        Skill.RANDOM: PydcsSkill.Random,
    }[skill]


def start_type_to_pydcs(st: StartType) -> PydcsStartType:
    return {
        StartType.COLD: PydcsStartType.Cold,
        StartType.WARM: PydcsStartType.Warm,
        StartType.RUNWAY: PydcsStartType.Runway,
    }[st]


def task_to_pydcs(task_type: TaskType):
    """Map TaskType to pydcs task class. None means the task has no
    corresponding pydcs flight task (e.g. EWR is a ground role)."""
    return {
        TaskType.CAP: dcs_task.CAP,
        TaskType.CAS: dcs_task.CAS,
        TaskType.SEAD: dcs_task.SEAD,
        TaskType.STRIKE: dcs_task.GroundAttack,
        TaskType.DEAD: dcs_task.SEAD,
        TaskType.INTERCEPT: dcs_task.CAP,
        TaskType.SWEEP: dcs_task.CAP,
        TaskType.PATROL: dcs_task.CAP,
        TaskType.AWACS: dcs_task.AWACS,
        TaskType.REFUELING: dcs_task.Refueling,
        TaskType.TRANSPORT: dcs_task.Transport,
        TaskType.ESCORT: dcs_task.Escort,
        TaskType.RECON: dcs_task.Reconnaissance,
        TaskType.ANTISHIP: dcs_task.AntishipStrike,
        TaskType.GROUND_ATTACK: dcs_task.GroundAttack,
        TaskType.AFAC: dcs_task.AFAC,
        TaskType.EWR: None,
    }.get(task_type)


def point_action_for_wp(waypoint: Waypoint) -> PointAction:
    if not waypoint.action:
        return PointAction.TurningPoint
    return {
        "TURNING_POINT": PointAction.TurningPoint,
        "FROM_PARKING_AREA": PointAction.FromParkingArea,
        "FROM_PARKING_AREA_HOT": PointAction.FromParkingAreaHot,
        "FROM_RUNWAY": PointAction.FromRunway,
        "LANDING": PointAction.Landing,
        "FLY_OVER_POINT": PointAction.FlyOverPoint,
        "OFF_ROAD": PointAction.OffRoad,
    }.get(waypoint.action, PointAction.TurningPoint)
