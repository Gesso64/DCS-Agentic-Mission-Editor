"""Campaign agent — Phase 10.

Designs campaign structure and renders per-mission specs from templates.
The architect runs once per campaign init; the renderer runs per-mission
during campaign execution.

Usage:
    from dcs_agentic.agents.campaign_agent import design_campaign, render_mission

    spec = design_campaign("5-mission strike campaign in Caucasus")
    mission = render_mission(spec, state)  # produces next MissionSpec
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..schemas import CampaignSpec, MissionSpec
from ..schemas.campaign import CampaignState
from .llm.client import LLMClient
from .llm.messages import build_campaign_prompt


def design_campaign(
    prompt: str,
    theatre: str = "Caucasus",
    model: Optional[str] = None,
    max_retries: int = 2,
) -> CampaignSpec:
    """Design a campaign from a natural-language prompt.

    Args:
        prompt: User's campaign description
        theatre: Theatre/map
        model: Optional model override
        max_retries: Retries on validation failure

    Returns:
        CampaignSpec with mission templates

    Raises:
        ValueError: If campaign design fails validation
    """
    system = build_campaign_prompt(
        "agents/prompts/campaign_architect.md",
        theatre=theatre,
    )

    client = LLMClient(model=model, role="campaign_arch")
    last_error = None

    for attempt in range(1 + max_retries):
        response = client.message(
            system=system,
            user=prompt if attempt == 0 else (
                f"The previous attempt failed with:\n{last_error}\n\n"
                f"Please fix and resubmit."
            ),
            max_tokens=8192,
            temperature=0.3,
        )

        raw = response["content"].strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        try:
            data = json.loads(raw)
            spec = CampaignSpec.model_validate(data)
            return spec
        except Exception as e:
            last_error = str(e)
            continue

    raise ValueError(
        f"Failed to produce valid CampaignSpec after {max_retries + 1} attempts. "
        f"Last error: {last_error}"
    )


def render_mission(
    campaign: CampaignSpec,
    state: CampaignState,
    template_dir: str = "campaigns",
    model: Optional[str] = None,
) -> MissionSpec:
    """Render a mission from a campaign template + current state.

    Reads the Jinja2 template for the current mission, renders it with
    the campaign state, and returns a MissionSpec.

    Args:
        campaign: CampaignSpec with mission templates
        state: Current campaign state
        template_dir: Base directory for template files
        model: Optional model override

    Returns:
        MissionSpec ready for assembly
    """
    from jinja2 import Environment, FileSystemLoader, TemplateNotFound

    # Find the current mission link
    current_name = state.current_mission
    mission_link = None
    for m in campaign.missions:
        if m.name == current_name:
            mission_link = m
            break
    if mission_link is None or not mission_link.spec_template:
        raise ValueError(
            f"No template found for mission '{current_name}'"
        )

    # Load and render template
    env = Environment(loader=FileSystemLoader(template_dir))
    try:
        tpl = env.get_template(mission_link.spec_template)
    except TemplateNotFound:
        raise FileNotFoundError(
            f"Template file '{mission_link.spec_template}' not found in '{template_dir}'"
        )

    rendered = tpl.render(
        state=state.model_dump(),
        campaign=campaign.model_dump(),
    )

    data = json.loads(rendered)
    spec = MissionSpec.model_validate(data)
    return spec
