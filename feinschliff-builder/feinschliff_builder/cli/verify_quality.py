"""`feinschliff verify-quality` — render PNGs, run LLM rubric, write report."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from feinschliff_builder.verify.cache import VerifyCache
from feinschliff_builder.verify.llm.rubric import (
    RubricResult, result_to_defects,
    run_bullet_dump, run_claim_title, run_squint, run_title_body,
)


ALL_RUBRICS = ("squint", "title-body", "claim-title", "bullet-dump")


def register(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("deck", type=Path)
    parser.add_argument("--offline", action="store_true",
                        help="Skip LLM calls; emit status='skipped' per slide.")
    parser.add_argument("--no-cache", dest="no_cache", action="store_true",
                        help="Disable per-slide verify cache; re-judge every slide.")
    parser.add_argument("--plan", type=Path, default=None,
                        help="Path to deck_plan.json / plan YAML used to compute slide hashes.")
    parser.add_argument("--brand", default=None,
                        help="Brand name used for cache key (e.g. 'feinschliff').")
    parser.add_argument("--rubric", default=",".join(ALL_RUBRICS),
                        help=f"Comma-separated rubrics to run (default: all). "
                             f"Choices: {','.join(ALL_RUBRICS)}.")
    parser.add_argument("--out", type=Path,
                        help="Where to write the report. Default: alongside deck.")
    parser.add_argument("--json", dest="json_out", action="store_true",
                        help="Emit JSON instead of Markdown.")
    parser.set_defaults(func=cmd_verify_quality)


def cmd_verify_quality(args) -> int:
    deck: Path = args.deck
    if not deck.is_file():
        print(f"verify-quality: {deck} not found", file=sys.stderr)
        return 2

    rubrics = [r.strip() for r in args.rubric.split(",") if r.strip()]
    unknown = set(rubrics) - set(ALL_RUBRICS)
    if unknown:
        print(f"verify-quality: unknown rubric(s): {sorted(unknown)}", file=sys.stderr)
        return 2

    # Cache setup — disabled by --no-cache, or when no --plan is given.
    # VerifyCache is only constructed when caching is actually functional: both
    # flags must be clear AND a resolvable --plan was supplied.  Constructing it
    # when plan is None would cause cache.save() to write an empty dict to disk,
    # silently destroying a previously-populated cache file.
    cache: VerifyCache | None = None
    plan: dict | None = None
    brand: str | None = getattr(args, "brand", None)
    if not getattr(args, "no_cache", False):
        plan_path: Path | None = getattr(args, "plan", None)
        if plan_path is not None and plan_path.is_file():
            plan = _load_plan(plan_path)
    if not getattr(args, "no_cache", False) and plan is not None:
        cache = VerifyCache(deck_dir=deck.parent)

    pngs = _render_slide_pngs(deck) if "squint" in rubrics else {}

    results: dict[str, dict] = {}
    if "squint" in rubrics:
        results["squint"] = run_squint(
            deck, pngs, offline=args.offline,
            cache=cache, plan=plan, brand=brand,
        ).__dict__
    if "title-body" in rubrics:
        results["title-body"] = run_title_body(
            deck, offline=args.offline,
            cache=cache, plan=plan, brand=brand,
        ).__dict__
    if "claim-title" in rubrics:
        results["claim-title"] = run_claim_title(
            deck, offline=args.offline,
            cache=cache, plan=plan, brand=brand,
        ).__dict__
    if "bullet-dump" in rubrics:
        results["bullet-dump"] = run_bullet_dump(
            deck, offline=args.offline,
            cache=cache, plan=plan, brand=brand,
        ).__dict__

    # `suggest_fix` retired with the DSL pipeline (was DSL-plan-shape). The
    # rubric now writes raw defects only; downstream tooling decides how to
    # act on them.
    report_suggested_fixes: list[dict] = []
    _ = result_to_defects  # keep import alive for ABI consumers

    statuses = {r["status"] for r in results.values()}
    if "fail" in statuses:
        verdict = "fail"
    elif statuses == {"skipped"}:
        verdict = "skipped-llm"
    else:
        verdict = "pass"

    report = {
        "deck": str(deck),
        "verdict": verdict,
        "rubric": results,
        "artifacts": {"thumbnails": sorted(str(p) for p in pngs.values())},
        "suggested_fixes": report_suggested_fixes,
    }

    out_path = args.out or deck.with_name("verify_report" + (".json" if args.json_out else ".md"))
    if args.json_out:
        out_path.write_text(json.dumps(report, indent=2, default=_jsonable))
    else:
        out_path.write_text(_render_markdown(report))
    print(f"wrote {out_path} (verdict={verdict})")
    return 0 if verdict in {"pass", "skipped-llm"} else 1


def _render_slide_pngs(deck: Path) -> dict[int, Path]:
    from feinschliff_builder.verify.render_pngs import render_slides_to_png
    out_dir = deck.parent / (deck.stem + ".pngs")
    out_dir.mkdir(exist_ok=True)
    return render_slides_to_png(deck, out_dir)


def _load_plan(plan_path: Path) -> dict:
    """Load a plan file (JSON or YAML) and return it as a dict."""
    text = plan_path.read_text(encoding="utf-8")
    if plan_path.suffix in {".json"}:
        return json.loads(text)
    try:
        import yaml
        return yaml.safe_load(text) or {}
    except ImportError:
        # Fallback: try JSON anyway
        return json.loads(text)


def _jsonable(o):
    if hasattr(o, "to_dict"):
        return o.to_dict()
    if hasattr(o, "__dict__"):
        return o.__dict__
    return str(o)


_RUBRIC_DISPLAY = {
    "squint": "Squint test",
    "title-body": "Title-body coherence",
    "claim-title": "Claim title",
    "bullet-dump": "Bullet dump",
}


def _render_markdown(report: dict) -> str:
    lines = ["# Quality Verify Report", "", f"**Deck:** `{report['deck']}`", "",
             f"**Verdict:** {report['verdict']}", ""]
    for rubric, payload in report["rubric"].items():
        display = _RUBRIC_DISPLAY.get(rubric, rubric.replace("-", " ").title())
        lines.append(f"## {display}")
        lines.append("")
        lines.append(f"Status: **{payload['status']}**")
        for p in payload["per_slide"]:
            lines.append(f"- slide {p['slide_index']}: {p['status']} — {p.get('reason','')}")
        lines.append("")
    fixes = report.get("suggested_fixes", [])
    if fixes:
        lines.append("## Suggested fixes")
        lines.append("")
        for fix in fixes:
            slot = fix.get("slot", "?")
            instr = fix.get("instruction", "")
            lines.append(f"- slide {fix['slide_index']}: slot '{slot}' — {instr}")
        lines.append("")
    return "\n".join(lines) + "\n"
