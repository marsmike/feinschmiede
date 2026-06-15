"""`feinschliff deck …` subcommands: multi-slide composer + layout picker.

Subcommands:

  feinschliff deck build <plan.yaml> [-o OUT.pptx]
      Build one .pptx from a plan that lists N slides, each pinning a
      layout and inline content (or a content file).

  feinschliff deck pick <signals.yaml>
      Print a recommended layout id based on structured signals.

  feinschliff deck wireframe <layout.slide.dsl> --brand <id> [-o out.svg]
      Render a DSL layout as an annotated SVG wireframe (bounding boxes for
      text slots, picture slots, rect backgrounds). No PPTX round-trip needed.
      Add --overlay-pptx <file.pptx> to embed the actual rendered slide behind
      the wireframe boxes for pixel-accurate deviation analysis.

  feinschliff deck wireframe-sheet <plan.yaml> [-o sheet.svg]
      Render every slide in a plan as a wireframe and compose them into a
      single SVG contact sheet. Useful as a fast layout-regression baseline:
      store the SVGs in git, regenerate after DSL changes, and diff.

Plan schema (build):

  brand: feinschliff                       # default brand for slides
  out:   deck.pptx                         # output path; --output overrides
  slides:
    - layout: layouts/title-orange.slide.dsl
      content:
        pgmeta: "Q1 2026"
        title:  "..."
    - layout: layouts/quote.slide.dsl
      content_file: examples/v2/quote.yaml  # alternative to inline
    - layout: brands/gs-ramspau/layouts/stundenplan.slide.dsl
      brand:  gs-ramspau                    # per-slide override
      content_file: brands/gs-ramspau/examples/v2/stundenplan.yaml
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import yaml

from feinschliff.deck.orchestrate import (
    patch_set_hash as _patch_set_hash_fn,
)

from feinschmiede.brand_discovery import find_brand

# Core verify imports — available without feinschliff-builder.
from feinschliff.verify.deck.titles import extract_titles_from_plan
from feinschliff.verify.deck.storyline import render_contact_sheet, write_storyline_report
from feinschliff.verify.deck.claim_evidence import judge_plan, write_report as write_claim_evidence_report
from feinschliff.verify.deck.ghost_deck import judge_ghost_deck, write_ghost_deck_report
from feinschliff.verify.deck.title_lint import lint_titles
from feinschliff.pipeline_log import log_event


def _bundled_assets() -> Path:
    """Return the assets/ directory shipped inside this plugin."""
    return Path(__file__).resolve().parents[1] / "assets"


def _bundled_compounds() -> Path:
    """Return the compounds/ directory shipped inside the feinschmiede engine."""
    import feinschmiede

    return Path(feinschmiede.__file__).resolve().parent / "compounds"


def _find_toolkit_file(rel: str) -> Path | None:
    """Resolve *rel* against each discovered layout dir's parent (i.e. the
    plugin root), returning the first match.  Used to replace hard-coded
    ``REPO_ROOT / rel`` fallback lookups in the deck CLI.
    """
    from feinschliff.layout_discovery import all_layout_dirs
    for layout_dir in all_layout_dirs():
        candidate = (layout_dir.parent / rel).resolve()
        if candidate.is_file():
            return candidate
    return None


def register(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="deck_command", required=True)




    p_intake_v = sub.add_parser(
        "intake-validate",
        help="Validate a deck_brief.yaml against the schema. "
             "Exit 0 = valid, 1 = invalid (errors to stderr), 2 = plumbing.",
    )
    p_intake_v.add_argument("brief", help="Path to deck_brief.yaml")
    p_intake_v.set_defaults(func=cmd_intake_validate)

    p_intake_s = sub.add_parser(
        "intake-skeleton",
        help="Emit a deck_brief.yaml skeleton seeded by heuristic "
             "inference. The orchestrating skill fills the remaining "
             "fields via AskUserQuestion before writing the final brief.",
    )
    p_intake_s.add_argument(
        "--brief", default=None,
        help="Optional brief text, or a path to a brief file. "
             "When supplied, infer_from_text seeds known fields.",
    )
    p_intake_s.add_argument(
        "-o", "--output", default=None,
        help="Output path. Default: stdout.",
    )
    p_intake_s.set_defaults(func=cmd_intake_skeleton)

    p_commit_v = sub.add_parser(
        "commitment-validate",
        help="Validate a commitment.yaml against the schema and "
             "(optionally) cross-check arc-alignment against the matching "
             "deck_type arc schema. Exit 0 clean / 1 invalid / 2 plumbing.",
    )
    p_commit_v.add_argument("commitment", help="Path to commitment.yaml")
    p_commit_v.add_argument(
        "--check-arc",
        action="store_true",
        help="Also run check_arc_alignment against the loaded arc schema "
             "for the commitment's deck_type.",
    )
    p_commit_v.set_defaults(func=cmd_commitment_validate)

    p_storyline = sub.add_parser(
        "storyline",
        help="Emit a title-only contact sheet from a deck_plan.json / "
             "content_plan.json (Phase 2 storyline gate).",
    )
    p_storyline.add_argument("plan", help="Path to deck_plan.json or content_plan.json")
    p_storyline.add_argument(
        "-o", "--output", required=True,
        help="Output path for the storyline_report.md",
    )
    p_storyline.add_argument(
        "--brief-summary", default=None,
        help="Optional one-line summary shown above the contact sheet.",
    )
    p_storyline.set_defaults(func=cmd_storyline)

    p_ce = sub.add_parser(
        "claim-evidence",
        help="Mid-plan claim-evidence text gate (step 2b). "
             "Judges each claim-carrying slide for title-body coherence "
             "before render. Cheap Haiku pass, no PPTX round-trip.",
    )
    p_ce.add_argument("plan", help="Path to plan.yaml or plan.json")
    p_ce.add_argument(
        "--design-brief",
        default=None,
        help="Path to design_brief.json (optional — enables per-slide claim hints).",
    )
    p_ce.add_argument(
        "-o", "--output", required=True,
        help="Output path for claim_evidence_report.md",
    )
    p_ce.add_argument(
        "--offline", action="store_true",
        help="Skip all LLM calls; return clean verdicts (for testing).",
    )
    p_ce.add_argument(
        "--model", default="claude-haiku-4-5-20251001",
        help="Model to use for judgment (default: claude-haiku-4-5-20251001).",
    )
    p_ce.set_defaults(func=cmd_claim_evidence)

    p_gd = sub.add_parser(
        "ghost-deck",
        help="Ghost-deck title-strip check: judge whether slide titles tell a "
             "coherent argument without body content. Exit 0 = pass/warn, 1 = fail, "
             "2 = plumbing.",
    )
    p_gd.add_argument(
        "plan",
        help="Path to plan.yaml (or a flat YAML list of titles).",
    )
    p_gd.add_argument(
        "-o", "--output", required=True,
        help="Output path for ghost_deck_report.md.",
    )
    p_gd.add_argument(
        "--offline", action="store_true",
        help="Skip all LLM calls; return a pass verdict (for CI without keys).",
    )
    p_gd.add_argument(
        "--model", default="claude-haiku-4-5-20251001",
        help="Model to use for judgment (default: claude-haiku-4-5-20251001).",
    )
    p_gd.set_defaults(func=cmd_ghost_deck)

    p_tl = sub.add_parser(
        "title-lint",
        help="Deterministic title rules: empty, too-long, no-verb, and-conjunction. "
             "Zero LLM. Exit 0 = clean, 1 = issues found, 2 = plumbing.",
    )
    p_tl.add_argument(
        "plan",
        help="Path to plan.yaml (or a flat YAML list of titles).",
    )
    p_tl.add_argument(
        "-o", "--output", required=True,
        help="Output path for title_lint_report.md.",
    )
    p_tl.add_argument(
        "--json", dest="emit_json", action="store_true",
        help="Emit issues as a JSON array to stdout instead of a markdown report.",
    )
    p_tl.set_defaults(func=cmd_title_lint)




    p_book = sub.add_parser(
        "book",
        help="Render an annotated speaker-book PDF from a deck plan + "
             "design brief. Front matter (takeaway, audience, frame, "
             "red_line, hook) + one page per slide with the rendered "
             "thumbnail, claim, speaker notes, audience_fit, and role.",
    )
    p_book.add_argument("plan", help="Path to the deck plan YAML.")
    p_book.add_argument(
        "--design-brief", required=True,
        help="Path to design_brief.json (front matter + per-slide role / "
             "audience_fit come from here).",
    )
    p_book.add_argument(
        "--pptx", default=None,
        help="Path to the rendered .pptx (used to extract per-slide PNG "
             "thumbnails). If omitted, the book is rendered without "
             "thumbnails — useful for fast preview while authoring.",
    )
    p_book.add_argument(
        "-o", "--output", required=True,
        help="Output path for the speaker-book .pdf.",
    )
    p_book.set_defaults(func=cmd_book)

    # `deck plan` is a thin alias for `deck storyline` — same CLI surface,
    # same handler. The mode-level work (steps 0 → 1c only, no render) is
    # the skill orchestrator's job; the CLI part is just the storyline
    # report materialization helper. See
    # skills/deck/references/modes.md::plan for the mode semantics.
    p_plan = sub.add_parser(
        "plan",
        help="Emit a title-only storyline report (alias for `deck storyline`). "
             "Implements the CLI surface of the /deck plan mode — steps 0 → 1c "
             "only, no render. See skills/deck/references/modes.md::plan.",
    )
    p_plan.add_argument("plan", help="Path to deck_plan.json or content_plan.json")
    p_plan.add_argument(
        "-o", "--output", required=True,
        help="Output path for the storyline_report.md",
    )
    p_plan.add_argument(
        "--brief-summary", default=None,
        help="Optional one-line summary shown above the contact sheet.",
    )
    p_plan.set_defaults(func=cmd_storyline)

    # ── Pipeline timing logs + parallel plan authoring ──────────────────
    # (`log-event`, `timing`, `plan-skeleton`, `plan-merge`) — extracted
    # into deck_subcommands/plan_log.py to keep this file from growing.
    from feinschliff.cli.deck_subcommands import plan_log
    plan_log.register(sub)

    # ── Parallel-verify aspect helpers ──────────────────────────────────
    p_aspect = sub.add_parser(
        "verify-aspect",
        help="Run one focused verify aspect on a built deck. Each aspect "
             "is independently runnable; spawning multiple aspects in "
             "parallel + collating gives the parallel-verify path.",
    )
    p_aspect.add_argument(
        "aspect",
        choices=["bbox", "font", "narrative", "brand", "image", "content",
                 "notes-coherence"],
        help="bbox = bounding-box / overflow; font = legibility / role "
             "mismatches; narrative = SCQA / claim-title across titles; "
             "brand = color contrast / token discipline; image = picture "
             "slot fit / style consistency; content = title-body coherence; "
             "notes-coherence = per-slide speaker notes track the deck's "
             "red_line.",
    )
    p_aspect.add_argument("--plan", required=True,
                          help="Path to the deck plan.yaml.")
    p_aspect.add_argument("--pptx", default=None,
                          help="Path to the built .pptx (required for bbox/font/brand/image).")
    p_aspect.add_argument("--png-dir", default=None,
                          help="Directory with rendered slide-NN.png files.")
    p_aspect.add_argument("--design-brief", default=None,
                          help="Path to design_brief.json (used by narrative).")
    p_aspect.add_argument("-o", "--output", required=True,
                          help="Output path for verify-<aspect>.json.")
    p_aspect.set_defaults(func=cmd_verify_aspect)

    p_vs = sub.add_parser(
        "verify-static",
        help="Pre-render static geometry verify: detect slot-overflow and "
             "empty-placeholder defects from a plan.yaml without rendering. "
             "Exit 0 = clean, 1 = defects found, 2 = plumbing error.",
    )
    p_vs.add_argument("plan", help="Path to the deck plan YAML")
    p_vs.add_argument(
        "--json",
        action="store_true",
        help="Emit defects as a JSON array to stdout instead of the human "
             "readable format. Shape: [{slide_index, kind, severity, "
             "message, meta}, ...]",
    )
    p_vs.add_argument(
        "--brand", default=None,
        help="Override brand. Default: from plan.brand or 'feinschliff'.",
    )
    p_vs.set_defaults(func=cmd_verify_static)


    p_collate = sub.add_parser(
        "verify-collate",
        help="Merge per-aspect verify outputs into a single verify_report.md.",
    )
    p_collate.add_argument(
        "--aspect", action="append", default=[], metavar="PATH",
        help="One per aspect: path to a verify-<aspect>.json file.",
    )
    p_collate.add_argument("--plan", required=True,
                           help="Path to the deck plan.yaml (for slide titles).")
    p_collate.add_argument("--iteration", type=int, default=1,
                           help="Iteration number (header field).")
    p_collate.add_argument("--budget", type=int, default=3,
                           help="Iteration budget (header field).")
    p_collate.add_argument("--png-dir", default=None,
                           help="PNG directory (header reference).")
    p_collate.add_argument("-o", "--output", required=True,
                           help="Output path for verify_report.md.")
    p_collate.set_defaults(func=cmd_verify_collate)


def _patch_set_hash(patches: list) -> str:
    """Delegate to feinschliff.deck.orchestrate.patch_set_hash."""
    return _patch_set_hash_fn(patches)


def cmd_intake_validate(args) -> int:
    """Validate a deck_brief.yaml against the intake schema."""
    from feinschliff.intake import load_brief

    path = Path(args.brief).resolve()
    if not path.is_file():
        print(f"deck: deck_brief not found: {path}", file=sys.stderr)
        return 2
    try:
        load_brief(path)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    print(f"deck: deck_brief OK ({path})")
    return 0


def cmd_commitment_validate(args) -> int:
    """Validate commitment.yaml; optionally cross-check arc alignment."""
    from feinschliff.storyline import (
        check_arc_alignment,
        load_all_arcs,
        load_commitment,
    )

    path = Path(args.commitment).resolve()
    if not path.is_file():
        print(f"deck: commitment not found: {path}", file=sys.stderr)
        return 2
    try:
        commitment = load_commitment(path)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    if args.check_arc:
        arcs = load_all_arcs()
        arc = arcs.get(commitment["deck_type"])
        if arc is None:
            print(
                f"deck: no arc schema for deck_type={commitment['deck_type']!r}",
                file=sys.stderr,
            )
            return 1
        misses = check_arc_alignment(commitment, arc)
        if misses:
            for m in misses:
                print(f"deck: arc: {m}", file=sys.stderr)
            return 1
    print(f"deck: commitment OK ({path})")
    return 0


def cmd_intake_skeleton(args) -> int:
    """Emit a deck_brief.yaml skeleton seeded by heuristic inference."""
    from feinschliff.intake import empty_brief, infer_from_text

    brief = empty_brief()
    if args.brief:
        brief_text = args.brief
        candidate = Path(args.brief)
        if candidate.is_file():
            brief_text = candidate.read_text()
        brief.update(infer_from_text(brief_text))
    out_yaml = yaml.safe_dump(brief, allow_unicode=True, sort_keys=False)
    if args.output:
        Path(args.output).write_text(out_yaml)
        print(f"deck: wrote skeleton to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out_yaml)
    return 0


def cmd_book(args) -> int:
    """`feinschliff deck book` — annotated speaker-book PDF.

    Loads the deck plan + design brief, optionally renders per-slide
    PNG thumbnails from the built .pptx (via the existing
    `feinschliff_builder.verify.render_pngs.render_slides_to_png` helper), and writes a
    multi-page PDF: front matter page + one page per slide.

    The brief is the source of truth for deck-level fields (takeaway,
    audience, frame, …) and per-slide role / audience_fit. Speaker
    notes come from the plan's per-slide `notes:` field (preferred);
    when absent, the brief's per-slide `notes` is used as fallback.
    """
    import json as _json
    import tempfile as _tempfile

    from feinschliff.book import (
        BookSlide, DeckFrontMatter, compose_book_pdf,
    )
    from feinschliff_builder.verify.render_pngs import render_slides_to_png

    plan_path = Path(args.plan).resolve()
    brief_path = Path(args.design_brief).resolve()
    out_path = Path(args.output).resolve()

    if not plan_path.is_file():
        print(f"deck book: plan not found: {plan_path}", file=sys.stderr)
        return 2
    if not brief_path.is_file():
        print(f"deck book: design_brief not found: {brief_path}",
              file=sys.stderr)
        return 2

    plan = yaml.safe_load(plan_path.read_text()) or {}
    brief = _json.loads(brief_path.read_text(encoding="utf-8"))

    front = DeckFrontMatter(
        takeaway=brief.get("takeaway", ""),
        audience=brief.get("audience", ""),
        audience_notes=brief.get("audience_notes", ""),
        frame=brief.get("frame", ""),
        frame_rationale=brief.get("frame_rationale", ""),
        red_line=brief.get("red_line", ""),
        hook_technique=(brief.get("hook") or {}).get("technique", ""),
        hook_opener=(brief.get("hook") or {}).get("opener", ""),
        deck_title=brief.get("takeaway") or plan.get("title"),
    )

    # Optional thumbnail render. The PDF is still useful without —
    # the speaker reads notes + claims even when the .pptx isn't
    # built yet (early-iteration mode).
    thumbnails: dict[int, Path] = {}
    tmp_ctx = None
    if args.pptx:
        pptx_path = Path(args.pptx).resolve()
        if pptx_path.is_file():
            tmp_ctx = _tempfile.TemporaryDirectory()
            thumbnails = render_slides_to_png(pptx_path, Path(tmp_ctx.name))
        else:
            print(f"deck book: --pptx not found, skipping thumbnails: "
                  f"{pptx_path}", file=sys.stderr)

    plan_slides = plan.get("slides") or []
    brief_slides = {int(s.get("index", 0)): s
                    for s in (brief.get("slides") or [])}

    book_slides: list[BookSlide] = []
    for i, spec in enumerate(plan_slides):
        brief_s = brief_slides.get(i, {})
        content = spec.get("content") or {}
        claim = (brief_s.get("claim")
                 or content.get("title")
                 or content.get("action_title")
                 or "")
        notes = spec.get("notes") or brief_s.get("notes") or ""
        thumb = thumbnails.get(i + 1)  # render_slides_to_png is 1-based
        book_slides.append(BookSlide(
            index=i,
            role=brief_s.get("role", ""),
            claim=claim,
            notes=notes,
            audience_fit=brief_s.get("audience_fit", ""),
            thumbnail_path=thumb,
            section_label=spec.get("section"),
        ))

    try:
        compose_book_pdf(front, book_slides, out_path)
    finally:
        if tmp_ctx is not None:
            tmp_ctx.cleanup()

    print(f"wrote {out_path} ({len(book_slides)} slide page(s) + 1 "
          f"front-matter page; thumbnails: "
          f"{'yes' if thumbnails else 'no'})")
    return 0


def cmd_storyline(args) -> int:
    plan_path = Path(args.plan).resolve()
    out_path = Path(args.output).resolve()
    try:
        titles = extract_titles_from_plan(plan_path)
    except FileNotFoundError as exc:
        print(f"deck storyline: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"deck storyline: {exc}", file=sys.stderr)
        return 2

    contact_sheet = render_contact_sheet(titles, brief_summary=args.brief_summary)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_storyline_report(out_path, contact_sheet=contact_sheet)
    print(f"wrote {out_path} ({len([t for t in titles if t])} non-empty title(s) "
          f"across {len(titles)} slide(s))")
    return 0


def cmd_claim_evidence(args) -> int:
    """``feinschliff deck claim-evidence`` — mid-plan claim-evidence gate.

    Exit codes:
    - 0: clean (all judged slides pass)
    - 1: dirty (at least one slide has a claim-evidence defect)
    - 2: plumbing error (plan not found, parse failure, etc.)
    """
    plan_path = Path(args.plan).resolve()
    out_path = Path(args.output).resolve()

    # Load plan
    try:
        plan_text = plan_path.read_text()
    except FileNotFoundError as exc:
        print(f"deck claim-evidence: {exc}", file=sys.stderr)
        return 2

    try:
        plan: dict = yaml.safe_load(plan_text) or {}
    except Exception as exc:  # noqa: BLE001
        print(f"deck claim-evidence: failed to parse plan: {exc}", file=sys.stderr)
        return 2

    # Load optional design brief
    design_brief: dict | None = None
    if args.design_brief:
        brief_path = Path(args.design_brief).resolve()
        try:
            import json as _json
            brief_text = brief_path.read_text()
            # Accept both JSON and YAML
            try:
                design_brief = _json.loads(brief_text)
            except _json.JSONDecodeError:
                design_brief = yaml.safe_load(brief_text) or {}
        except FileNotFoundError as exc:
            print(f"deck claim-evidence: {exc}", file=sys.stderr)
            return 2
        except Exception as exc:  # noqa: BLE001
            print(f"deck claim-evidence: failed to parse design brief: {exc}", file=sys.stderr)
            return 2

    slide_count = len(plan.get("slides") or [])

    try:
        results = judge_plan(
            plan,
            design_brief=design_brief,
            offline=args.offline,
            model=args.model,
        )
    except SystemExit:
        raise  # propagate ANTHROPIC_API_KEY error
    except Exception as exc:  # noqa: BLE001
        print(f"deck claim-evidence: judgment failed: {exc}", file=sys.stderr)
        return 2

    # Token-cost estimate (AC6)
    judged_count = len(results)
    if not args.offline and results:
        from feinschliff.verify.llm.prompts import claim_evidence_prompt
        # Rough estimate: average prompt length × slides judged / 4 chars/token
        sample_prompt = claim_evidence_prompt("Sample title", "Sample body text.")
        avg_tokens_per_slide = len(sample_prompt) // 4
        total_k = (avg_tokens_per_slide * judged_count) // 1000
        print(
            f"claim-evidence: {judged_count} slides judged, "
            f"~{max(total_k, 1)}k input tokens via {args.model}",
            file=sys.stderr,
        )
    else:
        print(
            f"claim-evidence: {judged_count} slides judged (--offline, 0 tokens)",
            file=sys.stderr,
        )

    overall = write_claim_evidence_report(out_path, results, slide_count=slide_count)
    print(f"wrote {out_path} (verdict: {overall}, {judged_count} judged / {slide_count} total)")

    return 0 if overall == "clean" else 1


def _load_titles_from_path(path: Path) -> list[str]:
    """Load titles from *path*.

    Accepts two shapes:
    - A plan YAML with a top-level ``slides`` list (delegated to
      ``extract_titles_from_plan``).
    - A flat YAML list of strings (titles directly).

    Raises ``FileNotFoundError`` or ``ValueError`` on bad input.
    """
    if not path.is_file():
        raise FileNotFoundError(f"file not found: {path}")
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if isinstance(data, list):
        # Flat list of titles
        return [str(t).strip() if t else "" for t in data]
    if isinstance(data, dict) and "slides" in data:
        # Plan-YAML shape — delegate to extract_titles_from_plan
        return extract_titles_from_plan(path)
    raise ValueError(
        f"unrecognised shape: expected a plan YAML with `slides:` or a flat list of titles ({path})"
    )


def cmd_ghost_deck(args) -> int:
    """``feinschliff deck ghost-deck`` — narrative coherence check on titles.

    Exit codes:
    - 0: pass or warn (titles form a coherent story, or minor issues only)
    - 1: fail (significant narrative gaps detected)
    - 2: plumbing error (file not found, parse failure, etc.)
    """
    plan_path = Path(args.plan).resolve()
    out_path = Path(args.output).resolve()

    try:
        titles = _load_titles_from_path(plan_path)
    except FileNotFoundError as exc:
        print(f"deck ghost-deck: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"deck ghost-deck: {exc}", file=sys.stderr)
        return 2

    try:
        result = judge_ghost_deck(titles, offline=args.offline, model=args.model)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"deck ghost-deck: judgment failed: {exc}", file=sys.stderr)
        return 2

    write_ghost_deck_report(result, out_path)
    issue_count = len(result.issues)
    print(
        f"wrote {out_path} "
        f"(verdict: {result.verdict}, {issue_count} issue(s), {len(titles)} title(s))"
    )
    return 1 if result.verdict == "fail" else 0


def cmd_title_lint(args) -> int:
    """``feinschliff deck title-lint`` — deterministic title rules, zero LLM.

    Exit codes:
    - 0: clean (no issues)
    - 1: issues found (at least one warn or fail)
    - 2: plumbing error (file not found, parse failure, etc.)
    """
    import json as _json

    plan_path = Path(args.plan).resolve()
    out_path = Path(args.output).resolve()

    try:
        titles = _load_titles_from_path(plan_path)
    except FileNotFoundError as exc:
        print(f"deck title-lint: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"deck title-lint: {exc}", file=sys.stderr)
        return 2

    issues = lint_titles(titles)

    if getattr(args, "emit_json", False):
        import dataclasses
        sys.stdout.write(_json.dumps([dataclasses.asdict(i) for i in issues], indent=2) + "\n")
    else:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fail_count = sum(1 for i in issues if i.severity == "fail")
        warn_count = sum(1 for i in issues if i.severity == "warn")
        parts: list[str] = [
            f"# Title Lint — {len(titles)} titles",
            "",
            f"**Issues:** {len(issues)} ({fail_count} fail, {warn_count} warn)",
            "",
        ]
        if not issues:
            parts.append("_No issues._")
        else:
            for iss in issues:
                parts.append(f"- [{iss.severity.upper()}] `{iss.rule}` — {iss.message}")
        out_path.write_text("\n".join(parts) + "\n", encoding="utf-8")
        print(
            f"wrote {out_path} "
            f"({len(issues)} issue(s) across {len(titles)} title(s))"
        )

    return 1 if issues else 0


# ──────────────────────────────────────────────────────────────────────────────
# Parallel verify — focused aspect checks
# ──────────────────────────────────────────────────────────────────────────────

def cmd_verify_aspect(args) -> int:
    """`feinschliff deck verify-aspect <aspect> --plan plan.yaml -o out.json`

    Each aspect runs an independent narrow check. Designed to be spawned
    as one subagent per aspect — N aspects run in parallel, then
    `verify-collate` merges them into a single verify_report.md.

    Implementation note: aspects that need LLM judgment (narrative,
    image-style, content-cohesion) currently emit a stub finding entry
    pointing the orchestrator at the relevant PNGs/files. The deterministic
    aspects (bbox, font, brand) emit actual findings. The orchestrator
    fills LLM-judged aspects via subagent dispatch.
    """
    import json as _json
    aspect = args.aspect
    plan_path = Path(args.plan).resolve()
    plan = yaml.safe_load(plan_path.read_text(encoding="utf-8")) or {}
    slides = plan.get("slides") or []

    out: dict = {
        "aspect": aspect,
        "plan": str(plan_path),
        "iteration_check_ms": None,
        "findings": [],  # list of {slide, kind, message, severity, hint}
        "summary": "",
        "needs_llm": False,
    }

    _t0 = time.perf_counter()

    if aspect == "bbox":
        # Deterministic: re-run feinschliff verify on the plan, surface
        # text-overflow / out-of-bounds / diagram-overflow defects.
        from feinschliff.pipeline import compile_slide
        import tempfile

        with tempfile.TemporaryDirectory() as _tmp:
            diagrams_out = Path(_tmp) / "diagrams"
            diagrams_out.mkdir()
            for i, spec in enumerate(slides):
                layout_path = (plan_path.parent / spec["layout"]).resolve()
                if not layout_path.is_file():
                    layout_path = _find_toolkit_file(spec["layout"]) or layout_path
                try:
                    brand_dir = find_brand(spec.get("brand")
                                           or plan.get("brand")
                                           or "feinschliff").root
                except ValueError:
                    continue
                try:
                    r = compile_slide(  # noqa: F821 (DSL-era subcommand, retired)
                        layout_path=layout_path,
                        ctx=spec.get("content") or {},
                        brand_dir=brand_dir,
                        slide_index=i + 1,
                        diagrams_out_dir=diagrams_out,
                    )
                except Exception as e:
                    out["findings"].append({
                        "slide": i + 1, "kind": "compile-error",
                        "severity": "fatal",
                        "message": str(e)[:200], "hint": "see plan.yaml",
                    })
                    continue
                for d in r.defects:
                    out["findings"].append({
                        "slide": i + 1, "kind": d.kind.value,
                        "severity": d.severity.value,
                        "message": d.message[:240], "hint": "",
                    })

    elif aspect == "font":
        # Deterministic-ish: surface diagram-text-too-small from build,
        # plus a hint pointing the orchestrator at any slide where a text
        # primitive uses role=detail (most fragile per past runs).
        for i, spec in enumerate(slides):
            dsl = (spec.get("content") or {}).get("diagram_dsl") or ""
            if "size:detail" in dsl or " detail " in dsl:
                out["findings"].append({
                    "slide": i + 1, "kind": "detail-role-fragile",
                    "severity": "warn",
                    "message": "Diagram uses role=detail — close to the 10pt floor "
                               "after region/slide scaling; consider promoting to body.",
                    "hint": "search the diagram_dsl for `size:detail` or `detail `",
                })

    elif aspect == "narrative":
        # Reads titles + design_brief + storyline_report (if present).
        # The actual SCQA / claim-title judgment is LLM work; emit a
        # contact-sheet snapshot for the orchestrator subagent.
        titles = [
            (s.get("content") or {}).get("title")
            or (s.get("content") or {}).get("action_title")
            or s.get("_meta", {}).get("title", "?")
            for s in slides
        ]
        out["needs_llm"] = True
        out["contact_sheet"] = list(enumerate(titles, start=1))
        if args.design_brief:
            db = Path(args.design_brief).resolve()
            if db.is_file():
                try:
                    out["design_brief"] = _json.loads(db.read_text(encoding="utf-8"))
                except _json.JSONDecodeError:
                    pass

    elif aspect == "brand":
        # Deterministic-ish: scan diagram_dsl for fill tokens brand_bridge
        # can't resolve (semantic names + the upstream Excalidraw aliases).
        # Brand pack discipline check.
        from feinschmiede.diagrams.brand_bridge import SEMANTIC_NAMES
        from feinschmiede.diagrams.excalidraw_expand import _COLOR_ALIASES
        canonical = SEMANTIC_NAMES | frozenset(_COLOR_ALIASES)
        import re
        for i, spec in enumerate(slides):
            dsl = (spec.get("content") or {}).get("diagram_dsl") or ""
            for m in re.finditer(r"fill:([a-z0-9_-]+)", dsl):
                tok = m.group(1)
                if tok not in canonical:
                    out["findings"].append({
                        "slide": i + 1, "kind": "non-canonical-token",
                        "severity": "warn",
                        "message": f"Diagram uses fill:{tok}, not in the "
                                   f"{len(canonical)}-name semantic vocabulary.",
                        "hint": "use one of: " + ", ".join(sorted(canonical)[:10]) + ", …",
                    })

    elif aspect == "image":
        # Picture-slot presence + style consistency check. Surfaces slides
        # that declare an image_style but have no picture slot, or
        # vice-versa. LLM verification of actual style match is a separate
        # subagent step (needs_llm=True).
        if args.design_brief:
            try:
                db = _json.loads(Path(args.design_brief).read_text(encoding="utf-8"))
                out["image_style"] = db.get("image_style")
            except (OSError, _json.JSONDecodeError):
                pass
        out["needs_llm"] = True
        for i, spec in enumerate(slides):
            c = spec.get("content") or {}
            has_pic = any(k in c for k in ("hero_image", "picture", "image", "photo"))
            if has_pic and not out.get("image_style"):
                out["findings"].append({
                    "slide": i + 1, "kind": "image-style-undeclared",
                    "severity": "warn",
                    "message": "Slide uses a picture slot but design_brief.image_style "
                               "is unset.",
                    "hint": "set image_style in design_brief.json",
                })

    elif aspect == "content":
        # Title-body coherence + filler-word lint. Deterministic part:
        # scan body slots for filler words. LLM part: claim/proof match.
        FILLER = {"basically", "actually", "really", "very", "just", "simply", "in order to"}
        out["needs_llm"] = True
        for i, spec in enumerate(slides):
            c = spec.get("content") or {}
            for key in ("body", "supporting_body", "so_what"):
                val = c.get(key) or ""
                if not isinstance(val, str):
                    continue
                low = val.lower()
                hits = [w for w in FILLER if w in low]
                if hits:
                    out["findings"].append({
                        "slide": i + 1, "kind": "filler-word",
                        "severity": "warn",
                        "message": f"{key} contains filler: {', '.join(hits)}",
                        "hint": "Cut the filler — strong sentences don't need it.",
                    })

    elif aspect == "notes-coherence":
        # Pair the deck's red_line against each slide's (claim, notes).
        # The orchestrator LLM judges whether the spoken delivery tracks
        # the arc: drift / contradiction / off-arc tangents → dirty.
        from feinschliff.verify.deck.notes_coherence import (
            SlideForCoherence,
            render_contact_sheet as _render_notes_sheet,
        )
        out["needs_llm"] = True
        red_line = ""
        if args.design_brief:
            db_path = Path(args.design_brief).resolve()
            if db_path.is_file():
                try:
                    db = _json.loads(db_path.read_text(encoding="utf-8"))
                    red_line = db.get("red_line", "") or ""
                    out["red_line"] = red_line
                    out["design_brief"] = db
                except _json.JSONDecodeError:
                    pass
        coherence_slides: list[SlideForCoherence] = []
        for i, spec in enumerate(slides):
            c = spec.get("content") or {}
            coherence_slides.append(SlideForCoherence(
                index=i,
                role=spec.get("_meta", {}).get("role", ""),
                claim=c.get("title") or c.get("action_title") or "",
                notes=spec.get("notes"),
            ))
        # Cheap deterministic pre-flag: hook slide missing notes.
        # The LLM judge handles drift / off-arc semantics.
        if coherence_slides and not (coherence_slides[0].notes or "").strip():
            out["findings"].append({
                "slide": 1, "kind": "hook-notes-missing",
                "severity": "warn",
                "message": "Hook slide has no speaker notes; expected the "
                           "deck-level storyline articulating the red_line.",
                "hint": "Author the full red_line arc into slide 1's notes.",
            })
        out["contact_sheet"] = _render_notes_sheet(red_line, coherence_slides)

    out["iteration_check_ms"] = int(
        (time.perf_counter() - _t0) * 1000
    )
    out["summary"] = (
        f"{len(out['findings'])} finding(s) "
        f"({'needs LLM' if out['needs_llm'] else 'deterministic only'})"
    )

    out_path = Path(args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_json.dumps(out, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    log_event(plan_path.parent, f"verify-aspect:{aspect}", "tick",
              elapsed_ms=out["iteration_check_ms"],
              findings=len(out["findings"]))
    print(f"wrote {out_path} — {out['summary']}")
    return 0


def cmd_verify_collate(args) -> int:
    """`feinschliff deck verify-collate --aspect a.json --aspect b.json -o report.md`
    Merge per-aspect verify outputs into a unified verify_report.md.
    """
    import json as _json
    plan_path = Path(args.plan).resolve()
    plan = yaml.safe_load(plan_path.read_text(encoding="utf-8")) or {}
    slides = plan.get("slides") or []

    # Aggregate findings grouped by slide index. Each finding carries its
    # source aspect so the report makes the parallel checks visible.
    by_slide: dict[int, list[dict]] = {}
    aspects_seen: list[str] = []
    needs_llm: list[str] = []
    total_findings = 0

    for path_str in args.aspect:
        p = Path(path_str).resolve()
        if not p.is_file():
            print(f"deck verify-collate: aspect file not found: {p}",
                  file=sys.stderr)
            continue
        try:
            data = _json.loads(p.read_text(encoding="utf-8"))
        except _json.JSONDecodeError as e:
            print(f"deck verify-collate: {p}: {e}", file=sys.stderr)
            continue
        aspect = data.get("aspect", p.stem)
        aspects_seen.append(aspect)
        if data.get("needs_llm"):
            needs_llm.append(aspect)
        for f in data.get("findings", []) or []:
            f = dict(f)
            f["aspect"] = aspect
            by_slide.setdefault(int(f.get("slide", 0)), []).append(f)
            total_findings += 1

    # Decide verdict: clean iff no findings + no LLM aspects waiting.
    fatal = any(
        f.get("severity") == "fatal"
        for fs in by_slide.values() for f in fs
    )
    dirty = total_findings > 0 or fatal
    verdict = "dirty" if dirty else ("pending-llm" if needs_llm else "clean")

    lines: list[str] = []
    lines.append(f"# Verify Report — {plan_path.name}")
    lines.append("")
    lines.append(f"- **Iteration:** {args.iteration} of {args.budget}")
    lines.append(f"- **Verdict:** {verdict}"
                 + (f" — {total_findings} finding(s) across "
                    f"{len(by_slide)} slide(s)" if dirty else ""))
    lines.append(f"- **Aspects checked:** {', '.join(aspects_seen) or '(none)'}")
    if needs_llm:
        lines.append(f"- **Pending LLM verdict from:** {', '.join(needs_llm)}")
    if args.png_dir:
        lines.append(f"- **Rendered PNGs:** `{args.png_dir}`")
    lines.append("")
    lines.append("---")
    lines.append("")

    for i, spec in enumerate(slides, start=1):
        title = (spec.get("content") or {}).get("title") \
                or (spec.get("content") or {}).get("action_title") \
                or spec.get("_meta", {}).get("title", "(untitled)")
        layout_name = Path(spec.get("layout", "?")).name.replace(".slide.dsl", "")
        findings = by_slide.get(i, [])
        if not findings:
            lines.append(f"## Slide {i} — {title!r} ({layout_name}) ✅")
            lines.append("")
            lines.append("_No defects._")
        else:
            lines.append(f"## Slide {i} — {title!r} ({layout_name})")
            lines.append("")
            for f in findings:
                lines.append(
                    f"- **[{f['aspect']}/{f.get('kind', '?')}]** "
                    f"{f.get('message', '')}"
                )
                if f.get("hint"):
                    lines.append(f"  → {f['hint']}")
        lines.append("")

    out_path = Path(args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    log_event(plan_path.parent, "verify-collate", "tick",
              aspects=len(aspects_seen), findings=total_findings,
              verdict=verdict, iteration=args.iteration)
    print(f"wrote {out_path} — verdict: {verdict}, "
          f"{total_findings} finding(s) across {len(by_slide)} slide(s)")
    return 0


def cmd_verify_static(args) -> int:
    """`feinschliff deck verify-static <plan.yaml>` — pre-render static check.

    Inspects a plan.yaml for geometry defects that can be detected from the
    DSL + populated content without rendering (slot-overflow,
    empty-placeholder). Cheaper than a full build: catches class of defect
    in ~10-50 ms vs ~3 s/slide for a render-based check.

    Exit codes:
      0 — clean (no defects)
      1 — one or more defects found
      2 — plumbing error (plan not found, brand resolution failure, etc.)
    """
    import json as _json
    from feinschliff_builder.verify.static import validate as _validate_static

    plan_path = Path(args.plan).resolve()
    if not plan_path.is_file():
        print(f"deck verify-static: plan not found: {plan_path}", file=sys.stderr)
        return 2

    try:
        plan = yaml.safe_load(plan_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        print(f"deck verify-static: could not load plan: {exc}", file=sys.stderr)
        return 2

    brand_name = getattr(args, "brand", None) or plan.get("brand") or "feinschliff"
    try:
        brand_obj = find_brand(brand_name)
    except ValueError as exc:
        print(f"deck verify-static: {exc}", file=sys.stderr)
        return 2

    try:
        bag = _validate_static(plan, brand=brand_obj, plan_dir=plan_path.parent)
    except Exception as exc:  # noqa: BLE001
        print(f"deck verify-static: unexpected error: {exc}", file=sys.stderr)
        return 2

    if getattr(args, "json", False):
        # Produce a backward-compatible schema so `deck apply-fixes --defects`
        # can consume this output: {slide_index, kind, severity, message, meta}.
        out = []
        for d in bag:
            extra = d.extra or {}
            entry = {
                "slide_index": extra.get("slide_index", 0),
                "kind": d.kind.value,
                "severity": d.severity.value,
                "message": d.message,
                "meta": {k: v for k, v in extra.items() if k != "slide_index"},
            }
            if d.location is not None:
                entry["location"] = d.location
            out.append(entry)
        print(_json.dumps(out, indent=2, ensure_ascii=False))
    else:
        if bag:
            for d in bag:
                _loc = d.location or "slide ?"
                print(
                    f"{_loc}: [{d.severity.value.upper()}] {d.kind.value} — {d.message}"
                )
        else:
            print("verify-static: clean — no defects found")

    return 1 if bag else 0


def _parse_severity(value: str):
    """Parse a severity string that may use either engine or legacy vocabulary.

    ``deck verify-static --json`` emits ENGINE severity values because it goes
    through ``feinschliff_builder.verify.static.validate()``, which maps the
    legacy Severity enum to the ``feinschmiede.diagnostics`` engine enum before
    serialising:

        legacy FATAL  → engine "error"
        legacy WARN   → engine "warning"
        legacy INFO   → engine "info"

    Legacy values (``"fatal"``, ``"warn"``, ``"info"``) are also accepted so
    that hand-crafted defect files and older tooling continue to work.

    The inverse mapping applied here exactly undoes validate()'s forward mapping:

        engine "error"   → Severity.FATAL
        engine "warning" → Severity.WARN
        engine "info"    → Severity.INFO
        legacy "fatal"   → Severity.FATAL  (pass-through)
        legacy "warn"    → Severity.WARN   (pass-through)

    Raises ``ValueError`` for unrecognised values (caller logs + skips).
    """
    from feinschliff.defects import Severity
    _ENGINE_TO_LEGACY = {
        "error": Severity.FATAL,
        "warning": Severity.WARN,
        "info": Severity.INFO,
    }
    if value in _ENGINE_TO_LEGACY:
        return _ENGINE_TO_LEGACY[value]
    # Fall through to legacy enum constructor (handles "fatal", "warn", "info").
    return Severity(value)


