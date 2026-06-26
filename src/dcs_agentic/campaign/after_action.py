"""After-action report parsing — Phase 11.

Three sources are supported:
  A. DCS Lua callback — embed `LUA_HOOK_SCRIPT` in every campaign .miz;
     it writes a JSON file on `mission end`. `parse_lua_callback(json)`
     converts the dict to an AfterAction.
  B. TacView .acmi — parse the text-mode ACMI to extract destroyed
     objects by coalition. Best-effort; ACMI is verbose and we look
     only at the event log + object metadata.
  C. Manual CLI — `dcs-agentic campaign report --winner blue …`.
     Already shipped in cli/campaign.py.

The Lua callback path is the canonical one: ACMI parsing is a
convenience for users who already record TacView.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from ..schemas.campaign import AfterAction


__all__ = [
    "AfterAction",
    "LUA_HOOK_SCRIPT",
    "parse_lua_callback",
    "parse_tacview",
    "load_outcome",
]


# ─── Lua hook script ──────────────────────────────────────────────────────
# Drop this into a mission's "Mission Scripting > MISSION START" trigger
# (or attach via spec.custom_scripts) to write outcome JSON when the
# mission ends. Output path is hard-coded relative to DCS Saved Games.

LUA_HOOK_SCRIPT = r"""
-- dcs-agentic after-action hook.
-- Writes outcome JSON to: <Saved Games>/DCS/Logs/<mission_name>.outcome.json
-- when the mission ends.

local function dump(t, indent)
    indent = indent or ""
    local s = "{\n"
    local next_indent = indent .. "  "
    local keys = {}
    for k in pairs(t) do table.insert(keys, k) end
    table.sort(keys, function(a, b) return tostring(a) < tostring(b) end)
    for i, k in ipairs(keys) do
        local v = t[k]
        local key = string.format("%q", tostring(k))
        local val
        if type(v) == "table" then
            val = dump(v, next_indent)
        elseif type(v) == "string" then
            val = string.format("%q", v)
        elseif type(v) == "boolean" then
            val = tostring(v)
        else
            val = tostring(v)
        end
        s = s .. next_indent .. key .. ": " .. val
        if i < #keys then s = s .. "," end
        s = s .. "\n"
    end
    return s .. indent .. "}"
end

dcs_agentic = dcs_agentic or {
    blue_losses = {},
    red_losses = {},
    captured   = {},
    flags_set  = {},
    blue_score = 0,
    red_score  = 0,
    start_time = timer.getTime(),
}

local handler = {}
function handler:onEvent(e)
    if e.id == world.event.S_EVENT_DEAD or e.id == world.event.S_EVENT_CRASH then
        local unit = e.initiator
        if unit and unit.getCoalition then
            local coa = unit:getCoalition()
            local name = unit:getName() or "unknown"
            if coa == coalition.side.BLUE then
                table.insert(dcs_agentic.blue_losses, name)
            elseif coa == coalition.side.RED then
                table.insert(dcs_agentic.red_losses, name)
            end
        end
    elseif e.id == world.event.S_EVENT_BASE_CAPTURED then
        local base = e.place
        if base and base.getName then
            dcs_agentic.captured[base:getName()] = "unknown"
        end
    elseif e.id == world.event.S_EVENT_MISSION_END then
        dcs_agentic.duration = timer.getTime() - dcs_agentic.start_time
        local mission_name = env.mission.theatre or "mission"
        local outpath = lfs.writedir() .. "Logs/" .. mission_name .. ".outcome.json"
        local f = io.open(outpath, "w")
        if f then
            f:write(dump(dcs_agentic))
            f:close()
        end
    end
end
world.addEventHandler(handler)
""".lstrip()


# ─── Lua callback parser ─────────────────────────────────────────────────


def parse_lua_callback(data: Dict[str, Any], mission_name: Optional[str] = None) -> AfterAction:
    """Convert a Lua-emitted outcome dict to an AfterAction.

    Args:
        data: Parsed JSON dict from the Lua hook
        mission_name: Override for the mission_name field (the Lua hook
            doesn't always know its own name).

    Expected dict shape (all keys optional except mission_name on
    AfterAction — supplied by the caller if missing):

        {
          "mission_name":  "Op Lion D-Day",
          "winner":        "blue"|"red"|"draw"|null,
          "blue_score":    1000,
          "red_score":     500,
          "blue_losses":   ["Hornet 1-1", ...],
          "red_losses":    [...],
          "captured":      {"Sochi-Adler": "blue", ...},
          "flags_set":     {"alpha_done": true},
          "duration":      seconds,
          "notes":         "..."
        }
    """
    return AfterAction(
        mission_name=data.get("mission_name") or mission_name or "unknown",
        winner=data.get("winner"),
        blue_score=int(data.get("blue_score", 0)),
        red_score=int(data.get("red_score", 0)),
        blue_losses=list(data.get("blue_losses", [])),
        red_losses=list(data.get("red_losses", [])),
        captured=dict(data.get("captured", {})),
        flags_set=dict(data.get("flags_set", {})),
        duration_seconds=data.get("duration") or data.get("duration_seconds"),
        notes=data.get("notes"),
    )


# ─── TacView .acmi parser ────────────────────────────────────────────────
# ACMI text format v2.x. We extract:
#   - Title / Author (top-of-file properties)
#   - Per-object: id, Name, Coalition
#   - Event=Destroyed entries — produce losses per coalition.
#   - Highest #timestamp seen → duration_seconds.

_PROPERTY_RE = re.compile(r"^0,([A-Za-z]+)=(.*)$")
_FRAME_RE = re.compile(r"^#([0-9.]+)\s*$")
_OBJECT_RE = re.compile(r"^([0-9A-Fa-f]+),(.*)$")
_EVENT_RE = re.compile(r"^0,Event=Destroyed\|([0-9A-Fa-f]+)(?:\|([0-9A-Fa-f]+))?")


def parse_tacview(filepath: str, mission_name: Optional[str] = None) -> AfterAction:
    """Best-effort .acmi → AfterAction.

    Only the text mode of TacView .acmi is supported. Compressed .zip.acmi
    files must be extracted first.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"TacView file not found: {filepath}")

    objects: Dict[str, Dict[str, str]] = {}
    blue_losses: list[str] = []
    red_losses: list[str] = []
    duration = 0.0
    title: Optional[str] = None

    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.rstrip("\n").rstrip("\r")
            if not line:
                continue

            m_frame = _FRAME_RE.match(line)
            if m_frame:
                try:
                    duration = max(duration, float(m_frame.group(1)))
                except ValueError:
                    pass
                continue

            m_prop = _PROPERTY_RE.match(line)
            if m_prop:
                key, value = m_prop.group(1), m_prop.group(2)
                if key == "Title" and title is None:
                    title = value
                # Event=Destroyed|<obj_id>[|<killer_id>]
                if key == "Event" and value.startswith("Destroyed|"):
                    bits = value.split("|")
                    if len(bits) >= 2:
                        victim_id = bits[1]
                        victim = objects.get(victim_id, {})
                        name = victim.get("Name", victim_id)
                        coa = (victim.get("Coalition") or "").lower()
                        if "allies" in coa or "blue" in coa:
                            blue_losses.append(name)
                        elif "enemies" in coa or "red" in coa:
                            red_losses.append(name)
                continue

            m_obj = _OBJECT_RE.match(line)
            if m_obj:
                obj_id, body = m_obj.group(1), m_obj.group(2)
                attrs = objects.setdefault(obj_id, {})
                for token in body.split(","):
                    if "=" in token:
                        k, v = token.split("=", 1)
                        attrs[k] = v
                continue

    return AfterAction(
        mission_name=mission_name or title or path.stem,
        winner=None,
        blue_score=0,
        red_score=0,
        blue_losses=blue_losses,
        red_losses=red_losses,
        captured={},
        flags_set={},
        duration_seconds=duration if duration > 0 else None,
        notes="parsed from TacView .acmi",
    )


# ─── Auto-dispatch ───────────────────────────────────────────────────────


def load_outcome(filepath: str, mission_name: Optional[str] = None) -> AfterAction:
    """Load an outcome from a file, autodetecting the format by extension."""
    path = Path(filepath)
    suffix = path.suffix.lower()
    if suffix == ".acmi":
        return parse_tacview(filepath, mission_name=mission_name)
    if suffix in (".json", ""):
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return parse_lua_callback(data, mission_name=mission_name)
    raise ValueError(
        f"Unknown outcome file type '{suffix}'. Use .json (Lua callback) or .acmi (TacView)."
    )
