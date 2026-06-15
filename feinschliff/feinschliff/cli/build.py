"""`feinschliff build` — DSL pipeline: layout + brand + content → .pptx.

  feinschliff build <layout.slide.dsl> --brand <id> [--content YAML] [--var k=v]... -o OUT.pptx

The layout file is parsed; the content YAML provides slot values; the
brand pack's tokens + compounds are loaded; the full graph is expanded
to primitives; the emitter writes a .pptx.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from feinschliff.dsl.parser import parse_file
from feinschmiede import compounds_dir
from feinschmiede.dsl.tokens import load_tokens_with_theme
from feinschliff.dsl.expander import load_compounds_for_brand
from feinschliff.dsl.pptx_emit import build_presentation
from feinschliff.content_validator import validate_content, emit_defects_and_abort_message
from feinschliff.slot_budget import compute_slot_budgets
from feinschliff.pipeline import compile_slide
from feinschliff.defects import fatal_kinds, format_defect
from feinschliff.io.image_provider import discover_providers, get_provider
from feinschliff.io.image_providers import chain_from_brand_config


def _bundled_assets() -> Path:
    """Return the assets/ directory shipped inside this plugin."""
    return Path(__file__).resolve().parents[1] / "assets"


def register(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("layout", help="Path to a .slide.dsl file")
    parser.add_argument("--brand", required=True, help="Brand id (dir name under brands/)")
    parser.add_argument("--content", help="YAML file with slot values")
    parser.add_argument("--var", action="append", help="Override a single slot: --var key=value")
    parser.add_argument("-o", "--output", required=True, help="Output .pptx path")
    parser.add_argument(
        "--skip-content-lint",
        action="store_true",
        help="Skip pre-render content lints (title-length, action-verb-leading). "
             "For emergency overrides only.",
    )
    parser.add_argument(
        "--allow-diagram-warnings",
        action="store_true",
        help="Ship even when diagram-overflow or diagram-text-too-small "
             "defects surface. Otherwise these are fatal by default.",
    )
    parser.add_argument(
        "--allow-missing-assets",
        action="store_true",
        help="Ship even when a picture slot points at a missing file or is "
             "unset. Default: fatal. Mark intentionally-empty slots with "
             "`optional:true` to skip the abort without this flag.",
    )
    parser.add_argument(
        "--embed-fonts",
        action="store_true",
        help="Embed brand display/body font files into the .pptx so "
             "recipients without the fonts render faithfully (opt-in; "
             "enlarges the file). "
             "No font-license (fsType) check is performed — verify your "
             "brand fonts permit embedding.",
    )
    parser.add_argument(
        "--theme",
        default=None,
        help="Theme name to overlay on the brand tokens (e.g. 'orange'). "
             "Defaults to the brand's $default_theme.",
    )
    parser.set_defaults(func=cmd_build)


def cmd_build(args) -> int:
    from feinschmiede.brand_discovery import find_brand

    layout_path = Path(args.layout).resolve()
    try:
        brand = find_brand(args.brand)
    except ValueError as e:
        print(f"feinschliff: {e}", file=sys.stderr)
        return 2
    brand_dir = brand.root

    # Resolve build-time image provider / provider chain from the brand's
    # tokens.json. The new `$image_providers` (plural list) takes precedence
    # and builds a ProviderChain; the legacy `$image_provider` (singular dict)
    # still works via chain_from_brand_config's backwards-compat path.
    # Absent → chain and provider are both None; any `picture query:` raises a
    # loud DSLError inside the emitter; brands using only `picture path:` build
    # as before.
    discover_providers()
    provider = None
    chain = None
    # Load raw tokens to check for plural $image_providers key.
    _raw_tokens = getattr(brand, "tokens", {}) or {}
    _ip_list = _raw_tokens.get("$image_providers")
    if _ip_list is not None:
        chain = chain_from_brand_config(_ip_list, brand_root=brand.root)
    elif brand.image_provider_config:
        # Backwards compat: singular $image_provider → one-element chain.
        chain = chain_from_brand_config(brand.image_provider_config, brand_root=brand.root)
        # Also set legacy provider for callers that use it directly.
        cfg = brand.image_provider_config
        provider = get_provider(cfg["kind"], cfg.get("config"))

    theme = getattr(args, "theme", None)
    tokens = load_tokens_with_theme(brand_dir, theme)
    compounds = load_compounds_for_brand(
        brand_dir, std_dir=compounds_dir()
    )

    layout_nodes, layout_compounds = parse_file(layout_path)
    for cd in layout_compounds:
        compounds[cd.name] = cd

    ctx = {}
    if args.content:
        ctx = yaml.safe_load(Path(args.content).read_text()) or {}
    for kv in (args.var or []):
        if "=" not in kv:
            print(f"feinschliff: --var expects key=value, got '{kv}'", file=sys.stderr)
            return 2
        k, _, v = kv.partition("=")
        ctx[k.strip()] = v

    if not args.skip_content_lint:
        # Strip `.slide.dsl` (and any leading path) to get the bare layout
        # name (e.g. "executive-summary") — this is what the structural
        # validators key on.
        layout_name = layout_path.name
        if layout_name.endswith(".slide.dsl"):
            layout_name = layout_name[: -len(".slide.dsl")]
        slot_budgets = compute_slot_budgets(layout_nodes, tokens, compounds=compounds)
        content_defects = validate_content(
            ctx, slide_index=1, layout=layout_name, slot_budgets=slot_budgets,
        )
        # Mirror deck.py's severity split: warn-severity defects (e.g.
        # slot-collision) are logged but never abort the build; only fatal
        # defects block the render.  Parity required — both entry points
        # call validate_content with slot_budgets, so both must handle the
        # same defect vocabulary.
        warn_defects, fatal_defects = [], []
        for d in content_defects:
            (warn_defects if getattr(d, "severity", "fatal") == "warn"
             else fatal_defects).append(d)
        for d in warn_defects:
            print(f"build: WARN: {d}", file=sys.stderr)
        if fatal_defects:
            emit_defects_and_abort_message({1: fatal_defects}, cli_name="build")
            return 1

    result = compile_slide(
        layout_path=layout_path,
        ctx=ctx,
        brand_dir=brand_dir,
        slide_index=1,
        diagrams_out_dir=Path(args.output).resolve().parent / "diagrams",
        theme=theme,
    )

    allowed_to_skip: set[str] = set()
    if args.allow_diagram_warnings:
        allowed_to_skip |= {"diagram-overflow", "diagram-text-too-small"}

    blocking = [
        d for d in result.defects
        if d.kind.value in fatal_kinds() and d.kind.value not in allowed_to_skip
    ]
    for d in result.defects:
        print(f"feinschliff build: {format_defect(d)}", file=sys.stderr)
    if blocking:
        print(
            f"feinschliff build: aborting — {len(blocking)} fatal defect(s). "
            f"Pass --allow-diagram-warnings to demote "
            f"diagram-overflow/diagram-text-too-small (if those are the only blockers).",
            file=sys.stderr,
        )
        return 1

    primitives = result.primitives
    tokens = result.tokens

    asset_root = brand_dir / "assets"
    asset_root_fallback = _bundled_assets()
    out_path = Path(args.output).resolve()
    prs = build_presentation(
        primitives, tokens,
        asset_root=asset_root,
        asset_root_fallback=asset_root_fallback,
        image_provider=provider,
        provider_chain=chain,
        deck_dir=out_path.parent,
    )
    missing = getattr(prs, "missing_assets", []) or []
    # --allow-missing-assets is suppressed when a provider chain is configured
    # and failed — the operator must fix the chain config, not ship a blank deck.
    chain_failed = chain is not None and any(
        e.get("kind") == "chain-miss" for e in missing
    )
    if missing and (chain_failed or not getattr(args, "allow_missing_assets", False)):
        for entry in missing:
            kind = entry.get("kind", "missing")
            path = entry.get("path") or "(unset)"
            line = entry.get("line_no", "?")
            print(
                f"feinschliff build: missing asset ({kind}) at "
                f"line {line}: {path}",
                file=sys.stderr,
            )
        print(
            f"feinschliff build: aborting — {len(missing)} missing required "
            f"asset(s). Mark optional slots with `optional:true` or pass "
            f"--allow-missing-assets to ship anyway.",
            file=sys.stderr,
        )
        return 1
    if getattr(args, "embed_fonts", False):
        from feinschliff.dsl.font_embed import embed_brand_fonts

        embedded = embed_brand_fonts(prs, tokens)
        if embedded:
            print(f"embedded fonts: {', '.join(embedded)}", file=sys.stderr)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))
    print(f"wrote {out_path} ({len(prs.slides)} slide, "
          f"{len(primitives)} primitives expanded from "
          f"{len(layout_nodes)} layout nodes)")
    return 0
