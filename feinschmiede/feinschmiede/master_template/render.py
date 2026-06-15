"""Orchestrator: open the master, strip its example slides, apply each plan.

Public entry point:
    render(brand_pack: Path, plans: Iterable[FillPlan | ClonePlan], out: Path) -> Path
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pptx import Presentation

from feinschmiede.master_template.catalog import Catalog, load_catalog
from feinschmiede.master_template.clone_plan import ClonePlan, apply_clone_plan
from feinschmiede.master_template.fill_plan import FillPlan, apply_fill_plan

_PPTX_RELS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def render(
    brand_pack: Path,
    plans: Iterable[FillPlan | ClonePlan],
    out: Path,
    *,
    catalog: Catalog | None = None,
) -> Path:
    cat = catalog or load_catalog(Path(brand_pack))
    prs = Presentation(str(cat.master_pptx))
    strip_existing_slides(prs)

    for plan in plans:
        if isinstance(plan, FillPlan):
            apply_fill_plan(prs, plan, cat)
        elif isinstance(plan, ClonePlan):
            apply_clone_plan(prs, plan, cat)
        else:
            raise TypeError(f"unknown plan type: {type(plan).__name__}")

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))
    return out


def strip_existing_slides(prs) -> None:
    sld_id_lst = prs.slides._sldIdLst
    rels = prs.part.rels
    for sld_id in list(sld_id_lst):
        r_id = sld_id.get(_PPTX_RELS)
        sld_id_lst.remove(sld_id)
        if r_id in rels:
            rels.pop(r_id)
