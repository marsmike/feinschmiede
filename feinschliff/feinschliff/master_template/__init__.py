"""Master-template renderer for feinschmiede brand packs.

Open a brand pack's master.pptx, optionally overlay a color theme, then
play a list of FillPlan / ClonePlan entries against it. Ported from
abzug (~390 LOC, four data-shape modules + render dispatcher + brand
helpers) plus the theme_overlay module that lets a single master.pptx
serve N visual variations without authoring multiple files.
"""
from feinschliff.master_template._brand import master_path
from feinschliff.master_template.fill_plan import FillPlan, PictureRef, ChartSpec
from feinschliff.master_template.clone_plan import ClonePlan
from feinschliff.master_template.render import render
from feinschliff.master_template.theme_overlay import apply_theme

__all__ = ["FillPlan", "ClonePlan", "PictureRef", "ChartSpec", "render", "apply_theme", "master_path"]
