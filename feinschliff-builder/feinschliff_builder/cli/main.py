"""feinschliff-builder CLI entry point.

Registers the QA + verification subcommands:
  - `eval`            grade generated artifacts vs a skill's evals.json
  - `verify`          validate a built .pptx deck
  - `verify-quality`  LLM quality rubric over a rendered deck
  - `verify-diagram`  validate diagram artifacts

The legacy decompile / slotify / compile-html / audit / brand paths were
removed when the DSL pipeline retired in favor of the master-template
renderer (`feinschmiede.master_template`). Brand packs are now authored
as master.pptx + layouts.yaml + snippets.yaml; no decompiling needed.
"""
from __future__ import annotations

import argparse
import sys

from feinschliff_builder.cli import (
    eval as eval_cmd,
    verify as verify_cmd,
    verify_quality as verify_quality_cmd,
    verify_diagram as verify_diagram_cmd,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="feinschliff-builder",
        description="Feinschliff QA toolkit (verify + grade rendered decks).",
    )
    sub = parser.add_subparsers(dest="command")
    sub.required = True

    eval_cmd.register(sub.add_parser("eval", help="Grade generated artifacts vs a skill's evals.json"))
    verify_cmd.register(sub.add_parser("verify", help="Validate a built .pptx deck"))
    verify_quality_cmd.register(sub.add_parser("verify-quality", help="LLM quality rubric"))
    verify_diagram_cmd.register(sub.add_parser("verify-diagram", help="Validate diagram artifacts"))

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
