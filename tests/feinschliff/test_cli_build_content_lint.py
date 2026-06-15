"""Integration test: cli/build.py invokes content_validator and exits
non-zero on error-severity defects."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FEINSCHLIFF = REPO / "feinschliff"
LAYOUT = FEINSCHLIFF / "brands" / "feinschliff" / "layouts" / "action-title.slide.dsl"


def _run_build(content_yaml: str, tmp_path: Path) -> subprocess.CompletedProcess:
    content_file = tmp_path / "content.yaml"
    content_file.write_text(content_yaml)
    out_file = tmp_path / "out.pptx"
    return subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli", "build",
            str(LAYOUT),
            "--brand", "feinschliff",
            "--content", str(content_file),
            "-o", str(out_file),
        ],
        capture_output=True, text=True, cwd=FEINSCHLIFF,
    )


def test_build_passes_on_clean_content(tmp_path):
    result = _run_build(
        "title: Q3 revenue rose 12%\n",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr


def test_build_fails_on_title_too_long(tmp_path):
    long_title = "title: " + " ".join(f"w{i}" for i in range(20)) + "\n"
    result = _run_build(long_title, tmp_path)
    assert result.returncode != 0
    assert "title-length" in (result.stderr + result.stdout)


def test_deck_build_fails_on_one_bad_slide(tmp_path):
    """Multi-slide deck: one slide with too-long title aborts the deck."""
    long_title = " ".join(f"w{i}" for i in range(20))
    plan_yaml = f"""
brand: feinschliff
slides:
  - layout: {FEINSCHLIFF / "brands" / "feinschliff" / "layouts" / "action-title.slide.dsl"}
    content:
      title: "Q3 revenue rose 12 percent"
  - layout: {FEINSCHLIFF / "brands" / "feinschliff" / "layouts" / "action-title.slide.dsl"}
    content:
      title: "{long_title}"
"""
    plan_file = tmp_path / "plan.yaml"
    plan_file.write_text(plan_yaml)
    out_file = tmp_path / "out.pptx"
    result = subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli", "deck", "build",
            str(plan_file),
            "-o", str(out_file),
        ],
        capture_output=True, text=True, cwd=FEINSCHLIFF,
    )
    assert result.returncode != 0, result.stdout + result.stderr
    combined = result.stderr + result.stdout
    assert "slide 2" in combined
    assert "title-length" in combined


def test_deck_build_passes_on_clean_multi_slide(tmp_path):
    """Multi-slide deck with all clean slides exits 0."""
    plan_yaml = f"""
brand: feinschliff
slides:
  - layout: {FEINSCHLIFF / "brands" / "feinschliff" / "layouts" / "action-title.slide.dsl"}
    content:
      title: "Q3 revenue rose 12 percent"
  - layout: {FEINSCHLIFF / "brands" / "feinschliff" / "layouts" / "action-title.slide.dsl"}
    content:
      title: "Customer churn dropped 8 points"
"""
    plan_file = tmp_path / "plan.yaml"
    plan_file.write_text(plan_yaml)
    out_file = tmp_path / "out.pptx"
    result = subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli", "deck", "build",
            str(plan_file),
            "-o", str(out_file),
        ],
        capture_output=True, text=True, cwd=FEINSCHLIFF,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_build_skip_content_lint_flag(tmp_path):
    """--skip-content-lint bypasses content checks on single-slide build."""
    content_file = tmp_path / "content.yaml"
    content_file.write_text("title: " + " ".join(f"w{i}" for i in range(20)) + "\n")
    out_file = tmp_path / "out.pptx"
    result = subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli", "build",
            str(LAYOUT),
            "--brand", "feinschliff",
            "--content", str(content_file),
            "-o", str(out_file),
            "--skip-content-lint",
        ],
        capture_output=True, text=True, cwd=FEINSCHLIFF,
    )
    assert result.returncode == 0, result.stderr


def test_deck_build_skip_content_lint_flag(tmp_path):
    """--skip-content-lint bypasses content checks on multi-slide build."""
    long_title = " ".join(f"w{i}" for i in range(20))
    plan_yaml = f"""
brand: feinschliff
slides:
  - layout: {FEINSCHLIFF / "brands" / "feinschliff" / "layouts" / "action-title.slide.dsl"}
    content:
      title: "{long_title}"
"""
    plan_file = tmp_path / "plan.yaml"
    plan_file.write_text(plan_yaml)
    out_file = tmp_path / "out.pptx"
    result = subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli", "deck", "build",
            str(plan_file),
            "-o", str(out_file),
            "--skip-content-lint",
        ],
        capture_output=True, text=True, cwd=FEINSCHLIFF,
    )
    assert result.returncode == 0, result.stderr
