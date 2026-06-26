"""Validation layer — Phase 7.

Cross-cutting checks beyond what Pydantic catches. Each check is a pure
function `check(spec, report) -> None` that reads a MissionSpec and
records issues on the report. Validators are read-only.

Public API:
    from dcs_agentic.validation import validate
    report = validate(spec)
"""

from ..errors import AssemblyReport
from . import (
    coordinate_sanity,
    fuel_range,
    references,
    route_sanity,
    weapons_match,
)


_CHECKS = (
    coordinate_sanity.check,
    fuel_range.check,
    weapons_match.check,
    route_sanity.check,
    references.check,
)


def validate(spec) -> AssemblyReport:
    """Run every registered validator against `spec`. Returns a fresh report."""
    report = AssemblyReport()
    for fn in _CHECKS:
        try:
            fn(spec, report)
        except Exception as e:
            report.error(
                "VALIDATOR_CRASHED",
                f"{fn.__module__}: {type(e).__name__}: {e}",
                hint="This is a validator bug — please report it.",
            )
    return report
