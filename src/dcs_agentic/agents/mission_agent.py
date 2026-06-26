"""Mission designer agent — Phase 8.

Single-shot mission creation from natural-language prompts.
Produces a MissionSpec JSON that the assembler validates and saves.

Usage:
    from dcs_agentic.agents.mission_agent import design_mission

    spec = design_mission("2-ship CAP over Batumi", theatre="Caucasus")
"""

from typing import Optional

from ..schemas import MissionSpec
from .llm.client import LLMClient
from .llm.messages import build_system_prompt, format_user_message


def design_mission(
    prompt: str,
    theatre: str = "Caucasus",
    model: Optional[str] = None,
    max_retries: int = 2,
) -> MissionSpec:
    """Design a mission from a natural-language prompt.

    Args:
        prompt: User's natural-language mission description
        theatre: Theatre/map to use for coordinates and airport lookups
        model: Optional model override (e.g. "claude-sonnet-4-6" for GLM)
        max_retries: Number of retries if validation fails (default 2)

    Returns:
        Validated MissionSpec ready for assembly

    Raises:
        ValueError: If the LLM fails to produce valid JSON after all retries
    """
    system = build_system_prompt(
        "agents/prompts/mission_designer.md",
        theatre=theatre,
    )

    client = LLMClient(model=model, role="designer")
    last_error = None

    raw = ""
    for attempt in range(1 + max_retries):
        if attempt == 0:
            user_msg = format_user_message(prompt)
        else:
            user_msg = (
                f"Your previous response could not be parsed as a valid MissionSpec.\n"
                f"Error: {last_error}\n\n"
                f"Previous output:\n```json\n{raw}\n```\n\n"
                f"Original request: {prompt}\n\n"
                f"Return ONLY the corrected MissionSpec JSON, no commentary."
            )

        response = client.message(
            system=system,
            user=user_msg,
            max_tokens=8192,
            temperature=0.3,
        )

        raw = response["content"].strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        try:
            import json
            data = json.loads(raw)
            spec = MissionSpec.model_validate(data)
            return spec
        except Exception as e:
            last_error = str(e)
            continue

    raise ValueError(
        f"Failed to produce valid MissionSpec after {max_retries + 1} attempts. "
        f"Last error: {last_error}\nRaw response: {raw}"
    )
