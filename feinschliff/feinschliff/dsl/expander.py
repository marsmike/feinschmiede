"""DSL expander: resolves slot interpolation + compound calls into a
primitives-only node list.

Two passes:
  1. **Slot interpolation** — replace `{{ slot:NAME }}` in any string
     value with content from the per-slide content map.
  2. **Compound resolution** — recursively replace compound-call nodes
     with their body (param-substituted), until only primitives remain.

Primitives recognised: `canvas`, `theme`, `text`, `rect`, `line`,
`picture`. Anything else is treated as a compound call and looked up
in the union of toolkit-standard compounds + brand-specific compounds.
Brand compounds win on name collision (explicit override).
"""
from __future__ import annotations

import ast
import operator
import re
import warnings
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from .parser import DSLNode, CompoundDef, parse_file

if TYPE_CHECKING:
    from feinschmiede.brand import BrandPack
    from feinschmiede.dsl.ast import Document, Element


@dataclass
class ExpansionDiagnostic:
    """One diagnostic produced during compound expansion.

    `kind` is a machine-readable tag — e.g. `"unknown_compound"` — that
    CLIs can pivot exit codes on. `message` is human-readable. `source`
    + `line_no` come from the DSLNode that triggered it.
    """

    kind: str
    message: str
    source: str = ""
    line_no: int = 0

    def format(self) -> str:
        loc = f"{self.source}:{self.line_no}" if self.source else f"line {self.line_no}"
        return f"[{self.kind}] {self.message} ({loc})"


_AST_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _safe_eval(expr: str, ctx: dict) -> float:
    """Evaluate a small arithmetic expression with ctx-resolved variables.

    Accepts numeric literals, bare names (looked up in ctx), and the four
    binary operators + - * /. Variables resolve via `_lookup` to support
    dotted/indexed paths.
    """
    tree = ast.parse(expr, mode="eval").body

    def walk(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.Name):
            v = _lookup(node.id, ctx)
            if v is _MISSING:
                raise KeyError(node.id)
            return float(v)
        if isinstance(node, ast.Subscript) or isinstance(node, ast.Attribute):
            # rebuild source-key from the AST so _lookup handles dotted/[i]
            src = ast.unparse(node)
            v = _lookup(src, ctx)
            if v is _MISSING:
                raise KeyError(src)
            return float(v)
        if isinstance(node, ast.BinOp) and type(node.op) in _AST_OPS:
            return _AST_OPS[type(node.op)](walk(node.left), walk(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _AST_OPS:
            return _AST_OPS[type(node.op)](walk(node.operand))
        raise ValueError(f"unsupported expression node {type(node).__name__}")

    return walk(tree)


PRIMITIVES = {"canvas", "theme", "text", "rect", "line", "polyline", "picture", "shape", "native"}


# ---------------------------------------------------------------------------
# Typed Document entry point
# ---------------------------------------------------------------------------

def expand_document(doc: "Document", pack: "BrandPack") -> "Document":
    """Expand a typed :class:`~feinschmiede.dsl.ast.Document` using brand compounds.

    Wraps :func:`expand_compounds` via per-COMPOUND-element DSLNode
    reconstruction.  Non-compound elements pass through the typed AST
    unchanged.  The input document is not mutated.

    Each slide's elements go through compound expansion; diagram blocks
    are NOT rendered (use :func:`expand_diagram_blocks` for that).  This
    entry point is intended for content-slot interpolation and compound
    resolution on a plan-level Document (one per deck, slides carry
    layout + content metadata).

    Parameters
    ----------
    doc:
        The typed Document to expand.
    pack:
        BrandPack whose compounds/ directory contributes brand-specific
        compound definitions.

    Returns
    -------
    Document
        A new Document with compound-call Elements replaced by their
        expanded primitive children.
    """
    import feinschmiede
    from feinschmiede.dsl.ast import Document, Slide

    std_dir = Path(feinschmiede.__file__).resolve().parent / "compounds"
    compounds = load_compounds_for_brand(pack.root, std_dir=std_dir)

    expanded_slides: list[Slide] = []
    for slide in doc.slides:
        expanded_elements = _expand_elements(slide.elements, compounds)
        expanded_slides.append(Slide(
            layout=slide.layout,
            elements=expanded_elements,
            meta=dict(slide.meta),
            notes=slide.notes,
        ))
    return Document(
        version=doc.version,
        slides=expanded_slides,
        meta=dict(doc.meta),
    )


def _expand_elements(
    elements: list["Element"],
    compounds: dict,
) -> list["Element"]:
    """Recursively expand COMPOUND-kind Elements using the compounds map.

    Returns a new flat list of expanded elements.  Non-compound elements
    pass through unchanged.  This mirrors ``expand_compounds`` but operates
    on the typed Element AST rather than DSLNode lists.
    """
    from feinschmiede.dsl.ast import Element, ElementKind

    out: list[Element] = []
    for el in elements:
        if el.kind is ElementKind.COMPOUND:
            compound_name = el.props.get("compound_name") or el.props.get("_dsl_kind", "")
            cd = compounds.get(compound_name)
            if cd is None:
                # Unknown compound — pass through as-is (matches expand_compounds behaviour).
                out.append(el)
            else:
                # Reconstruct a DSLNode, run expand_compounds, convert back.
                from feinschliff.dsl.parser import DSLNode
                call_node = DSLNode(
                    kind=compound_name,
                    pos_args=list(el.props.get("pos_args") or []),
                    kw_args={k: v for k, v in el.props.items()
                             if k not in ("pos_args", "label", "source", "line_no",
                                          "compound_name", "_dsl_kind")},
                    label=el.props.get("label"),
                )
                expanded_nodes, _ = expand_compounds([call_node], compounds)
                from feinschliff.dsl.parser import _node_to_element
                for n in expanded_nodes:
                    out.append(_node_to_element(n))
        elif el.kind is ElementKind.GROUP and el.children:
            out.append(Element(
                kind=el.kind,
                props=dict(el.props),
                children=_expand_elements(el.children, compounds),
            ))
        else:
            out.append(el)
    return out


# ---------------------------------------------------------------------------
# Compound library loading
# ---------------------------------------------------------------------------

def load_compounds(*dirs: Path) -> dict[str, CompoundDef]:
    """Load all `*.dsl` from each dir, latter dirs override earlier on
    name collision (so brand-specific beats toolkit-standard)."""
    out: dict[str, CompoundDef] = {}
    for d in dirs:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.dsl")):
            _nodes, defs = parse_file(f)
            for cd in defs:
                out[cd.name] = cd
    return out


def load_compounds_for_brand(
    brand_root: Path, *, std_dir: Path, brands_dir: Path | None = None
) -> dict[str, CompoundDef]:
    """Load compounds for a brand: engine-bundled toolkit compounds + brand-local.

    Brand-local compounds/ override toolkit compounds on name collision.
    Each brand pack is self-contained (no extends inheritance). The
    ``brands_dir`` argument is accepted but ignored.
    """
    return load_compounds(std_dir, brand_root / "compounds")


# ---------------------------------------------------------------------------
# Slot interpolation
# ---------------------------------------------------------------------------

# `{{ … }}` captures the full body. Bodies may be a single key path
# (`columns[0].counter`, `kpis[2].value`) or a small arithmetic expression
# (`y+h-1`, `x+w/2`) that mixes ctx names with int literals.
_SLOT_RE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")
_KEY_PART_RE = re.compile(r"(\w+)|\[(\d+)\]")

# `{{ key|default("Fallback") }}` — emit the literal when key is missing or
# empty-string. Single filter only; the rest of the slot grammar stays
# untouched. Used by layouts that want translatable defaults without forcing
# every deck to author the slot.
_DEFAULT_FILTER_RE = re.compile(
    r'^([\w\.\[\]]+)\s*\|\s*default\(\s*"([^"]*)"\s*\)\s*$'
)

# An arithmetic operator that is NOT inside `[...]` index brackets — used to
# tell a plain key path (`columns[0].counter`) from an expression (`x+w/2`).
_ARITH_OP_RE = re.compile(r"[+\-*/](?![^\[]*\])")


def _lookup(key: str, ctx: dict):
    """Walk a dotted/indexed key path against ctx; return the leaf value or
    a sentinel `_MISSING` if any step misses."""
    val = ctx
    for m in _KEY_PART_RE.finditer(key):
        word, idx = m.group(1), m.group(2)
        if word is not None:
            if isinstance(val, dict) and word in val:
                val = val[word]
            else:
                return _MISSING
        else:
            i = int(idx)
            if isinstance(val, (list, tuple)) and 0 <= i < len(val):
                val = val[i]
            else:
                return _MISSING
    return val


_MISSING = object()


def _interp(text: str, ctx: dict) -> str:
    """Replace `{{ … }}` placeholders with ctx-resolved values.

    Body forms:
      - simple key path (`title`, `columns[0].counter`)
      - arithmetic expression (`y+h-1`, `x+w/2`) with ctx names + literals

    Missing keys / unresolvable expressions resolve to an empty string.
    This is the production-safe behavior: it lets `if:{{ optional }}`
    guards suppress nodes whose binding is absent (instead of leaking
    the literal `{{ … }}` token into the rendered slide).
    """
    def repl(m: re.Match) -> str:
        body = m.group(1).strip()
        # `{{ key|default("fallback") }}` — literal fallback for missing slots.
        dm = _DEFAULT_FILTER_RE.match(body)
        if dm is not None:
            key, fallback = dm.group(1), dm.group(2)
            val = _lookup(key, ctx)
            # Only a MISSING key falls back. An explicit "" (or None) BLANKS
            # the slot — content plans on slotified brand layouts need a way
            # to suppress showcase copy per slide, and "" is that way.
            if val is _MISSING:
                return fallback
            if val is None:
                return ""
            return str(val)
        # Simple key path: no arithmetic operators outside of brackets.
        if not _ARITH_OP_RE.search(body):
            val = _lookup(body, ctx)
            if val is _MISSING:
                return ""
            return str(val)
        try:
            result = _safe_eval(body, ctx)
            return str(int(result)) if result == int(result) else f"{result:g}"
        except (KeyError, ValueError, SyntaxError, ZeroDivisionError):
            return ""
    return _SLOT_RE.sub(repl, text)


def interpolate_nodes(nodes: list[DSLNode], ctx: dict) -> list[DSLNode]:
    """Apply slot interpolation to every string-valued field on every node.

    `_for` nodes unroll here: the iterable is looked up in ctx and the body
    is recursively interpolated once per element, with the loop variable
    and a 0-based `i` index added to ctx. If the iterable is missing or
    empty the block simply emits nothing.
    """
    out: list[DSLNode] = []
    for n in nodes:
        if n.kind == "_for":
            var = n.kw_args.get("var", "item")
            iter_expr = n.kw_args.get("iter", "").strip()
            iterable = _lookup(iter_expr, ctx)
            if iterable is _MISSING or not iterable:
                continue
            for idx, item in enumerate(iterable):
                sub_ctx = dict(ctx)
                sub_ctx[var] = item
                sub_ctx["i"] = idx
                out.extend(interpolate_nodes(n.body or [], sub_ctx))
            continue
        new_pos = [_interp(p, ctx) for p in n.pos_args]
        new_kw = {k: (_interp(v, ctx) if isinstance(v, str) else v) for k, v in n.kw_args.items()}
        new_label = _interp(n.label, ctx) if n.label is not None else None
        out.append(replace(n, pos_args=new_pos, kw_args=new_kw, label=new_label))
    return out


# ---------------------------------------------------------------------------
# Snap-to-rail post-pass
# ---------------------------------------------------------------------------

# Element kinds whose visible left edge is the eye's alignment cue. Tight
# scope on purpose: this only snaps content text whose drift breaks the
# left rail. Structural rects, shapes, pictures, lines and embedded
# diagram frames stay untouched so panels / grids / illustrations that
# intentionally bleed past the rail are preserved. Per-node opt-out via
# `nosnap:true` attribute for the rare TEXT node that needs to sit off-rail.
_SNAP_KINDS: frozenset[str] = frozenset({"text"})


def _node_box(n: DSLNode) -> tuple[float, float, float, float] | None:
    """(x, y, w, h) in canvas px for a primitive that has a position+size,
    or `None` if we can't extract one. Used by the snap pass and the lint
    to find "shoulder" elements that explain an intentional indent."""
    if not n.pos_args:
        return None
    try:
        x_str, y_str = n.pos_args[0].split(",", 1)
        x = float(x_str.strip())
        y = float(y_str.strip())
    except (ValueError, IndexError):
        return None
    w = h = 0.0
    if len(n.pos_args) >= 2 and "x" in n.pos_args[1]:
        try:
            w_str, h_str = n.pos_args[1].lower().split("x", 1)
            w = float(w_str.strip())
            h = float(h_str.strip())
        except (ValueError, IndexError):
            pass
    if w == 0 and n.kw_args.get("maxwidth"):
        try:
            w = float(n.kw_args["maxwidth"])
        except (ValueError, TypeError):
            pass
    if h == 0 and n.kw_args.get("maxheight"):
        try:
            h = float(n.kw_args["maxheight"])
        except (ValueError, TypeError):
            pass
    return x, y, w, h


def snap_to_rails(nodes: list[DSLNode], tokens) -> list[DSLNode]:
    """Snap left edges of text nodes to the brand's `slide.left-rail`.

    Reads token `slide.left-rail` (default: `slide.padding-x`, default 100)
    and `slide.rail-snap-threshold` (default 30). A text node whose x sits
    within ±threshold of the rail but isn't exactly on it has its x snapped
    to the rail and its maxwidth shrunk by the same delta so the right edge
    stays put. Opt-out with `nosnap:true`.

    Indent-respecting: if any sibling has its right edge in (rail, text.x]
    and its y range overlaps the text's vertical band by 8+ pixels, the
    text is treated as an intentional indent past a shoulder element
    (bullet glyph, counter chip, illustration band) and is left in place.
    That keeps designs like exec-summary's bullet-square + indented body
    intact while still catching pure drift (e.g. 104 vs 100 in
    horizontal-bullets where no shoulder exists).
    """
    # Snap is brand-opt-in. Brands declare `slide.rail-snap-enabled: 1`
    # in tokens.json. Decompiled brand packs whose layouts came from a
    # source PPTX with a different native rail (e.g. x=76 vs x=85 etc.)
    # stay off until the rail is tuned per-brand. A brand that opts in
    # but sets no explicit `left-rail` inherits the value from
    # `slide.padding-x` (default 100).
    try:
        enabled = bool(int(tokens.slide("rail-snap-enabled")))
    except Exception:
        enabled = False
    if not enabled:
        return nodes
    try:
        rail = int(tokens.slide("left-rail")) or int(tokens.slide("padding-x")) or 100
    except Exception:
        rail = 100
    try:
        threshold = int(tokens.slide("rail-snap-threshold")) or 30
    except Exception:
        threshold = 30
    if threshold <= 0 or rail <= 0:
        return nodes

    boxes = [(_node_box(n), n) for n in nodes]

    def _direct_shoulder(text_x: float, text_y: float, text_h: float,
                          self_node: DSLNode) -> bool:
        ty0, ty1 = text_y, text_y + max(text_h, 1.0)
        for box, other in boxes:
            if other is self_node or box is None:
                continue
            ox, oy, ow, oh = box
            right = ox + max(ow, 1.0)
            if not (rail <= right <= text_x):
                continue
            oy1 = oy + max(oh, 1.0)
            overlap = min(ty1, oy1) - max(ty0, oy)
            if overlap >= 8:
                return True
        return False

    def _has_left_shoulder(text_x: float, text_y: float, text_h: float,
                           self_node: DSLNode) -> bool:
        # Direct shoulder: a structural element to the left in this row.
        if _direct_shoulder(text_x, text_y, text_h, self_node):
            return True
        # Block-inherited shoulder: a sibling text at the SAME x within
        # 80px vertically has a direct shoulder, so the block is indented
        # together. Catches "bullet square next to heading; body sits
        # below at the same indent" patterns.
        for box, other in boxes:
            if other is self_node or box is None:
                continue
            if other.kind not in _SNAP_KINDS:
                continue
            ox, oy, _ow, oh = box
            if ox != text_x or abs(oy - text_y) > 80:
                continue
            if _direct_shoulder(ox, oy, oh, other):
                return True
        return False

    out: list[DSLNode] = []
    for n in nodes:
        if (n.kind not in _SNAP_KINDS
                or n.kw_args.get("nosnap") in ("true", "1", True)):
            out.append(n)
            continue
        box = _node_box(n)
        if box is None:
            out.append(n)
            continue
        x, y, _w, h = box
        if x == rail or abs(x - rail) > threshold:
            out.append(n)
            continue
        if x > rail and _has_left_shoulder(x, y, h, n):
            out.append(n)
            continue
        dx = rail - x
        y_out = int(y) if y == int(y) else y
        new_pos = [f"{rail},{y_out}"] + list(n.pos_args[1:])
        new_kw = dict(n.kw_args)
        mw = new_kw.get("maxwidth")
        if mw is not None:
            try:
                new_kw["maxwidth"] = str(max(1, int(mw) - int(dx)))
            except (ValueError, TypeError):
                pass
        out.append(replace(n, pos_args=new_pos, kw_args=new_kw))
    return out


def rail_drift_report(nodes: list[DSLNode], tokens) -> list[str]:
    """List drift the snap pass will silently fix at render time: text
    nodes whose x is within ±threshold of the left rail, off-rail, and
    without a shoulder element justifying the indent. Mirrors
    `snap_to_rails` exactly — what shows up here is exactly what snap is
    rewriting. Empty list = clean. Surfaces in `feinschliff-builder
    audit` so authors can choose to fix the source instead of relying on
    the silent fix. Brand-gated by `slide.rail-snap-enabled`."""
    try:
        enabled = bool(int(tokens.slide("rail-snap-enabled")))
    except Exception:
        enabled = False
    if not enabled:
        return []
    try:
        rail = int(tokens.slide("left-rail")) or int(tokens.slide("padding-x")) or 100
    except Exception:
        rail = 100
    try:
        threshold = int(tokens.slide("rail-snap-threshold")) or 30
    except Exception:
        threshold = 30
    boxes = [(_node_box(n), n) for n in nodes]

    def _direct_shoulder(text_x: float, text_y: float, text_h: float,
                          self_node: DSLNode) -> bool:
        ty0, ty1 = text_y, text_y + max(text_h, 1.0)
        for box, other in boxes:
            if other is self_node or box is None:
                continue
            ox, oy, ow, oh = box
            right = ox + max(ow, 1.0)
            if not (rail <= right <= text_x):
                continue
            oy1 = oy + max(oh, 1.0)
            overlap = min(ty1, oy1) - max(ty0, oy)
            if overlap >= 8:
                return True
        return False

    def _has_left_shoulder(text_x: float, text_y: float, text_h: float,
                           self_node: DSLNode) -> bool:
        # Direct shoulder: a structural element to the left in this row.
        if _direct_shoulder(text_x, text_y, text_h, self_node):
            return True
        # Block-inherited shoulder: a sibling text at the SAME x within
        # 80px vertically has a direct shoulder, so the block is indented
        # together. Catches "bullet square next to heading; body sits
        # below at the same indent" patterns.
        for box, other in boxes:
            if other is self_node or box is None:
                continue
            if other.kind not in _SNAP_KINDS:
                continue
            ox, oy, _ow, oh = box
            if ox != text_x or abs(oy - text_y) > 80:
                continue
            if _direct_shoulder(ox, oy, oh, other):
                return True
        return False

    report: list[str] = []
    for n in nodes:
        if n.kind not in _SNAP_KINDS:
            continue
        if n.kw_args.get("nosnap") in ("true", "1", True):
            continue
        box = _node_box(n)
        if box is None:
            continue
        x, y, _w, h = box
        if x == rail or abs(x - rail) > threshold:
            continue
        if x > rail and _has_left_shoulder(x, y, h, n):
            continue
        label = (n.label or "").strip().strip('"')[:32]
        report.append(f"x={x:g} → rail={rail} (drift {x - rail:+g}px) {label!r}")
    return report


# ---------------------------------------------------------------------------
# Native-payload slot interpolation
# ---------------------------------------------------------------------------

# Text runs inside a native payload's carried PPTX XML. DOTALL: a run may
# legally contain newlines after XML unescaping (it cannot contain `<`).
_NATIVE_T_RE = re.compile(r"(<a:t>)(.*?)(</a:t>)", re.S)


def apply_slot_debug_color(nodes: list[DSLNode], color: str) -> list[DSLNode]:
    """Force every slot-bearing `text` node to render in ``color``.

    Slot-coverage debugging: build once with defaults, once with every slot
    bound + a debug color — text that stays brand-colored in the second
    render is NOT slot-covered (baked chrome). Replaceable pictures (path
    carries an image slot) get a debug-coloured border via the
    `_debug_border` kwarg the picture emitter honours. MUST run BEFORE
    `interpolate_nodes`: detection is by the node's label / path kwarg
    still carrying a `{{ … }}` slot marker, which interpolation resolves
    away."""
    for n in nodes:
        if n.kind == "text" and "{{" in (n.label or ""):
            n.kw_args["color"] = color
        elif n.kind == "picture" and "{{" in (n.kw_args.get("path") or ""):
            n.kw_args["_debug_border"] = color
    return nodes


def interpolate_native_text(
    nodes: list[DSLNode], ctx: dict, *, asset_root: Path | None = None,
    debug_color: str | None = None,
) -> list[DSLNode]:
    """Resolve `{{ slot }}` templates inside `native` payloads' text runs.

    The slotify pass (feinschliff-builder) rewrites placeholder `<a:t>` runs in
    carried tables / grouped shapes / custGeom chrome to
    `{{ text_N | default("…") }}` templates. Those live inside the base64
    `b64:` blob (or a sidecar `xml_file:`), so `interpolate_nodes` cannot see
    them — this pass decodes each payload, interpolates every text run via
    the same `_interp` slot grammar, and re-inlines the result as `b64:` so
    the emitter stays payload-agnostic.

    Sidecar payloads are read from `asset_root / xml_file` and inlined for
    THIS build only — the pack's sidecar file (the template) is never
    rewritten. Payloads without a `{{` marker pass through untouched, and a
    sidecar without markers keeps its `xml_file:` reference. Interpolated
    values are XML-escaped; newlines flatten to spaces (an `<a:t>` run cannot
    span paragraphs).

    ``debug_color`` (slot-coverage debugging, e.g. "#E6007E"): every run that
    held a slot template additionally gets a solidFill of that colour on its
    parent `<a:r>` run properties, so slot-covered native text is visually
    separable from baked chrome in a render diff.
    """
    import base64
    from xml.sax.saxutils import escape as _xml_escape
    from xml.sax.saxutils import unescape as _xml_unescape

    for n in nodes:
        if n.kind != "native":
            continue
        if debug_color is not None and (
                n.kw_args.get("media") or n.kw_args.get("media_file")):
            # Carried template images keep their (often colourful) pixels and
            # may have text BAKED into the bitmap — in the coverage render
            # they grey out so nothing reads as bindable content.
            n.kw_args["_debug_desat"] = "1"
        xml: str | None = None
        blob = n.kw_args.get("b64")
        if blob:
            try:
                xml = base64.b64decode(blob).decode("utf-8")
            except (ValueError, UnicodeDecodeError):
                continue  # undecodable payload — emitter will report it
        elif n.kw_args.get("xml_file") and asset_root is not None:
            sidecar = asset_root / n.kw_args["xml_file"]
            if sidecar.is_file():
                xml = sidecar.read_text(encoding="utf-8")
        if xml is None or "{{" not in xml:
            continue

        def repl(m: re.Match) -> str:
            # saxutils.unescape covers &amp;/&lt;/&gt; only — quote entities
            # must be listed, else default("…") templates never match the
            # slot grammar's ASCII-quote filter.
            inner = _xml_unescape(m.group(2),
                                  {"&quot;": '"', "&apos;": "'"})
            if "{{" not in inner:
                return m.group(0)
            resolved = _interp(inner, ctx).replace("\n", " ")
            return m.group(1) + _xml_escape(resolved) + m.group(3)

        new_xml = _NATIVE_T_RE.sub(repl, xml)
        if debug_color is not None:
            new_xml = _tint_slot_runs(xml, new_xml, debug_color)
        n.kw_args["b64"] = base64.b64encode(new_xml.encode("utf-8")).decode("ascii")
        n.kw_args.pop("xml_file", None)
    return nodes


_A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


def _tint_slot_runs(template_xml: str, resolved_xml: str, color: str) -> str:
    """Set a solidFill on every run whose text came from a slot template.

    Walks the TEMPLATE and RESOLVED documents in parallel (same shape — only
    text content differs) and tints the resolved run when the template run
    carried a `{{ … }}` marker. lxml-based; on any parse error the resolved
    XML is returned untinted (debug aid, never a build blocker)."""
    try:
        from lxml import etree
        tmpl = etree.fromstring(template_xml.encode("utf-8"))
        out = etree.fromstring(resolved_xml.encode("utf-8"))
    except Exception:
        return resolved_xml
    hexval = color.lstrip("#").upper()
    t_runs = tmpl.iter("{%s}t" % _A_NS)
    o_runs = out.iter("{%s}t" % _A_NS)
    for t_el, o_el in zip(t_runs, o_runs):
        if "{{" not in (t_el.text or ""):
            continue
        run = o_el.getparent()
        if run is None or not run.tag.endswith("}r"):
            continue
        rpr = run.find("{%s}rPr" % _A_NS)
        if rpr is None:
            rpr = etree.SubElement(run, "{%s}rPr" % _A_NS)
            run.remove(rpr)
            run.insert(0, rpr)
        for fill in rpr.findall("{%s}solidFill" % _A_NS):
            rpr.remove(fill)
        fill = etree.SubElement(rpr, "{%s}solidFill" % _A_NS)
        etree.SubElement(fill, "{%s}srgbClr" % _A_NS).set("val", hexval)
        # solidFill must precede latin/cs font tags per schema; move first.
        rpr.remove(fill)
        rpr.insert(0, fill)
    return etree.tostring(out, encoding="unicode")


_NATIVE_REPLACEABLE_MARKERS = ("<c:chart", "<dgm:", "relIds")
_XFRM_RE = re.compile(
    r'<a:off x="(-?\d+)" y="(-?\d+)"/><a:ext cx="(\d+)" cy="(\d+)"/>')


def mark_native_replaceables(
    nodes: list[DSLNode], color: str, *, asset_root: Path | None = None,
    emu_to_px: float = 0.0,
) -> list[DSLNode]:
    """Slot-coverage debugging: outline chart / SmartArt natives.

    Their data is replaceable post-export (PowerPoint edits the carried
    part graph) but not slot-bindable — in the coverage render they get a
    debug-coloured outline rect at the native's frame geometry so they read
    as "replaceable here" alongside magenta slot text and bordered picture
    slots. Requires the EMU→canvas-px scale; 0.0 disables (no geometry, no
    mark)."""
    import base64

    if not emu_to_px:
        return nodes
    out: list[DSLNode] = []
    for n in nodes:
        out.append(n)
        if n.kind != "native":
            continue
        xml: str | None = None
        if n.kw_args.get("b64"):
            try:
                xml = base64.b64decode(n.kw_args["b64"]).decode("utf-8", "replace")
            except ValueError:
                continue
        elif n.kw_args.get("xml_file") and asset_root is not None:
            sidecar = asset_root / n.kw_args["xml_file"]
            if sidecar.is_file():
                xml = sidecar.read_text(encoding="utf-8", errors="replace")
        if xml is None or not any(m in xml for m in _NATIVE_REPLACEABLE_MARKERS):
            continue
        g = _XFRM_RE.search(xml.replace("\n", ""))
        if g is None:
            continue
        x, y, w, h = (float(v) * emu_to_px for v in g.groups())
        if w < 4 or h < 4:
            continue
        out.append(DSLNode(
            kind="rect",
            pos_args=[f"{x:.0f},{y:.0f}", f"{w:.0f}x{h:.0f}"],
            kw_args={"stroke": color, "stroke-width": "8"},
            label=None, line_no=n.line_no, source=n.source,
        ))
    return out


# ---------------------------------------------------------------------------
# Compound resolution
# ---------------------------------------------------------------------------

def expand_compounds(
    nodes: list[DSLNode],
    compounds: dict[str, CompoundDef],
    *,
    depth: int = 0,
    max_depth: int = 8,
    _diagnostics: list[ExpansionDiagnostic] | None = None,
) -> tuple[list[DSLNode], list[ExpansionDiagnostic]]:
    """Recursively replace compound-call nodes with their parameter-
    substituted bodies until only primitives remain.

    A compound call is matched by `kind` against the compounds map. The
    call's `pos_args`/`kw_args`/`label` become a param-binding dict that
    gets interpolated into every body node.

    `max_depth` guards against runaway recursion (compound A calls
    compound B calls compound A …); the default matches docs/dsl-grammar.md.

    Returns `(primitives, diagnostics)`. Diagnostics is a list of
    `ExpansionDiagnostic` describing non-fatal issues (e.g.
    `unknown_compound`, `unknown_param`) gathered during expansion.
    Callers (CLIs) decide whether any diagnostic kind should fail the
    build — `expand_compounds` itself does not raise for them.
    """
    if depth > max_depth:
        raise RecursionError(
            f"compound expansion exceeded depth {max_depth} — cycle?"
        )

    # Top-level caller starts a fresh diagnostics list; recursive frames
    # share it so callers see all diagnostics in one pass.
    diags = _diagnostics if _diagnostics is not None else []

    out: list[DSLNode] = []
    for n in nodes:
        if n.kind in PRIMITIVES:
            out.append(n)
            continue
        if n.kind == "_for":
            # Reached `expand_compounds` only when `interpolate_nodes` was
            # skipped (e.g. wireframe --show-slots). Emit the body once so
            # the layout's structure is still visible; the placeholders
            # inside survive un-interpolated.
            sub_out, _ = expand_compounds(
                n.body or [], compounds,
                depth=depth + 1, max_depth=max_depth,
                _diagnostics=diags,
            )
            out.extend(sub_out)
            continue
        cd = compounds.get(n.kind)
        if cd is None:
            # Not a primitive, not a known compound. Record a diagnostic
            # and drop the node — the CLI decides if this is fatal.
            diags.append(ExpansionDiagnostic(
                kind="unknown_compound",
                message=f"unknown element '{n.kind}' — not a primitive and not a registered compound; skipping",
                source=n.source,
                line_no=n.line_no,
            ))
            continue
        bindings = _bind_params(cd, n, diags)
        body = interpolate_nodes(cd.body, bindings)
        sub_out, _ = expand_compounds(
            body, compounds,
            depth=depth + 1, max_depth=max_depth,
            _diagnostics=diags,
        )
        out.extend(sub_out)
    return out, diags


def expand_diagram_blocks(
    nodes: list[DSLNode],
    brand_dir: Path,
    out_dir: Path,
    layout_dir: Path | None = None,
    *,
    slide_index: int = 1,
    theme_tokens_path: Path | None = None,
) -> list[DSLNode]:
    """Replace svg/excalidraw block nodes with picture primitives pointing at
    rendered PNGs. Carries diagram metadata so wireframe can render the
    internal bbox layer alongside the slide-level wireframe.

    Renders are content-hash-cached: artifacts are named
    ``s{slide_index}-{id}-{hash}.{svg,excalidraw,png}`` where the hash covers
    every input the renderer depends on (see the cache-key comment below).
    When BOTH the expanded artifact text (.svg/.excalidraw) and its .png
    already exist for the current hash, the expand + write + render steps are
    skipped and the existing PNG is reused; wireframe primitives and
    ``_diagram_meta`` are still rebuilt for every node so downstream
    validators see exactly what they would on a fresh render. Artifacts whose
    name is NOT in the current hash set are deleted up front, so the
    structural-lint globs (``s{slide_index}-*.{excalidraw,svg}`` in
    pipeline.py) never lint a stale file as current.

    Parameters
    ----------
    nodes:
        Post-parse node list (output of ``parse_lines`` / ``parse_file``).
    brand_dir:
        Path to the active brand directory (passed through to diagram expanders
        for colour resolution).
    out_dir:
        Directory where rendered artifacts (.svg/.excalidraw + .png) are
        written.  Must exist before calling.
    layout_dir:
        Base directory for resolving ``from:`` relative paths.  Defaults to
        ``out_dir.parent`` when not supplied.
    """
    import hashlib
    import json as _json

    from feinschmiede.diagrams import svg_expand, excalidraw_expand
    # Module-level access (not `from … import render`) so tests can
    # monkeypatch feinschmiede.diagrams.render.render and observe cache hits.
    from feinschmiede.diagrams import render as _render_mod
    from feinschmiede.diagrams.diagram_wireframe import (
        primitives_from_svg_dsl,
        primitives_from_excalidraw_dsl,
    )

    # Tokens hash for the diagram cache key. Diagram colours resolve through
    # the FULL `extends:` chain (brand_bridge merges parent tokens), so hashing
    # only the child brand's tokens.json would reuse a stale PNG when a PARENT
    # token is edited — common for a brand that inherits its palette via
    # `extends:`. Hash the merged, extends-resolved tokens instead. When a theme
    # is active (`theme_tokens_path`), its bytes are also included so two themes
    # of the same brand never share diagram cache entries. Computed once per call
    # (constant across this slide's diagram nodes). Falls back to the child file
    # alone if the chain can't be resolved, so a malformed parent degrades to a
    # stale-cache risk rather than crashing the build.
    try:
        from feinschmiede.dsl.tokens import load_tokens_with_theme
        # Derive theme name from theme_tokens_path (themes/<name>/tokens.json)
        _theme_name: str | None = None
        if theme_tokens_path is not None and theme_tokens_path.is_file():
            _theme_name = theme_tokens_path.parent.name
        _merged_raw = load_tokens_with_theme(brand_dir, _theme_name).raw
        _tokens_hash = hashlib.sha1(
            _json.dumps(_merged_raw, sort_keys=True,
                        separators=(",", ":")).encode()
        ).hexdigest()[:12]
    except Exception:  # noqa: BLE001 — never block a render on token resolution
        _tj = brand_dir / "tokens.json"
        _tokens_hash = (
            hashlib.sha1(_tj.read_bytes()).hexdigest()[:12]
            if _tj.exists() else ""
        )
        # Append theme bytes if available so fallback hashes still differ per theme.
        if theme_tokens_path is not None and theme_tokens_path.is_file():
            _tokens_hash = hashlib.sha1(
                (_tokens_hash + hashlib.sha1(
                    theme_tokens_path.read_bytes()
                ).hexdigest()).encode()
            ).hexdigest()[:12]
    _layout_dir_name = layout_dir.name if layout_dir is not None else ""

    # ---- Pass 1: compute each diagram's cache identity -------------------
    # Everything the hash needs is available WITHOUT expanding: body text
    # (the `from:` file read happens here, before hashing, exactly as it did
    # when hashing lived in the render loop), kind, geometry, virtual dims,
    # brand name, tokens hash, from_path, layout dir name. Geometry errors
    # for malformed blocks fire here — before any hashing or cleanup.
    #
    # Cache key must include every input the renderer actually depends
    # on. Hashing only `body` collides whenever two slides share the same
    # diagram id + body but differ on brand, region size, or kind — the
    # later render then overwrites the earlier PNG (Review #0.1).
    # Virtual canvas dimensions also participate so identical bodies
    # rendered at different scales don't collide. `_tokens_hash` (merged
    # extends chain) and `_layout_dir_name` are computed once above.
    # from_path and layout_dir prevent collisions across layouts that
    # embed the same external DSL file.
    infos: list[dict | None] = []
    expected_names: set[str] = set()
    for n in nodes:
        if n.kind not in ("svg", "excalidraw"):
            infos.append(None)
            continue

        # All diagram geometry lives in kw_args (set by _parse_diagram_block,
        # which only runs when the line matched the multi-line block header:
        # `<kind> <id> <x>,<y> <w>x<h> {` with the brace at END of line). If
        # geometry is absent the header didn't match — almost always a
        # single-line `{ … }` body or a multi-token id. Fail with the fix
        # rather than a bare KeyError deep in the expander.
        if "x" not in n.kw_args:
            raise SyntaxError(
                f"{n.source or '<dsl>'} line {n.line_no}: malformed '{n.kind}' "
                f"diagram block — no geometry parsed. Use the multi-line form "
                f"with the opening brace at END of line:\n"
                f"  {n.kind} <id> <x>,<y> <w>x<h> {{\n"
                f"    path p \"M 0,0 L 1,1 Z\" fill:accent\n"
                f"  }}\n"
                f"Single-line `{{ … }}` body and a missing/multi-token <id> are "
                f"not supported here."
            )
        w: int = n.kw_args["w"]  # type: ignore[assignment]
        h: int = n.kw_args["h"]  # type: ignore[assignment]
        dsl_id: str = n.kw_args["id"]  # type: ignore[assignment]

        # Virtual viewport: when the layout block declares `virtual:WxH`, the
        # body is authored in WxH coords and the renderer rasterizes at WxH.
        # PowerPoint downscales on insert. When absent, the slot IS the canvas
        # (legacy behavior, preserved bit-for-bit).
        _vw = n.kw_args.get("virtual_w")
        virtual_w: int = _vw if _vw is not None else w  # type: ignore[assignment]
        _vh = n.kw_args.get("virtual_h")
        virtual_h: int = _vh if _vh is not None else h  # type: ignore[assignment]

        # Resolve body: inline string or external file.
        body: str = n.kw_args.get("body") or ""  # type: ignore[assignment]
        from_path: str | None = n.kw_args.get("from")  # type: ignore[assignment]
        if from_path:
            base = layout_dir or out_dir.parent
            raw = Path(base / from_path).read_text()
            # Strip any canvas line — region/virtual size IS the canvas when
            # embedded. Files keep `canvas` for standalone-render workflows.
            body = "\n".join(
                line for line in raw.splitlines()
                if not line.strip().startswith("canvas ")
            )

        key_blob = "|".join((
            str(slide_index),
            n.kind,
            f"{w}x{h}",
            f"v{virtual_w}x{virtual_h}",
            brand_dir.name,
            _tokens_hash,
            from_path or "",
            _layout_dir_name,
            body,
        ))
        body_hash = hashlib.sha1(key_blob.encode()).hexdigest()[:10]
        ext = ".svg" if n.kind == "svg" else ".excalidraw"
        artifact = out_dir / f"s{slide_index}-{dsl_id}-{body_hash}{ext}"
        png = artifact.with_suffix(".png")
        infos.append({
            "body": body,
            "virtual_w": virtual_w,
            "virtual_h": virtual_h,
            "artifact": artifact,
            "png": png,
        })
        expected_names.add(artifact.name)
        expected_names.add(png.name)

    # ---- Stale cleanup: keep current-hash artifacts, drop the rest -------
    # Artifacts are content-hash-named and out_dir is persistent on the
    # `feinschliff build` path, so a changed diagram leaves the old hash file
    # behind. The structural-lint loops glob `s{slide_index}-*`, so a stale
    # artifact would be linted as if current. Only files NOT in the current
    # hash set are deleted — matching ones survive and feed the cache below.
    # The `s{idx}-` prefix is glob-safe (`s5-*` does not match `s50-*`). Only
    # runs when this slide actually has diagrams.
    if out_dir.exists() and expected_names:
        for stale in out_dir.glob(f"s{slide_index}-*"):
            if stale.name not in expected_names:
                stale.unlink(missing_ok=True)

    # ---- Pass 2: render (cache-aware) and build picture nodes -------------
    out: list[DSLNode] = []
    for n, info in zip(nodes, infos):
        if info is None:
            out.append(n)
            continue

        x: int = n.kw_args["x"]  # type: ignore[assignment]
        y: int = n.kw_args["y"]  # type: ignore[assignment]
        # w, h, dsl_id are re-read from the node here (always present); only
        # render-affecting inputs are stashed in `info` to keep the stash small.
        w = n.kw_args["w"]  # type: ignore[assignment]
        h = n.kw_args["h"]  # type: ignore[assignment]
        dsl_id = n.kw_args["id"]  # type: ignore[assignment]
        body = info["body"]
        virtual_w = info["virtual_w"]
        virtual_h = info["virtual_h"]
        artifact: Path = info["artifact"]
        png: Path = info["png"]

        # Wireframe primitives are rebuilt on every call — cache hit or miss —
        # because downstream validators read them out of `_diagram_meta`.
        # They need only the body DSL, not the expanded artifact.
        if n.kind == "svg":
            prims = primitives_from_svg_dsl(body, brand_dir, canvas_w=virtual_w)
        else:
            prims = primitives_from_excalidraw_dsl(body, brand_dir, canvas_w=virtual_w)

        # Cache hit requires BOTH the expanded artifact text and a non-empty PNG:
        # the lint loops read the artifact, pptx emit reads the PNG. A zero-byte
        # PNG from an interrupted render is treated as a miss so it gets
        # re-rendered cleanly. Anything less re-expands and re-renders from scratch.
        if not (artifact.exists() and png.exists() and png.stat().st_size > 0):
            if n.kind == "svg":
                expanded_text = svg_expand.expand(
                    body, brand_dir=brand_dir, canvas_override=(virtual_w, virtual_h)
                )
            else:
                expanded_text = excalidraw_expand.expand(
                    body, brand_dir=brand_dir, canvas_override=(virtual_w, virtual_h)
                )
            artifact.write_text(expanded_text)
            _render_mod.render(artifact, png, brand_dir=brand_dir)

        # Build a picture-kind DSLNode.  Geometry goes into kw_args (consistent
        # with how diagram nodes store their own geometry).  Diagram metadata is
        # stuffed into the sentinel key ``_diagram_meta`` — DSLNode has no
        # dedicated metadata field, so this is the cleanest non-breaking option.
        pic = DSLNode(
            kind="picture",
            kw_args={
                "id": dsl_id,
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "src": str(png),
                "_diagram_meta": {
                    "kind": n.kind,
                    "source_dsl": body,
                    "internal_primitives": [p.__dict__ for p in prims],
                    "virtual_canvas_w": virtual_w,
                    "virtual_canvas_h": virtual_h,
                    "slot_w": w,
                    "slot_h": h,
                },
            },
            line_no=n.line_no,
            source=n.source,
        )
        out.append(pic)
    return out


def _bind_params(
    cd: CompoundDef,
    call: DSLNode,
    diagnostics: list[ExpansionDiagnostic] | None = None,
) -> dict:
    """Build the binding dict for a compound call.

    Every declared parameter is bound — defaulted to "" when the caller
    omits it — so `{{ name }}` placeholders inside the body never leak
    through as literal text. Positional args fill in declaration order;
    keyword args override positional; `label` carries the trailing
    quoted string when present.

    Undeclared kwargs are accepted (so layouts can pass overrides), but
    a warning is emitted via `warnings.warn` AND an `unknown_param`
    diagnostic is appended (if `diagnostics` is provided) so the typo
    `vlaue:"x"` doesn't silently leak.
    """
    declared = set(cd.params)
    bindings: dict[str, str] = dict.fromkeys(cd.params, "")
    for i, p in enumerate(cd.params):
        if i < len(call.pos_args):
            bindings[p] = call.pos_args[i]
    for k, v in call.kw_args.items():
        if k not in declared:
            msg = (
                f"compound '{cd.name}' (called at {call.source}:{call.line_no}): "
                f"unknown parameter '{k}' (declared params: {sorted(declared) or '[]'})"
            )
            warnings.warn(msg, UserWarning, stacklevel=2)
            if diagnostics is not None:
                diagnostics.append(ExpansionDiagnostic(
                    kind="unknown_param",
                    message=msg,
                    source=call.source,
                    line_no=call.line_no,
                ))
        bindings[k] = v
    if call.label is not None:
        bindings.setdefault("label", call.label)
    return bindings
