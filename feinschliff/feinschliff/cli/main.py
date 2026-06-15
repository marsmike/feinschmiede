"""Top-level CLI entry. Dispatches to subcommands."""
from __future__ import annotations

import argparse
import sys

from feinschliff.env import load_home_env

# Load ~/.env BEFORE any anthropic / openai SDK constructs itself — the SDKs
# capture API keys at import time. Mirrors feinklang and feinschnitt.
load_home_env()

from feinschliff.cli import deck as deck_cmd  # noqa: E402
from feinschliff.cli import doctor as doctor_cmd  # noqa: E402
from feinschliff.cli import render_master as render_master_cmd  # noqa: E402
from feinschliff.cli import ship as ship_cmd  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="feinschliff")
    sub = p.add_subparsers(dest="command", required=True)

    deck_parser = sub.add_parser(
        "deck",
        help="Multi-slide deck composer + layout picker",
    )
    deck_cmd.register(deck_parser)

    ship_parser = sub.add_parser(
        "ship",
        help="One-command build + verify + verify-quality with a single verdict",
    )
    ship_cmd.register(ship_parser)

    render_master_parser = sub.add_parser(
        "render-master",
        help="Render a deck from a master-template brand pack (master.pptx + layouts.yaml)",
    )
    render_master_cmd.register(render_master_parser)

    p_doctor = sub.add_parser(
        "doctor",
        help="Probe the install for missing deps + config; print plain-English fixes.",
    )
    p_doctor.add_argument(
        "--json",
        action="store_true",
        help="Emit checks as JSON array instead of human-readable.",
    )
    p_doctor.set_defaults(func=doctor_cmd.cmd_doctor)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    rc = args.func(args)
    return 0 if rc is None else int(rc)


if __name__ == "__main__":
    sys.exit(main())
