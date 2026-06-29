"""LLM client wrapper.

Thin wrapper around the Anthropic SDK that respects the user's LiteLLM proxy
(ANTHROPIC_BASE_URL) and selects models by role.

Usage:
    client = LLMClient(role="designer")
    response = client.message(system=system_text, user=user_text)
"""

import os
from typing import Any, Dict, List, Optional

from anthropic import Anthropic

# Public Anthropic model IDs used when no --model override or proxy is set.
# Override any of these via --model on the CLI / the GUI's Settings dialog,
# or point ANTHROPIC_BASE_URL at a LiteLLM/OpenRouter proxy and pass
# whatever alias your proxy understands.
DEFAULT_MODELS = {
    "designer":         "claude-opus-4-5",    # one-shot quality matters most
    "editor":           "claude-sonnet-4-5",  # many cheap turns, tools constrain
    "campaign_arch":    "claude-opus-4-5",    # cross-mission reasoning
    "template_render":  "claude-sonnet-4-5",  # routine per-mission filling
}

# Models that trigger automatic escalation from editor to designer tier
ESCALATION_KEYWORDS = {"redesign", "rebuild", "rewrite", "restructure"}
ESCALATION_MODEL = "claude-opus-4-5"


class LLMClient:
    """Wraps Anthropic SDK for DCS Agentic Mission Editor.

    All LLM calls go through this class. It handles:
      - Model selection by role
      - LiteLLM proxy URL override
      - System prompt caching
      - Structured output (JSON mode) for mission designer
    """

    def __init__(
        self,
        model: Optional[str] = None,
        role: str = "designer",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """Initialize the LLM client.

        Args:
            model: Specific model alias override. If None, uses DEFAULT_MODELS[role].
            role: Agent role for model selection ("designer", "editor", "campaign_arch", "template_render").
            api_key: Anthropic API key. Defaults to ANTHROPIC_API_KEY env var.
            base_url: Base URL override. Defaults to ANTHROPIC_BASE_URL env var (LiteLLM proxy).
        """
        self.model = model or DEFAULT_MODELS.get(role, "claude-opus-4-7")
        self.role = role

        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not resolved_key.strip():
            raise ValueError(
                "No ANTHROPIC_API_KEY configured. Set the environment variable "
                "or pass api_key to LLMClient()."
            )

        self.client = Anthropic(
            api_key=resolved_key,
            base_url=base_url or os.environ.get("ANTHROPIC_BASE_URL"),
        )

    def message(
        self,
        system: str,
        user: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        cache_system: bool = True,
        max_tokens: int = 8192,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """Send a message to the LLM and return the parsed response.

        Args:
            system: System prompt text
            user: User message text
            tools: Optional list of tool definitions (Anthropic tool-use format)
            cache_system: Whether to mark the system block for prompt caching
            max_tokens: Maximum output tokens
            temperature: Sampling temperature (lower = more deterministic)

        Returns:
            Dict with keys:
              - "content": The text content of the response
              - "tool_calls": List of tool use dicts (if tools were used)
              - "stop_reason": Why the model stopped
              - "usage": Token usage info
        """
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"} if cache_system else None,
                }
            ],
            "messages": [{"role": "user", "content": user}],
        }

        if tools:
            kwargs["tools"] = tools

        response = self.client.messages.create(**kwargs)
        return self._parse_response(response)

    def message_with_history(
        self,
        system: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        cache_system: bool = True,
        max_tokens: int = 8192,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """Send a conversation with history to the LLM.

        Args:
            system: System prompt text
            messages: List of message dicts with "role" and "content" keys
            tools: Optional list of tool definitions
            cache_system: Whether to cache the system prompt
            max_tokens: Maximum output tokens
            temperature: Sampling temperature

        Returns:
            Dict with keys: content, tool_calls, stop_reason, usage
        """
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"} if cache_system else None,
                }
            ],
            "messages": messages,
        }

        if tools:
            kwargs["tools"] = tools

        response = self.client.messages.create(**kwargs)
        return self._parse_response(response)

    def _parse_response(self, response) -> Dict[str, Any]:
        """Parse Anthropic response into a standard dict."""
        content = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                content.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        return {
            "content": "".join(content) if content else "",
            "tool_calls": tool_calls,
            "stop_reason": response.stop_reason,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        }

    def check_for_escalation(self, user_input: str) -> Optional[str]:
        """Check if the user input triggers an escalation to a better model.

        Returns the escalation model alias if triggered, None otherwise.
        """
        lower = user_input.lower()
        if any(kw in lower for kw in ESCALATION_KEYWORDS):
            return ESCALATION_MODEL
        return None
