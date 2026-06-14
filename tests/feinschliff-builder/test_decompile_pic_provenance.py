"""Pic changeability follows the source author's own markers, not size:
placeholder pics and JPEG photos stay fillable picture slots; plain
PNG/SVG pics of ANY size are fixed corporate-design graphics and are
carried natively (verbatim element + media) so they are not bindable.

Regression for a corporate-pack regression: a 1920x426 PNG illustration band
("Grafik 27", deliberately NOT a placeholder) decompiled to a replaceable
image slot, while the audit flagged 142 icon/illustration natives that are
legitimate CD chrome under the provenance rule.
"""
from __future__ import annotations

from lxml import etree

from feinschliff_builder.decompile.pptx_svg_decompile import CanvasMap, _walk

_EMU_W, _EMU_H = 12192000, 6858000

_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

_PNG = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
_JPG = (b"\xff\xd8\xff\xe0" + b"\x00" * 64)


class _StubPart:
    def __init__(self, partname: str, blob: bytes):
        self.partname = partname
        self.blob = blob


class _StubSlidePart:
    def __init__(self, media: _StubPart):
        self._media = media

    def related_part(self, rid: str):
        return self._media


class _StubSlide:
    def __init__(self, media: _StubPart):
        self.part = _StubSlidePart(media)


def _pic_xml(ph: bool = False, name: str = "Grafik 27") -> str:
    ph_el = '<p:ph type="pic" idx="1"/>' if ph else ""
    nvpr = f"<p:nvPr>{ph_el}</p:nvPr>"
    # 3000000x2400000 EMU ≈ 472x378 px — far above any mark size.
    return f"""
      <p:pic xmlns:p="{_P}" xmlns:a="{_A}" xmlns:r="{_R}">
        <p:nvPicPr><p:cNvPr id="28" name="{name}"/><p:cNvPicPr/>{nvpr}</p:nvPicPr>
        <p:blipFill><a:blip r:embed="rId9"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>
        <p:spPr>
          <a:xfrm><a:off x="0" y="450000"/><a:ext cx="3000000" cy="2400000"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
      </p:pic>
    """


def _decompile_pic(partname: str, blob: bytes, ph: bool = False,
                   name: str = "Grafik 27"):
    tree = etree.fromstring(
        f'<p:spTree xmlns:p="{_P}" xmlns:a="{_A}">'
        f'{_pic_xml(ph=ph, name=name)}</p:spTree>'.encode()
    )
    shapes: list = []
    cmap = CanvasMap(_EMU_W, _EMU_H, 1920, 1080)
    slide = _StubSlide(_StubPart(partname, blob))
    _walk(tree, (0, 0), shapes, slide, cmap, {}, {})
    pics = [s for s in shapes if s.kind == "pic"]
    assert len(pics) == 1
    return pics[0]


def test_plain_png_pic_is_carried_natively_regardless_of_size():
    pic = _decompile_pic("/ppt/media/image9.png", _PNG)
    assert pic.native_xml is not None, (
        "plain PNG pic must be fixed CD chrome (carried natively), not a slot"
    )


def test_plain_jpeg_pic_stays_a_slot():
    pic = _decompile_pic("/ppt/media/image9.jpg", _JPG)
    assert pic.native_xml is None, (
        "JPEG photo must stay a fillable picture slot even outside a placeholder"
    )


def test_placeholder_pic_stays_a_slot():
    pic = _decompile_pic("/ppt/media/image9.png", _PNG, ph=True)
    assert pic.native_xml is None, (
        "placeholder pic is the template's own replaceable-content marker"
    )
    assert pic.ph_type == "pic"


def test_placeholder_named_pic_stays_a_slot():
    """Filling a content placeholder with a picture may DROP the <p:ph>
    element entirely (a corporate-pack picture region in a regression deck: name 'Content
    Placeholder 5', no ph) — the placeholder-derived shape name is the
    surviving marker and must keep the pic a fillable slot. German UI
    names ('Inhaltsplatzhalter', 'Bildplatzhalter') count too."""
    for nm in ("Content Placeholder 5", "Inhaltsplatzhalter 6",
               "Bildplatzhalter 2"):
        pic = _decompile_pic("/ppt/media/image9.png", _PNG, name=nm)
        assert pic.native_xml is None, f"{nm!r} must stay a picture slot"
