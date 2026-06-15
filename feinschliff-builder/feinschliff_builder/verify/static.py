"""Pre-render static geometry verify.

Inspects a plan.yaml dict (post-merge, content filled) for geometry defects
that do NOT require rendering. Returns one :class:`~feinschliff.defects.Defect` per
problem; empty list = clean.

Two defect classes are detected:

- **SLOT_OVERFLOW** — text in ``slide.content[slot]`` exceeds the pixel
  budget computed from the layout's ``maxwidth``/``maxheight`` nodes.
  Delegates to :func:`feinschliff.content_validator.check_slot_overflow` via the
  same ``textfit.fits()`` helper the autoshrink emitter uses.
  **Severity is FATAL** — real font metrics make the predictor trustworthy.
  Escape hatches: autoshrink on the layout, or set
  ``FEINSCHMIEDE_NO_REAL_METRICS=1`` to fall back to the legacy estimator.

- **EMPTY_PLACEHOLDER** — a slot that the layout interpolates via
  ``{{ slot_name }}`` is either absent from the content dict or is an empty
  / whitespace-only string. Severity is WARN (not fatal); the orchestrator
  decides whether to abort.

Usage::

    from pathlib import Path
    from feinschliff_builder.verify.static import static_verify, validate

    # Legacy API (list of Defect):
    defects = static_verify(plan, brand_dir=Path("brands/feinschliff"))

    # New typed API (DiagnosticBag):
    from feinschmiede.brand import BrandPack
    pack = BrandPack.load(Path("brands/feinschliff"))
    bag = validate(plan, brand=pack)
    if bag.has_errors():
        print(f"{len(bag)} error(s)")
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from feinschliff.defects import Defect, DefectKind, Severity

if TYPE_CHECKING:
    from feinschmiede.brand import BrandPack
    from feinschmiede.diagnostics import DiagnosticBag

# Slot interpolation RE — matches {{ slot_name }}, {{ cells[0].heading }}, etc.
_SLOT_RE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")
# Normalise array indices: cells[0].heading → cells[].heading
_IDX_RE = re.compile(r"\[\d+\]")
# Extract slot-path tokens from an expression that may contain math operators.
# Matches identifier chains like 'bars[0].width', 'phases[1].to_event',
# 'chart.series[0].pct' — stopping at non-identifier characters (operators,
# parens, spaces). Used to separate slot references from arithmetic context.
_SLOT_PATH_RE = re.compile(r"[A-Za-z_]\w*(?:\[\d+\]|\.\w+)*")

# Well-known optional scalar slots that layouts may interpolate but authors
# intentionally leave empty.  EMPTY_PLACEHOLDER is suppressed for these.
_OPTIONAL_SLOT_NAMES: frozenset[str] = frozenset({
    "eyebrow",          # small kicker/category above title
    "kicker",           # alt name for eyebrow
    "so_what",          # data slide takeaway, optional
    "pgmeta",           # chrome: "Chapter · 3 / 30"
    "footer_left",
    "footer_right",
    "caption",
    "attribution",
    "byline",
    "subtitle",         # often optional companion to title
    "supporting_body",  # secondary body text
    "watermark",
    "footnote",         # deck version tag, optional
    "tracker",          # eyebrow tracker line, optional
})


def _resolve_layout_path(plan_dir: Path, layout_rel: str) -> Path | None:
    """Resolve a layout path from the plan directory or discovered layout dirs."""
    from feinschliff.layout_discovery import all_layout_dirs

    candidate = (plan_dir / layout_rel).resolve()
    if candidate.is_file():
        return candidate
    # Try each discovered layout directory (bundled first, then env/user).
    for layout_dir in all_layout_dirs():
        candidate2 = (layout_dir.parent / layout_rel).resolve()
        if candidate2.is_file():
            return candidate2
    return None


def _collect_interpolated_slots(nodes: list) -> tuple[set[str], set[str]]:
    """Walk DSL nodes and collect slot names from ``{{ slot }}`` interpolations.

    Returns ``(required_scalar_slots, structural_array_bases)`` where:

    - ``required_scalar_slots``: normalised slot paths that must be non-empty
      in content (scalar slots not in ``_OPTIONAL_SLOT_NAMES``; excludes
      content-flexible array-shape slots).
    - ``structural_array_bases``: bare array names (e.g. ``bars``, ``phases``)
      whose elements appear in sizing/positioning pos_args of non-text DSL
      nodes.  The caller checks whether these arrays are present and non-empty
      in the content dict.

    **Structural-array detection heuristic:**
    Array-shape slots (``bars[].width``) are normally exempt from
    EMPTY_PLACEHOLDER because an array being empty is a content choice.
    However, when a slot appears in a *positional argument* of a non-text
    DSL node (``rect``, ``line``, etc.) the value drives sizing/positioning
    math — missing values cause render crashes.  The base array name is
    collected into ``structural_array_bases`` so the caller can check for
    presence separately.

    Arithmetic expressions (e.g. ``{{ bars[0].width*12 }}``,
    ``{{ (phases[0].to_event - phases[0].from_event)*375 }}``) are parsed
    with ``_SLOT_PATH_RE`` to extract just the slot references before applying
    normalisation, avoiding false positives from numeric suffixes.
    """
    from feinschliff.dsl.parser import DSLNode

    required: set[str] = set()
    structural_array_bases: set[str] = set()

    def _slot_refs_in_expr(raw: str) -> list[str]:
        """Extract normalised slot paths from a Jinja2 expression.

        Simple case (no operators): normalise the whole expression.
        Arithmetic case: use _SLOT_PATH_RE to pull out identifier-path tokens.
        """
        if re.search(r"[+\-*/()\s]", raw):
            paths = []
            for path_m in _SLOT_PATH_RE.finditer(raw):
                paths.append(path_m.group(0))
            return [_IDX_RE.sub("[]", p) for p in paths if p]
        return [_IDX_RE.sub("[]", raw)]

    def _slots_in_string(s: str) -> list[str]:
        """Extract normalised slot names from a string containing {{ }} exprs."""
        result = []
        for m in _SLOT_RE.finditer(s):
            raw = m.group(1).strip()
            if "|default(" in raw:
                continue
            result.extend(_slot_refs_in_expr(raw))
        return result

    def _visit(node: DSLNode, *, in_for_body: bool = False) -> None:
        is_text_node = (node.kind == "text")
        is_for_node = (node.kind == "_for")

        # ── label (text node labels; other nodes rarely have labels) ─────────
        # Skip slot collection inside for-block bodies — all slot references
        # there use loop-scoped variables (e.g. `row.label`, `i`) rather than
        # content-dict keys.
        label = getattr(node, "label", None) or ""
        if not in_for_body:
            for normalised in _slots_in_string(label):
                if "[]" in normalised:
                    # Array-shape slot in a label — content-flexible, skip.
                    continue
                base_name = normalised.split(".")[0]
                if base_name in _OPTIONAL_SLOT_NAMES:
                    continue
                required.add(normalised)

        # ── pos_args of non-text nodes — structural sizing/positioning ────────
        # Skip structural detection when:
        # (a) we're inside a for-block body — variables like `i` and `row.*`
        #     are loop-scoped, not content slots.
        # (b) the node carries an `if:` kw_arg — rendering is conditional and
        #     the array is by definition optional.
        kw_args = getattr(node, "kw_args", None) or {}
        has_if_guard = bool(kw_args.get("if"))
        if not is_text_node and not is_for_node and not in_for_body and not has_if_guard:
            for arg in getattr(node, "pos_args", None) or []:
                for normalised in _slots_in_string(arg):
                    if "[]" in normalised:
                        # Array slot in a non-text pos_arg → structural.
                        base = normalised.split(".")[0].rstrip("[]").split("[")[0]
                        structural_array_bases.add(base)
                    else:
                        base_name = normalised.split(".")[0]
                        if base_name not in _OPTIONAL_SLOT_NAMES:
                            required.add(normalised)

        # ── recurse into children (e.g. compound body) ───────────────────────
        for child in getattr(node, "children", None) or []:
            _visit(child, in_for_body=in_for_body)
        # ── recurse into for-block body — mark children as in_for_body ───────
        if is_for_node and getattr(node, "body", None):
            for child in node.body:
                _visit(child, in_for_body=True)

    for node in nodes:
        _visit(node)

    return required, structural_array_bases


def _flatten_content_keys(ctx: dict, prefix: str = "") -> dict[str, str]:
    """Flatten a nested content dict to normalised-path → value.

    Mirrors the normalisation in ``feinschliff.content_validator.iter_slot_values``:
    array indices collapse to ``[]``.
    """
    out: dict[str, str] = {}
    if isinstance(ctx, dict):
        for k, v in ctx.items():
            child = f"{prefix}.{k}" if prefix else k
            out.update(_flatten_content_keys(v, child))
    elif isinstance(ctx, list):
        for item in ctx:
            out.update(_flatten_content_keys(item, f"{prefix}[]"))
    elif ctx is not None:
        out[prefix] = str(ctx)
    return out


def static_verify(
    plan: dict,
    brand_dir: Path,
    *,
    plan_dir: Path | None = None,
) -> list[Defect]:
    """Inspect a plan dict for geometry defects without rendering.

    Parameters
    ----------
    plan:
        The loaded plan.yaml dict (post-merge, content filled in). The dict
        must contain a ``slides`` list with entries that each carry at least
        a ``layout`` field.
    brand_dir:
        Path to the active brand directory (used by ``load_tokens`` and
        ``load_compounds_for_brand``).
    plan_dir:
        Directory that ``layout:`` paths in the plan are resolved relative to.
        When *None* (the default), falls back to the current working directory.
        Layout resolution also searches all discovered layout dirs as a fallback,
        so toolkit layouts resolve without an explicit ``plan_dir``. CLI callers
        that load a plan from a file should pass ``plan_path.parent`` so
        brand-relative layout overrides resolve correctly.

    Returns
    -------
    list[Defect]
        One :class:`~feinschliff.defects.Defect` per detected problem.  Empty list
        means clean.  SLOT_OVERFLOW defects carry
        :attr:`~feinschliff.defects.Severity.FATAL`; EMPTY_PLACEHOLDER defects
        carry :attr:`~feinschliff.defects.Severity.WARN`.
    """
    from feinschliff.dsl.parser import parse_file
    from feinschmiede import compounds_dir
    from feinschmiede.dsl.tokens import load_tokens_with_theme
    from feinschliff.dsl.expander import load_compounds_for_brand
    from feinschliff.slot_budget import compute_slot_budgets
    from feinschliff.content_validator import (
        check_slot_overflow,
        iter_slot_values,
        ContentDefect,
    )

    defects: list[Defect] = []
    slides_spec = plan.get("slides") or []

    # Resolve layout paths against plan_dir when supplied; fall back to CWD
    # so existing callers that don't pass plan_dir still work (the layout
    # resolution also searches all discovered layout dirs as a fallback).
    effective_plan_dir = plan_dir if plan_dir is not None else Path.cwd()

    # Deck-level default theme: plan.get("theme") or None (→ brand $default_theme).
    default_theme = plan.get("theme")
    # Load deck-level tokens once (used as fallback when per-slide theme matches).
    tokens = load_tokens_with_theme(brand_dir, default_theme)
    compounds = load_compounds_for_brand(
        brand_dir, std_dir=compounds_dir()
    )

    for i, spec in enumerate(slides_spec):
        slide_index = i + 1
        layout_rel = spec.get("layout", "")

        layout_path = _resolve_layout_path(effective_plan_dir, layout_rel)
        if layout_path is None:
            # Can't resolve layout → skip, don't crash
            print(
                f"verify-static: slide {slide_index}: layout not found: "
                f"{layout_rel!r} — skipped",
                file=sys.stderr,
            )
            continue

        try:
            layout_nodes, layout_compounds = parse_file(layout_path)
        except Exception as exc:  # noqa: BLE001
            print(
                f"verify-static: slide {slide_index}: parse error in "
                f"{layout_path.name}: {exc} — skipped",
                file=sys.stderr,
            )
            continue

        # Merge layout-local compounds into the brand compounds dict.
        local_compounds = dict(compounds)
        for cd in layout_compounds:
            local_compounds[cd.name] = cd

        ctx = spec.get("content") or {}

        # Per-slide theme: slide `theme:` key > deck-level default.
        slide_theme = spec.get("theme", default_theme)
        slide_tokens = (
            load_tokens_with_theme(brand_dir, slide_theme)
            if slide_theme != default_theme
            else tokens
        )

        # ── 1. EMPTY_PLACEHOLDER ──────────────────────────────────────────
        # Collect all {{ slot }} interpolations in the layout and check
        # whether each is supplied and non-empty in the content dict.
        interpolated, structural_bases = _collect_interpolated_slots(layout_nodes)
        flat_content = _flatten_content_keys(ctx)

        for slot_path in sorted(interpolated):
            value = flat_content.get(slot_path)
            if value is None or (isinstance(value, str) and not value.strip()):
                defects.append(Defect(
                    slide_index=slide_index,
                    kind=DefectKind.EMPTY_PLACEHOLDER,
                    severity=Severity.WARN,
                    message=(
                        f"slot {slot_path!r} is empty or missing "
                        f"(layout: {layout_path.name})"
                    ),
                    meta={"slot": slot_path, "layout": layout_path.name},
                ))

        # ── 1b. STRUCTURAL ARRAY CHECK ────────────────────────────────────
        # For each structural array base (e.g. 'bars'), verify that the
        # content dict has a non-empty list at that key.  A missing or empty
        # structural array will cause a render crash (WxH parse error), so
        # this fires EMPTY_PLACEHOLDER as a pre-render warning.
        for base in sorted(structural_bases):
            arr = ctx.get(base)
            if arr is None or (isinstance(arr, list) and len(arr) == 0):
                slot_path = f"{base}[]"
                defects.append(Defect(
                    slide_index=slide_index,
                    kind=DefectKind.EMPTY_PLACEHOLDER,
                    severity=Severity.WARN,
                    message=(
                        f"structural array {slot_path!r} is empty or missing "
                        f"(layout: {layout_path.name})"
                    ),
                    meta={"slot": slot_path, "layout": layout_path.name},
                ))

        # ── 2. SLOT_OVERFLOW ─────────────────────────────────────────────
        # Compute per-slot pixel budgets from the DSL and check whether
        # the supplied content will fit without wrapping beyond max_lines.
        try:
            slot_budgets = compute_slot_budgets(
                layout_nodes, slide_tokens, compounds=local_compounds
            )
        except Exception as exc:  # noqa: BLE001
            print(
                f"verify-static: slide {slide_index}: could not compute "
                f"slot budgets for {layout_path.name}: {exc} — overflow "
                "checks skipped",
                file=sys.stderr,
            )
            slot_budgets = {}

        if slot_budgets:
            for norm_path, raw_path, value in iter_slot_values(ctx):
                budget = slot_budgets.get(norm_path)
                if budget is None:
                    continue
                content_defects: list[ContentDefect] = check_slot_overflow(
                    value, slot=raw_path, budget=budget, slide_index=slide_index,
                )
                for cd in content_defects:
                    budget_chars = budget.max_chars
                    over_by = max(0, len(value) - budget_chars)
                    defects.append(Defect(
                        slide_index=slide_index,
                        kind=DefectKind.SLOT_OVERFLOW,
                        severity=Severity.FATAL,
                        message=cd.message,
                        meta={
                            "slot": cd.slot,
                            "budget_chars": budget_chars,
                            "over_by": over_by,
                        },
                    ))

    return defects


# ---------------------------------------------------------------------------
# Typed DiagnosticBag entry point
# ---------------------------------------------------------------------------

def validate(
    plan: dict,
    brand: "BrandPack",
    bag: "DiagnosticBag | None" = None,
    *,
    plan_dir: Path | None = None,
) -> "DiagnosticBag":
    """Inspect a plan dict for static geometry defects, returning a DiagnosticBag.

    Typed entry point that wraps :func:`static_verify` and maps its legacy
    ``Defect`` objects to ``feinschmiede.diagnostics.Defect`` objects in a
    ``DiagnosticBag``.

    Parameters
    ----------
    plan:
        The loaded plan.yaml dict.
    brand:
        Active brand pack.
    bag:
        Optional existing bag to accumulate into.  When None, a fresh
        ``DiagnosticBag()`` is created.
    plan_dir:
        Directory for resolving relative layout paths.

    Returns
    -------
    DiagnosticBag
        The (possibly pre-populated) bag with newly found defects appended.
    """
    from feinschmiede.diagnostics import (
        DiagnosticBag as _Bag,
        Defect as _NewDefect,
        DefectKind as _NewKind,
        Severity as _NewSev,
    )

    if bag is None:
        bag = _Bag()

    # Run the existing static_verify to get legacy Defect objects.
    legacy_defects = static_verify(plan, brand_dir=brand.root, plan_dir=plan_dir)

    # Map legacy Severity (FATAL/WARN/INFO) → new Severity (ERROR/WARNING/INFO).
    _SEV_MAP = {
        "fatal": _NewSev.ERROR,
        "warn": _NewSev.WARNING,
        "info": _NewSev.INFO,
    }

    for ld in legacy_defects:
        try:
            new_kind = _NewKind(ld.kind.value)
        except ValueError:
            new_kind = _NewKind.INTERNAL
        new_sev = _SEV_MAP.get(ld.severity.value, _NewSev.WARNING)
        extra: dict = dict(ld.meta) if ld.meta else {}
        if ld.slide_index:
            extra.setdefault("slide_index", ld.slide_index)
        bag.add(_NewDefect(
            kind=new_kind,
            severity=new_sev,
            message=ld.message,
            location=f"slide {ld.slide_index}" if ld.slide_index else None,
            extra=extra,
        ))

    return bag
