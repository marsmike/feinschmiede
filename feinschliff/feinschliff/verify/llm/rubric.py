"""Core LLM judge helper — minimal rubric caller for deck quality gates.

This module provides only `_judge`, the low-level Anthropic API call used
by ghost_deck and claim_evidence. The full rubric suite (squint, title-body,
claim-title, bullet-dump with caching) lives in feinschliff-builder, which
has access to the render artefacts those rubrics need.
"""
from __future__ import annotations

import functools
import json
import os
import re
from typing import Any


@functools.lru_cache(maxsize=1)
def _client():
    """Construct an Anthropic SDK client routed via the operator's gateway.

    Refuses to fall back to ``api.anthropic.com``. The user's shell may carry
    a gateway-issued ``ANTHROPIC_API_KEY`` (e.g. an OpenRouter ``sk-or-…``
    key) that is invalid against Anthropic's API directly — silently
    defaulting to the direct endpoint surfaces as ``Connection error`` or a
    401 from the wrong account. Require explicit gateway config:

    - ``ANTHROPIC_BASE_URL`` — gateway endpoint (e.g.
      ``https://openrouter.ai/api/v1``)
    - ``ANTHROPIC_AUTH_TOKEN`` (preferred) or ``ANTHROPIC_API_KEY`` — bearer
      credential for the gateway

    See :file:`~/.claude/projects/-Users-mike-work-feinschmiede/memory/
    never-direct-anthropic-gemini.md`.
    """
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise SystemExit(
            "verify: anthropic library not installed; "
            "install it with `uv pip install anthropic` or use --offline to skip LLM calls"
        ) from exc
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "").strip()
    if not base_url:
        raise SystemExit(
            "verify: ANTHROPIC_BASE_URL not set — refusing to call api.anthropic.com "
            "directly. Configure your gateway (ANTHROPIC_BASE_URL + "
            "ANTHROPIC_AUTH_TOKEN), or pass --offline to skip LLM calls."
        )
    auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN", "").strip()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not auth_token and not api_key:
        raise SystemExit(
            "verify: neither ANTHROPIC_AUTH_TOKEN nor ANTHROPIC_API_KEY is set; "
            "use --offline to skip LLM calls"
        )
    # Gateway clients prefer auth_token (bearer); api_key is accepted as a
    # fallback for gateways that re-use the x-api-key header.
    if auth_token:
        return Anthropic(base_url=base_url, auth_token=auth_token)
    return Anthropic(base_url=base_url, api_key=api_key)


def _judge(prompt: str, model: str = "claude-haiku-4-5-20251001") -> dict[str, Any]:
    msg = _client().messages.create(
        model=model,
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in msg.content if hasattr(b, "text")).strip()
    text = re.sub(r"^\s*```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?\s*```\s*$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"status": "fail", "reason": f"unparseable: {text[:200]}"}
