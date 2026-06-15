"""End-to-end tests for `feinschliff deck plan-budgets`.

Runs the CLI command against a minimal plan.yaml (with layout: already set)
and asserts that _meta.slot_budgets is enriched per slide with both text slot
budgets and (where applicable) chart slot entries.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
FEINSCHLIFF = REPO / "feinschliff"

# Minimal plan.yaml with layouts already picked — plan-budgets needs layout: set.
# Use well-known toolkit layouts that exist in every feinschliff install.
_PICKED_PLAN = {
    "brand": "feinschliff",
    "out": "deck.pptx",
    "slides": [
        {
            "layout": "layouts/kpi-grid.slide.dsl",
            "content": {},
        },
        {
            "layout": "layouts/content-columns.slide.dsl",
            "content": {},
        },
    ],
}


def _run_plan_budgets(
    tmp_path: Path,
    plan: dict | None = None,
    extra_args: list[str] | None = None,
) -> tuple[int, str, str, Path]:
    """Write plan.yaml, run plan-budgets, return (rc, stdout, stderr, out_path)."""
    import os
    plan_file = tmp_path / "plan.yaml"
    plan_file.write_text(
        yaml.safe_dump(plan or _PICKED_PLAN, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    out = tmp_path / "plan_enriched.yaml"
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    cmd = [
        sys.executable, "-m", "feinschliff.cli", "deck", "plan-budgets",
        str(plan_file),
        "-o", str(out),
    ] + (extra_args or [])
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", env=env, cwd=FEINSCHLIFF,
    )
    return result.returncode, result.stdout, result.stderr, out


# ---------------------------------------------------------------------------
# Basic invocation tests
# ---------------------------------------------------------------------------

def test_plan_budgets_exits_zero(tmp_path):
    rc, stdout, stderr, out = _run_plan_budgets(tmp_path)
    assert rc == 0, f"plan-budgets failed:\nstdout={stdout}\nstderr={stderr}"


def test_plan_budgets_writes_output_file(tmp_path):
    rc, stdout, stderr, out = _run_plan_budgets(tmp_path)
    assert rc == 0
    assert out.is_file(), "output YAML not written"


def test_plan_budgets_stdout_mentions_enriched_slides(tmp_path):
    rc, stdout, stderr, out = _run_plan_budgets(tmp_path)
    assert rc == 0
    assert "enriched" in stdout.lower() or "enriched" in stderr.lower(), (
        f"Expected 'enriched' in output.\nstdout={stdout}\nstderr={stderr}"
    )


# ---------------------------------------------------------------------------
# Slot budget enrichment tests
# ---------------------------------------------------------------------------

def test_plan_budgets_adds_meta_slot_budgets(tmp_path):
    """After plan-budgets, each slide with a valid layout has _meta.slot_budgets."""
    rc, stdout, stderr, out = _run_plan_budgets(tmp_path)
    assert rc == 0, stderr
    enriched = yaml.safe_load(out.read_text(encoding="utf-8"))
    for i, slide in enumerate(enriched["slides"]):
        meta = slide.get("_meta", {})
        assert "slot_budgets" in meta, (
            f"slide {i}: _meta.slot_budgets missing after plan-budgets.\n"
            f"meta={meta}"
        )


def test_plan_budgets_slot_budgets_is_dict(tmp_path):
    rc, stdout, stderr, out = _run_plan_budgets(tmp_path)
    assert rc == 0, stderr
    enriched = yaml.safe_load(out.read_text(encoding="utf-8"))
    for i, slide in enumerate(enriched["slides"]):
        budgets = slide.get("_meta", {}).get("slot_budgets")
        assert isinstance(budgets, dict), (
            f"slide {i}: slot_budgets should be dict, got {type(budgets)}"
        )


def test_plan_budgets_preserves_content(tmp_path):
    """plan-budgets must not touch the content: blocks."""
    plan = dict(_PICKED_PLAN)
    plan["slides"] = [
        {
            "layout": "layouts/kpi-grid.slide.dsl",
            "content": {"title": "Revenue Q1", "kpis": [{"label": "ARR", "value": "€12M"}]},
        },
    ]
    rc, stdout, stderr, out = _run_plan_budgets(tmp_path, plan)
    assert rc == 0, stderr
    enriched = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert enriched["slides"][0]["content"]["title"] == "Revenue Q1"


def test_plan_budgets_idempotent(tmp_path):
    """Running plan-budgets twice produces the same output."""
    import os
    plan_file = tmp_path / "plan.yaml"
    plan_file.write_text(
        yaml.safe_dump(_PICKED_PLAN, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    out1 = tmp_path / "out1.yaml"
    out2 = tmp_path / "out2.yaml"
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    def _run(out_path):
        return subprocess.run(
            [
                sys.executable, "-m", "feinschliff.cli", "deck", "plan-budgets",
                str(plan_file), "-o", str(out_path),
            ],
            capture_output=True, text=True, encoding="utf-8", env=env, cwd=FEINSCHLIFF,
        )

    r1 = _run(out1)
    assert r1.returncode == 0
    # Feed the enriched output back as input
    plan_file.write_text(out1.read_text(encoding="utf-8"), encoding="utf-8")
    r2 = _run(out2)
    assert r2.returncode == 0

    e1 = yaml.safe_load(out1.read_text(encoding="utf-8"))
    e2 = yaml.safe_load(out2.read_text(encoding="utf-8"))
    for i in range(len(e1["slides"])):
        assert e1["slides"][i].get("_meta", {}).get("slot_budgets") == \
               e2["slides"][i].get("_meta", {}).get("slot_budgets"), \
               f"slide {i}: slot_budgets differ between runs"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

def test_plan_budgets_missing_file_exits_2(tmp_path):
    import os
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli", "deck", "plan-budgets",
            str(tmp_path / "nonexistent.yaml"),
            "-o", str(tmp_path / "out.yaml"),
        ],
        capture_output=True, text=True, encoding="utf-8", env=env, cwd=FEINSCHLIFF,
    )
    assert result.returncode == 2


def test_plan_budgets_slide_without_layout_skipped(tmp_path):
    """Slides with layout:null are skipped gracefully (no crash)."""
    plan = {
        "brand": "feinschliff",
        "out": "deck.pptx",
        "slides": [
            {"layout": None, "content": {}},
            {"layout": "layouts/kpi-grid.slide.dsl", "content": {}},
        ],
    }
    rc, stdout, stderr, out = _run_plan_budgets(tmp_path, plan)
    assert rc == 0, stderr
    enriched = yaml.safe_load(out.read_text(encoding="utf-8"))
    # Slide 0 has no layout → no _meta.slot_budgets added
    assert enriched["slides"][0].get("_meta", {}).get("slot_budgets") is None
    # Slide 1 has a layout → slot_budgets present
    assert "slot_budgets" in enriched["slides"][1].get("_meta", {})
