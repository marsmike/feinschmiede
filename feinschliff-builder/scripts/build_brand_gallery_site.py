"""Build the static brand-gallery site at `docs/index.html`.

Walks every brand pack under `brands/`, reads metadata from DESIGN.md +
tokens.json + catalog.json, and emits a single-page HTML site that
showcases all brands × all layouts as a browseable grid.

Layout thumbnails are referenced from Cloudflare R2 at
`https://assets.marsmike.com/feinschliff/brand-previews/<brand>/<NN>-<id>.png`,
so the repo stays light. The PNGs are uploaded separately via
`/tmp/atlas-fetch/upload_to_r2.py`.

Run:
    uv run python scripts/build_brand_gallery_site.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from html import escape
from pathlib import Path
from textwrap import dedent

REPO = Path(__file__).resolve().parent.parent  # feinschliff-builder/
WORKSPACE = REPO.parent                          # workspace root (post-split)
GALLERY_EXCLUDE: frozenset[str] = frozenset()

# Brands are split across feinschliff/ (core: 3 brands) and
# feinschliff-extra/ (10 brands) since v0.2.0. Index by name so the
# rest of the script can look up a brand root without caring which
# plugin ships it.
BRAND_ROOTS: dict[str, Path] = {}
for _plugin_brands in (
    WORKSPACE / "feinschliff" / "brands",
    WORKSPACE / "feinschliff-extra" / "brands",
):
    if _plugin_brands.is_dir():
        for _d in sorted(_plugin_brands.iterdir()):
            if _d.name in GALLERY_EXCLUDE:
                continue
            if _d.is_dir() and (_d / "tokens.json").is_file():
                BRAND_ROOTS[_d.name] = _d
# Shared toolkit layouts live with the core plugin.
SHARED_LAYOUTS = WORKSPACE / "feinschliff" / "brands" / "feinschliff" / "layouts"
DOCS = WORKSPACE / "docs" / "brands"
PREVIEWS = WORKSPACE / "docs" / "brand-previews"
R2_ASSET_BASE = "https://assets.marsmike.com/feinschliff/brand-previews"
LOCAL_ASSET_BASE = "../brand-previews"
ASSET_BASE = R2_ASSET_BASE  # overridden in main() when --local is passed
# Per-build cachebust appended to every image URL. The CDN at
# `assets.marsmike.com` caches aggressively and we cannot purge from
# this token; appending `?v=<build-stamp>` makes every Pages deploy mint
# fresh cache keys so updated renders surface immediately.
CACHE_BUST = str(int(time.time()))

DARK_FIRST: frozenset[str] = frozenset()  # no dark-first standalone brands remain

# Pull role/phase4 metadata from the picker so gallery cards show real roles.
# The try/except keeps the script runnable outside the feinschliff venv.
sys.path.insert(0, str(REPO))
try:
    from feinschliff.layout_picker import _LAYOUTS as _PICKER_LAYOUTS, _PHASE4_LAYOUTS
except ImportError:
    _PICKER_LAYOUTS: dict = {}
    _PHASE4_LAYOUTS: frozenset = frozenset()

# Brands whose tokens + slides are freely redistributable under MIT.
# The remaining brands carry trademarked visual identities (demo only).
# Note: catppuccin-latte/macchiato, feinschliff-dark, gruvbox-dark, nord,
# solarized-dark have been demoted to themes under the feinschliff brand.
_MIT_BRANDS = frozenset({
    "feinschliff",
    "annual-review", "geometric", "shapes", "scientific",
    "gs-ramspau",
})


def parse_design_md(path: Path) -> dict:
    """Extract YAML frontmatter + Overview prose from a brand's DESIGN.md."""
    text = path.read_text()
    fm = {}
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            fm_block = text[3:end].strip()
            body = text[end + 4:].strip()
            for line in fm_block.splitlines():
                m = re.match(r"^([\w-]+):\s*(.+?)(?:\s*#.*)?$", line)
                if m and not line.lstrip().startswith("#"):
                    fm[m.group(1)] = m.group(2).strip().strip('"').strip("'")

    # Overview = prose after first '## Overview' header until the next ##
    overview = ""
    m = re.search(r"^##\s+Overview\s*\n(.+?)(?=^## |\Z)", body, re.M | re.S)
    if m:
        overview = m.group(1).strip()
    return {"frontmatter": fm, "overview": overview}


def palette_from_tokens(tokens_path: Path) -> list[tuple[str, str, str]]:
    """Return [(slot_name, hex, description), ...] in canonical order."""
    tok = json.loads(tokens_path.read_text())
    color = tok.get("color", {})
    order = [
        "accent", "accent-hover", "highlight",
        "ink", "graphite", "steel", "silver",
        "paper", "paper-2", "off-white", "off-white-2",
        "navy-100", "navy-200", "navy-300", "navy-400",
        "navy-500", "navy-600", "navy-700", "navy-800", "black",
        "fog", "rule-dark", "white",
    ]
    rows = []
    for slot in order:
        meta = color.get(slot)
        if not meta or not isinstance(meta, dict):
            continue
        rows.append((slot, meta.get("$value", ""), meta.get("$description", "")))
    return rows


def typography_from_tokens(tokens_path: Path) -> dict:
    tok = json.loads(tokens_path.read_text())
    ff = tok.get("font-family", {})
    return {
        "display": (ff.get("display", {}) or {}).get("$value", []),
        "body": (ff.get("body", {}) or {}).get("$value", []),
        "mono": (ff.get("mono", {}) or {}).get("$value", []),
    }


def _humanize(layout_id: str) -> str:
    """`two-column-cards` → `Two Column Cards`."""
    return " ".join(part.capitalize() for part in layout_id.split("-"))


def discover_layouts(brand: str) -> list[dict]:
    """V2 layout discovery: shared layouts + brand overrides/extensions.

    For the feinschliff brand (which owns the shared toolkit layouts), the
    full shared set is returned. For extra brands that carry their own
    brand-specific layouts, only those brand-local layouts are returned —
    they don't ship the shared toolkit slides, so including them here would
    inflate the count and reference PNGs that don't exist for those brands.

    Role + phase4 metadata are pulled from feinschliff.layout_picker so layout cards
    show accurate classifications — including the four-column-cards fix
    (content-columns, not data-timeline).
    """
    brand_layouts = BRAND_ROOTS[brand] / "layouts"
    has_brand_layouts = brand_layouts.is_dir() and any(brand_layouts.glob("*.slide.dsl"))

    if has_brand_layouts and brand != "feinschliff":
        # Extra brand: show only its own layouts (shared toolkit isn't rendered for it)
        seen: dict[str, Path] = {}
        for dsl in sorted(brand_layouts.glob("*.slide.dsl")):
            seen[dsl.stem.removesuffix(".slide")] = dsl
    else:
        # feinschliff (or any future brand without a layouts/ dir): shared toolkit
        seen = {}
        for dsl in sorted(SHARED_LAYOUTS.glob("*.slide.dsl")):
            seen[dsl.stem.removesuffix(".slide")] = dsl
        if has_brand_layouts:
            for dsl in sorted(brand_layouts.glob("*.slide.dsl")):
                seen[dsl.stem.removesuffix(".slide")] = dsl

    return [
        {
            "id": lid,
            "name": _humanize(lid),
            "role": _PICKER_LAYOUTS.get(lid, {}).get("role", ""),
            "is_phase4": lid in _PHASE4_LAYOUTS,
        }
        for lid in sorted(seen)
    ]


def _themes_for_brand(root: Path) -> list[dict] | None:
    """Return per-theme palette+typography for brands that have a themes/ dir.

    Each entry: {id, name, palette, typography, is_default}.
    Returns None when the brand has no themes/ dir (extra brands).
    """
    themes_dir = root / "themes"
    if not themes_dir.is_dir():
        return None

    base = json.loads((root / "tokens.json").read_text())
    default_theme = base.get("$default_theme") or "default"

    result = []
    for theme_dir in sorted(themes_dir.iterdir()):
        if not theme_dir.is_dir():
            continue
        tj = theme_dir / "tokens.json"
        if not tj.is_file():
            continue
        theme_raw = json.loads(tj.read_bytes())
        # Deep-merge: theme tokens on top of brand base
        merged = _deep_merge_simple(base, theme_raw)
        tid = theme_dir.name
        result.append({
            "id": tid,
            "name": tid.replace("-", " ").title(),
            "palette": _palette_from_raw(merged),
            "typography": _typography_from_raw(merged),
            "is_default": (tid == default_theme),
        })
    return result or None


def _deep_merge_simple(base: dict, override: dict) -> dict:
    """Shallow-recursive deep merge of two token dicts (no Tokens validation)."""
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge_simple(result[k], v)
        else:
            result[k] = v
    return result


def _palette_from_raw(tok: dict) -> list[tuple[str, str, str]]:
    """Extract palette swatches from a raw (already-merged) token dict."""
    color = tok.get("color", {})
    order = [
        "accent", "accent-hover", "highlight",
        "ink", "graphite", "steel", "silver",
        "paper", "paper-2", "off-white", "off-white-2",
        "navy-100", "navy-200", "navy-300", "navy-400",
        "navy-500", "navy-600", "navy-700", "navy-800", "black",
        "fog", "rule-dark", "white",
    ]
    rows = []
    for slot in order:
        meta = color.get(slot)
        if not meta or not isinstance(meta, dict):
            continue
        rows.append((slot, meta.get("$value", ""), meta.get("$description", "")))
    return rows


def _typography_from_raw(tok: dict) -> dict:
    ff = tok.get("font-family", {})
    return {
        "display": (ff.get("display", {}) or {}).get("$value", []),
        "body": (ff.get("body", {}) or {}).get("$value", []),
        "mono": (ff.get("mono", {}) or {}).get("$value", []),
    }


def brand_meta(brand: str) -> dict:
    root = BRAND_ROOTS[brand]
    design = parse_design_md(root / "DESIGN.md")
    themes = _themes_for_brand(root)
    # Brand-level palette/typography = default theme's resolved tokens (or raw tokens for extra brands)
    default_theme = next((t for t in (themes or []) if t["is_default"]), None)
    palette = default_theme["palette"] if default_theme else palette_from_tokens(root / "tokens.json")
    typography = default_theme["typography"] if default_theme else typography_from_tokens(root / "tokens.json")
    return {
        "id": brand,
        "name": design["frontmatter"].get("name", brand),
        "version": design["frontmatter"].get("version", ""),
        "overview": design["overview"],
        "palette": palette,
        "typography": typography,
        "themes": themes,  # None for brands without themes/ dir
        "layouts": discover_layouts(brand),
        "is_dark": brand in DARK_FIRST,
        "has_atlas": (PREVIEWS / brand / "_atlas.png").is_file(),
        "license": "mit" if brand in _MIT_BRANDS else "demo",
    }


def _layout_card_html(brand_id: str, i: int, layout: dict) -> str:
    """Render one layout preview card, including role chip and Phase 4 badge."""
    lid = escape(layout["id"])
    role = escape(layout["role"])
    name = escape(layout["name"])
    url = f"{ASSET_BASE}/{brand_id}/{i:02d}-{lid}.png?v={CACHE_BUST}"
    ph4 = '<span class="badge badge-ph4">ph4</span>' if layout["is_phase4"] else ""
    return (
        f'<a class="layout-card" href="{url}" rel="noopener">\n'
        f'    <img loading="lazy" src="{url}" alt="{name}">\n'
        f'    <div class="meta">\n'
        f'        <span class="layout-id">{lid}{ph4}</span>\n'
        f'        <span class="layout-role" data-role="{role}">{role}</span>\n'
        f'    </div>\n'
        f'</a>\n'
    )


def _render_palette_html(palette: list[tuple[str, str, str]]) -> str:
    return "".join(
        f'<div class="swatch" style="--c:{escape(hex_)}" '
        f'title="{escape(slot)} · {escape(hex_)} · {escape(desc)}"><span>{escape(slot)}</span></div>'
        for slot, hex_, desc in palette
        if hex_
    )


def _render_typography_html(typography: dict) -> str:
    return (
        f'<div class="typography">'
        f'<span class="t-label">display</span>'
        f'<span class="t-sample" style="font-family: {", ".join(escape(f) for f in typography["display"])};">'
        f'The quick brown fox jumps over the lazy dog</span>'
        f'<span class="t-label">body</span>'
        f'<span class="t-sample t-body" style="font-family: {", ".join(escape(f) for f in typography["body"])};">'
        f'The quick brown fox jumps over the lazy dog</span>'
        f'</div>'
    )


def render_brand_section(brand: dict) -> str:
    themes = brand.get("themes")

    if themes:
        # Theme switcher: one button per theme; active = default theme
        default_id = next((t["id"] for t in themes if t["is_default"]), themes[0]["id"])
        switcher_buttons = "".join(
            f'<button class="theme-chip{" active" if t["is_default"] else ""}" '
            f'data-theme-target="{escape(t["id"])}">{escape(t["name"])}</button>'
            for t in themes
        )
        switcher_html = (
            f'<nav class="theme-switcher" aria-label="Theme">'
            f'{switcher_buttons}'
            f'</nav>'
        )
        # Per-theme palette + typography blocks (hidden when not active)
        theme_blocks_html = ""
        for t in themes:
            hidden = "" if t["is_default"] else " hidden"
            theme_blocks_html += (
                f'<div class="theme-block"{hidden} data-theme-block="{escape(t["id"])}">'
                f'{_render_typography_html(t["typography"])}'
                f'<div class="palette">{_render_palette_html(t["palette"])}</div>'
                f'</div>'
            )
        chrome_html = switcher_html + theme_blocks_html
        section_extra = f' data-default-theme="{escape(default_id)}"'
    else:
        # No themes — render as before
        chrome_html = (
            _render_typography_html(brand["typography"])
            + f'<div class="palette">{_render_palette_html(brand["palette"])}</div>'
        )
        section_extra = ""

    layout_cards = "".join(
        _layout_card_html(brand["id"], i, layout)
        for i, layout in enumerate(brand["layouts"], start=1)
    )
    dark_attr = ' data-dark="true"' if brand["is_dark"] else ""
    license_badge = (
        '<span class="badge badge-mit">MIT</span>'
        if brand["license"] == "mit"
        else '<span class="badge badge-demo">demo</span>'
    )
    atlas_html = ""
    if brand["has_atlas"]:
        atlas_url = f'{ASSET_BASE}/{brand["id"]}/_atlas.png?v={CACHE_BUST}'
        atlas_html = dedent(f'''\
            <a class="atlas-overview" href="{atlas_url}" target="_blank" rel="noopener"
               aria-label="Open {escape(brand["name"])} atlas overview in a new tab">
                <img loading="lazy" src="{atlas_url}" alt="{escape(brand["name"])} — all layouts at a glance">
                <span class="atlas-caption">{len(brand["layouts"])} layouts · open full size ↗</span>
            </a>
        ''')
    return dedent(f'''\
        <section class="brand"{dark_attr}{section_extra} id="{escape(brand["id"])}">
            <header class="brand-header">
                <h2>{escape(brand["name"])}<span class="brand-id"> · {escape(brand["id"])}</span> {license_badge}</h2>
                <p class="brand-overview">{escape(brand["overview"])}</p>
                {chrome_html}
            </header>
            {atlas_html}<div class="layouts">
                {layout_cards}
            </div>
        </section>
    ''')


CSS = r"""
:root {
  --bg: #faf8f3;
  --fg: #0b1a33;
  --muted: #5a6478;
  --accent: #c9a24a;
  --rule: #d6d1c2;
  --card-bg: #ffffff;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: 'Noto Sans', 'Helvetica Neue', Arial, sans-serif;
  background: var(--bg);
  color: var(--fg);
  line-height: 1.5;
}
header.site-header {
  padding: 48px 32px 24px;
  border-bottom: 1px solid var(--rule);
}
header.site-header .site-title { display: flex; align-items: center; gap: 16px; }
header.site-header .site-mark { width: 52px; height: 52px; flex: none; }
header.site-header h1 {
  margin: 0;
  font-size: 36px;
  font-weight: 700;
  letter-spacing: -0.02em;
}
header.site-header p {
  margin: 8px 0 0;
  color: var(--muted);
  max-width: 64ch;
}
nav.brand-nav {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--bg);
  border-bottom: 1px solid var(--rule);
  padding: 12px 32px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 13px;
}
nav.brand-nav a {
  text-decoration: none;
  color: var(--muted);
  padding: 4px 10px;
  border-radius: 4px;
  background: var(--card-bg);
  border: 1px solid var(--rule);
  white-space: nowrap;
}
nav.brand-nav a:hover { color: var(--fg); border-color: var(--accent); }
nav.brand-nav .group-label {
  color: var(--muted);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  font-size: 11px;
  padding: 4px 6px;
}
section.brand {
  border-top: 1px solid var(--rule);
  padding: 48px 32px 64px;
}
section.brand[data-dark="true"] {
  background: #0f1820;
  color: #e8e5dc;
}
section.brand[data-dark="true"] .brand-overview,
section.brand[data-dark="true"] .typography .t-label { color: #aab0bc; }
section.brand[data-dark="true"] .layout-card { background: #1a2230; border-color: #2a3140; }
section.brand[data-dark="true"] .layout-card .meta { border-top-color: #2a3140; }
section.brand[data-dark="true"] nav.brand-nav { background: #0f1820; }
.brand-header h2 {
  margin: 0 0 12px;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.01em;
}
.brand-header h2 .brand-id {
  font-weight: 400;
  color: var(--muted);
  font-size: 18px;
  letter-spacing: 0;
  margin-left: 8px;
}
.brand-overview {
  max-width: 80ch;
  margin: 0 0 16px;
}
.typography {
  display: grid;
  grid-template-columns: 80px 1fr;
  gap: 4px 16px;
  margin: 16px 0;
  font-size: 13px;
}
.t-label {
  color: var(--muted);
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  align-self: center;
}
.t-sample {
  font-size: 22px;
  font-weight: 500;
}
.t-sample.t-body { font-size: 14px; font-weight: 400; }
.palette {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin: 16px 0 8px;
}
.swatch {
  width: 64px;
  height: 64px;
  background: var(--c);
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  display: flex;
  align-items: flex-end;
  justify-content: flex-start;
  padding: 4px;
  font-size: 9px;
  font-family: ui-monospace, Menlo, monospace;
  color: rgba(0, 0, 0, 0.6);
  text-shadow: 0 0 2px rgba(255, 255, 255, 0.4);
  cursor: help;
}
.swatch span { background: rgba(255, 255, 255, 0.7); padding: 1px 3px; border-radius: 2px; }
.atlas-overview {
  display: block;
  margin: 24px 0 8px;
  border: 1px solid var(--rule);
  border-radius: 6px;
  overflow: hidden;
  background: var(--card-bg);
  text-decoration: none;
  color: inherit;
  position: relative;
  transition: box-shadow 0.15s ease;
}
.atlas-overview:hover { box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08); }
.atlas-overview img { display: block; width: 100%; height: auto; }
.atlas-overview .atlas-caption {
  position: absolute;
  right: 10px;
  bottom: 10px;
  background: rgba(11, 26, 51, 0.78);
  color: #f0ece4;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
section.brand[data-dark="true"] .atlas-overview { background: #1a2230; border-color: #2a3140; }
.layouts {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  margin-top: 32px;
}
.layout-card {
  background: var(--card-bg);
  border: 1px solid var(--rule);
  border-radius: 6px;
  overflow: hidden;
  text-decoration: none;
  color: inherit;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.layout-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}
.layout-card img {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: contain;
  background: #f0f0f0;
}
.layout-card .meta {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  border-top: 1px solid var(--rule);
  font-size: 12px;
}
.layout-id {
  font-family: ui-monospace, Menlo, monospace;
  font-weight: 600;
}
.layout-role {
  color: var(--muted);
  font-size: 11px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
footer.site-footer {
  padding: 32px;
  border-top: 1px solid var(--rule);
  color: var(--muted);
  font-size: 13px;
  text-align: center;
}
footer.site-footer a { color: var(--accent); }

/* ---- Badges (license + Phase 4) ---- */
.badge {
  display: inline-block;
  padding: 2px 7px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  vertical-align: middle;
  line-height: 1.5;
  white-space: nowrap;
}
.badge-mit  { background: #d4edda; color: #155724; border: 1px solid #a3cfac; }
.badge-demo { background: #f0f0f0; color: #555555; border: 1px solid #cccccc; }
.badge-ph4  { background: #e8eeff; color: #3555b0; border: 1px solid #bcc8ef;
              margin-left: 5px; font-size: 9px; }
section.brand[data-dark="true"] .badge-mit  { background: #1a3a24; color: #7ec8a0; border-color: #2a5c3a; }
section.brand[data-dark="true"] .badge-demo { background: #1a2230; color: #aab0bc; border-color: #2a3140; }
section.brand[data-dark="true"] .badge-ph4  { background: #1a2244; color: #8fa8e0; border-color: #2a3a6a; }

/* ---- Role chip colour-coding ---- */
.layout-role[data-role^="data"]    { color: #3555b0; }
.layout-role[data-role^="content"] { color: #1a6b2a; }
.layout-role[data-role^="title"],
.layout-role[data-role^="chapter"] { color: #a05c00; }
.layout-role[data-role="closer"],
.layout-role[data-role="quote"],
.layout-role[data-role="agenda"],
.layout-role[data-role="reference"] { color: var(--muted); }
section.brand[data-dark="true"] .layout-role[data-role^="data"]    { color: #8fa8e0; }
section.brand[data-dark="true"] .layout-role[data-role^="content"] { color: #7ec8a0; }
section.brand[data-dark="true"] .layout-role[data-role^="title"],
section.brand[data-dark="true"] .layout-role[data-role^="chapter"] { color: #d4aa6e; }

/* ---- Theme switcher ---- */
nav.theme-switcher {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 12px 0 4px;
}
.theme-chip {
  padding: 4px 12px;
  border-radius: 16px;
  border: 1px solid var(--rule);
  background: var(--card-bg);
  color: var(--muted);
  font-size: 12px;
  cursor: pointer;
  transition: border-color 0.12s ease, color 0.12s ease, background 0.12s ease;
}
.theme-chip:hover { border-color: var(--accent); color: var(--fg); }
.theme-chip.active {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
  font-weight: 600;
}
section.brand[data-dark="true"] .theme-chip {
  background: #1a2230;
  border-color: #2a3140;
  color: #aab0bc;
}
section.brand[data-dark="true"] .theme-chip.active {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}

/* ---- Lightbox ---- */
.lightbox {
  position: fixed;
  inset: 0;
  background: rgba(11, 26, 51, 0.95);
  display: none;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 32px;
  cursor: zoom-out;
}
.lightbox.open { display: flex; }
.lightbox-img {
  max-width: 100%;
  max-height: calc(100vh - 160px);
  object-fit: contain;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
  cursor: default;
}
.lightbox-caption {
  position: absolute;
  top: 24px;
  left: 32px;
  right: 32px;
  color: #f0ece4;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 16px;
  font-size: 14px;
  pointer-events: none;
}
.lightbox-caption strong { font-size: 16px; font-weight: 600; }
.lightbox-caption .lb-counter {
  font-family: ui-monospace, Menlo, monospace;
  color: #aab0bc;
}
.lightbox-btn {
  position: absolute;
  background: rgba(255, 255, 255, 0.08);
  color: #f0ece4;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  width: 56px;
  height: 56px;
  font-size: 28px;
  font-family: ui-monospace, Menlo, monospace;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s ease;
  user-select: none;
}
.lightbox-btn:hover { background: rgba(255, 255, 255, 0.18); }
.lightbox-btn.lb-prev { left: 24px; top: 50%; transform: translateY(-50%); }
.lightbox-btn.lb-next { right: 24px; top: 50%; transform: translateY(-50%); }
.lightbox-btn.lb-close { top: 24px; right: 24px; width: 40px; height: 40px; font-size: 20px; }
@media (max-width: 700px) {
  .lightbox-btn.lb-prev { left: 8px; }
  .lightbox-btn.lb-next { right: 8px; }
}
"""


HEAD = dedent('''\
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>feinschmiede — Brand Pack Gallery</title>
        <meta name="description" content="Visual reference for the 12 feinschmiede brand packs and the 41 slide layouts each brand renders.">
        <link rel="icon" type="image/svg+xml" href="../feinschmiede-mark.svg">
        <meta name="theme-color" content="#0B1A33">
        <meta property="og:type" content="website">
        <meta property="og:title" content="feinschmiede — Brand Pack Gallery">
        <meta property="og:description" content="Every feinschmiede brand pack rendered against the full layout catalog.">
        <meta property="og:url" content="https://marsmike.github.io/feinschmiede/brands/">
        <meta property="og:image" content="https://marsmike.github.io/feinschmiede/feinschmiede-social.png">
        <meta name="twitter:card" content="summary_large_image">
''')


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--local", action="store_true",
                    help="Use relative paths to ../brand-previews instead of the R2 CDN")
    args = ap.parse_args()
    if args.local:
        global ASSET_BASE
        ASSET_BASE = LOCAL_ASSET_BASE

    DOCS.mkdir(parents=True, exist_ok=True)
    brand_ids = sorted(BRAND_ROOTS)
    brands = [brand_meta(bid) for bid in brand_ids]

    light = [b for b in brands if not b["is_dark"]]
    dark = [b for b in brands if b["is_dark"]]

    nav_html = []
    if light:
        nav_html.append('<span class="group-label">Light</span>')
        for b in light:
            nav_html.append(f'<a href="#{escape(b["id"])}">{escape(b["id"])}</a>')
    if dark:
        nav_html.append('<span class="group-label">Dark</span>')
        for b in dark:
            nav_html.append(f'<a href="#{escape(b["id"])}">{escape(b["id"])}</a>')

    sections_html = "\n".join(render_brand_section(b) for b in brands)

    total_layouts = sum(len(b["layouts"]) for b in brands)
    total_themes = sum(len(b["themes"]) for b in brands if b.get("themes"))
    body_top = dedent(f'''\
        <header class="site-header">
            <div class="site-title"><img class="site-mark" src="../feinschmiede-mark.svg" alt="feinschmiede" width="52" height="52"><h1>feinschmiede — Brand Pack Gallery</h1></div>
            <p>{len(brands)} brands · {total_themes} themes · {total_layouts} layouts. Click any thumbnail to open the carousel — arrow keys / on-screen buttons navigate, Esc closes.</p>
        </header>
        <nav class="brand-nav">
            {chr(10).join(nav_html)}
        </nav>
        {sections_html}
        <footer class="site-footer">
            <p><a href="../">← feinschmiede home</a> · Source: <a href="https://github.com/marsmike/feinschmiede/tree/main/feinschliff">marsmike/feinschmiede</a> · {'Slide previews live in the repo at <code>docs/brand-previews/</code>.' if ASSET_BASE == LOCAL_ASSET_BASE else 'Slide previews hosted on Cloudflare R2 at <code>assets.marsmike.com</code>.'}</p>
        </footer>
    ''')
    # Lightbox markup + script kept as a plain string so JS curly braces
    # don't collide with Python f-string interpolation.
    body_lightbox = dedent('''\
        <div class="lightbox" id="lightbox" aria-hidden="true">
            <button class="lightbox-btn lb-close" aria-label="Close (Esc)">×</button>
            <button class="lightbox-btn lb-prev" aria-label="Previous (←)">‹</button>
            <img class="lightbox-img" alt="">
            <button class="lightbox-btn lb-next" aria-label="Next (→)">›</button>
            <div class="lightbox-caption">
                <span class="lb-title"><strong></strong> · <span class="lb-role"></span></span>
                <span class="lb-counter"></span>
            </div>
        </div>
        <script>
        (function () {
            try {
                const cards = Array.from(document.querySelectorAll('.layout-card'));
                const lb = document.getElementById('lightbox');
                if (!lb || cards.length === 0) {
                    console.warn('lightbox: not initialised', { lb: !!lb, cardCount: cards.length });
                    return;
                }
                const img = lb.querySelector('.lightbox-img');
                const titleEl = lb.querySelector('.lb-title strong');
                const roleEl = lb.querySelector('.lb-role');
                const counterEl = lb.querySelector('.lb-counter');
                let cur = 0;

                function showAt(idx) {
                    cur = ((idx % cards.length) + cards.length) % cards.length;
                    const card = cards[cur];
                    img.src = card.getAttribute('href');
                    const id = card.querySelector('.layout-id').textContent;
                    const role = card.querySelector('.layout-role').textContent;
                    const brand = card.closest('.brand').id;
                    titleEl.textContent = brand + ' · ' + id;
                    roleEl.textContent = role;
                    counterEl.textContent = (cur + 1) + ' / ' + cards.length;
                }
                function openLB(idx) {
                    showAt(idx);
                    lb.classList.add('open');
                    lb.setAttribute('aria-hidden', 'false');
                    document.body.style.overflow = 'hidden';
                }
                function closeLB() {
                    lb.classList.remove('open');
                    lb.setAttribute('aria-hidden', 'true');
                    img.src = '';
                    document.body.style.overflow = '';
                }

                cards.forEach(function (card, idx) {
                    card.addEventListener('click', function (e) {
                        e.preventDefault();
                        e.stopPropagation();
                        openLB(idx);
                    });
                });
                lb.querySelector('.lb-close').addEventListener('click', function (e) { e.stopPropagation(); closeLB(); });
                lb.querySelector('.lb-prev').addEventListener('click', function (e) { e.stopPropagation(); showAt(cur - 1); });
                lb.querySelector('.lb-next').addEventListener('click', function (e) { e.stopPropagation(); showAt(cur + 1); });
                img.addEventListener('click', function (e) { e.stopPropagation(); });
                lb.addEventListener('click', closeLB);
                document.addEventListener('keydown', function (e) {
                    if (!lb.classList.contains('open')) return;
                    if (e.key === 'Escape') closeLB();
                    else if (e.key === 'ArrowLeft') showAt(cur - 1);
                    else if (e.key === 'ArrowRight') showAt(cur + 1);
                });
                console.log('lightbox ready: ' + cards.length + ' slides');
            } catch (err) {
                console.error('lightbox init failed:', err);
            }
        })();
        </script>
        <script>
        (function () {
            document.querySelectorAll('section.brand[data-default-theme]').forEach(function (section) {
                var chips = section.querySelectorAll('.theme-chip');
                var blocks = section.querySelectorAll('[data-theme-block]');
                chips.forEach(function (chip) {
                    chip.addEventListener('click', function () {
                        var tid = chip.getAttribute('data-theme-target');
                        chips.forEach(function (c) { c.classList.toggle('active', c === chip); });
                        blocks.forEach(function (b) {
                            b.hidden = b.getAttribute('data-theme-block') !== tid;
                        });
                    });
                });
            });
        })();
        </script>
    ''')
    body = body_top + body_lightbox

    html = (
        HEAD
        + f"        <style>{CSS}</style>\n"
        + "    </head>\n"
        + "    <body>\n"
        + body
        + "    </body>\n"
        + "</html>\n"
    )
    out = DOCS / "index.html"
    out.write_text(html)
    print(f"wrote {out} ({len(html)//1024} KB, {len(brands)} brands, "
          f"{total_themes} themes, {total_layouts} layouts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
