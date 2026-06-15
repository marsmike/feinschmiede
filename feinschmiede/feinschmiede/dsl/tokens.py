"""Token loader + resolver, including brief-defaults helper.

A brand pack ships a `tokens.json` (the existing v1 schema is fine for PoC).
Optional `DESIGN.md` frontmatter may declare `extends: <parent-brand>` to
inherit and selectively override.

  brand_pack/
    DESIGN.md          # frontmatter with extends + override notes
    tokens.json        # color / font-family / font-weight / font-size / slide
    compounds/*.dsl    # brand-specific compounds

Style refs in DSL (`style:eyebrow`) resolve here. A style is a *bundle* of
font-family + size + weight + color, looked up by name in tokens.json or
inherited from a parent brand. The bundle is built lazily from the role
name following the existing convention:

  style:title       -> font-family.display, font-size.slide-title,  weight.semibold, color.ink
  style:body        -> font-family.body,    font-size.body,         weight.regular,  color.graphite
  style:eyebrow     -> font-family.mono,    font-size.eyebrow,      weight.medium,   color.steel
  style:kpi-value   -> font-family.display, font-size.kpi-value,    weight.bold,     color.ink
  ...

The bundle defaults live in `STYLE_BUNDLES`; brands can override any field
via `tokens.json` -> `style: { <name>: {...} }` (forward-compatible -- not
required for PoC).

Fill refs (`fill:accent`, `stroke:fog`) resolve directly to the color
token of that name.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from feinschmiede.jsonwalk import deep_merge


_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "tokens.schema.json"

_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _is_hex_literal(s: str) -> bool:
    return bool(_HEX_RE.match(s))


def _expand_short_hex(s: str) -> str:
    # `#abc` → `#aabbcc`
    return "#" + "".join(ch * 2 for ch in s[1:])


def _strip_px(v: Any, key: str, brand_name: str) -> float:
    """Coerce a px-valued token to float. Accepts a bare number (assumed px)
    or a string ending in `"px"`. Raises ValueError on any other unit
    (`"1.5rem"`, `"12em"`) — silent acceptance would crash deeper in the
    emitter with a much less useful traceback.
    """
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s.endswith("px"):
        return float(s[:-2])
    # Accept a bare numeric string too (no unit) — common in tokens.json.
    try:
        return float(s)
    except ValueError:
        raise ValueError(
            f"brand '{brand_name}': token '{key}' has value '{v}' — "
            f"expected a number in px (e.g. '24px' or 24). Other CSS units "
            f"are not supported in v2 tokens."
        ) from None


def _load_tokens_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_tokens(merged: dict[str, Any], brand_name: str) -> None:
    """Validate a merged tokens dict against tokens.schema.json. Raises ValueError on failure."""
    validator = Draft202012Validator(_load_tokens_schema())
    errors = sorted(validator.iter_errors(merged), key=lambda e: list(e.absolute_path))
    if not errors:
        return
    parts = [f"brand '{brand_name}': tokens.json validation failed (schema: {_SCHEMA_PATH}):"]
    for err in errors:
        loc = ".".join(str(p) for p in err.absolute_path) or "<root>"
        parts.append(f"  - {loc}: {err.message}")
    raise ValueError("\n".join(parts))


# Standard style bundles. Keys match the role tokens in tokens.json's
# font-size map. Brands can override the bundle in tokens.json under a
# top-level `style` key (not used in PoC).
STYLE_BUNDLES: dict[str, dict[str, Any]] = {
    # Element-role bundles. font-size keys must exist in tokens.json.font-size;
    # color keys must exist in tokens.json.color.
    # Optional keys per bundle:
    #   transform: "upper" → uppercase text at emit time (canonical .eyebrow rule)
    #   opacity:   0..1     → text opacity (canonical .pgmeta rule, opacity 0.7)
    #
    # Bindings tuned against feinschliff canonical CSS:
    "title":       {"font": "display", "size": "slide-title", "weight": "bold",     "color": "ink", "letter_spacing": -0.015, "line_height": 1.1},
    # Larger slide title for brands that author at ~80px (e.g. gs-ramspau).
    "title-l":     {"font": "display", "size": "title-l",     "weight": "bold",     "color": "ink", "letter_spacing": -0.02, "line_height": 1.05},
    "sub":         {"font": "display", "size": "sub",         "weight": "regular",  "color": "graphite"},
    "huge":        {"font": "display", "size": "huge",        "weight": "light",    "color": "ink", "line_height": 0.95},
    # Canonical .display class — 160px light w/ tight tracking + 0.95 line-height.
    "display":     {"font": "display", "size": "display",     "weight": "light",    "color": "ink", "letter_spacing": -0.035, "line_height": 0.95},
    # 200px inline-override used by the end-slide "Thank you." headline.
    "display-xl":  {"font": "display", "size": "display-xl",  "weight": "light",    "color": "ink", "letter_spacing": -0.035, "line_height": 0.95},
    # Ghosted big-number marks. Color is canonical ink; callers override via color:.
    "bignum":      {"font": "display", "size": "bignum",       "weight": "light",    "color": "ink", "letter_spacing": -0.04, "line_height": 0.85},
    # Column-card sub-elements — `.col-t` is font-weight 500 (medium), NOT bold.
    "col-num":     {"font": "mono",    "size": "col-num",     "weight": "regular",  "color": "accent",   "transform": "upper"},
    "col-title":   {"font": "display", "size": "col-title",   "weight": "medium",   "color": "ink", "letter_spacing": -0.012, "line_height": 1.15},
    "col-title-q": {"font": "display", "size": "col-title-q", "weight": "medium",   "color": "ink", "letter_spacing": -0.012, "line_height": 1.15},
    "col-body":    {"font": "body",    "size": "col-body",    "weight": "regular",  "color": "graphite"},
    "rule":        {"font": "display", "size": "footer",      "weight": "regular",  "color": "ink"},
    "body":        {"font": "body",    "size": "body",        "weight": "regular",  "color": "graphite"},
    # Small-body — 16px sans, the classifier in pptx_svg_decompile.py emits
    # this for ≤12pt source text (dense table cells, source credits, fine
    # print). Reuses the `footer` size token (16px) so brands don't need to
    # declare an extra font-size key.
    "body-sm":     {"font": "body",    "size": "footer",      "weight": "regular",  "color": "graphite"},
    # Chrome — canonical eyebrow, footer, pgmeta all uppercase mono. pgmeta is
    # also dimmed (CSS opacity 0.7); footer + eyebrow inherit full body color.
    "eyebrow":     {"font": "mono",    "size": "eyebrow",     "weight": "regular",  "color": "ink",      "transform": "upper"},
    "footer":      {"font": "mono",    "size": "footer",      "weight": "regular",  "color": "graphite", "transform": "upper"},
    "pgmeta":      {"font": "mono",    "size": "pgmeta",      "weight": "regular",  "color": "ink",      "transform": "upper", "opacity": 0.7},
    "kpi-value":   {"font": "display", "size": "kpi-value",   "weight": "light",    "color": "ink", "letter_spacing": -0.03, "line_height": 0.95},
    "kpi-unit":    {"font": "display", "size": "kpi-unit",    "weight": "light",    "color": "graphite"},
    "kpi-key":     {"font": "mono",    "size": "kpi-key",     "weight": "regular",  "color": "graphite", "transform": "upper", "letter_spacing": 0.1},
    "kpi-delta":   {"font": "mono",    "size": "kpi-delta",   "weight": "regular",  "color": "accent-hover"},
    "agenda-num":  {"font": "mono",    "size": "agenda-num",  "weight": "medium",   "color": "accent",   "transform": "upper"},
    "agenda-t":    {"font": "display", "size": "agenda-t",    "weight": "semibold", "color": "ink"},
    "agenda-d":    {"font": "body",    "size": "agenda-d",    "weight": "regular",  "color": "graphite"},
    "quote":       {"font": "display", "size": "quote",       "weight": "light",    "color": "ink", "letter_spacing": -0.025, "line_height": 1.1},
    "quote-attr":  {"font": "mono",    "size": "quote-attr",  "weight": "regular",  "color": "graphite", "transform": "upper"},
    "quote-glyph": {"font": "display", "size": "huge",        "weight": "light",    "color": "accent"},
    "brand-mark":  {"font": "display", "size": "footer",      "weight": "bold",     "color": "ink"},
    "wordmark":    {"font": "display", "size": "pgmeta",      "weight": "medium",   "color": "ink",      "transform": "upper", "letter_spacing": 0.1},
    # Button label — canonical .btn is 22px medium.
    "btn":         {"font": "display", "size": "btn",         "weight": "medium",   "color": "ink"},
    # Chip — sample component, mono caps small.
    "chip":        {"font": "mono",    "size": "chip",        "weight": "medium",   "color": "ink", "transform": "upper", "letter_spacing": 0.08},
    "detail":      {"font": "mono",    "size": "footer",      "weight": "regular",  "color": "steel"},
    # MCK / action-title family.
    "act-title":   {"font": "display", "size": "act-title",   "weight": "regular",  "color": "ink", "letter_spacing": -0.02, "line_height": 1.1},
    "act-kicker":  {"font": "mono",    "size": "act-kicker",  "weight": "regular",  "color": "ink", "transform": "upper", "letter_spacing": 0.12},
    "tracker":     {"font": "mono",    "size": "tracker",     "weight": "regular",  "color": "graphite", "transform": "upper", "letter_spacing": 0.12},
    "h-idx":       {"font": "mono",    "size": "h-idx",       "weight": "regular",  "color": "accent-hover", "transform": "upper", "letter_spacing": 0.14},
    "h-hd":        {"font": "display", "size": "h-hd",        "weight": "medium",   "color": "ink", "letter_spacing": -0.012, "line_height": 1.15},
    "h-li":        {"font": "body",    "size": "h-li",        "weight": "regular",  "color": "graphite", "line_height": 1.45},
    "lede":        {"font": "display", "size": "lede",        "weight": "light",    "color": "ink", "letter_spacing": -0.015, "line_height": 1.2},
}


@dataclass
class ResolvedStyle:
    font_family: list[str]
    size_px: float                   # design pixels at 1920×1080 canvas
    weight: int                      # 100..900
    color_hex: str                   # "#RRGGBB"
    transform: str | None = None     # None or "upper"
    opacity: float = 1.0             # 0.0..1.0 (multiplied into color at emit time)
    letter_spacing: float = 0.0      # em fraction (e.g. 0.1 = 10% letter-spacing)
    line_height: float = 1.2         # paragraph line-height multiplier (CSS line-height)
    color_role: str = "ink"          # token role name (preserved for hierarchy stepping)
    italic: bool = False             # italic face / synthesis (python-pptx font.italic)


@dataclass
class Tokens:
    """Resolved token bundle for one brand. Parent inheritance already
    flattened. Lookup by role name returns a ResolvedStyle."""
    raw: dict[str, Any]              # the fully-merged tokens.json dict
    brand_name: str

    # Layer 1 typography / picture / locale tokens — populated from `raw`
    # in __post_init__ so callers that construct via load_tokens get them
    # transparently. Defaults match an unset brand.
    display_tracking_curve: dict[int, float] = field(default_factory=dict)
    tnum_font: str | None = None
    tnum_slot_keys: set[str] = field(default_factory=set)
    picture_treatment: str = "none"
    locale: str = "en"

    # Layer 1 chart-sanitation tokens (read by Layer 2 chart layouts).
    chart_chrome: str = "minimal"
    chart_axis_color_role: str = "neutral-faint"
    chart_legend_threshold: int = 4

    def __post_init__(self) -> None:
        typography = self.raw.get("typography", {}) or {}
        curve_raw = typography.get("display_tracking_curve", {}) or {}
        if curve_raw and not self.display_tracking_curve:
            self.display_tracking_curve = {int(k): float(v) for k, v in curve_raw.items()}
        if self.tnum_font is None:
            self.tnum_font = typography.get("tnum_font")
        slot_keys_raw = typography.get("tnum_slot_keys")
        if slot_keys_raw and not self.tnum_slot_keys:
            self.tnum_slot_keys = set(slot_keys_raw)

        if self.picture_treatment == "none":
            self.picture_treatment = self.raw.get("picture_treatment", "none")
        if self.locale == "en":
            self.locale = self.raw.get("locale", "en")

        chart = self.raw.get("chart", {}) or {}
        if self.chart_chrome == "minimal":
            self.chart_chrome = chart.get("chrome", "minimal")
        if self.chart_axis_color_role == "neutral-faint":
            self.chart_axis_color_role = chart.get("axis_color_role", "neutral-faint")
        legend = chart.get("legend_threshold")
        if legend is not None:
            self.chart_legend_threshold = int(legend)

    @classmethod
    def from_dict(cls, raw: dict[str, Any], *, brand_name: str) -> Tokens:
        """Construct a Tokens bundle from an already-merged dict. Test-friendly
        — skips strict tokens.schema.json validation (use `load_tokens` for
        on-disk brand packs that need schema enforcement)."""
        return cls(raw=raw, brand_name=brand_name)

    # --- public lookups -----------------------------------------------

    def color(self, name: str) -> str:
        if isinstance(name, str) and name.startswith("#") and _is_hex_literal(name):
            # Inline hex passthrough — the decompiler emits raw `#RRGGBB`
            # for shape fills the reverse-token-mapping pass couldn't
            # resolve. Treat them as valid colours so the verify loop can
            # build the slide without forcing every literal into the
            # brand's palette.
            return name.upper() if len(name) == 7 else _expand_short_hex(name).upper()
        colors = self.raw.get("color", {})
        c = colors.get(name)
        if c is None:
            # chart-series ramp fallback — matches the same convention
            # `brand_bridge.resolve()` applies for the diagram DSL.
            # Brands that don't ship an explicit per-series tint
            # progression render every series in the brand's accent hue;
            # bar/pie chart decks still build instead of crashing the
            # whole layout with KeyError.
            if isinstance(name, str) and name.startswith("chart-series-"):
                fallback = colors.get("accent")
                if fallback is not None:
                    return fallback["$value"] if isinstance(fallback, dict) else fallback
            raise KeyError(f"brand '{self.brand_name}': no color token '{name}'")
        if isinstance(c, dict):           # designtokens schema: {"$value": "..."}
            return c["$value"]
        return c

    def font_family(self, name: str) -> list[str]:
        f = self.raw.get("font-family", {}).get(name)
        if f is None:
            raise KeyError(f"brand '{self.brand_name}': no font-family '{name}'")
        if isinstance(f, dict):
            return list(f["$value"])
        return list(f)

    def font_size_px(self, name: str) -> float:
        f = self.raw.get("font-size", {}).get(name)
        if f is None:
            raise KeyError(f"brand '{self.brand_name}': no font-size '{name}'")
        if isinstance(f, dict):
            v = f["$value"]
        else:
            v = f
        return _strip_px(v, f"font-size.{name}", self.brand_name)

    def font_weight(self, name: str) -> int:
        f = self.raw.get("font-weight", {}).get(name)
        if f is None:
            # Standard fallback weights match CSS conventions.
            return {"light": 300, "regular": 400, "medium": 500,
                    "semibold": 600, "bold": 700, "black": 900}.get(name, 400)
        if isinstance(f, dict):
            return int(f["$value"])
        return int(f)

    def slide(self, key: str) -> float:
        s = self.raw.get("slide", {}).get(key)
        if s is None:
            # Sane defaults for the 1920×1080 canvas.
            return {"width": 1920, "height": 1080,
                    "padding-x": 100, "padding-y-top": 100,
                    "padding-y-bottom": 80}.get(key, 0)
        if isinstance(s, dict):
            s = s["$value"]
        return _strip_px(s, f"slide.{key}", self.brand_name)

    # --- style-bundle resolver ----------------------------------------

    def resolve_style(self, name: str) -> ResolvedStyle:
        bundle = STYLE_BUNDLES.get(name)
        override = self.raw.get("style", {}).get(name) or {}
        # Brand-level overrides: tokens.json can declare a top-level `style`
        # map keyed by bundle name, where each value is either:
        #   (a) a partial override merged on top of an existing canonical
        #       STYLE_BUNDLES entry, OR
        #   (b) a full brand-defined style under a new name (used when one
        #       logical token needs distinct sizes/weights across chrome
        #       regions, e.g. wordmark large on covers vs. small in footer).
        # A `transform` override may set null to clear the canonical
        # transform (e.g. mixed-case eyebrow). The schema reserves this
        # top-level key under `lib/schemas/tokens.schema.json`.
        if bundle is None:
            required = {"font", "size", "weight", "color"}
            missing = required - override.keys()
            if missing:
                known = sorted(set(STYLE_BUNDLES.keys()) |
                               set(self.raw.get("style", {}).keys()))
                raise KeyError(
                    f"unknown style '{name}' (brand override missing "
                    f"{sorted(missing)}). Known: {known}"
                )
            bundle = override
        bundle = {**bundle, **override}
        return ResolvedStyle(
            font_family=self.font_family(bundle["font"]),
            size_px=self.font_size_px(bundle["size"]),
            weight=self.font_weight(bundle["weight"]),
            color_hex=self.color(bundle["color"]),
            transform=bundle.get("transform"),
            opacity=float(bundle.get("opacity", 1.0)),
            letter_spacing=float(bundle.get("letter_spacing", 0.0)),
            line_height=float(bundle.get("line_height", 1.2)),
            color_role=bundle["color"],
            italic=bool(bundle.get("italic", False)),
        )


# ---------------------------------------------------------------------------
# Brand pack loading
# ---------------------------------------------------------------------------

def load_raw_tokens(brand_root: Path) -> dict[str, Any]:
    """Load a brand's ``tokens.json`` and return the parsed dict.

    Each brand pack is self-contained (no ``extends`` inheritance). The
    ``brands_dir`` parameter is no longer accepted — pass only ``brand_root``.
    Use ``load_tokens`` for the validated ``Tokens`` bundle; the diagram
    brand_bridge consumes the raw dict directly.
    """
    tj = brand_root / "tokens.json"
    if not tj.is_file():
        return {}
    try:
        return json.loads(tj.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(
            f"tokens.json in brand '{brand_root.name}' is not valid JSON: {exc}"
        ) from exc


def load_tokens(brand_root: Path, *, brands_dir: Path | None = None) -> Tokens:
    """Load a brand's ``tokens.json`` as a validated :class:`Tokens` bundle.

    Each brand pack is fully self-contained. The ``brands_dir`` keyword
    argument is accepted but ignored (kept for call-site back-compat during
    the extends-removal migration; will be removed in a follow-up).
    """
    merged = load_raw_tokens(brand_root)
    validate_tokens(merged, brand_root.name)
    return Tokens(raw=merged, brand_name=brand_root.name)


def load_tokens_with_theme(
    brand_root: Path,
    theme_name: str | None = None,
    *,
    brands_dir: Path | None = None,
) -> Tokens:
    """Load brand tokens merged with a named theme's tokens overlay.

    When ``theme_name`` is None, uses the brand's ``$default_theme`` key
    (falling back to ``"default"``). When the brand has no ``themes/``
    directory, returns the brand's own tokens unchanged (back-compat for
    unmigrated packs and extra brands).

    The theme's ``tokens.json`` is deep-merged on top of the brand's
    tokens, then re-validated.

    Parameters
    ----------
    brand_root:
        Path to the brand directory.
    theme_name:
        Theme name to load, e.g. ``'claude'``. Defaults to the brand's
        declared ``$default_theme`` or ``"default"``.
    brands_dir:
        Accepted but ignored. Kept for call-site back-compat during
        the extends-removal migration.
    """
    # Load the base brand tokens (self-contained, no extends chain).
    brand_merged = load_raw_tokens(brand_root)

    # Determine which theme to load.
    themes_dir = brand_root / "themes"
    if not themes_dir.is_dir():
        # No themes/ — back-compat: treat as pre-migration pack
        validate_tokens(brand_merged, brand_root.name)
        return Tokens(raw=brand_merged, brand_name=brand_root.name)

    # Resolve theme name: explicit arg > $default_theme in tokens.json > "default"
    if theme_name is None:
        theme_name = brand_merged.get("$default_theme") or "default"

    theme_dir = themes_dir / theme_name
    theme_tj = theme_dir / "tokens.json"
    if not theme_tj.is_file():
        available = sorted(
            d.name for d in themes_dir.iterdir()
            if d.is_dir() and (d / "tokens.json").is_file()
        )
        raise ValueError(
            f"theme '{theme_name}' not found for brand '{brand_root.name}'. "
            f"Available themes: {', '.join(available) or '(none)'}"
        )

    theme_raw = json.loads(theme_tj.read_bytes())
    combined = deep_merge(brand_merged, theme_raw)
    label = f"{brand_root.name}:{theme_name}"
    validate_tokens(combined, label)
    return Tokens(raw=combined, brand_name=label)


# Allowed keys in brief_defaults — mirrors the schema enum constraints.
_BRIEF_DEFAULTS_KNOWN_KEYS: frozenset[str] = frozenset(
    {"verbosity", "image_style", "frame", "audience"}
)


def load_brief_defaults(brand_dir: Path) -> dict[str, str]:
    """Read brief_defaults from <brand_dir>/tokens.json.

    Returns {} if the brand has no brief_defaults block (back-compat for brands
    that haven't set any priors). If the file is missing, also returns {}.

    Unknown keys in brief_defaults emit a stderr warning but are included in
    the returned dict so callers can inspect them without a hard failure.
    """
    tokens_file = brand_dir / "tokens.json"
    if not tokens_file.is_file():
        return {}
    raw = json.loads(tokens_file.read_text(encoding="utf-8"))
    defaults: dict[str, Any] = raw.get("brief_defaults") or {}
    if not isinstance(defaults, dict):
        return {}
    unknown = set(defaults.keys()) - _BRIEF_DEFAULTS_KNOWN_KEYS
    if unknown:
        print(
            f"WARNING: brand '{brand_dir.name}' brief_defaults contains unknown "
            f"key(s): {sorted(unknown)}. Known: {sorted(_BRIEF_DEFAULTS_KNOWN_KEYS)}",
            file=sys.stderr,
        )
    return dict(defaults)
