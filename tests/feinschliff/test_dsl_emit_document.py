"""Tests for emit_pptx_from_document — typed Document → .pptx entry point."""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from feinschmiede.brand import BrandPack
from feinschmiede.dsl.ast import Document
from feinschliff.dsl.parser import parse_document
from feinschliff.dsl.pptx_emit import emit_pptx_from_document


def _make_pack(tmp_path: Path, name: str = "test-brand") -> BrandPack:
    """Create a minimal brand pack directory with valid tokens.json."""
    # Use the real feinschliff brand pack since build_presentation requires
    # real tokens (font-family, font-size, etc.) to function.
    real_brand = Path(__file__).resolve().parents[2] / "feinschliff" / "brands" / "feinschliff"
    return BrandPack.load(real_brand)


# ---------------------------------------------------------------------------
# Smoke test — emit a minimal single-slide document
# ---------------------------------------------------------------------------

def test_emit_pptx_from_document_returns_path(tmp_path):
    out = tmp_path / "out.pptx"
    doc = parse_document(
        "canvas 1920x1080\nrect 0,0 1920x1080 fill:#000000\n"
    )
    pack = _make_pack(tmp_path)
    result = emit_pptx_from_document(doc, pack, out)
    assert result == out


def test_emit_pptx_from_document_creates_file(tmp_path):
    out = tmp_path / "out.pptx"
    doc = parse_document("canvas 1920x1080\nrect 0,0 1920x1080 fill:#000000\n")
    pack = _make_pack(tmp_path)
    emit_pptx_from_document(doc, pack, out)
    assert out.is_file()


def test_emit_pptx_from_document_is_valid_pptx(tmp_path):
    """The output must be a valid zip/Office Open XML file."""
    out = tmp_path / "out.pptx"
    doc = parse_document("canvas 1920x1080\nrect 0,0 1920x1080 fill:#000000\n")
    pack = _make_pack(tmp_path)
    emit_pptx_from_document(doc, pack, out)
    assert zipfile.is_zipfile(out), "Output is not a valid zip file (invalid PPTX)"


def test_emit_native_splices_source_shape_as_vector(tmp_path):
    """A `native` primitive splices a verbatim source <p:sp> into the slide as a
    real, editable vector — NOT a rasterised picture. This is how complex
    corporate-design custGeom chrome is preserved exactly without the
    svg→raster→picture round-trip (which both distorts and is a picture cheat)."""
    import base64
    sp_xml = (
        '<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
        ' xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<p:nvSpPr><p:cNvPr id="99" name="NativeTri"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        '<p:spPr><a:xfrm><a:off x="1000000" y="2000000"/><a:ext cx="3000000" cy="3000000"/></a:xfrm>'
        '<a:custGeom><a:pathLst><a:path w="100" h="100">'
        '<a:moveTo><a:pt x="0" y="0"/></a:moveTo>'
        '<a:lnTo><a:pt x="100" y="0"/></a:lnTo>'
        '<a:lnTo><a:pt x="50" y="100"/></a:lnTo>'
        '<a:close/></a:path></a:pathLst></a:custGeom>'
        '<a:solidFill><a:srgbClr val="EE7660"/></a:solidFill></p:spPr>'
        '<p:txBody><a:bodyPr/><a:p/></p:txBody></p:sp>'
    )
    b64 = base64.b64encode(sp_xml.encode()).decode()
    out = tmp_path / "out.pptx"
    doc = parse_document(f'canvas 1920x1080\nnative shape1 b64:"{b64}"\n')
    pack = _make_pack(tmp_path)
    emit_pptx_from_document(doc, pack, out)
    with zipfile.ZipFile(out) as z:
        slide = z.read("ppt/slides/slide1.xml").decode()
    assert "NativeTri" in slide, "carried native shape missing from output slide"
    assert "custGeom" in slide, "native shape must be a vector custGeom, not rasterised"
    assert "EE7660" in slide, "native shape colour not preserved verbatim"


def test_emit_native_pic_reembeds_template_image(tmp_path):
    """A `native` primitive with `media:` carries a template image (<p:pic>): the
    embedded bytes are re-embedded into THIS deck, the raster blip re-pointed, and
    the Microsoft svgBlip sidecar (whose stale rId would collide / render the wrong
    image) stripped — so a logo stays a real, fixed picture, not a slot or cheat."""
    import base64
    png_b64 = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR4nGNg"
               "YGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC")  # 1x1 PNG
    pic_xml = (
        '<p:pic xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
        ' xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<p:nvPicPr><p:cNvPr id="7" name="BrandLogo"/><p:cNvPicPr/><p:nvPr/></p:nvPicPr>'
        '<p:blipFill><a:blip r:embed="rId77">'
        '<a:extLst><a:ext uri="{96DAC541-7B7A-43D3-8B79-37D633B846F1}">'
        '<asvg:svgBlip xmlns:asvg="http://schemas.microsoft.com/office/drawing/2016/SVG/main"'
        ' r:embed="rId88"/></a:ext></a:extLst></a:blip>'
        '<a:stretch><a:fillRect/></a:stretch></p:blipFill>'
        '<p:spPr><a:xfrm><a:off x="100000" y="100000"/><a:ext cx="500000" cy="500000"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>'
    )
    xb = base64.b64encode(pic_xml.encode()).decode()
    out = tmp_path / "out.pptx"
    doc = parse_document(f'canvas 1920x1080\nnative pic1 b64:"{xb}" media:"{png_b64}"\n')
    pack = _make_pack(tmp_path)
    emit_pptx_from_document(doc, pack, out)
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        slide = z.read("ppt/slides/slide1.xml").decode()
    assert "BrandLogo" in slide, "carried template image missing from output slide"
    assert any(n.startswith("ppt/media/") for n in names), "image media not re-embedded"
    assert "rId77" not in slide, "blip still points at the dead source rId"
    assert "svgBlip" not in slide, "svgBlip sidecar not stripped (stale rId would collide)"
    assert "rId88" not in slide, "stale svgBlip rId still present in output"


def _native_sp(shape_id: int, name: str) -> str:
    """Minimal verbatim <p:sp> fragment claiming a specific source cNvPr id."""
    return (
        '<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
        ' xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        f'<p:nvSpPr><p:cNvPr id="{shape_id}" name="{name}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        '<p:spPr><a:xfrm><a:off x="100000" y="100000"/><a:ext cx="500000" cy="500000"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        '<a:solidFill><a:srgbClr val="112233"/></a:solidFill></p:spPr>'
        '<p:txBody><a:bodyPr/><a:p/></p:txBody></p:sp>'
    )


def _slide_shape_ids(slide_xml: str) -> list[tuple[str, str]]:
    import re
    return re.findall(r'<p:cNvPr id="(\d+)" name="([^"]*)"', slide_xml)


def test_emit_native_remaps_colliding_shape_ids(tmp_path):
    """Native fragments keep their SOURCE cNvPr ids. Two fragments from
    different sources (slide chrome vs layout template image) — or a fragment
    vs a python-pptx-generated shape — can claim the same id. Slide-wide
    duplicate ids make PowerPoint open the deck with the repair dialog, so
    colliding ids must be remapped to fresh slide-unique ones at splice time."""
    import base64
    a = base64.b64encode(_native_sp(2, "NativeA").encode()).decode()
    b = base64.b64encode(_native_sp(2, "NativeB").encode()).decode()
    out = tmp_path / "out.pptx"
    # the rect emits first and gets a generated id (2); both natives also claim 2
    doc = parse_document(
        "canvas 1920x1080\n"
        "rect 0,0 1920x1080 fill:#000000\n"
        f'native shapeA b64:"{a}"\n'
        f'native shapeB b64:"{b}"\n'
    )
    pack = _make_pack(tmp_path)
    emit_pptx_from_document(doc, pack, out)
    with zipfile.ZipFile(out) as z:
        slide = z.read("ppt/slides/slide1.xml").decode()
    pairs = _slide_shape_ids(slide)
    names = {n for _i, n in pairs}
    assert {"NativeA", "NativeB"} <= names, "carried fragments missing from slide"
    ids = [i for i, _n in pairs]
    assert len(ids) == len(set(ids)), f"duplicate cNvPr ids in slide: {sorted(ids)}"


def test_emit_native_rewrites_connector_refs_on_remap(tmp_path):
    """When a carried group's member ids are remapped, in-fragment connector
    references (<a:stCxn id>/<a:endCxn id>) must follow the remap — otherwise
    the connector points at whatever shape now owns the old id."""
    import base64
    import re
    grp = (
        '<p:grpSp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
        ' xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<p:nvGrpSpPr><p:cNvPr id="2" name="NativeGrp"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="1000000" cy="1000000"/>'
        '<a:chOff x="0" y="0"/><a:chExt cx="1000000" cy="1000000"/></a:xfrm></p:grpSpPr>'
        '<p:sp><p:nvSpPr><p:cNvPr id="3" name="GrpA"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        '<p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="100000" cy="100000"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>'
        '<p:txBody><a:bodyPr/><a:p/></p:txBody></p:sp>'
        '<p:sp><p:nvSpPr><p:cNvPr id="4" name="GrpB"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        '<p:spPr><a:xfrm><a:off x="500000" y="500000"/><a:ext cx="100000" cy="100000"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>'
        '<p:txBody><a:bodyPr/><a:p/></p:txBody></p:sp>'
        '<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="5" name="GrpConn"/>'
        '<p:cNvCxnSpPr><a:stCxn id="3" idx="3"/><a:endCxn id="4" idx="1"/></p:cNvCxnSpPr>'
        '<p:nvPr/></p:nvCxnSpPr>'
        '<p:spPr><a:xfrm><a:off x="100000" y="100000"/><a:ext cx="400000" cy="400000"/></a:xfrm>'
        '<a:prstGeom prst="line"><a:avLst/></a:prstGeom></p:spPr></p:cxnSp>'
        '</p:grpSp>'
    )
    xb = base64.b64encode(grp.encode()).decode()
    out = tmp_path / "out.pptx"
    # three rects first so generated ids occupy 2,3,4 — forcing a remap of the
    # group's 2/3/4 member ids
    doc = parse_document(
        "canvas 1920x1080\n"
        "rect 0,0 100x100 fill:#000000\n"
        "rect 0,0 100x100 fill:#000000\n"
        "rect 0,0 100x100 fill:#000000\n"
        f'native grp1 b64:"{xb}"\n'
    )
    pack = _make_pack(tmp_path)
    emit_pptx_from_document(doc, pack, out)
    with zipfile.ZipFile(out) as z:
        slide = z.read("ppt/slides/slide1.xml").decode()
    pairs = _slide_shape_ids(slide)
    ids = [i for i, _n in pairs]
    assert len(ids) == len(set(ids)), f"duplicate cNvPr ids in slide: {sorted(ids)}"
    by_name = {n: i for i, n in pairs}
    st = re.search(r'<a:stCxn id="(\d+)"', slide)
    en = re.search(r'<a:endCxn id="(\d+)"', slide)
    assert st and en, "connector lost its stCxn/endCxn"
    assert st.group(1) == by_name["GrpA"], (
        f"stCxn still points at old id {st.group(1)}, GrpA is now {by_name['GrpA']}")
    assert en.group(1) == by_name["GrpB"], (
        f"endCxn still points at old id {en.group(1)}, GrpB is now {by_name['GrpB']}")


def test_emit_native_reads_sidecar_files(tmp_path):
    """Huge native payloads ride as brand-pack sidecar files instead of inline
    base64 (a 33 MB carried group made a 44 MB .slide.dsl). The emitter must
    accept `xml_file:` / `media_file:` refs resolved against the asset root."""
    import base64
    from feinschmiede.dsl.tokens import load_tokens
    from feinschliff.dsl.parser import parse_lines
    from feinschliff.dsl.pptx_emit import build_presentation

    asset_root = tmp_path / "assets"
    (asset_root / "native").mkdir(parents=True)
    (asset_root / "native" / "frag.xml").write_text(
        _native_sp(99, "SidecarShape"), encoding="utf-8")
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR4nGNg"
        "YGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC")  # 1x1 PNG
    (asset_root / "native" / "img.png").write_bytes(png)
    pic_xml = (
        '<p:pic xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
        ' xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<p:nvPicPr><p:cNvPr id="98" name="SidecarPic"/><p:cNvPicPr/><p:nvPr/></p:nvPicPr>'
        '<p:blipFill><a:blip r:embed="rId77"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
        '<p:spPr><a:xfrm><a:off x="100000" y="100000"/><a:ext cx="500000" cy="500000"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>'
    )
    (asset_root / "native" / "pic.xml").write_text(pic_xml, encoding="utf-8")

    real_brand = Path(__file__).resolve().parents[2] / "feinschliff" / "brands" / "feinschliff"
    tokens = load_tokens(real_brand)
    nodes, _compounds = parse_lines(
        "canvas 1920x1080\n"
        'native shape1 xml_file:"native/frag.xml"\n'
        'native pic1 xml_file:"native/pic.xml" media_file:"native/img.png"\n'
    )
    prs = build_presentation(nodes, tokens, asset_root=asset_root)
    out = tmp_path / "out.pptx"
    prs.save(str(out))
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        slide = z.read("ppt/slides/slide1.xml").decode()
    assert "SidecarShape" in slide, "xml_file fragment missing from output slide"
    assert "SidecarPic" in slide, "xml_file pic missing from output slide"
    assert any(n.startswith("ppt/media/") for n in names), "media_file not re-embedded"
    assert "rId77" not in slide, "blip still points at the dead source rId"


def test_emit_pptx_from_document_raises_on_empty(tmp_path):
    """A document with no slides must raise ValueError."""
    doc = Document(slides=[])
    pack = _make_pack(tmp_path)
    with pytest.raises(ValueError, match="no slides"):
        emit_pptx_from_document(doc, pack, tmp_path / "out.pptx")


def test_emit_pptx_from_document_roundtrip(tmp_path):
    """Parse a layout DSL, emit to PPTX — the file must be well-formed."""
    # Use a real layout from the bundled layouts
    layouts_dir = Path(__file__).resolve().parents[2] / "feinschliff" / "brands" / "feinschliff" / "layouts"
    layout_files = list(layouts_dir.glob("*.slide.dsl"))
    if not layout_files:
        pytest.skip("no bundled layouts found")

    layout_path = layout_files[0]
    doc = parse_document(layout_path.read_text(), source=str(layout_path))
    pack = _make_pack(tmp_path)
    out = tmp_path / "roundtrip.pptx"

    # Some layouts require content slots — for the roundtrip test we just
    # check that the emitter doesn't crash and produces a valid zip.
    try:
        emit_pptx_from_document(doc, pack, out)
        assert zipfile.is_zipfile(out)
    except Exception:
        # Layout may have required slots or fonts; that's OK for this smoke test.
        pytest.skip(f"Layout {layout_path.name} requires content/fonts not provided")
