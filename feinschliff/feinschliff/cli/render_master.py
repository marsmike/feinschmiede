"""`feinschliff render-master` — master-template renderer CLI.

For brand packs that ship a real `.pptx` master, skip the DSL pipeline
entirely. Open the master, fill placeholders by index, clone bespoke
source slides where needed.

  feinschliff render-master --brand-pack <path> --plans <yaml> -o OUT.pptx

The plans YAML is a list of FillPlan / ClonePlan entries:

  plans:
    - type: fill
      layout: "Title + Graphical Content + Text"
      fills:
        0: "Headline"
        1: ["First bullet", "Second bullet"]
        # chart:
        # 1: { kind: column, categories: [Q1,Q2], series: [["Revenue",[1,2]]] }
        # picture:
        # 1: { picture: ./image.png }
    - type: clone
      snippet_id: timeline-12-months
      text_replacements:
        - ["Timeline 4", "Roadmap H1 2026"]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

from feinschmiede.master_template import (
    ChartSpec,
    ClonePlan,
    FillPlan,
    PictureRef,
    render,
)


def register(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--brand-pack", required=True, help="Path to a master-template brand pack directory")
    parser.add_argument("--plans", required=True, help="YAML file with the list of plans")
    parser.add_argument("-o", "--output", required=True, help="Output .pptx path")
    parser.set_defaults(func=cmd_render_master)


def cmd_render_master(args: argparse.Namespace) -> int:
    brand_pack = Path(args.brand_pack)
    plans_path = Path(args.plans)
    out = Path(args.output)

    if not brand_pack.exists():
        print(f"brand pack not found: {brand_pack}", file=sys.stderr)
        return 2
    if not (brand_pack / "layouts.yaml").exists():
        print(
            f"{brand_pack} is not a master-template brand pack "
            "(missing layouts.yaml); use `feinschliff build` for DSL packs",
            file=sys.stderr,
        )
        return 2

    with plans_path.open() as fh:
        doc = yaml.safe_load(fh) or {}
    plans = [_parse_plan(p, plans_path.parent) for p in doc.get("plans", [])]

    out_path = render(brand_pack, plans, out)
    print(f"wrote {out_path} ({out_path.stat().st_size / 1024:.1f} KB, {len(plans)} slides)")
    return 0


def _parse_plan(d: dict[str, Any], base: Path) -> FillPlan | ClonePlan:
    kind = d.get("type", "fill")
    if kind == "clone":
        return ClonePlan(
            snippet_id=d["snippet_id"],
            text_replacements=[tuple(pair) for pair in d.get("text_replacements", [])],
        )
    if kind != "fill":
        raise ValueError(f"unknown plan type: {kind!r}")
    fills: dict[int, Any] = {}
    for idx_str, value in (d.get("fills") or {}).items():
        idx = int(idx_str)
        fills[idx] = _parse_fill_value(value, base)
    hero_d = d.get("hero_image")
    hero = _parse_picture(hero_d, base) if hero_d else None
    return FillPlan(layout=d["layout"], fills=fills, hero_image=hero)


def _parse_fill_value(value: Any, base: Path):
    if isinstance(value, list) and all(isinstance(x, str) for x in value):
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if "chart" in value:
            return _parse_chart(value["chart"])
        if "picture" in value:
            return _parse_picture(value, base)
    raise TypeError(f"unsupported fill value: {value!r}")


def _parse_chart(d: dict[str, Any]) -> ChartSpec:
    return ChartSpec(
        kind=d["kind"],
        categories=list(d["categories"]),
        series=[(name, list(values)) for name, values in d.get("series", [])],
    )


def _parse_picture(d: dict[str, Any], base: Path) -> PictureRef:
    raw = d["picture"]
    path = Path(raw)
    if not path.is_absolute():
        path = (base / path).resolve()
    return PictureRef(path=path, behind=bool(d.get("behind", False)))
