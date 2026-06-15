"""Default `deck build` static gate — optional-import degradation.

Task 9 wired the pre-render static geometry verifier
(feinschliff_builder.verify.static) into DEFAULT `deck build`: FATAL static
defects (slot-overflow) abort the build, WARN-only results do not. The
builder package is an OPTIONAL dependency of feinschliff, so the gate must
degrade to a no-op when `feinschliff_builder` is not importable — the same
pattern as pipeline.py's structural validators. These tests hide the builder
package and assert default builds keep working without the gate.

The gate's positive behavior (overflow aborts, WARN-only ships) is covered
end-to-end in feinschliff-builder/tests/test_verify_static.py, where the
builder package is a hard dependency of the suite.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from feinschliff.cli import deck

PLUGIN_ROOT = Path(__file__).resolve().parents[2] / "feinschliff"
LAYOUT = PLUGIN_ROOT / "brands" / "feinschliff" / "layouts" / "executive-summary.slide.dsl"

# Exceeds executive-summary's action_title budget (max_lines=1, ~84 chars).
_OVERFLOW_TITLE = (
    "We must urgently restructure our go-to-market approach because "
    "enterprise revenue has declined for three consecutive quarters"
)


def _hide_builder(monkeypatch):
    """Make every `feinschliff_builder*` import raise ImportError.

    Setting sys.modules entries to None causes the import machinery to raise
    ImportError deterministically without patching builtins.__import__.
    """
    for mod in (
        "feinschliff_builder",
        "feinschliff_builder.verify",
        "feinschliff_builder.verify.static",
    ):
        monkeypatch.setitem(sys.modules, mod, None)


def _build_args(plan_path: Path, out_path: Path, **overrides) -> argparse.Namespace:
    defaults = dict(
        plan=str(plan_path),
        output=str(out_path),
        skip_content_lint=False,
        allow_diagram_warnings=False,
        allow_missing_assets=False,
        strict_static=False,
        autofix=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _write_plan(tmp_path: Path, title: str) -> Path:
    plan = {
        "brand": "feinschliff",
        "slides": [
            {
                "layout": str(LAYOUT),
                "content": {
                    "action_title": title,
                    "footer_left": "Corp",
                    "footer_right": "2026",
                },
            }
        ],
    }
    plan_path = tmp_path / "plan.yaml"
    plan_path.write_text(yaml.safe_dump(plan, sort_keys=False), encoding="utf-8")
    return plan_path


def test_default_build_degrades_to_no_gate_without_builder(tmp_path, monkeypatch):
    """Builder absent → the static gate is a silent no-op; the build ships.

    --skip-content-lint isolates the gate: with the in-package content lint
    disabled AND the builder package hidden, nothing may block the build —
    not even an overflowing slot (that is the documented degradation, same
    as pipeline.py's structural validators).
    """
    monkeypatch.setenv("FEINSCHLIFF_QUIET_NOTES_BUDGET", "1")
    _hide_builder(monkeypatch)
    plan_path = _write_plan(tmp_path, _OVERFLOW_TITLE)
    out_path = tmp_path / "deck.pptx"

    rc = deck.cmd_build(_build_args(plan_path, out_path, skip_content_lint=True))

    assert rc == 0, "default build must not crash or abort when builder is absent"
    assert out_path.exists(), "deck.pptx must be written (gate degraded to no-op)"


def test_default_build_clean_plan_without_builder(tmp_path, monkeypatch):
    """Builder absent + clean plan → default build works end to end."""
    monkeypatch.setenv("FEINSCHLIFF_QUIET_NOTES_BUDGET", "1")
    _hide_builder(monkeypatch)
    plan_path = _write_plan(tmp_path, "Enterprise revenue declined three quarters")
    out_path = tmp_path / "deck.pptx"

    rc = deck.cmd_build(_build_args(plan_path, out_path))

    assert rc == 0
    assert out_path.exists()
