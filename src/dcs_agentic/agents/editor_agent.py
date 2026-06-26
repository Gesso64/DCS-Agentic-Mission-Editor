"""Editor agent — Phase 9.

Multi-turn tool-call based editing of an existing MissionSpec.
Loads a spec, applies incremental mutations via tool calls, and returns
the modified spec for assembly.

Usage:
    from dcs_agentic.agents.editor_agent import edit_mission

    spec = edit_mission(spec, "Add an AWACS east of Batumi")
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from ..schemas import MissionSpec
from .llm.client import LLMClient
from .llm.messages import build_editor_prompt, format_user_message
from .tools.mutations import TOOLS, apply_tool


def edit_mission(
    spec: MissionSpec,
    instruction: str,
    theatre: str = "Caucasus",
    model: Optional[str] = None,
    max_turns: int = 20,
) -> MissionSpec:
    """Edit an existing mission spec via interactive tool calls.

    Args:
        spec: The starting MissionSpec to modify
        instruction: Natural-language edit instruction
        theatre: Theatre for catalog lookups
        model: Optional model override
        max_turns: Max LLM turns before force-exit (default 20)

    Returns:
        Modified MissionSpec

    Raises:
        ValueError: If the editor fails to complete within max_turns
    """
    system = build_editor_prompt(
        "agents/prompts/editor.md",
        theatre=theatre,
    )

    client = LLMClient(model=model, role="editor")

    # Check for escalation keywords
    escalation_model = client.check_for_escalation(instruction)
    if escalation_model:
        client.model = escalation_model

    messages: List[Dict[str, Any]] = [
        {"role": "user", "content": format_user_message(instruction, spec=spec)}
    ]

    response: Optional[Dict[str, Any]] = None
    turn = 0
    for turn in range(max_turns):
        response = client.message_with_history(
            system=system,
            messages=messages,
            tools=TOOLS,
            max_tokens=4096,
            temperature=0.3,
        )

        if response["stop_reason"] == "end_turn" or not response.get("tool_calls"):
            break

        assistant_content: List[Dict[str, Any]] = []
        if response.get("content"):
            assistant_content.append({"type": "text", "text": response["content"]})
        for tool_call in response["tool_calls"]:
            assistant_content.append({
                "type": "tool_use",
                "id": tool_call["id"],
                "name": tool_call["name"],
                "input": tool_call["input"],
            })
        messages.append({"role": "assistant", "content": assistant_content})

        tool_results: List[Dict[str, Any]] = []
        for tool_call in response["tool_calls"]:
            try:
                spec, result = apply_tool(spec, tool_call["name"], tool_call["input"])
            except Exception as e:
                result = f"Error: {type(e).__name__}: {e}"
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_call["id"],
                "content": result,
            })
        messages.append({"role": "user", "content": tool_results})

    if response is not None and response["stop_reason"] != "end_turn" and turn >= max_turns - 1:
        raise ValueError(
            f"Editor did not complete within {max_turns} turns. "
            f"Last response: {response['content'][:200]}"
        )

    return spec
