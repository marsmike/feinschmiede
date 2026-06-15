"""Deck orchestration helpers extracted from cli/deck.py.

Business-logic functions that were inline in ``cli/deck.py`` but are
independently testable and reusable outside the CLI:

- :func:`signals_from_slide` — extract layout-picker signals from a
  content-plan slide entry.
- :func:`resolve_layout_path` — find a layout DSL file for a given name
  in brand-local and toolkit pools.
- :func:`slot_budgets_for_layout` — compute slot budgets for a layout.
- :func:`build_primitives_for_layout` — parse + expand a layout DSL file
  with optional slot filling.
- :func:`build_refurbished_deck` — build a PPTX from a list of refurbished
  slide plans (each with a ``{layout, content}`` dict).
- :func:`patch_set_hash` — stable hash of an autofix patch set for
  oscillation detection.
- :func:`compose_from_brief` — read a deck plan YAML (the "brief") and
  return a typed :class:`~feinschmiede.dsl.ast.Document`.

``cli/deck.py`` delegates to these functions; callers outside the CLI
can import them directly.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from feinschmiede.dsl.tokens import Tokens

# ── constants ─────────────────────────────────────────────────────────────────

# Maps `diagram_kind` hints from content_plan into the layout picker's
# preferred role.
DIAGRAM_KIND_TO_ROLE: dict[str, str] = {
    "concept": "content-with-visual",
    "chart":   "data-quantity",
    "process": "data-timeline",
    "compare": "data-comparison",
}


# ── patch_set_hash ────────────────────────────────────────────────────────────

def patch_set_hash(patches: list) -> str:
    """Stable hash of an autofix patch set — used for oscillation detection.

    Two cycles that would apply identical changes produce the same hash so the
    autofix loop can detect oscillation and halt before wasting iterations.
    """
    items = sorted(
        (p.slide_index, p.action, str(sorted((p.payload or {}).items())))
        for p in patches
    )
    return hashlib.sha256(repr(items).encode()).hexdigest()


# ── _slot_lengths_from_slide ──────────────────────────────────────────────────

def _slot_lengths_from_slide(slide: dict[str, Any]) -> dict[str, int]:
    """Derive a conservative slot-name → char-count mapping from a content-plan slide.

    Only maps fields whose names correspond 1:1 to canonical slot names used
    in layout frontmatter and slot-binding code (see
    ``feinschliff.deck.content_metadata.warn_overbudget_slots``).  Unmapped
    fields are silently ignored — a sparse result is correct; overcounting
    would penalise layouts that aren't actually over-budget.

    Current mappings:
        ``title``    → ``"title"`` slot   (present in nearly every layout)
        ``subtitle`` → ``"subtitle"`` slot (declared in layouts that have one)
    """
    out: dict[str, int] = {}
    title = slide.get("title")
    if isinstance(title, str) and title:
        out["title"] = len(title)
    subtitle = slide.get("subtitle")
    if isinstance(subtitle, str) and subtitle:
        out["subtitle"] = len(subtitle)
    return out


# ── signals_from_slide ────────────────────────────────────────────────────────

def signals_from_slide(slide: dict[str, Any]) -> dict[str, Any]:
    """Extract layout-picker / layout-budget kwargs from a content-plan slide.

    Centralised here so per-slide and deck-wide pickers agree on which
    fields feed selection.

    Parameters
    ----------
    slide:
        A single entry from the ``slides`` list of a content plan.

    Returns
    -------
    dict
        Keyword-argument dict accepted by :func:`feinschliff.layout_picker.pick_layout`,
        plus an optional ``layout`` pin passthrough consumed by
        :func:`feinschliff.layout_budget.plan_deck_layouts` (an explicitly
        pinned slide bypasses the picker — and any deck-map default).
    """
    role = slide.get("role") or slide.get("purpose") or (
        DIAGRAM_KIND_TO_ROLE.get(str(slide.get("diagram_kind") or ""))
        or "content-columns"
    )
    # slot_lengths: prefer an explicitly provided dict; fall back to the
    # conservative field→slot derivation so callers don't need to pre-compute.
    explicit_lengths = slide.get("slot_lengths")
    slot_lengths: dict[str, int] | None = (
        explicit_lengths
        if isinstance(explicit_lengths, dict) and explicit_lengths
        else (_slot_lengths_from_slide(slide) or None)
    )
    return {
        "role":            role,
        "concept_count":   slide.get("concept_count"),
        "data_quantity":   slide.get("data_quantity"),
        "comparison":      slide.get("comparison"),
        "narrative_role":  slide.get("narrative_role"),
        "narrative_act":   slide.get("narrative_act"),
        "time_axis_role":  slide.get("time_axis_role"),
        "audience_mode":   slide.get("audience_mode"),
        "diagram_kind":       slide.get("diagram_kind"),
        "diagram_complexity": slide.get("diagram_complexity"),
        "layout":             slide.get("layout"),
        "slot_lengths":       slot_lengths,
    }


# ── resolve_layout_path ───────────────────────────────────────────────────────

def resolve_layout_path(brand_root: Path, layout_name: str) -> Path | None:
    """Return the DSL path for *layout_name*.

    Checks brand-local first (``<brand_root>/layouts/<name>.slide.dsl``),
    then falls back to the toolkit pool via
    :func:`feinschliff.layout_discovery.find_layout`.

    Parameters
    ----------
    brand_root:
        Root directory of the brand pack (e.g. ``brands/feinschliff``).
    layout_name:
        Bare layout identifier, e.g. ``"title-orange"``.

    Returns
    -------
    Path or None
        Absolute path to the ``.slide.dsl`` file, or ``None`` when not found.
    """
    from feinschliff.layout_discovery import (
        find_layout as _find_layout,
        resolve_brand_prefixed as _resolve_brand_prefixed,
    )
    brand_local = brand_root / "layouts" / f"{layout_name}.slide.dsl"
    if brand_local.is_file():
        return brand_local
    # ``<brand>-<stem>`` form addresses a sibling brand pack under the
    # same ``brands/`` parent — lets plans pick a specific brand's
    # layout when two packs ship the same stem.
    cross = _resolve_brand_prefixed(brand_root, layout_name)
    if cross is not None:
        return cross
    layout = _find_layout(layout_name)
    return layout.path if layout is not None else None


# ── slot_budgets_for_layout ───────────────────────────────────────────────────

def _chart_slot_budgets_from_nodes(nodes: list) -> dict[str, dict]:
    """Scan DSL nodes for ``native`` lines carrying chart kwargs and emit
    chart slot budget entries.

    For each ``native`` node that carries ``chart_categories`` / ``chart_values``
    / ``chart_colors`` kw_args (as emitted by ``slotify_native_charts``), three
    slots are produced:

    - ``chart_N_values``      — ``{kind, item_type, capacity, must_bind, hint}``
    - ``chart_N_categories``  — same shape
    - ``chart_N_colors``      — same shape but ``must_bind: false``

    ``capacity`` is decoded from the base64-encoded JSON default list carried in
    the kw_arg's Jinja default filter, e.g.::

        chart_values:"{{ chart_1_values | default('WzguMiwgMy4yXQ==') }}"

    The base64 is decoded → json.loads → len().  On any decode failure the
    capacity falls back to 0.
    """
    import base64
    import json
    import re

    _DEFAULT_RE = re.compile(r"default\('([^']+)'\)")

    def _cap_from_kwarg(raw_value: str) -> int:
        """Decode base64 JSON list from a Jinja default filter and return len."""
        m = _DEFAULT_RE.search(raw_value)
        if not m:
            return 0
        try:
            lst = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
            return len(lst) if isinstance(lst, list) else 0
        except Exception:
            return 0

    out: dict[str, dict] = {}
    chart_counter = 0

    for node in nodes:
        if node.kind != "native":
            continue
        kw = node.kw_args
        if "chart_categories" not in kw:
            continue

        chart_counter += 1
        n = chart_counter

        cats_raw = kw.get("chart_categories", "")
        vals_raw = kw.get("chart_values", "")
        cols_raw = kw.get("chart_colors", "")

        cats_cap = _cap_from_kwarg(cats_raw)
        vals_cap = _cap_from_kwarg(vals_raw)
        cols_cap = _cap_from_kwarg(cols_raw)

        # Derive default sample values from the base64 payload for the hint.
        def _sample(raw: str, limit: int = 3) -> str:
            m2 = _DEFAULT_RE.search(raw)
            if not m2:
                return ""
            try:
                lst = json.loads(base64.b64decode(m2.group(1)).decode("utf-8"))
                sample = lst[:limit]
                tail = "…" if len(lst) > limit else ""
                return repr(sample) + tail
            except Exception:
                return ""

        vals_sample = _sample(vals_raw)
        cats_sample = _sample(cats_raw)

        out[f"chart_{n}_values"] = {
            "kind": "list",
            "item_type": "number",
            "capacity": vals_cap,
            "must_bind": True,
            "hint": (
                f"Numeric values, one per category. "
                f"Baked default: {vals_sample}. "
                f"MUST override — stock data ships if unbound."
            ),
        }
        out[f"chart_{n}_categories"] = {
            "kind": "list",
            "item_type": "string",
            "capacity": cats_cap,
            "must_bind": True,
            "hint": (
                f"Category labels, one per data point. "
                f"Baked default: {cats_sample}. "
                f"MUST override — stock labels ship if unbound."
            ),
        }
        out[f"chart_{n}_colors"] = {
            "kind": "list",
            "item_type": "hex_color",
            "capacity": cols_cap,
            "must_bind": False,
            "hint": (
                "Hex colors (no #) per data point. "
                "Optional — leave unbound to keep baked palette."
            ),
        }

    return out


def slot_budgets_for_layout(
    layout_name: str,
    brand_root: Path,
    tokens: "Tokens",
) -> dict[str, dict]:
    """Compute slot budgets for *layout_name*.

    Returns a plain serialisable dict mapping slot names to budget dicts.
    Text slots carry ``{chars_per_line, max_lines, max_chars}``; chart slots
    carry ``{kind, item_type, capacity, must_bind, hint}``.

    Returns an empty dict and logs a warning on any error so the caller
    never crashes.

    Parameters
    ----------
    layout_name:
        Bare layout identifier.
    brand_root:
        Root directory of the brand pack.
    tokens:
        Loaded token set for the brand.
    """
    from feinschliff.dsl.parser import parse_file
    from feinschliff.slot_budget import compute_slot_budgets

    import sys

    layout_path = resolve_layout_path(brand_root, layout_name)
    if layout_path is None:
        print(
            f"deck plan-skeleton: layout {layout_name!r} not found in brand "
            f"or toolkit; slot_budgets will be empty",
            file=sys.stderr,
        )
        return {}
    try:
        nodes, _ = parse_file(layout_path)
        budgets = compute_slot_budgets(nodes, tokens)
    except Exception as exc:  # noqa: BLE001
        print(
            f"deck plan-skeleton: could not compute slot budgets for "
            f"{layout_name!r}: {exc}",
            file=sys.stderr,
        )
        return {}

    result: dict[str, dict] = {
        slot: {
            "chars_per_line": b.chars_per_line,
            "max_lines": b.max_lines,
            "max_chars": b.max_chars,
        }
        for slot, b in budgets.items()
    }
    # Augment with chart slot entries from native nodes.
    result.update(_chart_slot_budgets_from_nodes(nodes))
    return result


# ── build_primitives_for_layout ───────────────────────────────────────────────

def build_primitives_for_layout(
    layout_path: Path,
    brand: str,
    content_path: Path | None,
    *,
    skip_interpolation: bool = False,
) -> tuple[list, Any]:
    """Parse, expand, and return ``(primitives, tokens)`` for a single layout.

    When *skip_interpolation* is True the slot-filling pass is skipped so
    ``{{ slot_name }}`` labels are preserved in the primitives.  This is
    the correct mode for wireframe rendering.

    Parameters
    ----------
    layout_path:
        Path to the ``.slide.dsl`` layout file.
    brand:
        Brand identifier (directory name under ``brands/``).
    content_path:
        Optional path to a YAML file with slot values.  Ignored when
        *skip_interpolation* is True.
    skip_interpolation:
        When True, skip slot-filling even if *content_path* is provided.

    Returns
    -------
    tuple[list, Tokens]
        ``(primitives, tokens)`` — the expanded node list and the loaded
        token set for the brand.
    """
    import yaml

    from feinschmiede.brand_discovery import find_brand
    from feinschliff.dsl.expander import expand_compounds, interpolate_nodes, load_compounds_for_brand
    import feinschmiede
    from feinschliff.dsl.parser import parse_file
    from feinschmiede.dsl.tokens import load_tokens

    def _bundled_compounds() -> Path:
        return Path(feinschmiede.__file__).resolve().parent / "compounds"

    brand_dir = find_brand(brand).root
    tokens = load_tokens(brand_dir)
    compounds = load_compounds_for_brand(brand_dir, std_dir=_bundled_compounds())
    layout_nodes, layout_compounds = parse_file(layout_path)
    for cd in layout_compounds:
        compounds[cd.name] = cd
    if skip_interpolation:
        source_nodes = layout_nodes
    else:
        ctx: dict = {}
        if content_path and content_path.is_file():
            ctx = yaml.safe_load(content_path.read_text()) or {}
        source_nodes = interpolate_nodes(layout_nodes, ctx)
    primitives, _ = expand_compounds(source_nodes, compounds)
    return primitives, tokens


# ── build_refurbished_deck ────────────────────────────────────────────────────

def build_refurbished_deck(
    slides_plan: list[dict[str, Any]],
    brand: str,
    out_path: Path,
) -> None:
    """Build a multi-slide PPTX from refurbished slide plan entries.

    Each entry in *slides_plan* is ``{layout: str, content: dict}``.
    Uses the existing ``build_multi_slide`` pipeline.

    Parameters
    ----------
    slides_plan:
        List of ``{layout, content}`` dicts (as produced by ``cmd_polish``).
    brand:
        Brand identifier.
    out_path:
        Output ``.pptx`` path.

    Raises
    ------
    ValueError
        When the brand cannot be found.
    FileNotFoundError
        When a layout DSL file cannot be resolved.
    """
    import tempfile

    from feinschmiede.brand_discovery import find_brand
    from feinschliff.dsl.expander import (
        expand_compounds, expand_diagram_blocks, interpolate_nodes,
        load_compounds_for_brand,
    )
    from feinschliff.dsl.parser import parse_file
    from feinschliff.dsl.pptx_emit import build_multi_slide
    import feinschmiede
    from feinschmiede.dsl.tokens import load_tokens
    from feinschliff.io.image_provider import discover_providers, get_provider
    from feinschliff.layout_discovery import find_layout as _find_layout

    def _bundled_assets() -> Path:
        return Path(__file__).resolve().parents[2] / "assets"

    def _bundled_compounds() -> Path:
        return Path(feinschmiede.__file__).resolve().parent / "compounds"

    try:
        brand_obj = find_brand(brand)
    except ValueError as e:
        raise ValueError(f"deck polish: {e}") from None
    brand_dir = brand_obj.root

    discover_providers()
    provider = None
    if brand_obj.image_provider_config:
        cfg = brand_obj.image_provider_config
        provider = get_provider(cfg["kind"], cfg.get("config"))

    tokens = load_tokens(brand_dir)
    compounds = load_compounds_for_brand(brand_dir, std_dir=_bundled_compounds())
    slides_payload: list[tuple[list, Any, Path]] = []

    with tempfile.TemporaryDirectory() as tmp:
        diagrams_out = Path(tmp) / "diagrams"
        diagrams_out.mkdir()
        for slide_idx, entry in enumerate(slides_plan, start=1):
            _layout_name = entry["layout"]
            if _layout_name.endswith(".slide.dsl"):
                _layout_name = _layout_name[:-len(".slide.dsl")]
            _ly = _find_layout(_layout_name)
            if _ly is None:
                raise FileNotFoundError(
                    f"deck polish: layout not found: {entry['layout']!r}"
                )
            layout_path = _ly.path
            layout_nodes, layout_compounds = parse_file(layout_path)
            local_compounds = dict(compounds)
            for cd in layout_compounds:
                local_compounds[cd.name] = cd
            interp = interpolate_nodes(layout_nodes, entry.get("content") or {})
            interp = expand_diagram_blocks(
                interp,
                brand_dir=brand_dir,
                out_dir=diagrams_out,
                layout_dir=layout_path.parent,
                slide_index=slide_idx,
            )
            primitives, diagnostics = expand_compounds(interp, local_compounds)
            import sys
            for d in diagnostics:
                print(f"deck polish: {d.format()}", file=sys.stderr)
            notes = entry.get("notes")
            if notes is not None:
                slides_payload.append((primitives, tokens, brand_dir / "assets", notes))
            else:
                slides_payload.append((primitives, tokens, brand_dir / "assets"))

        prs = build_multi_slide(
            slides_payload,
            asset_root_fallback=_bundled_assets(),
            image_provider=provider,
            deck_dir=out_path.parent,
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        prs.save(str(out_path))


# ── compose_from_brief ────────────────────────────────────────────────────────

def compose_from_brief(brief_path: Path, brand: "Any") -> "Any":
    """Build a typed :class:`~feinschmiede.dsl.ast.Document` from a deck plan YAML.

    Reads a plan YAML (the "brief") in the standard ``feinschliff deck build``
    format — ``brand:``, ``slides: [{layout:, content:}, …]`` — resolves each
    slide's layout DSL file via :func:`resolve_layout_path`, parses it into a
    typed :class:`~feinschmiede.dsl.ast.Slide`, and assembles all slides into a single
    :class:`~feinschmiede.dsl.ast.Document`.

    .. note::
        Slot interpolation (``{{ slot_name }}`` → content values) is **not**
        performed here.  The returned ``Document`` preserves slot placeholders
        as-is.  Callers that need fully-filled slides should call
        :func:`build_primitives_for_layout` instead.

    Parameters
    ----------
    brief_path:
        Path to a deck plan YAML (``brand:``, ``slides:`` with ``layout:``
        and optional ``content:`` keys).
    brand:
        A :class:`~feinschmiede.brand.pack.BrandPack` instance.  Its ``root``
        attribute supplies the brand directory for layout resolution.

    Returns
    -------
    Document
        A typed :class:`~feinschmiede.dsl.ast.Document` with one
        :class:`~feinschmiede.dsl.ast.Slide` per entry in ``plan.slides``.

    Raises
    ------
    FileNotFoundError
        When *brief_path* or a referenced layout DSL file cannot be found.
    ValueError
        When the plan YAML is missing the ``slides`` key.
    """
    import yaml
    from feinschmiede.dsl.ast import Document
    from feinschliff.dsl.parser import parse_document_file

    text = brief_path.read_text(encoding="utf-8")
    plan: dict = yaml.safe_load(text) or {}
    slides_spec = plan.get("slides")
    if not isinstance(slides_spec, list):
        raise ValueError(
            f"compose_from_brief: {brief_path}: missing or invalid 'slides' list"
        )

    brief_dir = brief_path.parent
    all_slides = []

    for i, spec in enumerate(slides_spec):
        layout_rel = spec.get("layout") or ""
        # Try plan-dir-relative first, then brand-local, then toolkit pool.
        layout_path: Path | None = None
        candidate = (brief_dir / layout_rel).resolve()
        if candidate.is_file():
            layout_path = candidate
        else:
            layout_name = Path(layout_rel).stem
            if layout_name.endswith(".slide"):
                layout_name = layout_name[:-len(".slide")]
            layout_path = resolve_layout_path(brand.root, layout_name)

        if layout_path is None or not layout_path.is_file():
            raise FileNotFoundError(
                f"compose_from_brief: slide {i}: layout not found: {layout_rel!r}"
            )

        slide_doc = parse_document_file(layout_path)
        # slide_doc has exactly one Slide; carry notes from the plan if present.
        for slide in slide_doc.slides:
            notes = spec.get("notes")
            if notes is not None:
                slide.notes = notes
            all_slides.append(slide)

    return Document(version=1, slides=all_slides)
