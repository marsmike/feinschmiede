"""Public surface — re-export the master-template kernel.

Skills and small scripts call:

    from feinschliff import FillPlan, ClonePlan, render, apply_theme

The catalog inspector lives at `feinschliff.master_template.catalog` and
runs as `python -m feinschliff.master_template.catalog <brand_pack>`.
"""
from feinschliff.master_template import (
    ChartSpec,
    ClonePlan,
    FillPlan,
    PictureRef,
    apply_theme,
    master_path,
    render,
)

__all__ = ["FillPlan", "ClonePlan", "PictureRef", "ChartSpec", "render", "apply_theme", "master_path"]
