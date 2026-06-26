"""MissionAssembler — orchestrator that delegates to per-concern builders.

This file is intentionally thin. Per-concern logic lives in
pipeline/builders/. Per-type lookups live in catalog/. Unit conversions
live in units.py.

Add a new build stage by:
  1. Writing pipeline/builders/<concern>.py with a
     `build_<concern>(mission, spec, report)` function.
  2. Importing and calling it from `assemble()` below, in the right
     position relative to its dependencies (coalitions first, then
     groups, then triggers, then drawings).
"""

import os
from datetime import datetime, timezone
from typing import Optional

from dcs import Mission
from dcs.terrain import Caucasus

from ..catalog import theatres as catalog_theatres
from ..errors import AssemblyError, AssemblyReport
from ..schemas import MissionSpec
from .builders.carrier_ops import build_carrier_ops
from .builders.coalitions import build_coalitions
from .builders.custom_scripts import build_custom_scripts
from .builders.drawings import build_drawings
from .builders.farps import build_farps
from .builders.flights import build_flights
from .builders.ground import build_ground
from .builders.naval import build_naval
from .builders.statics import build_statics
from .builders.triggers import build_triggers
from .builders.weather import build_weather


class MissionAssembler:
    """Assembles a DCS .miz file from a declarative MissionSpec.

    Issues are accumulated in `self.report`. Pass `strict=True` to raise
    AssemblyError if any issue is severity=ERROR. Agents should always
    read `report.issues` after assembly to surface problems.
    """

    def __init__(self, spec: MissionSpec, strict: bool = False, validate: bool = False):
        self.spec = spec
        self.strict = strict
        self.validate = validate
        self.mission: Optional[Mission] = None
        self.report = AssemblyReport()

    def assemble(self) -> Mission:
        """Build the Mission object from the spec and return it."""
        if self.validate:
            from ..validation import validate as _validate
            pre = _validate(self.spec)
            for issue in pre.issues:
                self.report.add(issue.severity, issue.code, issue.message,
                                context=issue.context, hint=issue.hint)

        terrain_cls = catalog_theatres.resolve(self.spec.theatre)
        if terrain_cls is None:
            self.report.error(
                "UNKNOWN_THEATRE",
                f"Unknown theatre '{self.spec.theatre}', falling back to Caucasus",
                hint=f"Use one of: {catalog_theatres.all_aliases()}",
            )
            terrain_cls = Caucasus

        self.mission = Mission(terrain=terrain_cls())
        self._setup_basic_info()

        build_coalitions(self.mission, self.spec, self.report)
        build_weather(self.mission, self.spec, self.report)
        build_flights(self.mission, self.spec, self.report)
        build_ground(self.mission, self.spec, self.report)
        build_naval(self.mission, self.spec, self.report)
        build_carrier_ops(self.mission, self.spec, self.report)
        build_statics(self.mission, self.spec, self.report)
        build_farps(self.mission, self.spec, self.report)
        build_drawings(self.mission, self.spec, self.report)
        build_triggers(self.mission, self.spec, self.report)
        build_custom_scripts(self.mission, self.spec, self.report)

        if self.strict and self.report.has_errors():
            raise AssemblyError(self.report)

        return self.mission

    def _setup_basic_info(self) -> None:
        brief = self.spec.briefing
        if brief:
            if brief.description:
                self.mission.set_description_text(brief.description)
            if brief.blue_task:
                self.mission.set_description_bluetask_text(brief.blue_task)
            if brief.red_task:
                self.mission.set_description_redtask_text(brief.red_task)
        if self.spec.sortie:
            self.mission.set_sortie_text(self.spec.sortie)
        if self.spec.start_time is not None:
            # pydcs wants a naive datetime; build it via tz-aware UTC then drop the tz.
            # Using bare fromtimestamp() would interpret in the host's local zone.
            self.mission.start_time = datetime.fromtimestamp(
                self.spec.start_time, tz=timezone.utc
            ).replace(tzinfo=None)

    def save(self, filepath: str) -> str:
        """Assemble and save the .miz file. Returns the path on success."""
        mission = self.assemble()
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        mission.save(filepath)
        return filepath
