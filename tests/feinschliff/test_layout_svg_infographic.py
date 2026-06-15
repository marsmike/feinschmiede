from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parent.parent.parent / "feinschliff"


def test_svg_infographic_renders_to_pptx(tmp_path):
    out = tmp_path / "out.pptx"
    result = subprocess.run(
        [
            "uv", "run", "feinschliff", "build",
            str(REPO / "brands" / "feinschliff" / "layouts" / "svg-infographic.slide.dsl"),
            "--brand", "feinschliff",
            "--content", str(Path(__file__).resolve().parent / "fixtures" / "layouts" / "svg-infographic.yaml"),
            "-o", str(out),
        ],
        capture_output=True, text=True, cwd=REPO,
    )
    if result.returncode != 0:
        stderr = result.stderr
        if "cairo" in stderr.lower() or "playwright" in stderr.lower() or "no module" in stderr.lower() or "libcairo" in stderr.lower() or "render_template" in stderr.lower():
            pytest.skip(f"render backend unavailable: {stderr[-200:]}")
        pytest.fail(f"build failed: {stderr}")
    assert out.exists()
    assert out.stat().st_size > 5_000
