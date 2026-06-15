"""Tests for `feinschliff deck plan-skeleton` — slot budgets in _meta."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
FEINSCHLIFF = REPO / "feinschliff"

# Minimal content_plan with 3 slides, using roles that have stable layout picks.
_CONTENT_PLAN = {
    "brand": "feinschliff",
    "slides": [
        {
            "index": 0,
            "title": "Revenue grew 22% last quarter",
            "role": "data-quantity",
            "data_quantity": 3,
        },
        {
            "index": 1,
            "title": "Three strategic pillars drive growth",
            "role": "content-columns",
            "concept_count": 3,
        },
        {
            "index": 2,
            "title": "Action required by end of month",
            "role": "action-title",
        },
    ],
}

_BUDGET_KEYS = {"chars_per_line", "max_lines", "max_chars"}


def _run_skeleton(tmp_path: Path, plan: dict | None = None) -> tuple[int, str, str, Path]:
    """Write plan JSON, run plan-skeleton, return (rc, stdout, stderr, out_path)."""
    cp = tmp_path / "content_plan.json"
    cp.write_text(json.dumps(plan or _CONTENT_PLAN))
    out = tmp_path / "plan.skeleton.yaml"
    import os
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli", "deck", "plan-skeleton",
            str(cp),
            "-o", str(out),
        ],
        capture_output=True, text=True, encoding="utf-8", env=env, cwd=FEINSCHLIFF,
    )
    return result.returncode, result.stdout, result.stderr, out


def test_plan_skeleton_succeeds(tmp_path):
    rc, stdout, stderr, out = _run_skeleton(tmp_path)
    assert rc == 0, f"plan-skeleton failed:\nstdout={stdout}\nstderr={stderr}"
    assert out.is_file(), "output skeleton YAML not written"


def test_plan_skeleton_slides_have_slot_budgets(tmp_path):
    """Every slide in the skeleton must carry slot_budgets inside _meta."""
    rc, stdout, stderr, out = _run_skeleton(tmp_path)
    assert rc == 0, f"plan-skeleton failed:\nstdout={stdout}\nstderr={stderr}"
    skel = yaml.safe_load(out.read_text())
    slides = skel["slides"]
    assert len(slides) == len(_CONTENT_PLAN["slides"])

    for i, slide in enumerate(slides):
        meta = slide.get("_meta", {})
        assert "slot_budgets" in meta, (
            f"slide {i}: _meta is missing slot_budgets key; _meta={meta}"
        )
        budgets = meta["slot_budgets"]
        assert isinstance(budgets, dict), f"slide {i}: slot_budgets should be a dict"


def test_plan_skeleton_emits_empty_budgets_for_cascade_picker(tmp_path):
    """Post-#118: plan-skeleton emits empty slot_budgets per slide.
    The cascade orchestrator picks layouts, then `plan-budgets` enriches
    `_meta.slot_budgets` (including chart_* slots — see test_plan_budgets.py).
    """
    rc, stdout, stderr, out = _run_skeleton(tmp_path)
    assert rc == 0, f"plan-skeleton failed:\nstdout={stdout}\nstderr={stderr}"
    skel = yaml.safe_load(out.read_text())
    for i, slide in enumerate(skel["slides"]):
        assert slide["layout"] is None, f"slide {i}: cascade should pick, not skeleton"
        assert slide["_meta"]["slot_budgets"] == {}, (
            f"slide {i}: skeleton must emit empty budgets; plan-budgets fills them"
        )


def test_plan_skeleton_budget_entries_have_expected_keys(tmp_path):
    """Every budget entry must contain chars_per_line, max_lines, max_chars."""
    rc, stdout, stderr, out = _run_skeleton(tmp_path)
    assert rc == 0, f"plan-skeleton failed:\nstdout={stdout}\nstderr={stderr}"
    skel = yaml.safe_load(out.read_text())
    for i, slide in enumerate(skel["slides"]):
        budgets = slide.get("_meta", {}).get("slot_budgets", {})
        for slot, budget in budgets.items():
            missing = _BUDGET_KEYS - set(budget.keys())
            assert not missing, (
                f"slide {i}, slot {slot!r}: budget missing keys {missing}; "
                f"got {budget}"
            )


def test_plan_skeleton_budget_values_are_positive_ints(tmp_path):
    """Budget values must be positive integers."""
    rc, stdout, stderr, out = _run_skeleton(tmp_path)
    assert rc == 0, f"plan-skeleton failed:\nstdout={stdout}\nstderr={stderr}"
    skel = yaml.safe_load(out.read_text())
    for i, slide in enumerate(skel["slides"]):
        budgets = slide.get("_meta", {}).get("slot_budgets", {})
        for slot, budget in budgets.items():
            for key in _BUDGET_KEYS:
                val = budget[key]
                assert isinstance(val, int), (
                    f"slide {i}, slot {slot!r}, key {key!r}: expected int, got {type(val)}"
                )
                assert val > 0, (
                    f"slide {i}, slot {slot!r}, key {key!r}: expected > 0, got {val}"
                )


def test_plan_skeleton_layout_and_content_still_present(tmp_path):
    """Existing skeleton fields (layout, content) must still be present."""
    rc, stdout, stderr, out = _run_skeleton(tmp_path)
    assert rc == 0, f"plan-skeleton failed:\nstdout={stdout}\nstderr={stderr}"
    skel = yaml.safe_load(out.read_text())
    for i, slide in enumerate(skel["slides"]):
        assert "layout" in slide, f"slide {i}: missing 'layout' key"
        assert "content" in slide, f"slide {i}: missing 'content' key"


# ── plan-merge regression: _meta (including slot_budgets) must be stripped ──

def _run_merge(tmp_path: Path, skel_path: Path, slide_count: int) -> tuple[int, str, str, Path]:
    """Write minimal chunk files and run plan-merge."""
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir(exist_ok=True)
    chunk_files = []
    for idx in range(slide_count):
        chunk = {"index": idx, "content": {"title": f"Slide {idx} title"}}
        cp = chunks_dir / f"slide-{idx:02d}.yaml"
        cp.write_text(yaml.dump(chunk))
        chunk_files.append(str(cp))
    out = tmp_path / "plan.yaml"
    cmd = [
        sys.executable, "-m", "feinschliff.cli", "deck", "plan-merge",
        str(skel_path),
        *[arg for f in chunk_files for arg in ("--chunk", f)],
        "-o", str(out),
    ]
    import os
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", env=env, cwd=FEINSCHLIFF,
    )
    return result.returncode, result.stdout, result.stderr, out


def test_plan_merge_strips_meta_including_slot_budgets(tmp_path):
    """plan-merge must strip _meta (and thus slot_budgets) from all slides."""
    # First produce a skeleton.
    rc, stdout, stderr, skel_path = _run_skeleton(tmp_path)
    assert rc == 0, f"plan-skeleton failed:\nstdout={stdout}\nstderr={stderr}"
    skel = yaml.safe_load(skel_path.read_text())
    slide_count = len(skel["slides"])

    # Now merge.
    rc2, stdout2, stderr2, merged_path = _run_merge(tmp_path, skel_path, slide_count)
    assert rc2 == 0, (
        f"plan-merge failed:\nstdout={stdout2}\nstderr={stderr2}"
    )
    merged = yaml.safe_load(merged_path.read_text())
    for i, slide in enumerate(merged["slides"]):
        assert "_meta" not in slide, (
            f"slide {i}: plan-merge left _meta in merged plan: {slide}"
        )
        assert "slot_budgets" not in slide, (
            f"slide {i}: plan-merge left slot_budgets in merged plan: {slide}"
        )


def test_plan_skeleton_missing_plan(tmp_path):
    """plan-skeleton exits non-zero when the content_plan is missing."""
    out = tmp_path / "plan.skeleton.yaml"
    import os
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli", "deck", "plan-skeleton",
            str(tmp_path / "nope.json"),
            "-o", str(out),
        ],
        capture_output=True, text=True, encoding="utf-8", env=env, cwd=FEINSCHLIFF,
    )
    assert result.returncode != 0
    assert "not found" in (result.stderr + result.stdout).lower()
