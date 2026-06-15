"""`feinschliff deck …` subcommands for pipeline-timing logs and parallel
plan authoring (skeleton + merge).

Extracted from cli/deck.py to keep the dispatcher small. These four
subcommands are self-contained — they have no dependency on
feinschliff-builder and import only from the feinschliff core package.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from feinschliff.pipeline_log import (
    log_event,
    read_events,
    render_text_report,
    summarize,
)


def cmd_log_event(args) -> int:
    """`feinschliff deck log-event <phase> <status> --dir <deck-dir>` — used
    by the skill orchestrator (or any shell script) to append a phase
    transition marker to the deck's timing.jsonl.

    Returns 0 always — logging failures must never abort the pipeline.
    """
    extra: dict = {}
    if args.agent:
        extra["agent"] = args.agent
    if args.slide is not None:
        extra["slide"] = args.slide
    if args.note:
        extra["note"] = args.note
    log_event(
        args.dir, args.phase, args.status,
        elapsed_ms=args.elapsed_ms, **extra,
    )
    return 0


def cmd_timing(args) -> int:
    """`feinschliff deck timing <dir>` — render the timing.jsonl as a
    human-readable phase summary, or emit the structured summary as JSON
    via `--format json`."""
    events = read_events(args.dir)
    if not events:
        print(f"deck timing: no timing.jsonl found in {args.dir}", file=sys.stderr)
        return 1
    summary = summarize(events)
    if args.format == "json":
        import json as _json
        print(_json.dumps({"summary": summary, "events": events},
                          indent=2, ensure_ascii=False))
    else:
        print(render_text_report(events, summary), end="")
    return 0


def cmd_plan_skeleton(args) -> int:
    """`feinschliff deck plan-skeleton <content_plan>` — emit an unpicked
    skeleton plan.yaml. One entry per slide, `layout: null`, `content: {}`.

    Layout picking is the orchestrating LLM's job via the cascade in
    `skills/deck/references/picking.md`. It reads each layout's semantic
    annotations (`primary_message`, `when_not_to_use`, `chrome_subject`,
    …) and fills in `layout:` per slide. The deterministic signal-based
    picker that used to seed this skeleton is gone: it was blind to
    semantics and mis-matched pie / Gantt / swatch layouts that
    *structurally* fit. Trust the LLM with the semantic data.
    """
    import json as _json

    cp_path = Path(args.content_plan).resolve()
    if not cp_path.is_file():
        print(f"deck plan-skeleton: not found: {cp_path}", file=sys.stderr)
        return 2
    text = cp_path.read_text(encoding="utf-8")
    plan = (yaml.safe_load(text) if cp_path.suffix in (".yaml", ".yml")
            else _json.loads(text))
    if not isinstance(plan, dict) or not isinstance(plan.get("slides"), list):
        print(f"deck plan-skeleton: {cp_path}: missing `slides` list",
              file=sys.stderr)
        return 2

    brand = args.brand or plan.get("brand") or "feinschliff"
    out_pptx = args.out_pptx or "out/deck.pptx"

    skeleton_slides = [{
        "layout": None,
        "content": {},
        "_meta": {
            "index": slide.get("index"),
            "title": slide.get("title")
                      or slide.get("title_draft")
                      or "(untitled)",
            "role": slide.get("role") or slide.get("purpose"),
            "diagram_kind": slide.get("diagram_kind"),
            "layout_rationale": "cascade:pending",
            "slot_budgets": {},
        },
    } for slide in plan["slides"]]

    out = {"brand": brand, "out": out_pptx, "slides": skeleton_slides}
    out_path = Path(args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        yaml.safe_dump(out, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    log_event(out_path.parent, "skeleton:write", "tick",
              slides=len(skeleton_slides), brand=brand)
    print(f"wrote {out_path} ({len(skeleton_slides)} slides, brand={brand}) "
          f"— layouts unpicked; orchestrator runs the cascade per "
          f"picking.md")
    return 0


def cmd_plan_merge(args) -> int:
    """`feinschliff deck plan-merge --skeleton X --chunk Y --chunk Z -o W` —
    merge authored content chunks (from parallel subagents) into the
    skeleton plan.yaml.

    Each chunk is one of:
      {index: N, content: {...}}                — single slide
      [{index: 0, content: {...}}, {index: 1, ...}]  — multiple slides
      {slides: [...]}                            — plan.yaml-style fragment
    """
    skel_path = Path(args.skeleton).resolve()
    if not skel_path.is_file():
        print(f"deck plan-merge: skeleton not found: {skel_path}", file=sys.stderr)
        return 2
    plan = yaml.safe_load(skel_path.read_text(encoding="utf-8")) or {}
    slides = plan.get("slides") or []
    if not slides:
        print("deck plan-merge: skeleton has no slides", file=sys.stderr)
        return 2

    merged_count = 0
    for chunk_path in args.chunk:
        cp = Path(chunk_path).resolve()
        if not cp.is_file():
            print(f"deck plan-merge: chunk not found: {cp}", file=sys.stderr)
            return 2
        raw = yaml.safe_load(cp.read_text(encoding="utf-8"))
        entries: list[dict] = []
        if isinstance(raw, dict) and isinstance(raw.get("slides"), list):
            entries = raw["slides"]
        elif isinstance(raw, list):
            entries = raw
        elif isinstance(raw, dict) and "content" in raw:
            entries = [raw]
        else:
            print(f"deck plan-merge: {cp}: unrecognized chunk shape",
                  file=sys.stderr)
            return 2
        for entry in entries:
            idx = entry.get("index")
            content = entry.get("content")
            if idx is None or content is None:
                continue
            if not (0 <= idx < len(slides)):
                print(f"deck plan-merge: chunk index {idx} out of range",
                      file=sys.stderr)
                return 2
            slides[idx]["content"] = content
            if "layout" in entry:
                slides[idx]["layout"] = entry["layout"]
            merged_count += 1

    for s in slides:
        s.pop("_meta", None)

    out_path = Path(args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        yaml.safe_dump(plan, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    empty = [i for i, s in enumerate(slides) if not s.get("content")]
    log_event(out_path.parent, "plan-merge", "tick",
              merged=merged_count, total=len(slides), empty=len(empty))
    print(f"wrote {out_path} ({merged_count} chunk entries → "
          f"{len(slides)} slides; {len(empty)} still empty)")
    if empty:
        print(f"  empty slides: {empty}", file=sys.stderr)
        return 1
    return 0


def cmd_plan_budgets(args) -> int:
    """`feinschliff deck plan-budgets <plan.yaml>` — enrich a picked plan.yaml
    with ``_meta.slot_budgets`` per slide.

    Idempotent: re-running overwrites the ``_meta.slot_budgets`` key but
    leaves all other plan content unchanged.  Designed to run just after the
    cascade orchestrator fills in ``layout:`` per slide and before authoring
    fan-out so subagents know which chart slots exist and which ones
    ``must_bind: true``.

    Exits 0 on success, 2 on fatal input errors.
    """

    from feinschliff.deck.orchestrate import slot_budgets_for_layout
    from feinschmiede.brand_discovery import find_brand
    from feinschmiede.dsl.tokens import load_tokens

    plan_path = Path(args.plan).resolve()
    if not plan_path.is_file():
        print(f"deck plan-budgets: not found: {plan_path}", file=sys.stderr)
        return 2

    plan = yaml.safe_load(plan_path.read_text(encoding="utf-8")) or {}
    if not isinstance(plan, dict) or not isinstance(plan.get("slides"), list):
        print(f"deck plan-budgets: {plan_path}: missing `slides` list",
              file=sys.stderr)
        return 2

    brand_name = args.brand or plan.get("brand") or "feinschliff"
    try:
        brand_obj = find_brand(brand_name)
    except ValueError as e:
        print(f"deck plan-budgets: {e}", file=sys.stderr)
        return 2
    brand_root = brand_obj.root
    tokens = load_tokens(brand_root)

    enriched = 0
    for slide in plan["slides"]:
        layout_raw = slide.get("layout")
        if not layout_raw:
            continue
        # Strip path prefix + .slide.dsl suffix to get bare layout name.
        layout_name = Path(layout_raw).stem
        if layout_name.endswith(".slide"):
            layout_name = layout_name[:-len(".slide")]

        budgets = slot_budgets_for_layout(layout_name, brand_root, tokens)
        if "_meta" not in slide or not isinstance(slide["_meta"], dict):
            slide["_meta"] = {}
        slide["_meta"]["slot_budgets"] = budgets
        enriched += 1

    out_path = Path(args.output).resolve() if args.output else plan_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        yaml.safe_dump(plan, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    log_event(plan_path.parent, "plan-budgets", "tick",
              enriched=enriched, brand=brand_name)
    print(f"deck plan-budgets: enriched {enriched} slide(s) → {out_path}")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    """Add the log/timing/plan-skeleton/plan-merge/plan-budgets parsers to `sub`."""
    p_log = sub.add_parser(
        "log-event",
        help="Append one event to the deck's timing.jsonl. Used by the "
             "skill orchestrator to mark phase transitions (start/end).",
    )
    p_log.add_argument("phase", help="Phase name, e.g. 'step:2-plan'.")
    p_log.add_argument("status", choices=["start", "end", "tick", "fail"],
                       help="Event status.")
    p_log.add_argument("--dir", required=True,
                       help="Deck working directory (timing.jsonl lives here).")
    p_log.add_argument("--elapsed-ms", type=int, default=None,
                       help="For 'end' events: elapsed milliseconds.")
    p_log.add_argument("--agent", default=None,
                       help="Optional: agent identifier (for parallel fan-out).")
    p_log.add_argument("--slide", type=int, default=None,
                       help="Optional: slide index this event refers to.")
    p_log.add_argument("--note", default=None,
                       help="Optional one-line note for the event.")
    p_log.set_defaults(func=cmd_log_event)

    p_timing = sub.add_parser(
        "timing",
        help="Print stats from a deck's timing.jsonl — total wall clock, "
             "per-phase breakdown, and parallelism speedup.",
    )
    p_timing.add_argument("dir", help="Deck working directory.")
    p_timing.add_argument("--format", choices=["text", "json"], default="text",
                          help="Output format (default text).")
    p_timing.set_defaults(func=cmd_timing)

    p_skel = sub.add_parser(
        "plan-skeleton",
        help="Centrally pick a layout per slide from a content_plan.json "
             "and emit a skeleton plan.yaml with empty `content:` blocks. "
             "Fan-out authoring subagents fill the blocks in parallel.",
    )
    p_skel.add_argument("content_plan", help="Path to content_plan.json (or .yaml).")
    p_skel.add_argument("-o", "--output", required=True,
                        help="Output path for the skeleton plan.yaml.")
    p_skel.add_argument("--brand", default=None,
                        help="Override brand. Default: from content_plan or 'feinschliff'.")
    p_skel.add_argument("--out-pptx", default=None,
                        help="Sets the `out:` field of the skeleton (final pptx path).")
    p_skel.set_defaults(func=cmd_plan_skeleton)

    p_merge = sub.add_parser(
        "plan-merge",
        help="Merge per-slide content chunks (from parallel authoring "
             "subagents) into the skeleton plan.yaml.",
    )
    p_merge.add_argument("skeleton", help="Path to the skeleton plan.yaml.")
    p_merge.add_argument(
        "--chunk", action="append", default=[],
        metavar="PATH",
        help="One per slide chunk YAML. Each chunk is "
             "{index: N, content: {...}} OR a list of such entries.",
    )
    p_merge.add_argument("-o", "--output", required=True,
                         help="Output path for the merged plan.yaml.")
    p_merge.set_defaults(func=cmd_plan_merge)

    p_budgets = sub.add_parser(
        "plan-budgets",
        help="Enrich a picked plan.yaml with _meta.slot_budgets per slide "
             "(text slots + chart_N_* slots). Idempotent. Run after the cascade "
             "fills layout: and before authoring fan-out.",
    )
    p_budgets.add_argument("plan", help="Path to the plan.yaml (must have layout: per slide).")
    p_budgets.add_argument(
        "-o", "--output", default=None,
        help="Output path. Default: overwrite the input plan in-place.",
    )
    p_budgets.add_argument(
        "--brand", default=None,
        help="Override brand. Default: from plan.brand or 'feinschliff'.",
    )
    p_budgets.set_defaults(func=cmd_plan_budgets)
