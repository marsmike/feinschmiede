"""Tests for slotify_native_pictures — <p:grpSp> descent.

Covers:
  - Pic nested one level deep in a group with non-zero offset → correct canvas bbox.
  - Pic nested two levels deep → offsets stack correctly.
  - Group containing a promoted pic AND a sibling shape → sibling preserved.
  - Scaled group (ext != chExt) → pic stays native (not promoted).
  - Group pic below area threshold → stays native.
  - Decorative pic inside group → stays native.
  - Logo-named pic inside group → stays native.
"""
from __future__ import annotations

import base64


def _b64(xml: str) -> str:
    return base64.b64encode(xml.encode()).decode("ascii")


_NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS_ADEC = "http://schemas.microsoft.com/office/drawing/2017/decorative"

_CANVAS_W_PX = 1920
_CANVAS_H_PX = 1080
_EMU = 9525  # 1 design-px in EMU

# Large pic: 800×500 px (≈19% canvas) — well above area threshold.
_LARGE_CX_EMU = 800 * _EMU
_LARGE_CY_EMU = 500 * _EMU

# Small pic: 30×30 px (≈0.04%) — below any reasonable threshold.
_SMALL_CX_EMU = 30 * _EMU
_SMALL_CY_EMU = 30 * _EMU


def _make_pic_xml(
    x_emu: int,
    y_emu: int,
    cx_emu: int,
    cy_emu: int,
    name: str = "Picture 1",
    r_embed: str = "rId1",
    decorative: bool = False,
) -> str:
    """Minimal <p:pic> fragment with all required sub-elements."""
    dec = f'<adec:decorative xmlns:adec="{_NS_ADEC}" val="1"/>' if decorative else ""
    return (
        f'<p:pic xmlns:p="{_NS_P}" xmlns:a="{_NS_A}" xmlns:r="{_NS_R}">'
        "<p:nvPicPr>"
        f'<p:cNvPr id="1" name="{name}"/>'
        "<p:cNvPicPr/>"
        f"<p:nvPr>{dec}</p:nvPr>"
        "</p:nvPicPr>"
        "<p:blipFill>"
        f'<a:blip r:embed="{r_embed}"/>'
        "</p:blipFill>"
        "<p:spPr>"
        "<a:xfrm>"
        f'<a:off x="{x_emu}" y="{y_emu}"/>'
        f'<a:ext cx="{cx_emu}" cy="{cy_emu}"/>'
        "</a:xfrm>"
        "</p:spPr>"
        "</p:pic>"
    )


def _make_sp_xml(name: str = "TextBox 1") -> str:
    """Minimal <p:sp> (text shape) — a sibling shape inside a group."""
    return (
        f'<p:sp xmlns:p="{_NS_P}" xmlns:a="{_NS_A}">'
        "<p:nvSpPr>"
        f'<p:cNvPr id="99" name="{name}"/>'
        "<p:cNvSpPr/><p:nvPr/>"
        "</p:nvSpPr>"
        "<p:spPr>"
        "<a:xfrm>"
        f'<a:off x="0" y="0"/>'
        f'<a:ext cx="{100 * _EMU}" cy="{50 * _EMU}"/>'
        "</a:xfrm>"
        "</p:spPr>"
        "<p:txBody><a:bodyPr/><a:p><a:r><a:t>Label</a:t></a:r></a:p></p:txBody>"
        "</p:sp>"
    )


def _make_grpsp_xml(
    grp_off_x: int,
    grp_off_y: int,
    grp_cx: int,
    grp_cy: int,
    ch_off_x: int,
    ch_off_y: int,
    ch_cx: int,
    ch_cy: int,
    *children_xml: str,
) -> str:
    """Minimal <p:grpSp> with xfrm metadata and given child XML strings."""
    children = "".join(children_xml)
    return (
        f'<p:grpSp xmlns:p="{_NS_P}" xmlns:a="{_NS_A}">'
        "<p:nvGrpSpPr>"
        '<p:cNvPr id="10" name="Group 1"/>'
        "<p:cNvGrpSpPr/><p:nvPr/>"
        "</p:nvGrpSpPr>"
        "<p:grpSpPr>"
        "<a:xfrm>"
        f'<a:off x="{grp_off_x}" y="{grp_off_y}"/>'
        f'<a:ext cx="{grp_cx}" cy="{grp_cy}"/>'
        f'<a:chOff x="{ch_off_x}" y="{ch_off_y}"/>'
        f'<a:chExt cx="{ch_cx}" cy="{ch_cy}"/>'
        "</a:xfrm>"
        "</p:grpSpPr>"
        f"{children}"
        "</p:grpSp>"
    )


from feinschliff_builder.decompile.slotify import slotify_native_pictures


# ---------------------------------------------------------------------------
# One level deep — non-zero group offset → correct canvas bbox
# ---------------------------------------------------------------------------


def test_grouped_pic_one_level_canvas_bbox():
    """A pic at group-local (0,0) inside a group placed at (200,150) px
    should emerge at canvas coords (200,150)."""
    grp_off_x = 200 * _EMU  # group placed at x=200 px on canvas
    grp_off_y = 150 * _EMU  # group placed at y=150 px on canvas
    grp_cx = _LARGE_CX_EMU
    grp_cy = _LARGE_CY_EMU
    ch_off_x = 0
    ch_off_y = 0
    ch_cx = _LARGE_CX_EMU
    ch_cy = _LARGE_CY_EMU

    # Pic at (0,0) in group-local space.
    pic = _make_pic_xml(0, 0, _LARGE_CX_EMU, _LARGE_CY_EMU)
    grp = _make_grpsp_xml(
        grp_off_x, grp_off_y, grp_cx, grp_cy,
        ch_off_x, ch_off_y, ch_cx, ch_cy,
        pic,
    )
    payload = f'<root xmlns:p="{_NS_P}">{grp}</root>'
    dsl = f'native g1 b64:"{_b64(payload)}"\n'

    new_dsl, slots, logs = slotify_native_pictures(
        dsl, None,
        canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
    )

    assert len(slots) == 1, f"expected 1 slot, got {len(slots)}"
    s = slots[0]
    # Canvas coords: pic_local(0,0) + group_off(200,150) − chOff(0,0) = (200,150)
    assert s["x"] == 200, f"expected x=200, got {s['x']}"
    assert s["y"] == 150, f"expected y=150, got {s['y']}"
    assert s["w"] == 800
    assert s["h"] == 500
    assert "picture 200,150 800x500" in new_dsl


def test_grouped_pic_nonzero_choff():
    """Group with chOff=(50,30) placed at off=(300,200): translation is
    off−chOff=(250,170).  Pic at group-local (10,20) → canvas (260,190)."""
    grp_off_x = 300 * _EMU
    grp_off_y = 200 * _EMU
    ch_off_x = 50 * _EMU
    ch_off_y = 30 * _EMU
    # Same ext as chExt → pure translation (no scale).
    grp_cx = ch_cx = _LARGE_CX_EMU
    grp_cy = ch_cy = _LARGE_CY_EMU

    pic_local_x = 10 * _EMU
    pic_local_y = 20 * _EMU
    pic = _make_pic_xml(pic_local_x, pic_local_y, _LARGE_CX_EMU, _LARGE_CY_EMU)
    grp = _make_grpsp_xml(
        grp_off_x, grp_off_y, grp_cx, grp_cy,
        ch_off_x, ch_off_y, ch_cx, ch_cy,
        pic,
    )
    payload = f'<root xmlns:p="{_NS_P}">{grp}</root>'
    dsl = f'native g1 b64:"{_b64(payload)}"\n'

    new_dsl, slots, _ = slotify_native_pictures(
        dsl, None,
        canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
    )

    assert len(slots) == 1
    # canvas_x = pic_local_x/EMU + (grp_off_x - ch_off_x)/EMU = 10 + (300-50) = 260
    # canvas_y = 20 + (200-30) = 190
    assert slots[0]["x"] == 260, f"got x={slots[0]['x']}"
    assert slots[0]["y"] == 190, f"got y={slots[0]['y']}"
    assert "picture 260,190" in new_dsl


# ---------------------------------------------------------------------------
# Two levels deep — offsets accumulate
# ---------------------------------------------------------------------------


def test_grouped_pic_two_levels_deep():
    """Pic inside an inner group inside an outer group — offsets stack."""
    # Outer group: off=(100,50), chOff=(0,0) → delta=(100,50).
    outer_off_x = 100 * _EMU
    outer_off_y = 50 * _EMU
    outer_cx = outer_cy = 1000 * _EMU
    outer_ch_off_x = outer_ch_off_y = 0
    outer_ch_cx = outer_ch_cy = 1000 * _EMU

    # Inner group: off=(200,100), chOff=(0,0) → delta=(200,100).
    inner_off_x = 200 * _EMU
    inner_off_y = 100 * _EMU
    inner_cx = inner_cy = 900 * _EMU
    inner_ch_off_x = inner_ch_off_y = 0
    inner_ch_cx = inner_ch_cy = 900 * _EMU

    # Pic at group-local (0,0).
    pic = _make_pic_xml(0, 0, _LARGE_CX_EMU, _LARGE_CY_EMU)
    inner_grp = _make_grpsp_xml(
        inner_off_x, inner_off_y, inner_cx, inner_cy,
        inner_ch_off_x, inner_ch_off_y, inner_ch_cx, inner_ch_cy,
        pic,
    )
    outer_grp = _make_grpsp_xml(
        outer_off_x, outer_off_y, outer_cx, outer_cy,
        outer_ch_off_x, outer_ch_off_y, outer_ch_cx, outer_ch_cy,
        inner_grp,
    )
    payload = f'<root xmlns:p="{_NS_P}">{outer_grp}</root>'
    dsl = f'native g1 b64:"{_b64(payload)}"\n'

    new_dsl, slots, _ = slotify_native_pictures(
        dsl, None,
        canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
    )

    assert len(slots) == 1, f"expected 1 slot, got {len(slots)}: {slots}"
    # canvas = pic_local(0,0) + inner_delta(200,100) + outer_delta(100,50) = (300,150)
    assert slots[0]["x"] == 300, f"got x={slots[0]['x']}"
    assert slots[0]["y"] == 150, f"got y={slots[0]['y']}"
    assert "picture 300,150" in new_dsl


# ---------------------------------------------------------------------------
# Sibling shape preservation — promoted pic removed, sibling stays
# ---------------------------------------------------------------------------


def test_group_sibling_shape_preserved_after_pic_promotion():
    """A group holds one large pic (→ promoted) and one text shape (→ stays
    inside the native payload)."""
    grp_off_x = 0
    grp_off_y = 0
    grp_cx = ch_cx = 1920 * _EMU
    grp_cy = ch_cy = 1080 * _EMU
    ch_off_x = ch_off_y = 0

    pic = _make_pic_xml(0, 0, _LARGE_CX_EMU, _LARGE_CY_EMU)
    sp = _make_sp_xml(name="SiblingTextBox")
    grp = _make_grpsp_xml(
        grp_off_x, grp_off_y, grp_cx, grp_cy,
        ch_off_x, ch_off_y, ch_cx, ch_cy,
        pic, sp,
    )
    payload = f'<root xmlns:p="{_NS_P}">{grp}</root>'
    dsl = f'native g1 b64:"{_b64(payload)}"\n'

    new_dsl, slots, _ = slotify_native_pictures(
        dsl, None,
        canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
    )

    assert len(slots) == 1, f"expected 1 promoted slot, got {slots}"

    # The native line must still be present (group with sibling).
    assert "native g1" in new_dsl

    # Extract and decode the modified payload; sibling shape must remain.
    new_b64 = new_dsl.split('b64:"')[1].split('"')[0]
    import base64 as _b64_mod
    new_xml = _b64_mod.b64decode(new_b64).decode("utf-8")
    assert "SiblingTextBox" in new_xml, "sibling text shape was wrongly removed"
    assert "<p:pic" not in new_xml, "promoted pic was not removed"


# ---------------------------------------------------------------------------
# Scaled group — skipped, pic stays native
# ---------------------------------------------------------------------------


def test_scaled_group_pic_stays_native():
    """A group where ext != chExt (scaling) must be skipped — the pic
    stays inside the native payload with no promotion."""
    grp_off_x = 0
    grp_off_y = 0
    grp_cx = 500 * _EMU   # scaled: half the chExt width
    grp_cy = 250 * _EMU
    ch_off_x = ch_off_y = 0
    ch_cx = 1000 * _EMU   # chExt != ext → scaled
    ch_cy = 500 * _EMU

    pic = _make_pic_xml(0, 0, _LARGE_CX_EMU, _LARGE_CY_EMU)
    grp = _make_grpsp_xml(
        grp_off_x, grp_off_y, grp_cx, grp_cy,
        ch_off_x, ch_off_y, ch_cx, ch_cy,
        pic,
    )
    payload = f'<root xmlns:p="{_NS_P}">{grp}</root>'
    dsl = f'native g1 b64:"{_b64(payload)}"\n'

    new_dsl, slots, _ = slotify_native_pictures(
        dsl, None,
        canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
    )

    assert slots == [], f"expected no slots for scaled group, got {slots}"
    assert "picture " not in new_dsl
    assert "native g1" in new_dsl


# ---------------------------------------------------------------------------
# Area threshold — small pic in group stays native
# ---------------------------------------------------------------------------


def test_grouped_small_pic_stays_native():
    """Pic inside a group but below the area threshold stays in native."""
    grp_off_x = grp_off_y = ch_off_x = ch_off_y = 0
    grp_cx = grp_cy = ch_cx = ch_cy = 1920 * _EMU

    pic = _make_pic_xml(0, 0, _SMALL_CX_EMU, _SMALL_CY_EMU)
    grp = _make_grpsp_xml(
        grp_off_x, grp_off_y, grp_cx, grp_cy,
        ch_off_x, ch_off_y, ch_cx, ch_cy,
        pic,
    )
    payload = f'<root xmlns:p="{_NS_P}">{grp}</root>'
    dsl = f'native g1 b64:"{_b64(payload)}"\n'

    new_dsl, slots, _ = slotify_native_pictures(
        dsl, None,
        canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
        area_threshold=0.015,
    )

    assert slots == []
    assert "picture " not in new_dsl


# ---------------------------------------------------------------------------
# Decorative pic in group stays native
# ---------------------------------------------------------------------------


def test_grouped_decorative_pic_stays_native():
    grp_off_x = grp_off_y = ch_off_x = ch_off_y = 0
    grp_cx = grp_cy = ch_cx = ch_cy = 1920 * _EMU

    pic = _make_pic_xml(0, 0, _LARGE_CX_EMU, _LARGE_CY_EMU, decorative=True)
    grp = _make_grpsp_xml(
        grp_off_x, grp_off_y, grp_cx, grp_cy,
        ch_off_x, ch_off_y, ch_cx, ch_cy,
        pic,
    )
    payload = f'<root xmlns:p="{_NS_P}">{grp}</root>'
    dsl = f'native g1 b64:"{_b64(payload)}"\n'

    new_dsl, slots, _ = slotify_native_pictures(
        dsl, None,
        canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
    )

    assert slots == []
    assert "picture " not in new_dsl


# ---------------------------------------------------------------------------
# Logo-named pic in group stays native
# ---------------------------------------------------------------------------


def test_grouped_logo_named_pic_stays_native():
    grp_off_x = grp_off_y = ch_off_x = ch_off_y = 0
    grp_cx = grp_cy = ch_cx = ch_cy = 1920 * _EMU

    pic = _make_pic_xml(0, 0, _LARGE_CX_EMU, _LARGE_CY_EMU, name="Logo Main")
    grp = _make_grpsp_xml(
        grp_off_x, grp_off_y, grp_cx, grp_cy,
        ch_off_x, ch_off_y, ch_cx, ch_cy,
        pic,
    )
    payload = f'<root xmlns:p="{_NS_P}">{grp}</root>'
    dsl = f'native g1 b64:"{_b64(payload)}"\n'

    new_dsl, slots, _ = slotify_native_pictures(
        dsl, None,
        canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
    )

    assert slots == []
    assert "picture " not in new_dsl


# ---------------------------------------------------------------------------
# Mixed: direct pic + grouped pic → both promoted, numbering is continuous
# ---------------------------------------------------------------------------


def test_direct_and_grouped_pic_both_promoted():
    """Payload with one direct <p:pic> and one in a group → both promoted,
    image_1 and image_2 in document order."""
    # Direct pic (top-level).
    direct_pic = _make_pic_xml(
        50 * _EMU, 50 * _EMU, _LARGE_CX_EMU, _LARGE_CY_EMU, r_embed="rId1"
    )

    # Grouped pic.
    grp_off_x = 1000 * _EMU
    grp_off_y = 200 * _EMU
    grp_cx = grp_cy = ch_cx = ch_cy = 500 * _EMU
    ch_off_x = ch_off_y = 0
    inner_pic = _make_pic_xml(0, 0, _LARGE_CX_EMU, _LARGE_CY_EMU, r_embed="rId2")
    grp = _make_grpsp_xml(
        grp_off_x, grp_off_y, grp_cx, grp_cy,
        ch_off_x, ch_off_y, ch_cx, ch_cy,
        inner_pic,
    )

    payload = f'<root xmlns:p="{_NS_P}">{direct_pic}{grp}</root>'
    dsl = f'native g1 b64:"{_b64(payload)}"\n'

    new_dsl, slots, logs = slotify_native_pictures(
        dsl, None,
        canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
    )

    assert len(slots) == 2, f"expected 2 slots, got {slots}"
    names = [s["name"] for s in slots]
    assert "image_1" in names
    assert "image_2" in names
    assert new_dsl.count("picture ") == 2
