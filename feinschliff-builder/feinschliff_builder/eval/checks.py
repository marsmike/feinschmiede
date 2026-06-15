"""Deterministic eval checks for the /goal loop.

Each check is a string. Named checks take no args; count checks have the form
``<element><op><int>`` (e.g. ``rectangles==5``). Checks read an already-generated
artifact (.excalidraw / .svg) and return a bool. No LLM, no render.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

_COUNT_RE = re.compile(
    r"^(rectangles|ellipses|diamonds|arrows|text|lines)\s*(==|>=|<=|>|<)\s*(\d+)$"
)
_HEX_RE = re.compile(r"#[0-9a-fA-F]{6}")

# Plural check-token -> excalidraw element `type` string.
_ELEMENT_TYPE = {
    "rectangles": "rectangle",
    "ellipses": "ellipse",
    "diamonds": "diamond",
    "arrows": "arrow",
    "text": "text",
    "lines": "line",
}

_OPS = {
    "==": lambda a, b: a == b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
}


@dataclass
class CheckContext:
    """Shared state a check may need (the active brand pack dir)."""

    brand_dir: Path


def run_check(name: str, artifact: Path, ctx: CheckContext) -> bool:
    """Run a single named/count check against an artifact. Raises on unknown name."""
    if name == "valid-excalidraw-json" or name == "valid-svg":
        return _valid_diagram(artifact)
    if name == "has-viewBox":
        return "viewBox=" in artifact.read_text()
    if name == "uses-semantic-colors":
        return _uses_semantic_colors(artifact, ctx.brand_dir)
    if name == "title-on-grid":
        return _title_on_grid(artifact, ctx.brand_dir)
    if name == "footer-overridable":
        return _footer_overridable(artifact, ctx.brand_dir)
    m = _COUNT_RE.match(name)
    if m:
        return _count_check(artifact, m.group(1), m.group(2), int(m.group(3)))
    raise ValueError(f"unknown check: {name!r}")


def _valid_diagram(artifact: Path) -> bool:
    """True iff the structural validator finds no ERROR-severity defects."""
    from feinschmiede.diagnostics import Severity
    from feinschmiede.diagrams import structural_validator as sv

    try:
        defects = sv.validate_diagram_file(artifact)
    except Exception:
        return False
    return not any(d.severity == Severity.ERROR for d in defects)


def _count_check(artifact: Path, element: str, op: str, n: int) -> bool:
    try:
        doc = json.loads(artifact.read_text())
    except Exception:
        return False
    want = _ELEMENT_TYPE[element]
    count = sum(1 for el in doc.get("elements", []) if el.get("type") == want)
    return _OPS[op](count, n)


_TITLE_TEXT_RE = re.compile(r"^\s*text\s+(\d+),(\d+)\b")


def _title_on_grid(artifact: Path, brand_dir: Path, *, tol: float = 8.0) -> bool:
    """True iff the layout's title sits on the brand's left margin.

    The title is the first top-anchored `text` primitive (y within the top
    padding band). Its x must equal the brand's `slide.padding-x` (±tol).
    Reads the pack's OWN tokens, so it generalises across brands — it
    encodes the decompiler drift root cause (titles landing off-grid).
    """
    from feinschmiede.dsl.tokens import load_tokens

    tokens = load_tokens(brand_dir)
    pad_x = tokens.slide("padding-x")
    try:
        pad_y_top = tokens.slide("padding-y-top")
    except Exception:
        pad_y_top = pad_x
    for line in artifact.read_text().splitlines():
        m = _TITLE_TEXT_RE.match(line)
        if not m:
            continue
        x, y = int(m.group(1)), int(m.group(2))
        if y <= pad_y_top + 60:  # top-anchored line => the title
            return abs(x - pad_x) <= tol
    return True  # no top-anchored title (e.g. a cover) => nothing to misplace


def _footer_overridable(artifact: Path, brand_dir: Path) -> bool:
    """True iff the layout does NOT hardcode the brand's footer template
    defaults (`brand.footer-date` / `brand.footer-section`).

    Those values must reach the footer via deck-overridable content slots, not
    bare literal args — otherwise every deck shows the template's date/section.
    A value living inside a `{{ … }}` slot expression (even as a `default(...)`)
    is overridable and passes; the same value as a bare quoted arg fails. Brands
    that define no footer template defaults pass vacuously.
    """
    from feinschmiede.dsl.tokens import load_tokens

    tokens = load_tokens(brand_dir)
    brand = tokens.raw.get("brand", {})
    literals = [
        brand.get(k, {}).get("$value")
        for k in ("footer-date", "footer-section")
    ]
    literals = [v for v in literals if v]
    if not literals:
        return True  # no footer template defaults declared -> nothing to leak
    # Drop slot expressions so a value used only as a {{ … default("x") }} is
    # not mistaken for a hardcoded leak.
    stripped = re.sub(r"\{\{.*?\}\}", "", artifact.read_text())
    return not any(f'"{lit}"' in stripped for lit in literals)


def _uses_semantic_colors(artifact: Path, brand_dir: Path) -> bool:
    """True iff every #rrggbb in the artifact resolves to an active brand token."""
    from feinschmiede.diagrams.brand_bridge import (
        SEMANTIC_NAMES,
        BrandBridgeError,
        resolve,
    )

    palette: set[str] = set()
    for sem in SEMANTIC_NAMES:
        try:
            palette.add(resolve(sem, brand_dir).lower())
        except BrandBridgeError:
            pass
    text = artifact.read_text()
    matches = list(_HEX_RE.finditer(text))
    # An artifact with zero hex colours used NO brand token — that fails the
    # check (all() over an empty iterator would otherwise vacuously pass).
    return bool(matches) and all(m.group(0).lower() in palette for m in matches)
