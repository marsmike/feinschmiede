"""Rects must interleave with native pics in SOURCE z-order. Emitting all
rects before the pic section painted native-carried background art (a corporate-pack
slide 34's banner wave, spTree position BEFORE the content tiles) on top of
the rects it underlies in the source."""
from __future__ import annotations

import base64

from feinschliff_builder.decompile.pptx_svg_decompile import (
    CanvasMap,
    Shape,
    emit_dsl,
)

_EMU_W, _EMU_H = 12192000, 6858000


def _pic_sp(name: str) -> str:
    return (
        '<p:pic xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        f'<p:nvPicPr><p:cNvPr id="9" name="{name}"/></p:nvPicPr></p:pic>'
    )


def test_native_pic_before_rect_keeps_source_order():
    banner = Shape(kind="pic", x=0, y=79, w=1920, h=426, is_picture=True,
                   native_xml=_pic_sp("Banner"),
                   native_media=base64.b64encode(b"\x89PNG\r\n\x1a\n").decode())
    tile = Shape(kind="rect", x=521, y=267, w=398, h=284, fill="accent")
    # spTree order: banner first (background), tile rect ON TOP.
    dsl = emit_dsl([banner, tile], CanvasMap(_EMU_W, _EMU_H, 1920, 1080), "t")
    assert dsl.index("native pic") < dsl.index("rect 521,267"), (
        "background native must emit BEFORE the rect drawn over it:\n" + dsl
    )


def test_full_bleed_background_rect_still_first():
    bg = Shape(kind="rect", x=0, y=0, w=1920, h=1080, fill="paper")
    pic = Shape(kind="pic", x=0, y=0, w=200, h=60, is_picture=True,
                native_xml=_pic_sp("Logo"),
                native_media=base64.b64encode(b"\x89PNG\r\n\x1a\n").decode())
    # spTree order: bg rect AFTER the pic — the full-bleed special case
    # still forces it to the bottom of the paint order.
    dsl = emit_dsl([pic, bg], CanvasMap(_EMU_W, _EMU_H, 1920, 1080), "t")
    assert dsl.index("rect 0,0 1920x1080") < dsl.index("native pic")
