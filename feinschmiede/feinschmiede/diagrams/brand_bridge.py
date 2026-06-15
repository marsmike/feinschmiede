"""Resolve diagram DSL semantic color names against the active brand's tokens.

Single source of truth: only colors defined in brands/<b>/tokens.json are
allowed in diagram DSL. Literal hex / rgb / hsl are rejected; unknown
semantic names are rejected with a "did you mean" hint.

## Token path mismatch (finding)

The plan assumed nested paths like ``color.brand.primary``, ``color.surface.paper``,
etc. The actual tokens.json structure is **flat**: ``color.<name>`` (e.g.
``color.accent``, ``color.paper``). ``_TOKEN_PATHS`` maps the 17 semantic DSL
names to the real flat paths in every brand pack.
"""
from __future__ import annotations

import difflib
import os
import re
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Final

from feinschmiede.dsl.tokens import load_raw_tokens as _load_raw_tokens
from feinschmiede.jsonwalk import walk as _json_walk

if TYPE_CHECKING:
    from feinschmiede.brand import BrandPack

# 17 semantic names, fixed. Adding to this list is a coordinated change
# across brand_bridge, brand packs, and DSL references.
SEMANTIC_NAMES: Final[frozenset[str]] = frozenset({
    # brand
    "primary", "secondary", "tertiary", "accent",
    # surface
    "paper", "ink", "off-white", "chapter-slab", "surface", "surface-2",
    # semantic
    "success", "warning", "danger",
    # neutral
    "neutral", "neutral-soft", "neutral-strong",
    # status
    "status-on", "status-off", "status-pending",
    # chart series ramp — for pie/bar/line series where the brand defines
    # a graduated tint progression of its accent. Brands without explicit
    # chart-series-N tokens fall back to color.accent (all series same hue
    # — distinguishable only by labels). Six slots cover typical chart
    # series counts; >6 is unusual and indicates a chart-redesign signal.
    "chart-series-1", "chart-series-2", "chart-series-3",
    "chart-series-4", "chart-series-5", "chart-series-6",
})

# Maps each semantic DSL name to a dotted path inside tokens.json.
#
# All paths are flat under ``color.<name>`` — the real tokens.json structure.
# This differs from the original plan which assumed nested sub-groups like
# ``color.brand.*`` and ``color.surface.*``.  All brand packs and themes in the
# portfolio use the same flat layout (verified against feinschliff and its themes:
# catppuccin-latte, catppuccin-macchiato, gruvbox-dark, nord, feinschliff-dark).
_TOKEN_PATHS: Final[dict[str, str]] = {
    # Brand colors
    # "primary" and "accent" both route to the brand-accent slot: "primary" is
    # the canonical term in the DSL; "accent" is the alias for contexts that
    # explicitly call out an accent swatch.  Both point at color.accent.
    "primary":          "color.accent",          # primary branded hue (e.g. gold in feinschliff)
    "secondary":        "color.graphite",         # secondary text / support color
    "tertiary":         "color.steel",            # tertiary / muted label color
    "accent":           "color.highlight",        # alias for primary — hover/light variant of the brand accent
    # Surface
    # "paper" and "surface" are intentional aliases: both refer to the base
    # page/canvas background.  "surface" follows Material-style naming;
    # "paper" is the Feinschliff-native term.  Same physical token, two
    # semantic entry points for author convenience.
    "paper":            "color.paper",            # base page background (Feinschliff-native name)
    "ink":              "color.ink",              # body text on light
    "off-white":        "color.off-white",        # body text on dark (always light across brands)
    "chapter-slab":     "color.chapter-slab",     # deepest contrast band (always dark across brands)
    "surface":          "color.paper",            # alias for paper — base surface (Material-style name)
    "surface-2":        "color.paper-2",          # raised / secondary surface
    # Semantic severity
    "success":          "color.severity-low",     # green / positive
    "warning":          "color.severity-medium",  # amber / caution
    "danger":           "color.severity-high",    # red-rust / critical
    # Neutral ramp
    # "neutral" and "neutral-strong" alias into the steel/graphite tones:
    # "neutral" → color.steel (mid-grey, ~500-equivalent);
    # "neutral-strong" → color.graphite (dark-grey, ~700-equivalent).
    # These map the same physical tokens as "tertiary" and "secondary"
    # but signal context (neutral ramp) rather than typographic role.
    "neutral":          "color.steel",            # alias for tertiary — mid neutral (500-equivalent)
    "neutral-soft":     "color.silver",           # light neutral (300-equivalent)
    "neutral-strong":   "color.graphite",         # alias for secondary — dark neutral (700-equivalent)
    # Status
    "status-on":        "color.status-done",      # completed / active
    "status-off":       "color.status-next",      # not started / inactive
    "status-pending":   "color.status-current",   # in-progress / pending
    # Chart-series ramp — see SEMANTIC_NAMES comment. Brand-specific
    # tokens (color.chart-series-N) define the tint progression; resolve()
    # falls back to color.accent when a slot is missing.
    "chart-series-1":   "color.chart-series-1",
    "chart-series-2":   "color.chart-series-2",
    "chart-series-3":   "color.chart-series-3",
    "chart-series-4":   "color.chart-series-4",
    "chart-series-5":   "color.chart-series-5",
    "chart-series-6":   "color.chart-series-6",
}

_LITERAL_RE: Final = re.compile(r"^(#[0-9a-fA-F]{3,8}|rgba?\(|hsla?\()")


class BrandBridgeError(ValueError):
    """Raised when a diagram DSL color cannot be resolved."""


def resolve_with_pack(name: str, pack: "BrandPack") -> str:
    """Resolve a semantic color name using a :class:`~feinschmiede.brand.BrandPack`.

    Typed entry point for new code. Delegates to the existing
    :func:`resolve` implementation so all validation and fallback logic
    stays in one place.

    Parameters
    ----------
    name:
        Semantic color name, e.g. ``'primary'``, ``'paper'``.
    pack:
        BrandPack whose ``root`` directory contains ``tokens.json``.

    Raises
    ------
    BrandBridgeError
        On literal hex/rgb/hsl, unknown semantic name, or missing token.
    """
    return resolve(name, pack.root)



def resolve(name: str, brand_dir: Path) -> str:
    """Resolve a semantic color name to a hex string using brand tokens.

    Raises BrandBridgeError on:
    - literal hex/rgb/hsl
    - unknown semantic name
    - brand tokens missing the slot (after extends: walk)

    New code with a BrandPack should use :func:`resolve_with_pack` instead.
    """
    if _LITERAL_RE.match(name):
        # Hex literals pass through as-is. The decompile pipeline emits
        # `#RRGGBB` fills when nearest_token can't find a brand token
        # close enough to the source colour; rejecting them here would
        # leave the decompiled DSL unbuildable. Other literal forms
        # (rgb()/hsl()) are still flagged because they don't survive the
        # downstream SVG-attribute path.
        if name.startswith("#") and len(name) in (4, 7, 9):
            return name
        raise BrandBridgeError(
            f"literal color '{name}' — use semantic name "
            f"(see references/dsl-reference.md)"
        )

    if name not in SEMANTIC_NAMES:
        suggestion = _suggest(name)
        hint = f" (did you mean '{suggestion}'?)" if suggestion else ""
        raise BrandBridgeError(
            f"unknown color token '{name}'{hint} — valid: "
            f"{', '.join(sorted(SEMANTIC_NAMES))}"
        )

    tokens = _load_tokens(brand_dir)
    path = _TOKEN_PATHS[name]
    raw = _json_walk(tokens, path)
    value = _extract_value(raw)
    # Chart-series ramp falls back to accent when the brand doesn't define
    # an explicit tint progression — all series render in the brand's
    # primary hue, distinguishable only by labels. This keeps charts
    # building on brands without per-series colors.
    if value is None and name.startswith("chart-series-"):
        raw = _json_walk(tokens, "color.accent")
        value = _extract_value(raw)
    if value is None:
        raise BrandBridgeError(
            f"brand '{brand_dir.name}' missing token '{path}' for "
            f"semantic name '{name}'"
        )
    return value


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_tokens(brand_dir: Path) -> dict:
    """Load tokens.json for a brand.

    The result is cached per (resolved dir, tokens.json mtime) so
    per-color resolve() calls don't re-read disk; an edited tokens.json
    gets a fresh key.
    """
    tokens_path = brand_dir / "tokens.json"
    if not tokens_path.exists():
        raise BrandBridgeError(f"brand '{brand_dir.name}': tokens.json missing")
    return _cached_raw_tokens(brand_dir.resolve(), tokens_path.stat().st_mtime_ns)


@lru_cache(maxsize=32)
def _cached_raw_tokens(brand_dir: Path, _mtime_ns: int) -> dict:
    try:
        return _load_raw_tokens(brand_dir)
    except (ValueError, OSError) as exc:
        raise BrandBridgeError(str(exc)) from exc


def _extract_value(raw: object) -> str | None:
    """Extract a hex string from a raw token value.

    Handles both the Design Tokens draft-2 ``{"$value": "#RRGGBB"}`` shape
    and bare string values.
    """
    if isinstance(raw, dict) and "$value" in raw:
        v = raw["$value"]
        return v if isinstance(v, str) else None
    return raw if isinstance(raw, str) else None


def _suggest(unknown: str) -> str | None:
    """Return the closest semantic name by edit distance, or None."""
    matches = difflib.get_close_matches(unknown.lower(), SEMANTIC_NAMES, n=1, cutoff=0.6)
    return matches[0] if matches else None


# ---------------------------------------------------------------------------
# Font resolution
# ---------------------------------------------------------------------------

# Generic CSS family keywords — never quoted, never treated as a brand face.
_GENERIC_FAMILIES = frozenset({
    "serif", "sans-serif", "monospace", "cursive", "fantasy",
    "system-ui", "ui-monospace", "ui-serif", "ui-sans-serif", "ui-rounded",
})


@dataclass(frozen=True)
class BrandFonts:
    """Brand typography for the diagram pipeline (mirror of color resolve())."""
    body: tuple[str, ...]
    mono: tuple[str, ...]

    @property
    def svg_body(self) -> str:
        return _css_stack(self.body, "sans-serif")

    @property
    def svg_mono(self) -> str:
        return _css_stack(self.mono, "monospace")

    @property
    def primary_body(self) -> str | None:
        """First concrete (non-generic) body face, or None."""
        return next((f for f in self.body if f.lower() not in _GENERIC_FAMILIES), None)

    @property
    def primary_mono(self) -> str | None:
        """First concrete (non-generic) mono face, or None."""
        return next((f for f in self.mono if f.lower() not in _GENERIC_FAMILIES), None)


def _css_stack(families: tuple[str, ...], generic: str) -> str:
    """CSS font-family stack: concrete faces (multi-word quoted) + one generic."""
    names = [f"'{f}'" if " " in f else f
             for f in families if f.lower() not in _GENERIC_FAMILIES]
    return ", ".join([*names, generic])


def _font_family_values(tokens: dict, key: str) -> tuple[str, ...]:
    """Extract the font-family list for *key* (e.g. 'body', 'mono') from raw tokens."""
    raw = (tokens.get("font-family") or {}).get(key)
    if isinstance(raw, dict):
        raw = raw.get("$value")
    if isinstance(raw, (list, tuple)):
        return tuple(str(f) for f in raw)
    return ()


def resolve_fonts(brand_dir: Path) -> BrandFonts:
    """Resolve the brand's diagram typography from tokens ``font-family.body``
    (fallback ``.display``) and ``.mono``. Missing keys/tokens degrade to the
    bare generic family — a diagram never fails to render over fonts.

    Returns a BrandFonts — svg_body/svg_mono for SVG stacks, primary_body/primary_mono
    for the first concrete face (None when the brand has none).
    """
    try:
        tokens = _load_tokens(brand_dir)
    except BrandBridgeError:
        return BrandFonts(body=(), mono=())
    body = _font_family_values(tokens, "body") or _font_family_values(tokens, "display")
    mono = _font_family_values(tokens, "mono")
    return BrandFonts(body=body, mono=mono)


def relative_luminance(hex_color: str) -> float:
    """Perceived luminance 0..255 for picking readable label color."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return 128.0
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 0.299 * r + 0.587 * g + 0.114 * b


def label_color_for(fill_hex: str, brand_dir: Path) -> str:
    """Pick a readable label color for an arbitrary fill, brand-stable.

    Uses the (off-white, chapter-slab) pair instead of (paper, ink): the
    former is guaranteed light and the latter guaranteed dark across every
    brand pack (dark brands invert ink/paper, so ink-on-ink-fill produced
    invisible labels — see fill:ink boxes in the dark-theme showcase).
    """
    return resolve("off-white", brand_dir) if relative_luminance(fill_hex) < 128 else resolve("chapter-slab", brand_dir)


# ---------------------------------------------------------------------------
# Shared font-fallback guard (F4)
# ---------------------------------------------------------------------------

# One WARN per (brand, face) per process — fallback never breaks a render.
_warned_font_fallback: set[tuple[str, str]] = set()


def font_fallback_resolvable(brand_dir: Path, face: str | None, *, detail: str) -> bool:
    """True when *face* is fontconfig-resolvable. When it isn't, print ONE
    ``diagram-font-fallback`` WARN per (brand, face) per process — *detail*
    names the consumer's fallback behavior — and return False.
    None face → True (nothing to resolve; generic stacks are always safe)."""
    if face is None:
        return True
    from feinschmiede.text.measure import find_font_file
    if find_font_file(face) is not None:
        return True
    # Unresolvable face — warn once per (brand, face).
    key = (brand_dir.name, face)
    if key not in _warned_font_fallback:
        _warned_font_fallback.add(key)
        print(
            f"feinschmiede: WARN: diagram-font-fallback — brand face '{face}' "
            f"not fontconfig-resolvable; {detail}",
            file=sys.stderr,
        )
    return False


def strip_brand_directive(dsl: str) -> tuple[str, str | None]:
    """Split off a leading ``@brand <name>`` directive from diagram DSL.

    Returns (cleaned_dsl, directive_or_None). The directive is the second
    whitespace-split token after ``@brand``; lines without a value are
    silently dropped along with the directive line.
    """
    directive: str | None = None
    kept: list[str] = []
    for line in dsl.splitlines():
        s = line.strip()
        if s.startswith("@brand"):
            parts = s.split(maxsplit=1)
            if len(parts) == 2:
                directive = parts[1].strip()
            continue
        kept.append(line)
    return "\n".join(kept), directive


def resolve_brand_dir(
    directive: str | None = None,
    cli_flag: str | None = None,
    deck_context: str | None = None,
    *,
    brands_root: Path | None = None,
) -> Path:
    """Pick the active brand directory by precedence:

      1. CLI --brand flag
      2. DSL @brand directive
      3. FEINSCHLIFF_BRAND env var
      4. /deck build context
      5. default 'feinschliff'

    The explicit --brand flag outranks an authored @brand directive: the
    directive is a default baked into the DSL, the flag is the caller's
    invocation-time override.

    Returns a Path that may or may not exist — callers (e.g. resolve())
    can decide how to handle missing brand dirs.
    """
    env = os.environ.get("FEINSCHLIFF_BRAND")
    chosen = cli_flag or directive or env or deck_context or "feinschliff"
    if brands_root is not None:
        return brands_root / chosen
    from feinschmiede.brand_discovery import find_brand as _find_brand
    try:
        return _find_brand(chosen).root
    except ValueError as exc:
        # Preserve find_brand's actionable diagnostic (available brands +
        # every searched path + the FEINSCHLIFF_BRAND_PATH hint) rather than
        # collapsing it to a bare "not found" — callers surface str(exc).
        raise FileNotFoundError(str(exc)) from exc
