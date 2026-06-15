"""In-session LLM-judge contract — feinschliff verify never reaches out.

Verification gates that need LLM judgment (ghost-deck, claim-evidence,
verify-quality rubrics) are scored by the **orchestrating Claude** that
runs the pipeline — the one that already has the brief, the plan, and
the rendered artifacts in its context. The CLI subprocess never
constructs an LLM client and never calls a remote endpoint.

Why this contract:

- A subprocess client would route to whichever endpoint the env points
  at; gateway/key combinations vary by operator and can silently
  misroute (e.g. an OpenRouter ``sk-or-…`` key + an unset
  ``ANTHROPIC_BASE_URL`` → direct call to ``api.anthropic.com`` → 401).
- Duplicating the LLM call inside the subprocess also double-bills the
  same judgment that the orchestrator can produce from its existing
  context — wasteful and harder to audit.
- The orchestrator is the natural judge: it already saw the brief and
  the build artifacts and is the one writing the final report.

How verify gates work under this contract:

1. The CLI gate (e.g. ``feinschliff deck ghost-deck``) writes the prompt
   and any supporting context to ``out/<gate>.prompt.md``.
2. The gate writes a stub ``<gate>_report.md`` with verdict
   ``needs-orchestrator-judgment`` and a brief note pointing at the
   prompt.
3. The CLI exits 0 — the gate ran successfully; its output is the
   prompt, not a verdict.
4. The orchestrating Claude reads the prompt + report, judges in
   session, and overwrites the report with its verdict.

Calling :func:`_judge` directly is a programmer error and raises
``SystemExit``.

See :file:`~/.claude/projects/-Users-mike-work-feinschmiede/memory/
never-direct-anthropic-gemini.md`.
"""
from __future__ import annotations

from typing import Any


def _client():
    """Always raises — verify subprocesses never construct an LLM client.

    Kept as a named symbol so any caller patching it in tests gets a
    clear contract violation instead of a silent no-op.
    """
    raise SystemExit(
        "feinschliff verify does not construct an LLM client. The "
        "orchestrating Claude is the judge — emit the prompt as an "
        "artifact and let the in-session orchestrator write the verdict."
    )


def _judge(prompt: str, model: str | None = None) -> dict[str, Any]:
    """Always raises — see module docstring for the contract.

    Gate code must instead emit ``<gate>.prompt.md`` next to the report
    and stub a ``needs-orchestrator-judgment`` verdict that the
    orchestrator will overwrite.
    """
    raise SystemExit(
        "feinschliff verify does not call an LLM. Write the prompt to "
        "out/<gate>.prompt.md and emit a 'needs-orchestrator-judgment' "
        "stub verdict; the in-session orchestrator will read the prompt "
        "and write the final report."
    )
