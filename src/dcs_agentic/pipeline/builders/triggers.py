"""Trigger builder — Phase 5.

Translates spec-level Trigger / TriggerCondition / TriggerAction objects
to pydcs `dcs.condition.*`, `dcs.action.*`, and `dcs.triggers.TriggerRule`
instances, then appends them to `mission.triggerrules.triggers`.

Cross-references (group/unit names) are looked up against the live
mission. Unknown references are reported, not silently dropped.
"""

from typing import Any, Dict, Optional

from dcs import Mission, action as dcs_action, condition as dcs_condition
from dcs.triggers import Event, TriggerContinious, TriggerOnce, TriggerRule
from dcs.unitgroup import Group as PydcsGroup

from ...errors import AssemblyReport
from ...schemas import MissionSpec
from ...schemas.triggers import (
    ActionKind,
    Trigger,
    TriggerAction,
    TriggerCondition,
    TriggerKind,
)


# Coalition string → pydcs action.Coalition enum
_COALITION_MAP = {
    "blue": dcs_action.Coalition.Blue,
    "red": dcs_action.Coalition.Red,
    "neutral": dcs_action.Coalition.Neutral,
}


def build_triggers(mission: Mission, spec: MissionSpec, report: AssemblyReport) -> None:
    if not spec.triggers:
        return
    for t in spec.triggers:
        try:
            rule = _build_one(mission, t, report)
        except Exception as e:
            report.error(
                "TRIGGER_BUILD_FAILED",
                f"{type(e).__name__}: {e}",
                context=t.name,
            )
            continue
        if rule is not None:
            mission.triggerrules.triggers.append(rule)
            report.info(
                "TRIGGER_CREATED",
                f"Created trigger '{t.name}': "
                f"{len(t.conditions)} condition(s), {len(t.actions)} action(s)",
            )


def _build_one(
    mission: Mission, t: Trigger, report: AssemblyReport
) -> Optional[TriggerRule]:
    rule_cls = TriggerOnce if t.once else TriggerContinious
    rule = rule_cls(Event.NoEvent, comment=t.name)

    for cond in t.conditions:
        pydcs_cond = _map_condition(mission, cond, t.name, report)
        if pydcs_cond is not None:
            rule.add_condition(pydcs_cond)

    if not rule.rules:
        report.warn(
            "TRIGGER_NO_VALID_CONDITIONS",
            f"Trigger '{t.name}' has no resolvable conditions; skipping.",
            context=t.name,
        )
        return None

    for act in t.actions:
        pydcs_act = _map_action(mission, act, t.name, t.coalition, report)
        if pydcs_act is not None:
            rule.add_action(pydcs_act)

    if not rule.actions:
        report.warn(
            "TRIGGER_NO_VALID_ACTIONS",
            f"Trigger '{t.name}' has no resolvable actions; skipping.",
            context=t.name,
        )
        return None

    return rule


# ─── Condition mapping ──────────────────────────────────────────────────────


def _map_condition(
    mission: Mission, cond: TriggerCondition, trig_name: str, report: AssemblyReport
):
    kind = cond.kind
    if kind == TriggerKind.TIME_REACHED:
        return dcs_condition.TimeAfter(seconds=int(cond.time_seconds or 0))
    if kind == TriggerKind.UNIT_DEAD:
        unit_id = _resolve_unit_id(mission, cond.unit_name, trig_name, report)
        if unit_id is None:
            return None
        return dcs_condition.UnitDead(unit=unit_id)
    if kind == TriggerKind.GROUP_DEAD:
        group_id = _resolve_group_id(mission, cond.group_name, trig_name, report)
        if group_id is None:
            return None
        return dcs_condition.GroupDead(group=group_id)
    if kind == TriggerKind.UNIT_IN_ZONE:
        unit_id = _resolve_unit_id(mission, cond.unit_name, trig_name, report)
        zone_id = _resolve_zone_id(mission, cond.zone_name, trig_name, report)
        if unit_id is None or zone_id is None:
            return None
        return dcs_condition.UnitInZone(unit=unit_id, zone=zone_id)
    if kind == TriggerKind.FLAG_TRUE:
        return dcs_condition.FlagIsTrue(flag=cond.flag_name)

    report.warn(
        "TRIGGER_UNSUPPORTED_CONDITION",
        f"Trigger '{trig_name}': condition kind '{kind}' not supported yet.",
        context=trig_name,
    )
    return None


# ─── Action mapping ─────────────────────────────────────────────────────────


def _map_action(
    mission: Mission,
    act: TriggerAction,
    trig_name: str,
    coalition_filter: Optional[str],
    report: AssemblyReport,
):
    kind = act.kind
    duration = int(act.duration_seconds or 10)

    if kind == ActionKind.SHOW_MESSAGE:
        text = mission.string(act.message or "")
        if coalition_filter and coalition_filter.lower() in _COALITION_MAP:
            return dcs_action.MessageToCoalition(
                coalitionlist=_COALITION_MAP[coalition_filter.lower()],
                text=text,
                seconds=duration,
            )
        return dcs_action.MessageToAll(text=text, seconds=duration)

    if kind == ActionKind.PLAY_SOUND:
        # SoundToAll needs a ResourceKey for an asset registered with the mission.
        # We don't have an asset-registration path yet; emit a stub and warn.
        report.warn(
            "TRIGGER_SOUND_NOT_WIRED",
            f"Trigger '{trig_name}': PLAY_SOUND ('{act.sound_file}') is not yet "
            f"wired through the asset pipeline and was emitted as an empty SoundToAll.",
            context=trig_name,
            hint="Add the .ogg via mission.map_resource before referencing it.",
        )
        return dcs_action.SoundToAll()

    if kind == ActionKind.SET_FLAG:
        flag = act.flag_name
        value = act.flag_value if act.flag_value is not None else 1
        if value == 1:
            return dcs_action.SetFlag(flag=flag)
        return dcs_action.SetFlagValue(flag=flag, value=value)

    if kind == ActionKind.ACTIVATE_GROUP:
        group_id = _resolve_group_id(mission, act.group_name, trig_name, report)
        if group_id is None:
            return None
        return dcs_action.ActivateGroup(group=group_id)

    if kind == ActionKind.END_MISSION:
        winner = act.winner or ""
        return dcs_action.EndMission(winner=winner, text=mission.string(""))

    if kind == ActionKind.SET_GOAL_SCORE:
        # No 1:1 pydcs action; use a SetFlag with the score so downstream Lua
        # can read it. Real goal-score wiring is a Phase 11 concern.
        report.warn(
            "TRIGGER_SET_GOAL_SCORE_FALLBACK",
            f"Trigger '{trig_name}': SET_GOAL_SCORE has no direct pydcs action; "
            f"emitted as SetFlagValue('goal_score', {act.score}).",
            context=trig_name,
        )
        return dcs_action.SetFlagValue(flag="goal_score", value=int(act.score or 0))

    report.warn(
        "TRIGGER_UNSUPPORTED_ACTION",
        f"Trigger '{trig_name}': action kind '{kind}' not supported yet.",
        context=trig_name,
    )
    return None


# ─── Name → pydcs ID lookups ────────────────────────────────────────────────


def _resolve_group_id(
    mission: Mission, name: Optional[str], trig_name: str, report: AssemblyReport
) -> Optional[int]:
    if not name:
        return None
    g = mission.find_group(name)
    if g is None:
        report.warn(
            "TRIGGER_GROUP_UNKNOWN",
            f"Trigger '{trig_name}' references unknown group '{name}'.",
            context=trig_name,
        )
        return None
    return g.id


def _resolve_unit_id(
    mission: Mission, name: Optional[str], trig_name: str, report: AssemblyReport
) -> Optional[int]:
    if not name:
        return None
    for coalition in mission.coalition.values():
        for country in coalition.countries.values():
            for group_attr in (
                "plane_group", "helicopter_group", "vehicle_group",
                "ship_group", "static_group",
            ):
                for g in getattr(country, group_attr, []) or []:
                    for u in getattr(g, "units", []) or []:
                        if u.name == name:
                            return u.id
    report.warn(
        "TRIGGER_UNIT_UNKNOWN",
        f"Trigger '{trig_name}' references unknown unit '{name}'.",
        context=trig_name,
    )
    return None


def _resolve_zone_id(
    mission: Mission, name: Optional[str], trig_name: str, report: AssemblyReport
) -> Optional[int]:
    if not name:
        return None
    for zone in mission.triggers.zones():
        if zone.name == name:
            return zone.id
    report.warn(
        "TRIGGER_ZONE_UNKNOWN",
        f"Trigger '{trig_name}' references unknown trigger zone '{name}'.",
        context=trig_name,
        hint="Add a TriggerZone with this name to spec.zones (drawing builder).",
    )
    return None
