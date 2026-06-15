"""Tests for `deck build --strict-craft` CLI flag.

Verifies that:
- A plan whose slides violate a craft rule exits 1 when --strict-craft is set.
- A plan with clean slides exits 0 and writes craft_report.md.
- --strict-craft is a no-op (exit 0) when slides are clean even with many issues
  that are only WARN severity.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from feinschliff.cli import deck

PLUGIN_ROOT = Path(__file__).resolve().parents[2] / "feinschliff"
LAYOUT = PLUGIN_ROOT / "brands" / "feinschliff" / "layouts" / "executive-summary.slide.dsl"


def _build_args(plan_path: Path, out_path: Path, **overrides) -> argparse.Namespace:
    defaults = dict(
        plan=str(plan_path),
        output=str(out_path),
        skip_content_lint=False,
        allow_diagram_warnings=False,
        allow_missing_assets=False,
        strict_static=False,
        strict_craft=False,
        strict_visual=False,
        autofix=False,
        slot_debug_color=None,
        no_image_provider=True,
        workers=1,
        embed_fonts=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _write_plan(tmp_path: Path, slides: list[dict]) -> Path:
    plan = {
        "brand": "feinschliff",
        "slides": slides,
    }
    plan_path = tmp_path / "plan.yaml"
    plan_path.write_text(yaml.safe_dump(plan, sort_keys=False), encoding="utf-8")
    return plan_path


def test_strict_craft_fail_on_pie_chart(tmp_path, monkeypatch):
    """A slide using the pie-chart layout triggers a 'fail' verdict and exit 1."""
    monkeypatch.setenv("FEINSCHLIFF_QUIET_NOTES_BUDGET", "1")

    import feinschliff.quality as _quality_mod
    from feinschliff.quality.craft_rules import CraftIssue, CraftReport

    _fail_report = CraftReport(
        verdict="fail",
        issues=[
            CraftIssue(
                slide=1,
                rule="no-pie-chart",
                severity="fail",
                message="Pie/donut charts are forbidden (Knaflic): use a bar chart instead.",
                meta={"layout_stem": "pie-chart"},
            )
        ],
    )

    monkeypatch.setattr(_quality_mod, "check_craft_rules", lambda *a, **kw: _fail_report)

    slides = [
        {
            "layout": str(LAYOUT),
            "content": {
                "action_title": "Revenue grows this quarter",
                "footer_left": "Corp",
                "footer_right": "2026",
            },
        }
    ]
    plan_path = _write_plan(tmp_path, slides)
    out_path = tmp_path / "deck.pptx"

    rc = deck.cmd_build(_build_args(plan_path, out_path, strict_craft=True))

    assert rc == 1, "fail verdict must exit 1"
    report_path = out_path.parent / "craft_report.md"
    assert report_path.exists(), "craft_report.md must be written even on fail"
    assert "no-pie-chart" in report_path.read_text()


def test_strict_craft_passes_clean_slides(tmp_path, monkeypatch):
    """A clean plan exits 0 and writes craft_report.md with verdict clean."""
    monkeypatch.setenv("FEINSCHLIFF_QUIET_NOTES_BUDGET", "1")

    import feinschliff.quality as _quality_mod
    from feinschliff.quality.craft_rules import CraftReport

    _clean_report = CraftReport(verdict="clean", issues=[])
    monkeypatch.setattr(_quality_mod, "check_craft_rules", lambda *a, **kw: _clean_report)

    slides = [
        {
            "layout": str(LAYOUT),
            "content": {
                "action_title": "Revenue grows this quarter",
                "footer_left": "Corp",
                "footer_right": "2026",
            },
        }
    ]
    plan_path = _write_plan(tmp_path, slides)
    out_path = tmp_path / "deck.pptx"

    rc = deck.cmd_build(_build_args(plan_path, out_path, strict_craft=True))

    assert rc == 0, "clean verdict must exit 0"
    report_path = out_path.parent / "craft_report.md"
    assert report_path.exists(), "craft_report.md must be written on clean"
    assert "clean" in report_path.read_text()


def test_strict_craft_warn_exits_0(tmp_path, monkeypatch):
    """A warn-only verdict exits 0 (warn is non-blocking)."""
    monkeypatch.setenv("FEINSCHLIFF_QUIET_NOTES_BUDGET", "1")

    import feinschliff.quality as _quality_mod
    from feinschliff.quality.craft_rules import CraftIssue, CraftReport

    _warn_report = CraftReport(
        verdict="warn",
        issues=[
            CraftIssue(
                slide=1,
                rule="title-not-claim",
                severity="warn",
                message="Title appears to contain no finite verb.",
                meta={},
            )
        ],
    )
    monkeypatch.setattr(_quality_mod, "check_craft_rules", lambda *a, **kw: _warn_report)

    slides = [
        {
            "layout": str(LAYOUT),
            "content": {
                "action_title": "Revenue and costs",
                "footer_left": "Corp",
                "footer_right": "2026",
            },
        }
    ]
    plan_path = _write_plan(tmp_path, slides)
    out_path = tmp_path / "deck.pptx"

    rc = deck.cmd_build(_build_args(plan_path, out_path, strict_craft=True))

    assert rc == 0, "warn verdict must exit 0"
