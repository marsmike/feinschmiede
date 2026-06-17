"""Deep-copy a bespoke source slide. Patch text via XML `<a:t>` runs.

Replacements are queued per old-string — each `(old, new)` entry consumes
one occurrence in document order. Image rIds are remapped and packaged
media is deduped by partname so cloning a slide whose images live in the
master doesn't produce a duplicate-name zip entry.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

from lxml import etree

from feinschliff.master_template._brand import index_layouts, norm

_A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


@dataclass
class ClonePlan:
    source_idx: int
    replacements: list[tuple[str, str]] = field(default_factory=list)


def apply_clone(prs, source_prs, plan: ClonePlan, layout_by_name: dict | None = None) -> None:
    n_src = len(source_prs.slides)
    if not 0 <= plan.source_idx < n_src:
        raise IndexError(
            f"ClonePlan.source_idx={plan.source_idx} out of range; "
            f"source deck has {n_src} slides"
        )
    src_slide = source_prs.slides[plan.source_idx]
    src_name = norm(src_slide.slide_layout.name)
    # Reuse the caller's normalized layout index when given (render() builds it
    # once); otherwise build our own so apply_clone stays usable standalone.
    # index_layouts' collision policy matches the FillPlan path — a pack with
    # two layouts that normalize identically RAISES here, rather than silently
    # picking whichever python-pptx returns first.
    if layout_by_name is None:
        layout_by_name = index_layouts(prs)
    dest_layout = layout_by_name.get(src_name)
    if dest_layout is None:
        raise KeyError(
            f"clone source slide {plan.source_idx} uses layout "
            f"{src_slide.slide_layout.name!r} which is absent from target master"
        )
    new_slide = prs.slides.add_slide(dest_layout)

    # Drop the blank placeholders the layout dropped in.
    for sh in list(new_slide.shapes):
        sh._element.getparent().remove(sh._element)

    # Deep-copy source shapes (skipping group bookkeeping nodes).
    dest_spTree = new_slide.shapes._spTree
    for child in list(src_slide.shapes._spTree):
        if etree.QName(child).localname in ("nvGrpSpPr", "grpSpPr"):
            continue
        dest_spTree.append(copy.deepcopy(child))

    # Remap image rels: reuse existing target parts by partname.
    # KNOWN ISSUE: when `source_deck` is a different file with
    # an image at the same partname but different bytes, `prs.save()` may
    # raise a duplicate-name error or silently corrupt the output.
    package_parts = {
        rel.target_part.partname: rel.target_part
        for rel in prs.part.package.iter_rels()
        if rel.reltype.endswith("/image")
    }
    rid_map = {}
    for old_rid, rel in src_slide.part.rels.items():
        if not rel.reltype.endswith("/image"):
            continue
        target_part = package_parts.get(rel.target_part.partname, rel.target_part)
        rid_map[old_rid] = new_slide.part.relate_to(target_part, rel.reltype)
    if rid_map:
        embed_attr = f"{{{_R_NS}}}embed"
        for el in dest_spTree.iter():
            old = el.get(embed_attr)
            if old in rid_map:
                el.set(embed_attr, rid_map[old])

    # Patch text. Repeating entries queue per old-string.
    queues: dict[str, list[str]] = {}
    for old, new in plan.replacements:
        queues.setdefault(old, []).append(new)
    for t in dest_spTree.iter(f"{{{_A_NS}}}t"):
        if t.text in queues and queues[t.text]:
            t.text = queues[t.text].pop(0)
