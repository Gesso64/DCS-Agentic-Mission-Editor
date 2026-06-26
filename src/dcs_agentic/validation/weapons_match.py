"""Weapons-match validator.

Checks each flight's payload against its declared task. Substring match
against the CLSID is intentionally coarse — covers the common naming
patterns without trying to enumerate every weapon variant.
"""

from ..catalog import payloads as catalog_payloads
from ..errors import AssemblyReport


AA_MISSILES = {"AIM-9", "AIM-120", "AIM-7", "R-73", "R-27", "R-77",
               "Python", "Derby", "MICA", "Magic"}
ANTI_RADIATION = {"AGM-88", "AGM-45", "Kh-58", "Kh-31P", "ALARM"}
BOMBS = {"GBU", "Mk-82", "Mk-83", "Mk-84", "BLU", "SDB", "CBU", "KAB",
         "FAB", "BetAB"}
ASM = {"AGM-84", "AGM-158", "Kh-35", "3M-54", "Exocet", "Harpoon"}
CAS = {"AGM-65", "AGM-114", "Vikhr", "BGM-71", "S-8", "S-13", "Rocket"}


def _weapons_for_flight(flight):
    """Return a set of weapon name fragments (uppercase) for matching."""
    p = flight.payload
    if p is None:
        return None
    if p.pylons:
        return {item.clsid.upper() for item in p.pylons}
    if p.preset_name:
        try:
            preset = catalog_payloads.resolve(flight.aircraft_type, p.preset_name)
        except ValueError:
            return None
        return {clsid.upper() for (_, clsid, _) in preset.pylons}
    return None


def _any_match(weapons, keywords):
    return any(kw.upper() in w for w in weapons for kw in keywords)


def check(spec, report: AssemblyReport) -> None:
    for flight in spec.flights or []:
        task = flight.task
        if task is None:
            continue
        task_str = task.value if hasattr(task, "value") else str(task)

        weapons = _weapons_for_flight(flight)
        if weapons is None:
            # No payload defined — warn unless it's a non-combat task.
            if task_str.lower() not in ("recon", "transport", "awacs", "tanker", "ewr"):
                report.warn(
                    "WEAPONS_NO_PAYLOAD",
                    f"Flight '{flight.name}' task '{task_str}' has no payload defined",
                    context=flight.name,
                )
            continue

        checks = {
            "cap":      (AA_MISSILES, "A-A missiles"),
            "intercept": (AA_MISSILES, "A-A missiles"),
            "sweep":    (AA_MISSILES, "A-A missiles"),
            "patrol":   (AA_MISSILES, "A-A missiles"),
            "escort":   (AA_MISSILES, "A-A missiles"),
            "sead":     (ANTI_RADIATION, "anti-radiation missiles"),
            "dead":     (ANTI_RADIATION, "anti-radiation missiles"),
            "strike":   (BOMBS, "bombs"),
            "ground_attack": (BOMBS | CAS, "bombs or air-to-ground missiles"),
            "antiship": (ASM, "anti-ship missiles"),
            "cas":      (CAS | BOMBS, "CAS weapons"),
            "afac":     (CAS, "rockets / Mavericks for marking"),
        }
        expectation = checks.get(task_str.lower())
        if expectation is None:
            continue
        keywords, label = expectation
        if not _any_match(weapons, keywords):
            report.warn(
                "WEAPONS_TASK_MISMATCH",
                f"Flight '{flight.name}' task '{task_str}' but payload has no {label}",
                context=flight.name,
                hint=f"Expected one of: {', '.join(sorted(keywords))}",
            )
