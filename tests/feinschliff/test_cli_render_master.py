"""`feinschliff render-master` — CLI smoke + YAML parsing."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml

from feinschliff.cli.render_master import _parse_plan
from feinschmiede.master_template import ChartSpec, ClonePlan, FillPlan, PictureRef

HOME = Path(os.path.expanduser("~"))
BSH_PACK = HOME / "work/feinschliff-bsh/bsh-pack-v5"
REPO_ROOT = Path(__file__).resolve().parents[2] / "feinschliff"


def test_parse_fill_plan_text():
    plan = _parse_plan(
        {"type": "fill", "layout": "X", "fills": {0: "Headline", 1: ["a", "b"]}},
        Path("."),
    )
    assert isinstance(plan, FillPlan)
    assert plan.layout == "X"
    assert plan.fills[0] == "Headline"
    assert plan.fills[1] == ["a", "b"]


def test_parse_fill_plan_chart():
    plan = _parse_plan(
        {
            "type": "fill",
            "layout": "X",
            "fills": {
                1: {"chart": {"kind": "column", "categories": ["Q1"], "series": [["Rev", [1.0]]]}}
            },
        },
        Path("."),
    )
    assert isinstance(plan.fills[1], ChartSpec)
    assert plan.fills[1].kind == "column"


def test_parse_fill_plan_picture(tmp_path):
    img = tmp_path / "img.png"
    img.write_bytes(b"")
    plan = _parse_plan(
        {"type": "fill", "layout": "X", "fills": {2: {"picture": str(img)}}},
        tmp_path,
    )
    assert isinstance(plan.fills[2], PictureRef)
    assert plan.fills[2].path == img


def test_parse_clone_plan():
    plan = _parse_plan(
        {
            "type": "clone",
            "snippet_id": "timeline",
            "text_replacements": [["old", "new"]],
        },
        Path("."),
    )
    assert isinstance(plan, ClonePlan)
    assert plan.snippet_id == "timeline"
    assert plan.text_replacements == [("old", "new")]


def test_unknown_plan_type_raises():
    with pytest.raises(ValueError):
        _parse_plan({"type": "xyz"}, Path("."))


@pytest.mark.skipif(not BSH_PACK.exists(), reason="BSH v5 pack not present locally")
def test_cli_renders_bsh_pack_end_to_end(tmp_path):
    plans_yaml = tmp_path / "plans.yaml"
    out = tmp_path / "out.pptx"
    plans_yaml.write_text(
        yaml.safe_dump(
            {
                "plans": [
                    {
                        "type": "fill",
                        "layout": "Title + Graphical Content + Text",
                        "fills": {0: "CLI smoke", 1: ["bullet"]},
                    },
                    {
                        "type": "clone",
                        "snippet_id": "timeline-12-months",
                        "text_replacements": [["Timeline 4", "Roadmap"]],
                    },
                ]
            }
        )
    )
    proc = subprocess.run(
        [
            "uv", "run", "feinschliff", "render-master",
            "--brand-pack", str(BSH_PACK),
            "--plans", str(plans_yaml),
            "-o", str(out),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert out.exists() and out.stat().st_size > 0


def test_cli_rejects_non_master_brand_pack(tmp_path):
    pack = tmp_path / "dsl_pack"
    pack.mkdir()
    (pack / "tokens.json").write_text("{}")
    plans = tmp_path / "p.yaml"
    plans.write_text("plans: []\n")
    proc = subprocess.run(
        [
            "uv", "run", "feinschliff", "render-master",
            "--brand-pack", str(pack),
            "--plans", str(plans),
            "-o", str(tmp_path / "x.pptx"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "layouts.yaml" in proc.stderr
