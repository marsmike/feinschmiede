"""Opt-in brand-font embedding: `embed_brand_fonts` + `--embed-fonts` CLI flag.

Covers: fntdata parts + <p:embeddedFontLst> + embedTrueTypeFonts="1" land in
the saved package; idempotency; unresolvable families skip cleanly; <p:bold>
only when fontconfig yields a distinct bold file; end-to-end CLI flag.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from lxml import etree
from pptx import Presentation

from feinschmiede.dsl.tokens import Tokens
from feinschmiede.text.measure import find_font_file
from feinschliff.dsl.font_embed import embed_brand_fonts
from feinschliff.dsl.parser import parse_lines
from feinschliff.dsl.pptx_emit import build_presentation

pytestmark = pytest.mark.skipif(
    find_font_file("DejaVu Sans") is None,
    reason="DejaVu Sans not resolvable via fontconfig on this machine",
)

PLUGIN_ROOT = Path(__file__).resolve().parents[2] / "feinschliff"
_NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_SFNT_MAGICS = (b"\x00\x01\x00\x00", b"OTTO")


def _raw(family: str = "DejaVu Sans") -> dict:
    return {
        "color": {"ink": "#000000", "paper": "#FFFFFF"},
        "font-family": {"display": [family], "body": [family]},
        "font-size": {"body": "32px"},
        "font-weight": {"regular": 400},
        "style": {
            "body": {"font": "body", "size": "body",
                     "weight": "regular", "color": "ink"},
        },
    }


def _build(family: str = "DejaVu Sans"):
    """1-slide presentation + its tokens (reuses the test_italic pattern)."""
    nodes, _ = parse_lines(
        'text 100,100 "Hi" style:body maxwidth:800', source="<test>")
    tokens = Tokens.from_dict(_raw(family), brand_name="t")
    prs = build_presentation(nodes, tokens)
    return prs, tokens


def _save_and_open(prs, tmp_path: Path) -> zipfile.ZipFile:
    out = tmp_path / "out.pptx"
    prs.save(str(out))
    return zipfile.ZipFile(out)


def _fntdata_names(z: zipfile.ZipFile) -> list[str]:
    return [n for n in z.namelist() if n.startswith("ppt/fonts/")
            and n.endswith(".fntdata")]


def test_embed_adds_fntdata_parts_and_lst(tmp_path):
    prs, tokens = _build()
    assert embed_brand_fonts(prs, tokens) == ["DejaVu Sans"]

    out = tmp_path / "out.pptx"
    prs.save(str(out))
    z = zipfile.ZipFile(out)

    fonts = _fntdata_names(z)
    assert len(fonts) >= 1
    for name in fonts:
        assert z.read(name)[:4] in _SFNT_MAGICS

    pres_xml = z.read("ppt/presentation.xml").decode("utf-8")
    assert 'embedTrueTypeFonts="1"' in pres_xml
    assert "embeddedFontLst" in pres_xml
    assert 'typeface="DejaVu Sans"' in pres_xml

    # [Content_Types].xml must cover the fntdata extension or PowerPoint
    # rejects the package — the classic corruption source.
    ct = z.read("[Content_Types].xml").decode("utf-8")
    assert "application/x-fontdata" in ct

    Presentation(str(out))  # reopens cleanly


def test_embed_idempotent(tmp_path):
    prs, tokens = _build()
    first = embed_brand_fonts(prs, tokens)
    assert first == ["DejaVu Sans"]
    assert embed_brand_fonts(prs, tokens) == []  # second call: no-op

    z = _save_and_open(prs, tmp_path)
    n_parts_single = len(_fntdata_names(z))

    root = etree.fromstring(z.read("ppt/presentation.xml"))
    assert len(root.findall(f"{{{_NS_P}}}embeddedFontLst")) == 1

    # Same as a fresh single embed: nothing duplicated.
    prs2, tokens2 = _build()
    embed_brand_fonts(prs2, tokens2)
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    z2 = _save_and_open(prs2, fresh)
    assert n_parts_single == len(_fntdata_names(z2))


def test_embed_skips_unresolvable_family(tmp_path):
    prs, tokens = _build(family="No Such Font Family XYZ")
    assert embed_brand_fonts(prs, tokens) == []
    assert prs.element.get("embedTrueTypeFonts") is None
    assert prs.element.find(f"{{{_NS_P}}}embeddedFontLst") is None

    z = _save_and_open(prs, tmp_path)
    assert _fntdata_names(z) == []


def test_bold_entry_only_when_distinct_file(tmp_path):
    regular = find_font_file("DejaVu Sans")
    bold = find_font_file("DejaVu Sans", bold=True)
    distinct = (bold is not None and bold.suffix.lower() in {".ttf", ".otf"}
                and bold.resolve() != regular.resolve())

    prs, tokens = _build()
    embed_brand_fonts(prs, tokens)
    z = _save_and_open(prs, tmp_path)
    root = etree.fromstring(z.read("ppt/presentation.xml"))
    bold_els = root.findall(f".//{{{_NS_P}}}embeddedFont/{{{_NS_P}}}bold")

    if distinct:
        assert len(bold_els) == 1
        assert len(_fntdata_names(z)) == 2  # regular + bold parts
    else:
        assert bold_els == []
        assert len(_fntdata_names(z)) == 1


def test_embed_skips_unreadable_font_file(tmp_path, monkeypatch):
    """OSError on read_bytes() → WARN on stderr, empty result, no partial XML."""
    import feinschliff.dsl.font_embed as _fe

    real_find = _fe.find_font_file
    regular_path = real_find("DejaVu Sans")
    assert regular_path is not None, "pre-condition: DejaVu Sans must resolve"

    # Monkeypatch find_font_file to return a path that exists in name only.
    ghost = tmp_path / "ghost.ttf"
    # Do NOT create the file — it must raise OSError on read_bytes().

    def _fake_find(family, bold=False):
        return ghost

    monkeypatch.setattr(_fe, "find_font_file", _fake_find)

    prs, tokens = _build()
    import io
    import sys as _sys
    buf = io.StringIO()
    monkeypatch.setattr(_sys, "stderr", buf)
    result = embed_brand_fonts(prs, tokens)
    monkeypatch.setattr(_sys, "stderr", _sys.__stderr__)

    # Must return empty — no embedding happened.
    assert result == []
    # No partial XML: no <p:embeddedFontLst> and no embedTrueTypeFonts attr.
    assert prs.element.find(f"{{{_NS_P}}}embeddedFontLst") is None
    assert prs.element.get("embedTrueTypeFonts") is None
    # WARN must have been emitted.
    assert "WARN" in buf.getvalue()

    # Presentation must still save cleanly (no corrupt package state).
    out = tmp_path / "safe.pptx"
    prs.save(str(out))
    Presentation(str(out))


def test_cli_flag_embeds(tmp_path):
    """End-to-end `feinschliff build --embed-fonts` via subprocess, with a
    temp brand (feinschliff clone, fonts patched to DejaVu Sans) so the test
    does not depend on the feinschliff brand's Noto Sans being installed."""
    brands_root = tmp_path / "brands"
    brand_dir = brands_root / "dejavu-embed-test"
    shutil.copytree(PLUGIN_ROOT / "brands" / "feinschliff", brand_dir)
    tokens_path = brand_dir / "tokens.json"
    raw = json.loads(tokens_path.read_text())
    raw["font-family"]["display"] = {"$value": ["DejaVu Sans"]}
    raw["font-family"]["body"] = {"$value": ["DejaVu Sans"]}
    tokens_path.write_text(json.dumps(raw))

    content = tmp_path / "content.yaml"
    content.write_text("title: Q3 revenue rose 12%\n")
    out = tmp_path / "out.pptx"
    env = dict(os.environ, FEINSCHLIFF_BRAND_PATH=str(brands_root))
    result = subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli", "build",
            str(PLUGIN_ROOT / "brands" / "feinschliff" / "layouts" / "action-title.slide.dsl"),
            "--brand", "dejavu-embed-test",
            "--content", str(content),
            "--embed-fonts",
            # action-title has an optional-but-gated picture slot; that
            # gate is orthogonal to font embedding.
            "--allow-missing-assets",
            "-o", str(out),
        ],
        capture_output=True, text=True, cwd=PLUGIN_ROOT, env=env,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "embedded fonts: DejaVu Sans" in result.stderr

    z = zipfile.ZipFile(out)
    assert len(_fntdata_names(z)) >= 1
    assert 'embedTrueTypeFonts="1"' in z.read("ppt/presentation.xml").decode()
