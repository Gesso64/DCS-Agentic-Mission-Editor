"""
Typed errors for dcs-agentic.

The assembler can accumulate non-fatal issues (a missing payload, an unknown
airport) and return them with the mission. Agents need this — surfacing
structured errors lets the LLM repair its own spec instead of guessing why
a "successful" save looks wrong in DCS.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class AssemblyIssue:
    """A single problem encountered while assembling a mission."""
    severity: Severity
    code: str                       # stable identifier, e.g. "UNKNOWN_AIRCRAFT"
    message: str
    context: Optional[str] = None   # e.g. flight name, vehicle name
    hint: Optional[str] = None      # how to fix; surfaces to agents


@dataclass
class AssemblyReport:
    """Accumulated issues from one assembly pass."""
    issues: List[AssemblyIssue] = field(default_factory=list)

    def add(self, severity: Severity, code: str, message: str,
            context: Optional[str] = None, hint: Optional[str] = None) -> None:
        self.issues.append(AssemblyIssue(severity, code, message, context, hint))

    def warn(self, code: str, message: str, **kw) -> None:
        self.add(Severity.WARNING, code, message, **kw)

    def error(self, code: str, message: str, **kw) -> None:
        self.add(Severity.ERROR, code, message, **kw)

    def info(self, code: str, message: str, **kw) -> None:
        self.add(Severity.INFO, code, message, **kw)

    @property
    def errors(self) -> List[AssemblyIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> List[AssemblyIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    def has_errors(self) -> bool:
        return any(i.severity == Severity.ERROR for i in self.issues)

    def format(self) -> str:
        if not self.issues:
            return "No issues."
        lines = []
        for i in self.issues:
            ctx = f" [{i.context}]" if i.context else ""
            hint = f"  hint: {i.hint}" if i.hint else ""
            lines.append(f"  {i.severity.value.upper():7s} {i.code}{ctx}: {i.message}{hint}")
        return "\n".join(lines)


class AssemblyError(Exception):
    """Raised when --strict is set and the report has errors."""
    def __init__(self, report: AssemblyReport):
        self.report = report
        super().__init__(f"Mission assembly failed:\n{report.format()}")


class SpecValidationError(Exception):
    """Raised when a MissionSpec is structurally invalid in ways Pydantic
    doesn't catch (e.g. waypoint references airport not on this theatre)."""
    pass
