"""Typographic budget extractor.

Derives per-slot character/line constraints from layout slot metadata and the
active brand's token set. SlotBudget objects are used by content_validator to
catch text overflows before rendering, and by /deck generation to inform the
LLM of the actual pixel envelope.

The DSL-parse path (compute_slot_budgets from DSL nodes) has been removed
with the DSL pipeline. Slot budgets now come from the master-template catalog
(layouts.yaml slot metadata) or are constructed directly by callers.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

from feinschmiede.geometry import units


# ── font-metrics registration ─────────────────────────────────────────────────

# Per-family average char-width ratio tables (family → {normal, bold}).
# Brand packs populate this via ``register_tokens_font_metrics``; the default
# "default" entry approximates proportional Latin fonts.
_FONT_RATIOS: dict[str, dict[str, float]] = {
    "default": {"normal": 0.50, "bold": 0.55},
    "Open Sans": {"normal": 0.48, "bold": 0.53},
}
_REAL_METRICS: dict[tuple[str, bool], float] = {}  # (face, bold) → ratio


def register_font_metrics(family: str, *, normal: float, bold: float) -> None:
    """Register empirical width ratios for a font family."""
    _FONT_RATIOS[family] = {"normal": normal, "bold": bold}


def has_real_metrics(face: str, bold: bool) -> bool:
    return (face, bold) in _REAL_METRICS


def supported_fonts() -> frozenset[str]:
    return frozenset(_FONT_RATIOS.keys())


def chars_per_line(font_family: str, font_size_pt: float, bold: bool,
                   width_emu: int) -> int:
    """Estimate characters that fit on one wrapped line.

    Uses empirical width ratios when available; falls back to the 'default'
    heuristic (0.50 normal, 0.55 bold).
    """
    from feinschmiede.geometry.units import EMU_PER_PT
    width_pt = width_emu / EMU_PER_PT
    if font_size_pt <= 0 or width_pt <= 0:
        return 9999

    # Try real PIL metrics first (from feinschmiede.text.measure), then ratio
    # table, then default.
    ratio: float | None = None
    try:
        from feinschmiede.text.measure import avg_char_width_ratio
        ratio = avg_char_width_ratio(font_family, bold=bold)
    except ImportError:
        pass

    if ratio is None:
        entry = _FONT_RATIOS.get(font_family) or _FONT_RATIOS["default"]
        ratio = entry["bold"] if bold else entry["normal"]

    return max(1, int(width_pt / (font_size_pt * ratio)))


def register_tokens_font_metrics(tokens) -> None:
    """Register tokens' ``font-metrics`` width ratios.

    Block shape: ``{"<Family>": {"normal": 0.48, "bold": 0.53}, ...}``;
    ``$``-prefixed keys are skipped. Malformed entries are ignored.
    """
    raw = getattr(tokens, "raw", None)
    block = raw.get("font-metrics") if isinstance(raw, dict) else None
    if not isinstance(block, dict):
        return
    for family, m in block.items():
        if family.startswith("$") or not isinstance(m, dict):
            continue
        try:
            register_font_metrics(
                family, normal=float(m["normal"]), bold=float(m["bold"])
            )
        except (KeyError, TypeError, ValueError):
            continue


# Slot interpolation RE — matches {{ slot_name }}, {{ cells[0].heading }}, etc.
_SLOT_RE = re.compile(r"\{\{([^{}]+)\}\}")
# Normalise array indices: cells[0].heading → cells[].heading
_IDX_RE = re.compile(r"\[\d+\]")


def _extract_single_slot(label: str) -> str | None:
    """Return the normalised slot name if *label* contains exactly one slot
    interpolation, otherwise None (multi-slot or no-slot labels are skipped).
    """
    matches = _SLOT_RE.findall(label)
    if len(matches) != 1:
        return None
    raw = matches[0].strip()
    # Drop Jinja filters (e.g. `{{ text_5 | default("…") }}`) so the key is the
    # bare slot reference.
    raw = raw.split("|", 1)[0].strip()
    return _IDX_RE.sub("[]", raw)


@dataclass(frozen=True)
class SlotBudget:
    """Typographic budget for one text slot in a layout.

    All pixel values are in *design pixels* (1920×1080 canvas baseline).
    EMU-converted equivalents for ``textfit`` are exposed as properties.
    """
    slot: str               # normalised slot key, e.g. "action_title" or "cells[].heading"
    style: str              # style name, e.g. "act-title"
    size_px: float          # font size in design-px
    line_height: float      # CSS line-height multiplier
    width_px: float         # maxwidth in design-px
    height_px: float        # maxheight in design-px (0 = unconstrained)
    font_family: str        # primary font family name
    bold: bool              # whether the style uses bold weight
    x_px: float = 0.0       # slot origin x in design-px
    y_px: float = 0.0       # slot origin y in design-px
    autoshrink: bool = False  # emitter will shrink to fit (10pt floor) when True
    inset_w_emu: int = 0    # total horizontal text-frame inset (both sides summed)
    inset_h_emu: int = 0    # total vertical text-frame inset (both sides summed)
    emu_per_px: float = units.EMU_PER_PX_BASELINE  # design-px → EMU scale
    px_to_pt: float = units.PX_TO_PT_BASELINE       # design-px → pt scale

    # ── derived geometry ──────────────────────────────────────────────────
    @property
    def font_size_pt(self) -> float:
        """Rendered font size in pt."""
        return self.size_px * self.px_to_pt

    @property
    def size_pt(self) -> float:
        """Deprecated alias for :attr:`font_size_pt`."""
        return self.font_size_pt

    @property
    def width_emu(self) -> int:
        return int(self.width_px * self.emu_per_px)

    @property
    def height_emu(self) -> int:
        return int(self.height_px * self.emu_per_px)

    @property
    def chars_per_line(self) -> int:
        """Estimated characters that fit on one wrapped line."""
        return chars_per_line(self.font_family, self.font_size_pt, self.bold, self.width_emu)

    @property
    def max_lines(self) -> int:
        """Maximum lines that fit in height_px at this line-height.

        Returns a large sentinel (999) when height_px is 0 or very large,
        meaning the slot is effectively unconstrained vertically.
        """
        if self.height_px <= 0:
            return 999
        line_h_px = self.size_px * self.line_height
        if line_h_px <= 0:
            return 999
        em_px = min(line_h_px, self.size_px)
        return max(1, math.floor((self.height_px - em_px) / line_h_px) + 1)

    @property
    def max_chars(self) -> int:
        """Rough total character capacity (chars_per_line × max_lines)."""
        if self.max_lines >= 999:
            return 9999
        return self.chars_per_line * self.max_lines


def format_budget_hint(budgets: dict[str, SlotBudget]) -> str:
    """Return a compact, LLM-readable table of slot constraints.

    Suitable for injection into Step 2 of the /deck generation prompt so the
    model targets the actual pixel envelope rather than generic char counts.

    Example output::

        Slot typographic budgets (derived from layout + tokens):
        action_title  : style=act-title 56px | ~51 chars/line | max 2 lines | max ~102 chars total
        heading       : style=h-hd      32px | ~19 chars/line | max 2 lines | max ~38 chars total
        body          : style=body      26px | ~28 chars/line | max 3 lines | max ~84 chars total

        Rules:
        - Stay within chars/line to avoid unintended wrapping.
        - Avoid hyphenated compounds (week-on-week, production-grade) in narrow slots
          (≤25 chars/line) — renderers break at hyphens, causing extra lines.
        - Prefer short, unhyphenated words when chars/line < 25.
    """
    if not budgets:
        return ""

    lines = ["Slot typographic budgets (derived from layout + tokens):"]
    max_slot_len = max(len(s) for s in budgets)
    for slot, b in sorted(budgets.items()):
        if b.max_lines >= 999:
            lines_str = "unconstrained"
        else:
            lines_str = f"max {b.max_lines} line{'s' if b.max_lines != 1 else ''}"
        if b.max_chars >= 9999:
            chars_str = "unconstrained"
        else:
            chars_str = f"max ~{b.max_chars} chars total"
        lines.append(
            f"  {slot:<{max_slot_len}} : style={b.style} {b.size_px:.0f}px"
            f" | ~{b.chars_per_line} chars/line"
            f" | {lines_str}"
            f" | {chars_str}"
        )

    lines += [
        "",
        "Rules:",
        "  - Stay within chars/line to avoid unintended wrapping.",
        "  - Avoid hyphenated compounds (week-on-week, production-grade) in slots",
        "    with ≤25 chars/line — renderers break at hyphens, producing extra lines.",
        "  - Prefer short, unhyphenated words when chars/line < 25.",
    ]
    return "\n".join(lines)
