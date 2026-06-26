"""Cross-reference validator.

Triggers, carrier_ops, and FARP-on-static interactions reference other
parts of the spec by name. Pydantic doesn't validate cross-refs.
"""

from ..errors import AssemblyReport
from ..schemas.triggers import ActionKind, TriggerKind


def check(spec, report: AssemblyReport) -> None:
    flight_names = {f.name for f in (spec.flights or [])}
    vehicle_names = {v.name for v in (spec.vehicles or [])}
    ship_names = {s.name for s in (spec.ships or [])}
    static_names = {s.name for s in (spec.statics or [])}
    zone_names = {z.name for z in (spec.zones or [])}
    all_group_names = flight_names | vehicle_names | ship_names | static_names
    all_unit_names = all_group_names  # spec doesn't distinguish; same name pool

    # Triggers
    for trig in spec.triggers or []:
        for cond in trig.conditions or []:
            if cond.kind in (TriggerKind.UNIT_DEAD, TriggerKind.UNIT_IN_ZONE):
                if cond.unit_name and cond.unit_name not in all_unit_names:
                    report.warn(
                        "REF_UNIT_UNKNOWN",
                        f"Trigger '{trig.name}' references unknown unit '{cond.unit_name}'",
                        context=trig.name,
                    )
            if cond.kind == TriggerKind.GROUP_DEAD:
                if cond.group_name and cond.group_name not in all_group_names:
                    report.warn(
                        "REF_GROUP_UNKNOWN",
                        f"Trigger '{trig.name}' references unknown group '{cond.group_name}'",
                        context=trig.name,
                    )
            if cond.kind == TriggerKind.UNIT_IN_ZONE:
                if cond.zone_name and cond.zone_name not in zone_names:
                    report.warn(
                        "REF_ZONE_UNKNOWN",
                        f"Trigger '{trig.name}' references unknown zone '{cond.zone_name}'",
                        context=trig.name,
                    )
        for act in trig.actions or []:
            if act.kind == ActionKind.ACTIVATE_GROUP:
                if act.group_name and act.group_name not in all_group_names:
                    report.warn(
                        "REF_GROUP_UNKNOWN",
                        f"Trigger '{trig.name}' action references unknown group "
                        f"'{act.group_name}'",
                        context=trig.name,
                    )

    # Carrier ops → ship_name
    for ops in spec.carrier_ops or []:
        if ops.ship_name not in ship_names:
            report.error(
                "REF_CARRIER_SHIP_UNKNOWN",
                f"carrier_ops references ship '{ops.ship_name}' but no such "
                f"ship group exists in spec.ships",
                context=ops.ship_name,
                hint="Add the carrier to spec.ships",
            )

    # Mission goals → group/flag names (if goal references named units)
    # Pydantic doesn't enforce this; skip until the goal schema crystallises.
