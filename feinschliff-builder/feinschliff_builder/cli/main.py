"""feinschliff-builder CLI entry point.

Registers the brand-authoring pipeline (decompile, slotify, compile-html)
and the QA subcommands (audit, brand, eval, verify, verify-quality,
verify-diagram). The brand-bootstrap flow is `decompile` → `slotify` →
`/feinschliff-builder:improve-brand`; see feinschliff-builder/README.md.
"""
from __future__ import annotations

import argparse
import sys

from feinschliff_builder.cli import (
    audit as audit_cmd,
    brand as brand_cmd,
    compile as compile_cmd,
    decompile as decompile_cmd,
    eval as eval_cmd,
    slotify as slotify_cmd,
    verify as verify_cmd,
    verify_quality as verify_quality_cmd,
    verify_diagram as verify_diagram_cmd,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="feinschliff-builder",
        description="Feinschliff brand-pack authoring toolkit.",
    )
    sub = parser.add_subparsers(dest="command")
    sub.required = True

    audit_cmd.register(sub.add_parser("audit", help="Slot-coverage acceptance check for a brand pack"))
    brand_cmd.register(sub.add_parser("brand", help="Brand pack utilities"))
    compile_cmd.register(sub.add_parser("compile-html", help="Compile HTML to DSL skeletons"))
    decompile_cmd.register(sub.add_parser("decompile", help="Bulk-decompile a brand pack's layouts from a source PPTX (step 1 of bootstrap)"))
    slotify_cmd.register(sub.add_parser("slotify", help="Slotify decompiled layouts + emit picker frontmatter + deck-map.yaml (step 2 of bootstrap)"))
    eval_cmd.register(sub.add_parser("eval", help="Grade generated artifacts vs a skill's evals.json"))
    verify_cmd.register(sub.add_parser("verify", help="Validate a built .pptx deck"))
    verify_quality_cmd.register(sub.add_parser("verify-quality", help="LLM quality rubric"))
    verify_diagram_cmd.register(sub.add_parser("verify-diagram", help="Validate diagram DSL files"))

    # The office `deck` advanced subcommands (storyline, wireframe, polish, book,
    # strict-static/autofix, …) are built on this package. Re-expose office's own
    # deck parser here so a `feinschliff deck …` call can delegate to
    # `feinschliff-builder deck …` (this venv bundles office + builder, so the
    # inline path resolves). Optional: skip cleanly if office isn't importable.
    try:
        from feinschliff.cli import deck as office_deck
        office_deck.register(sub.add_parser(
            "deck", help="Office deck pipeline (builder-backed advanced features)"))
    except ImportError:
        pass

    args = parser.parse_args(argv)
    rc = args.func(args)
    if argv is None:
        sys.exit(rc or 0)
    return rc or 0


if __name__ == "__main__":
    main()
