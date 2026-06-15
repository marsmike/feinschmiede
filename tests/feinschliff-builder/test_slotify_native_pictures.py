"""Tests for slotify_native_pictures — promotes qualifying <p:pic> elements
inside native payloads to top-level ``image`` DSL slots."""
from __future__ import annotations

import base64
import struct
import zlib


def _b64(xml: str) -> str:
    return base64.b64encode(xml.encode()).decode("ascii")


def _make_1x1_png() -> bytes:
    """Return a minimal valid 1×1 white PNG."""
    def _chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = b"\x00\xff\xff\xff"
    compressed = zlib.compress(raw, 9)
    idat = _chunk(b"IDAT", compressed)
    iend = _chunk(b"IEND", b"")
    return signature + ihdr + idat + iend


# --- Minimal namespaced XML helpers ----------------------------------------

_NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _make_pic_xml(
    x_emu: int,
    y_emu: int,
    cx_emu: int,
    cy_emu: int,
    name: str = "Picture 1",
    r_embed: str = "rId1",
    decorative: bool = False,
) -> str:
    """Build a minimal <p:pic> XML fragment."""
    dec = '<adec:decorative val="1"/>' if decorative else ""
    return (
        f'<p:pic xmlns:p="{_NS_P}" xmlns:a="{_NS_A}" xmlns:r="{_NS_R}"'
        ' xmlns:adec="http://schemas.microsoft.com/office/drawing/2017/decorative">'
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


def _make_pic_xml_no_blip(x_emu: int, y_emu: int, cx_emu: int, cy_emu: int) -> str:
    """<p:pic> with no <a:blip> — no actual image data."""
    return (
        f'<p:pic xmlns:p="{_NS_P}" xmlns:a="{_NS_A}">'
        "<p:nvPicPr>"
        '<p:cNvPr id="2" name="Decoration"/>'
        "<p:cNvPicPr/><p:nvPr/>"
        "</p:nvPicPr>"
        "<p:blipFill/>"
        "<p:spPr>"
        "<a:xfrm>"
        f'<a:off x="{x_emu}" y="{y_emu}"/>'
        f'<a:ext cx="{cx_emu}" cy="{cy_emu}"/>'
        "</a:xfrm>"
        "</p:spPr>"
        "</p:pic>"
    )


# Canvas: 1920x1080 design-px → in EMU: 1920*9525 x 1080*9525
_CANVAS_W_PX = 1920
_CANVAS_H_PX = 1080
_EMU = 9525  # 1 design-px in EMU

# A "large" pic covering ~25% of the canvas (well above the 5% threshold)
_LARGE_X_EMU = 100 * _EMU
_LARGE_Y_EMU = 100 * _EMU
_LARGE_CX_EMU = 800 * _EMU   # 800 px wide
_LARGE_CY_EMU = 500 * _EMU   # 500 px tall  → 800*500 / (1920*1080) ≈ 19%

# A tiny pic covering ~0.1% of the canvas (below 5% threshold)
_SMALL_CX_EMU = 30 * _EMU
_SMALL_CY_EMU = 30 * _EMU


def _large_pic_xml(**kwargs) -> str:
    return _make_pic_xml(
        _LARGE_X_EMU, _LARGE_Y_EMU, _LARGE_CX_EMU, _LARGE_CY_EMU, **kwargs
    )


def _wrap_in_sp(pic_xml: str) -> str:
    """Wrap a <p:pic> in a minimal shape-tree context."""
    return (
        f'<p:sp xmlns:p="{_NS_P}">'
        f"{pic_xml}"
        "</p:sp>"
    )


from feinschliff_builder.decompile.slotify import slotify_native_pictures


# ---------------------------------------------------------------------------
# Happy-path: large content pic is promoted to image slot
# ---------------------------------------------------------------------------


def test_large_pic_promoted_to_image_slot():
    pic_xml = _large_pic_xml()
    payload = f'<root xmlns:p="{_NS_P}">{pic_xml}</root>'
    dsl = f'canvas 1920x1080\nnative graphic1 b64:"{_b64(payload)}"\n'

    new_dsl, slots, logs = slotify_native_pictures(
        dsl, None,
        canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
    )

    assert len(slots) == 1
    s = slots[0]
    assert s["name"] == "image_1"
    assert s["native_id"] == "graphic1"
    assert s["x"] == 100
    assert s["y"] == 100
    assert s["w"] == 800
    assert s["h"] == 500
    assert s["asset_path"] is None  # no asset_root provided

    # DSL must contain the promoted picture primitive bound to the new slot.
    # `picture` is the engine's image-rendering primitive (see
    # feinschliff/dsl/parser.py); emitting a non-existent `image` primitive
    # was the bug that caused FATAL unknown-compound at build time.
    assert 'picture 100,100 800x500 path:"{{ image_1 | default(' in new_dsl
    assert 'cover:true' in new_dsl

    # The native payload must no longer contain <p:pic
    new_b64 = new_dsl.split('b64:"')[1].split('"')[0]
    new_xml = base64.b64decode(new_b64).decode("utf-8")
    assert "<p:pic" not in new_xml

    # At least one log line
    assert any("graphic1" in l and "promoted" in l for l in logs)


# ---------------------------------------------------------------------------
# Skip: pic below area threshold stays in native
# ---------------------------------------------------------------------------


def test_small_pic_stays_in_native():
    pic_xml = _make_pic_xml(50 * _EMU, 50 * _EMU, _SMALL_CX_EMU, _SMALL_CY_EMU)
    payload = f'<root xmlns:p="{_NS_P}">{pic_xml}</root>'
    dsl = f'native graphic1 b64:"{_b64(payload)}"\n'

    new_dsl, slots, logs = slotify_native_pictures(
        dsl, None,
        canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
        area_threshold=0.05,
    )

    assert slots == []
    assert logs == []
    # DSL unchanged
    assert "image " not in new_dsl
    # Native line still present and identical
    assert 'native graphic1' in new_dsl


# ---------------------------------------------------------------------------
# Tile-grid content: pics at 2–4 % canvas DO promote at default threshold
# ---------------------------------------------------------------------------


def test_tile_grid_content_pics_promote_at_default_threshold():
    """Decompiled brand packs often ship content layouts as a 4–5 tile grid
    (product cards, feature strips). Each tile carries a content photo
    around 277×215 px = ~2.9 % of canvas — clearly content, not chrome.

    The original 5 % default treated these as small/decorative and left
    every tile baked inside the native, robbing the picker of a whole
    class of image-bearing content-role layouts. Default is now 1.5 %.
    """
    # Four tiles in a 2×2 grid, each 277 × 215 (≈ 2.9 % canvas).
    pic_xml = "".join(
        _make_pic_xml(x * _EMU, y * _EMU, 277 * _EMU, 215 * _EMU, name=f"Grafik {i}", r_embed=f"rId{i}")
        for i, (x, y) in enumerate(
            [(200, 200), (600, 200), (200, 500), (600, 500)], start=1
        )
    )
    payload = f'<root xmlns:p="{_NS_P}">{pic_xml}</root>'
    dsl = f'native graphic1 b64:"{_b64(payload)}"\n'

    new_dsl, slots, _ = slotify_native_pictures(
        dsl, None,
        canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
    )

    assert len(slots) == 4, f"expected 4 promoted tiles, got {len(slots)}"
    # All four should emit picture lines (the engine's actual primitive).
    assert new_dsl.count("picture ") == 4


# ---------------------------------------------------------------------------
# Skip: pic with logo-matching name stays in native
# ---------------------------------------------------------------------------


def test_logo_named_pic_stays_in_native():
    for name in ("Logo 1", "Brand Mark", "Company Icon", "Signet_Blue"):
        pic_xml = _large_pic_xml(name=name)
        payload = f'<root xmlns:p="{_NS_P}">{pic_xml}</root>'
        dsl = f'native graphic1 b64:"{_b64(payload)}"\n'

        new_dsl, slots, logs = slotify_native_pictures(
            dsl, None,
            canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
        )

        assert slots == [], f"Expected no slots for name={name!r}"
        assert "image " not in new_dsl


# ---------------------------------------------------------------------------
# Skip: decorative pic stays in native
# ---------------------------------------------------------------------------


def test_decorative_pic_stays_in_native():
    pic_xml = _large_pic_xml(decorative=True)
    payload = f'<root xmlns:p="{_NS_P}">{pic_xml}</root>'
    dsl = f'native graphic1 b64:"{_b64(payload)}"\n'

    new_dsl, slots, logs = slotify_native_pictures(
        dsl, None,
        canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
    )

    assert slots == []
    assert "image " not in new_dsl


# ---------------------------------------------------------------------------
# Skip: pic with no blip stays in native
# ---------------------------------------------------------------------------


def test_pic_without_blip_stays_in_native():
    pic_xml = _make_pic_xml_no_blip(_LARGE_X_EMU, _LARGE_Y_EMU, _LARGE_CX_EMU, _LARGE_CY_EMU)
    payload = f'<root xmlns:p="{_NS_P}">{pic_xml}</root>'
    dsl = f'native graphic1 b64:"{_b64(payload)}"\n'

    new_dsl, slots, logs = slotify_native_pictures(
        dsl, None,
        canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
    )

    assert slots == []
    assert "image " not in new_dsl


# ---------------------------------------------------------------------------
# next_idx parameter
# ---------------------------------------------------------------------------


def test_next_idx_controls_slot_name():
    pic_xml = _large_pic_xml()
    payload = f'<root xmlns:p="{_NS_P}">{pic_xml}</root>'
    dsl = f'native graphic1 b64:"{_b64(payload)}"\n'

    _, slots, _ = slotify_native_pictures(
        dsl, None,
        canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
        next_idx=3,
    )

    assert len(slots) == 1
    assert slots[0]["name"] == "image_3"


# ---------------------------------------------------------------------------
# Multiple pics: one qualified, one not
# ---------------------------------------------------------------------------


def test_mixed_pics_only_large_promoted():
    large = _large_pic_xml(r_embed="rId1")
    small = _make_pic_xml(
        200 * _EMU, 200 * _EMU, _SMALL_CX_EMU, _SMALL_CY_EMU, r_embed="rId2"
    )
    payload = f'<root xmlns:p="{_NS_P}">{large}{small}</root>'
    dsl = f'native graphic1 b64:"{_b64(payload)}"\n'

    new_dsl, slots, logs = slotify_native_pictures(
        dsl, None,
        canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
    )

    assert len(slots) == 1
    assert slots[0]["name"] == "image_1"

    # The small pic should still be in the modified native payload
    new_b64 = new_dsl.split('b64:"')[1].split('"')[0]
    new_xml = base64.b64decode(new_b64).decode("utf-8")
    # Large pic removed, small pic remains
    assert "<p:pic" in new_xml


# ---------------------------------------------------------------------------
# Native without any <p:pic> is left untouched
# ---------------------------------------------------------------------------


def test_native_without_pic_untouched():
    payload = '<p:sp xmlns:p="x"><a:t xmlns:a="y">Hello</a:t></p:sp>'
    dsl = f'native text1 b64:"{_b64(payload)}"\n'

    new_dsl, slots, logs = slotify_native_pictures(dsl, None)

    assert slots == []
    assert new_dsl == dsl


# ---------------------------------------------------------------------------
# Image slot line is inserted BEFORE the native line it came from
# ---------------------------------------------------------------------------


def test_image_line_inserted_before_native():
    pic_xml = _large_pic_xml()
    payload = f'<root xmlns:p="{_NS_P}">{pic_xml}</root>'
    dsl = f'canvas 1920x1080\nnative graphic1 b64:"{_b64(payload)}"\n'

    new_dsl, slots, _ = slotify_native_pictures(
        dsl, None,
        canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
    )

    lines = new_dsl.splitlines()
    picture_idx = next(i for i, l in enumerate(lines) if l.startswith("picture "))
    native_idx = next(i for i, l in enumerate(lines) if l.startswith("native "))
    assert picture_idx < native_idx, (
        "promoted picture line must appear before its source native line"
    )


# ---------------------------------------------------------------------------
# Idempotency: second run doesn't re-promote (pic already removed)
# ---------------------------------------------------------------------------


def test_idempotent_second_run():
    pic_xml = _large_pic_xml()
    payload = f'<root xmlns:p="{_NS_P}">{pic_xml}</root>'
    dsl = f'native graphic1 b64:"{_b64(payload)}"\n'

    first_dsl, slots1, _ = slotify_native_pictures(
        dsl, None,
        canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
    )
    second_dsl, slots2, _ = slotify_native_pictures(
        first_dsl, None,
        canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
    )

    # Second run finds no pics to promote
    assert slots2 == []
    assert first_dsl == second_dsl


# ---------------------------------------------------------------------------
# asset_root: image file saved when sidecar is resolvable
# ---------------------------------------------------------------------------


def test_asset_extraction_via_sidecar(tmp_path):
    """When a sidecar xml_file payload contains a <p:pic> with an r:embed
    that maps to an actual file under asset_root, the bytes are copied out."""
    import posixpath

    # Write a fake PNG under asset_root
    asset_root = tmp_path / "assets"
    asset_root.mkdir()
    png_bytes = _make_1x1_png()
    img_file = asset_root / "media" / "image1.png"
    img_file.parent.mkdir()
    img_file.write_bytes(png_bytes)

    # Build the sidecar XML with a Relationship block mapping rId1 -> media/image1.png
    rel_block = (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="image" Target="media/image1.png"/>'
        '</Relationships>'
    )
    pic_xml = _large_pic_xml(r_embed="rId1")
    payload = f'<root xmlns:p="{_NS_P}">{pic_xml}{rel_block}</root>'

    sidecar_name = "slide001_graphic.xml"
    sidecar = asset_root / sidecar_name
    sidecar.write_text(payload, encoding="utf-8")

    dsl = f'native graphic1 xml_file:"{sidecar_name}"\n'

    new_dsl, slots, logs = slotify_native_pictures(
        dsl, asset_root,
        canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
    )

    assert len(slots) == 1
    s = slots[0]
    assert s["asset_path"] is not None
    import pathlib
    assert pathlib.Path(s["asset_path"]).exists()
    assert pathlib.Path(s["asset_path"]).read_bytes() == png_bytes
