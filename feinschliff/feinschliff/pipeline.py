# feinschliff/feinschliff/pipeline.py
"""Shared per-slide compile pipeline.

Every CLI entrypoint that emits a `.pptx` slide flows through
`compile_slide()`. Returns a `CompileResult` carrying the emitted
primitives, all collected defects, and the slide canvas size.

This is the only place `validate_diagrams*` should be called outside of
unit tests. The returned defects use the `feinschliff.defects.Defect` dataclass —
caller decides which severities to honor and which to demote.
"""
from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path
from typing import Any

from feinschliff.defects import Defect, DefectKind, Severity, from_engine_defect

try:
    from feinschmiede.diagrams.structural_validator import (  # type: ignore[import]
        validate_excalidraw_structure,
        validate_svg_structure,
    )
except ImportError:  # structural_validator lives in feinschliff-builder
    def validate_excalidraw_structure(doc):  # type: ignore[misc]
        return []

    def validate_svg_structure(svg_text):  # type: ignore[misc]
        return []
from feinschliff.dsl.expander import (
    expand_compounds,
    expand_diagram_blocks,
    apply_slot_debug_color,
    mark_native_replaceables,
    interpolate_nodes,
    interpolate_native_text,
    load_compounds_for_brand,
)
from feinschliff.dsl.parser import parse_file
from feinschliff.dsl.pptx_emit import _slide_canvas
from feinschmiede import compounds_dir
from feinschmiede.dsl.tokens import load_tokens_with_theme
from feinschliff.layout_validator import (
    validate_diagrams,
    validate_diagrams_color,
    validate_diagrams_text_size,
)


@dataclasses.dataclass(frozen=True)
class CompileResult:
    primitives: list[Any]
    tokens: dict[str, Any]
    canvas: tuple[int, int]
    defects: list[Defect]


# Canonical implementation lives next to the budget walker so every
# compute_slot_budgets entry point registers pack metrics, not just builds
# that reach compile_slide. Re-exported under the old private name for
# existing callers.
from feinschliff.slot_budget import (  # noqa: E402
    register_tokens_font_metrics as _register_brand_font_metrics,
)

# Trailing slide-counter pattern that LLMs sometimes author into pgmeta,
# e.g. "Bahncard 100 · 5 / 11" or "Cover - 3/11". Strip it so the
# renderer footer (bottom-right NN / TT) is never duplicated in the header.
_PGMETA_COUNTER_RE = re.compile(r"\s*[·\-—|]\s*\d{1,3}\s*/\s*\d{1,3}\s*$")


def compile_slide(
    *,
    layout_path: Path,
    ctx: dict[str, Any],
    brand_dir: Path,
    slide_index: int,
    diagrams_out_dir: Path,
    craft_check: bool = False,
    theme: str | None = None,
) -> CompileResult:
    """Compile a single slide from DSL to primitives + defects.

    Parameters
    ----------
    layout_path:
        Path to the ``.slide.dsl`` layout file.
    ctx:
        Content dict (slot bindings).
    brand_dir:
        Path to the active brand directory.
    slide_index:
        1-based slide index used for diagram cache keys and defect reporting.
    diagrams_out_dir:
        Directory where diagram artifacts (SVG, excalidraw) are written.
    craft_check:
        When True, enables stricter craft-quality checks.
    theme:
        Theme name to overlay on the brand tokens (e.g. ``'orange'``).
        When None, the brand's ``$default_theme`` is used.  If the brand has
        no ``themes/`` directory, tokens are loaded brand-only (back-compat).
    """
    diagrams_out_dir.mkdir(parents=True, exist_ok=True)

    tokens = load_tokens_with_theme(brand_dir, theme)
    # Brand packs may ship width ratios for their own (often proprietary)
    # fonts via a tokens `font-metrics` block — register them so the
    # slot-budget / verify-static predictors measure those fonts accurately.
    _register_brand_font_metrics(tokens)
    compounds = load_compounds_for_brand(
        brand_dir, std_dir=compounds_dir(),
    )

    layout_nodes, layout_compounds = parse_file(layout_path)
    for cd in layout_compounds:
        compounds[cd.name] = cd

    # Defensive: strip any trailing slide-counter that was erroneously
    # authored into pgmeta (e.g. "Deck Name · 5 / 11"). The renderer stamps
    # the slide counter as a separate bottom-right footer; allowing it in
    # pgmeta too would produce duplicates visible in the header. This strip
    # is idempotent and safe — pgmeta content never legitimately ends with
    # a "· NN / TT" pattern.
    if isinstance(ctx, dict) and isinstance(ctx.get("pgmeta"), str):
        ctx = dict(ctx)
        ctx["pgmeta"] = _PGMETA_COUNTER_RE.sub("", ctx["pgmeta"])

    # Slot-coverage debugging (deck build --slot-debug-color): every
    # slot-sourced text renders in this colour, so a render diff against the
    # defaults build shows exactly which text is bindable vs baked chrome.
    debug_color = ctx.get("_slot_debug_color") if isinstance(ctx, dict) else None
    if debug_color:
        layout_nodes = apply_slot_debug_color(layout_nodes, debug_color)
    interp = interpolate_nodes(layout_nodes, ctx)
    # Resolve {{ slot }} templates that the slotify pass planted INSIDE native
    # payloads (carried tables / grouped shapes) — they ride in the b64 blob /
    # sidecar XML and are invisible to interpolate_nodes above.
    interp = interpolate_native_text(interp, ctx, asset_root=brand_dir / "assets",
                                     debug_color=debug_color)
    if debug_color:
        # Charts / SmartArt: data-replaceable post-export but not bindable —
        # outline them so the coverage render marks every replaceable region.
        try:
            _w_emu = float(tokens.slide("width_emu") or 0)
        except Exception:
            _w_emu = 0.0
        _cw, _ch = _slide_canvas(interp)
        interp = mark_native_replaceables(
            interp, debug_color, asset_root=brand_dir / "assets",
            emu_to_px=(_cw / _w_emu) if _w_emu else 0.0)
    interp = expand_diagram_blocks(
        interp,
        brand_dir=brand_dir,
        out_dir=diagrams_out_dir,
        layout_dir=layout_path.parent,
        slide_index=slide_index,
    )

    # Snap-to-rail: enforce the brand's left-rail (slide.left-rail, default
    # slide.padding-x) on every text node whose x sits within ±threshold of
    # it. The visual-vocabulary skill spells the principle: "every element
    # anchors to an invisible grid; misaligned elements read as mistakes".
    # Per-node opt-out via `nosnap:true`. Disabled when the threshold token
    # is 0.
    from feinschliff.dsl.expander import snap_to_rails
    interp = snap_to_rails(interp, tokens)

    sw, sh = _slide_canvas(interp)

    defects: list[Defect] = []
    raw: list = []
    raw.extend(validate_diagrams(interp, slide_index=slide_index, slide_w=sw, slide_h=sh))
    raw.extend(validate_diagrams_color(interp, slide_index=slide_index, brand_dir=brand_dir))
    raw.extend(validate_diagrams_text_size(interp, slide_index=slide_index, slide_w=sw, slide_h=sh))
    for r in raw:
        defects.append(_legacy_to_defect(r, slide_index))

    # Structural lint over every diagram artifact this slide just wrote.
    # `expand_diagram_blocks` writes `s<idx>-<id>-<hash>.{excalidraw,svg}`
    # files into `diagrams_out_dir` (see lib/dsl/expander.py); scanning by
    # slide_index prefix is deterministic and won't double-count earlier
    # slides' files.
    for artifact in diagrams_out_dir.glob(f"s{slide_index}-*.excalidraw"):
        try:
            doc = json.loads(artifact.read_text())
        except json.JSONDecodeError:
            # File-level malformed JSON is caught by validate_excalidraw_file
            # in the CLI; here we just skip rather than crash the build.
            continue
        for d in validate_excalidraw_structure(doc):
            # validate_excalidraw_structure stamps slide_index=0 by default;
            # restamp with the real index so reports group correctly.
            defects.append(from_engine_defect(d, slide_index=slide_index))
    for artifact in diagrams_out_dir.glob(f"s{slide_index}-*.svg"):
        try:
            svg_text = artifact.read_text()
        except OSError:
            continue
        for d in validate_svg_structure(svg_text):
            defects.append(from_engine_defect(d, slide_index=slide_index))

    primitives, diagnostics = expand_compounds(interp, compounds)
    for d in diagnostics:
        if d.kind == "unknown_compound":
            defects.append(Defect(
                slide_index=slide_index,
                kind=DefectKind.UNKNOWN_COMPOUND,
                severity=Severity.FATAL,
                message=f"unknown compound: Check the compound name or load order. {d.format()}",
                meta={"diagnostic_kind": d.kind},
            ))

    if craft_check:
        from feinschliff.quality.craft_rules import check_craft_rules
        _craft_report = check_craft_rules(
            [{"layout": str(layout_path), "content_inline": ctx}]
        )
        for _ci in _craft_report.issues:
            if _ci.severity == "fail":
                defects.append(Defect(
                    slide_index=slide_index,
                    kind=DefectKind.CRAFT_RULE,
                    severity=Severity.FATAL,
                    message=f"[{_ci.rule}] {_ci.message}",
                    meta=dict(_ci.meta),
                ))

    return CompileResult(
        primitives=primitives,
        tokens=tokens,
        canvas=(sw, sh),
        defects=defects,
    )


_KIND_MAP = {
    "diagram-overflow": DefectKind.DIAGRAM_OVERFLOW,
    "diagram-text-too-small": DefectKind.DIAGRAM_TEXT_TOO_SMALL,
    "diagram-color-mismatch": DefectKind.DIAGRAM_COLOR_MISMATCH,
}


def _legacy_to_defect(legacy_obj: Any, slide_index: int) -> Defect:
    kind_str = getattr(legacy_obj, "kind", None) or "diagram-overflow"
    kind = _KIND_MAP.get(kind_str, DefectKind.DIAGRAM_OVERFLOW)
    return Defect(
        slide_index=slide_index,
        kind=kind,
        severity=Severity.FATAL if kind_str in {"diagram-overflow", "diagram-text-too-small"} else Severity.WARN,
        message=getattr(legacy_obj, "message", str(legacy_obj)),
        meta={k: v for k, v in getattr(legacy_obj, "__dict__", {}).items() if not k.startswith("_")},
    )
