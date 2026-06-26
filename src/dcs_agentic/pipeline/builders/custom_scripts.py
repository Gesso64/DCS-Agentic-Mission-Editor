"""Custom Lua script builder."""

from dcs import Mission

from ...errors import AssemblyReport
from ...schemas import MissionSpec


def build_custom_scripts(mission: Mission, spec: MissionSpec, report: AssemblyReport) -> None:
    if not spec.custom_scripts:
        return
    for script in spec.custom_scripts:
        if script.name == "init" and script.content:
            mission.init_script = script.content
            report.info("SCRIPT_INSTALLED", f"init script set ({len(script.content)} chars)")
        elif script.file_path:
            mission.init_script_file = script.file_path
            report.info("SCRIPT_INSTALLED", f"init script file set: {script.file_path}")
        else:
            report.warn(
                "SCRIPT_IGNORED",
                f"Custom script '{script.name}' has neither inline content "
                f"(with name='init') nor file_path; ignored.",
                context=script.name,
            )
