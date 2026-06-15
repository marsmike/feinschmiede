"""Picture insertion: into a PICTURE placeholder, or at an arbitrary bbox
(used for chapter hero images that sit behind the layout's text).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PictureRef:
    path: Path
    behind: bool = False


def insert_picture_into_placeholder(slide, ph_idx: int, ref: PictureRef) -> None:
    ph = next(p for p in slide.placeholders if p.placeholder_format.idx == ph_idx)
    ph.insert_picture(str(ref.path))


def insert_picture_at_bbox(
    slide,
    ref: PictureRef,
    bbox_emu: tuple[int, int, int, int],
) -> None:
    left, top, width, height = bbox_emu
    pic = slide.shapes.add_picture(str(ref.path), left, top, width, height)
    if ref.behind:
        sp_tree = slide.shapes._spTree
        sp_tree.remove(pic._element)
        sp_tree.insert(2, pic._element)
