"""FillPlan: one slide off a named layout with placeholder fills.

Fill values:
  str               → single-line text
  list[str]         → multi-paragraph; first becomes ph.text, rest add_paragraph
  ChartSpec         → chart replaces the placeholder
  PictureRef        → picture into the placeholder

`hero_image` is for chapter layouts that expect an image behind the layout's
chrome at a brand-known bbox (declared in layouts.yaml).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from feinschmiede.master_template.catalog import Catalog
from feinschmiede.master_template.chart import ChartSpec, add_chart_into_placeholder
from feinschmiede.master_template.picture import (
    PictureRef,
    insert_picture_at_bbox,
    insert_picture_into_placeholder,
)

FillValue = str | list[str] | ChartSpec | PictureRef


@dataclass
class FillPlan:
    layout: str
    fills: dict[int, FillValue] = field(default_factory=dict)
    hero_image: PictureRef | None = None


def apply_fill_plan(prs, plan: FillPlan, catalog: Catalog) -> None:
    layout_entry = catalog.layouts.get(plan.layout)
    if layout_entry is None:
        raise KeyError(f"layout not in catalog: {plan.layout!r}")
    layout = _layout_by_name(prs, plan.layout)
    slide = prs.slides.add_slide(layout)

    for idx, value in plan.fills.items():
        if isinstance(value, ChartSpec):
            add_chart_into_placeholder(slide, idx, value)
        elif isinstance(value, PictureRef):
            insert_picture_into_placeholder(slide, idx, value)
        elif isinstance(value, str):
            _fill_text(slide, idx, [value])
        elif isinstance(value, list):
            _fill_text(slide, idx, value)
        else:
            raise TypeError(f"unsupported fill value type: {type(value).__name__}")

    if plan.hero_image is not None:
        bbox = layout_entry.hero_image_bbox_emu
        if bbox is None:
            raise ValueError(
                f"layout {plan.layout!r} has hero_image fill but no "
                "hero_image_bbox_emu in layouts.yaml"
            )
        insert_picture_at_bbox(slide, plan.hero_image, bbox)


def _layout_by_name(prs, name: str):
    target = _normalize(name)
    for layout in prs.slide_layouts:
        if _normalize(layout.name) == target:
            return layout
    raise KeyError(f"layout not in master: {name!r}")


def _normalize(name: str) -> str:
    """Strip ASCII whitespace + NBSP. PowerPoint masters often ship layout
    names with trailing U+00A0 (looks like a space in the editor). Without
    NBSP-aware compare, lookups against template names silently fail."""
    return name.strip().strip(" ").strip()


def _fill_text(slide, idx: int, lines: list[str]) -> None:
    ph = next(
        (p for p in slide.placeholders if p.placeholder_format.idx == idx),
        None,
    )
    if ph is None:
        raise KeyError(f"placeholder idx {idx} missing on layout")
    tf = ph.text_frame
    tf.text = lines[0]
    for line in lines[1:]:
        tf.add_paragraph().text = line
