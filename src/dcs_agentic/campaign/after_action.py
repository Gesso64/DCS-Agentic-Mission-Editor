"""After-action report — outcome of a single mission.

Part of Phase 10/11. Captures the result of a mission for campaign state
updates. Three sourcing methods are planned:
  A. DCS Lua callback (preferred long-term)
  B. TacView .acmi parsing
  C. Manual CLI (shipped first)

Currently only method C is implemented.
"""

from typing import Any, Dict, List, Optional

from ..schemas.campaign import AfterAction

__all__ = ["AfterAction"]


def parse_lua_callback(json_data: Dict[str, Any]) -> AfterAction:
    """Parse a DCS Lua mission_end callback payload.

    NOT YET IMPLEMENTED. Placeholder for Phase 11.
    """
    raise NotImplementedError("Lua callback parsing is Phase 11 — not yet implemented")


def parse_tacview(filepath: str) -> AfterAction:
    """Parse a TacView .acmi file into an AfterAction.

    NOT YET IMPLEMENTED. Placeholder for Phase 11.
    """
    raise NotImplementedError("TacView parsing is Phase 11 — not yet implemented")