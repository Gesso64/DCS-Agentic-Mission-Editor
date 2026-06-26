"""Agent tool definitions and dispatch.

This package provides the tool surface for the editor agent (Phase 9)
and campaign agent (Phase 10). Tools follow Anthropic's tool-use schema.
"""

from .mutations import TOOLS, apply_tool

__all__ = ["TOOLS", "apply_tool"]