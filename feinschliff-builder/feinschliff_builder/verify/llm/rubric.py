"""LLM rubric callers — return per-slide results, one per rubric class."""
from __future__ import annotations

import base64
import dataclasses
import functools
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from feinschliff.defects import Defect, DefectKind, Severity
from feinschliff_builder.verify.cache import CachedVerdict, VerifyCache, slide_hash
from feinschliff_builder.verify.deck.squint import make_squint_thumbnail
from feinschliff.verify.deck.title_body import extract_slide_title_and_body
from feinschliff.verify.llm import prompts


Status = Literal["pass", "fail", "skipped"]


@dataclasses.dataclass(frozen=True)
class RubricResult:
    rubric: str
    status: Status
    per_slide: list[dict[str, Any]]


@functools.lru_cache(maxsize=1)
def _client():
    """Anthropic SDK client routed via the operator's gateway.

    Refuses to fall back to ``api.anthropic.com`` — see the longer
    rationale in :mod:`feinschliff.verify.llm.rubric._client`. Mirror of
    that function: keep the two in sync if you change the gateway
    contract.
    """
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise SystemExit(
            "verify-quality: anthropic library not installed; "
            "install it with `uv pip install anthropic` or use --offline to skip LLM calls"
        ) from exc
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "").strip()
    if not base_url:
        raise SystemExit(
            "verify-quality: ANTHROPIC_BASE_URL not set — refusing to call "
            "api.anthropic.com directly. Configure your gateway "
            "(ANTHROPIC_BASE_URL + ANTHROPIC_AUTH_TOKEN), or pass --offline "
            "to skip LLM calls."
        )
    auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN", "").strip()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not auth_token and not api_key:
        raise SystemExit(
            "verify-quality: neither ANTHROPIC_AUTH_TOKEN nor ANTHROPIC_API_KEY "
            "is set; use --offline to skip LLM calls"
        )
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


def run_squint(
    deck_path: Path,
    rendered_pngs: dict[int, Path],
    *,
    offline: bool = False,
    cache: VerifyCache | None = None,
    plan: dict | None = None,
    brand: str | None = None,
) -> RubricResult:
    per_slide: list[dict[str, Any]] = []
    for idx, png in sorted(rendered_pngs.items()):
        if offline:
            per_slide.append({"slide_index": idx, "status": "skipped", "reason": "--offline"})
            continue
        # Cache lookup
        h: str | None = None
        if cache is not None and plan is not None and brand is not None:
            slide = plan["slides"][idx - 1]
            h = slide_hash(slide, brand)
            hit = cache.get(h, "squint")
            if hit is not None:
                entry = {"slide_index": idx, **hit.findings, "cached": True}
                entry["slide_index"] = idx  # re-assert: findings may carry a stale index
                per_slide.append(entry)
                continue
        thumb = png.with_name(png.stem + "-thumb.png")
        make_squint_thumbnail(png, thumb, scale=0.25)
        b64 = base64.b64encode(thumb.read_bytes()).decode()
        out = _judge(prompts.squint_prompt(b64))
        if cache is not None and h is not None:
            cache.put(CachedVerdict(
                slide_hash=h,
                rubric="squint",
                status=out.get("status", "fail"),
                findings=out,
                cached_at=datetime.now(timezone.utc).isoformat(),
            ))
        fresh = {"slide_index": idx, **out}
        fresh["slide_index"] = idx  # re-assert: LLM output may contain a slide_index key
        per_slide.append(fresh)
    if cache is not None:
        cache.save()
    status: Status = (
        "skipped" if offline
        else ("fail" if any(p["status"] == "fail" for p in per_slide) else "pass")
    )
    return RubricResult("squint", status, per_slide)


def _run_text_rubric(
    deck_path: Path,
    *,
    rubric_name: str,
    prompt_fn,
    requires_body: bool,
    offline: bool,
    cache: VerifyCache | None = None,
    plan: dict | None = None,
    brand: str | None = None,
) -> RubricResult:
    from pptx import Presentation
    prs = Presentation(str(deck_path))
    per_slide: list[dict[str, Any]] = []
    for idx, _ in enumerate(prs.slides, start=1):
        title, body = extract_slide_title_and_body(deck_path, idx)
        missing = (not title) or (requires_body and not body)
        if missing:
            reason = "empty title or body" if requires_body else "empty title"
            per_slide.append({"slide_index": idx, "status": "skipped", "reason": reason})
            continue
        if offline:
            per_slide.append({"slide_index": idx, "status": "skipped", "reason": "--offline"})
            continue
        # Cache lookup
        h: str | None = None
        if cache is not None and plan is not None and brand is not None:
            slides = plan.get("slides", [])
            if idx - 1 < len(slides):
                h = slide_hash(slides[idx - 1], brand)
                hit = cache.get(h, rubric_name)
                if hit is not None:
                    entry = {"slide_index": idx, **hit.findings, "cached": True}
                    entry["slide_index"] = idx  # re-assert: findings may carry a stale index
                    per_slide.append(entry)
                    continue
        out = _judge(prompt_fn(title, body))
        if cache is not None and h is not None:
            cache.put(CachedVerdict(
                slide_hash=h,
                rubric=rubric_name,
                status=out.get("status", "fail"),
                findings=out,
                cached_at=datetime.now(timezone.utc).isoformat(),
            ))
        fresh = {"slide_index": idx, **out}
        fresh["slide_index"] = idx  # re-assert: LLM output may contain a slide_index key
        per_slide.append(fresh)
    if cache is not None:
        cache.save()
    status: Status = (
        "skipped" if offline or all(p["status"] == "skipped" for p in per_slide)
        else ("fail" if any(p["status"] == "fail" for p in per_slide) else "pass")
    )
    return RubricResult(rubric_name, status, per_slide)


def run_title_body(
    deck_path: Path,
    *,
    offline: bool = False,
    cache: VerifyCache | None = None,
    plan: dict | None = None,
    brand: str | None = None,
) -> RubricResult:
    return _run_text_rubric(
        deck_path, rubric_name="title-body",
        prompt_fn=prompts.title_body_prompt,
        requires_body=True, offline=offline,
        cache=cache, plan=plan, brand=brand,
    )


def run_claim_title(
    deck_path: Path,
    *,
    offline: bool = False,
    cache: VerifyCache | None = None,
    plan: dict | None = None,
    brand: str | None = None,
) -> RubricResult:
    return _run_text_rubric(
        deck_path, rubric_name="claim-title",
        prompt_fn=prompts.claim_title_prompt,
        requires_body=False, offline=offline,
        cache=cache, plan=plan, brand=brand,
    )


def run_bullet_dump(
    deck_path: Path,
    *,
    offline: bool = False,
    cache: VerifyCache | None = None,
    plan: dict | None = None,
    brand: str | None = None,
) -> RubricResult:
    return _run_text_rubric(
        deck_path, rubric_name="bullet-dump",
        prompt_fn=prompts.bullet_dump_prompt,
        requires_body=True, offline=offline,
        cache=cache, plan=plan, brand=brand,
    )


def result_to_defects(r: RubricResult) -> list[Defect]:
    kind_for_rubric = {
        "squint": DefectKind.SQUINT_TEST,
        "title-body": DefectKind.TITLE_BODY_COHERENCE,
        "claim-title": DefectKind.CLAIM_TITLE,
        "bullet-dump": DefectKind.BULLET_DUMP,
    }
    out: list[Defect] = []
    for p in r.per_slide:
        if p["status"] != "fail":
            continue
        out.append(Defect(
            slide_index=p["slide_index"],
            kind=kind_for_rubric[r.rubric],
            severity=Severity.WARN,
            message=p.get("reason", ""),
            meta={"rubric": r.rubric},
        ))
    return out
