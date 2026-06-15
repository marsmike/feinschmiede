"""Master-template renderer: open a brand-authored .pptx, add slides off its
layouts, fill placeholders by index. Replaces the DSL pipeline for brands that
ship a real master.

Three mechanisms:
  - FillPlan        → layout-fill (placeholders → strings / paragraphs)
  - ChartSpec       → chart into an OBJECT placeholder, master theme applied
  - PictureRef      → image into a PICTURE placeholder or arbitrary bbox
  - ClonePlan       → deep-copy a bespoke source slide, patch text via XML
"""

from feinschmiede.master_template.catalog import (
    Catalog,
    LayoutEntry,
    PlaceholderSchema,
    SnippetEntry,
    load_catalog,
)
from feinschmiede.master_template.chart import ChartSpec
from feinschmiede.master_template.clone_plan import ClonePlan
from feinschmiede.master_template.fill_plan import FillPlan
from feinschmiede.master_template.picture import PictureRef
from feinschmiede.master_template.render import render, strip_existing_slides
from feinschmiede.master_template.themes import (
    build_swap,
    discover_themes,
    load_theme_colors,
    recolor_element,
)

__all__ = [
    "Catalog",
    "ChartSpec",
    "ClonePlan",
    "FillPlan",
    "LayoutEntry",
    "PictureRef",
    "PlaceholderSchema",
    "SnippetEntry",
    "build_swap",
    "discover_themes",
    "load_catalog",
    "load_theme_colors",
    "recolor_element",
    "render",
    "strip_existing_slides",
]
