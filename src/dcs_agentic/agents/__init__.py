"""DCS Agentic Mission Editor - AI Agents.

This package provides the LLM-powered agent layer for designing, editing,
and managing DCS World missions and campaigns.

Available agents:

- mission_agent.design_mission()  — single-shot mission creation from prompts
- editor_agent.edit_mission()     — multi-turn tool-based mission editing
- campaign_agent.design_campaign() — campaign structure design
- campaign_agent.render_mission()  — per-mission template rendering

Tool surface:
- tools.mutations.TOOLS      — list of tool definitions
- tools.mutations.apply_tool — apply a tool mutation to a MissionSpec

LLM interface:
- llm.client.LLMClient       — Anthropic SDK wrapper
- llm.messages.*             — prompt building utilities
"""

from . import campaign_agent, editor_agent, mission_agent
from .llm import client as llm_client
from . import tools as agent_tools

__all__ = [
    "mission_agent",
    "editor_agent",
    "campaign_agent",
    "llm_client",
    "agent_tools",
]