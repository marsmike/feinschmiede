"""Per-layout semantic annotation helpers for decompiled brand packs.

Two public functions:

- ``manifest_for_pack(pack_dir)`` — walks all layouts in a pack and returns
  a list of per-layout dicts describing slot inventory, existing annotation
  values, and candidate thumbnail/PDF paths.  Consuming code (typically an
  orchestrating Claude session) reads this manifest to decide what to
  annotate and where to find visual evidence.

- ``apply_annotation(layout_path, annotation)`` — writes annotation fields
  into the layout's YAML frontmatter, preserving every other field byte-for-
  byte.  Uses the same ``apply_profile`` / ``_merge_annotations`` machinery
  as the profile generator so the rewrite is idempotent and loss-free.

No LLM is invoked here.  This module is intentionally free of the
``anthropic`` SDK — judging is performed by the orchestrating Claude session
that calls these helpers.
"""
from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any

import yaml

from feinschliff.dsl.parser import split_frontmatter

# ---------------------------------------------------------------------------
# Internal patterns — lightweight DSL sniffers
# ---------------------------------------------------------------------------

# Jinja text-slot line:  {{ text_N | default("…") }}
_TEXT_SLOT_RE = re.compile(r'\{\{\s*text_\d+\s*\|')
# Jinja image-slot line: {{ image | default("…") }} or {{ image_N | … }}
_IMAGE_SLOT_RE = re.compile(r'\{\{\s*image\d*\s*\|')
# Raw `picture` lines that have a Jinja image binding (not a static path).
# We count the Jinja bindings, not every `picture` line.
_PICTURE_JINJA_RE = re.compile(r'^picture\b.*\{\{\s*image', re.M)

# Native-payload kind markers (cheap substring sniff on decoded XML).
_CHART_MARKER = "<c:chart"
_TABLE_MARKER = "<a:tbl"
_SMARTART_MARKERS = ("<dgm:", "relIds")

# Payload block in DSL:  native <kind> b64:"…"  or  native <kind> xml_file:"…"
_NATIVE_B64_RE = re.compile(r'^native\s+\w+\s+.*?b64:"([^"]+)"', re.M)
_NATIVE_XMLFILE_RE = re.compile(r'^native\s+\w+\s+.*?xml_file:"([^"]+)"', re.M)

# Annotation field names recognised by apply_annotation.
_ANNOTATION_KEYS = frozenset(
    {"description", "when_to_use", "when_not_to_use", "chrome_subject", "primary_message"}
)


# ---------------------------------------------------------------------------
# Slot inventory
# ---------------------------------------------------------------------------

def _decode_native_payloads(body: str, pack_dir: Path) -> list[str]:
    """Return a list of decoded XML strings for every native payload in *body*."""
    xmls: list[str] = []
    for m in _NATIVE_B64_RE.finditer(body):
        try:
            xmls.append(base64.b64decode(m.group(1)).decode("utf-8", errors="replace"))
        except Exception:
            pass
    for m in _NATIVE_XMLFILE_RE.finditer(body):
        candidate = pack_dir / m.group(1)
        if candidate.is_file():
            try:
                xmls.append(candidate.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                pass
    return xmls


def _slot_inventory(body: str, pack_dir: Path) -> dict[str, int]:
    """Count elements of interest in one layout body.

    Returned dict keys:
      text_slots          — Jinja text_N bindings
      image_slots         — Jinja image / image_N bindings on picture lines
      native_pics         — ``native`` lines that are not chart/table/smartart
      native_graphic_frames — native lines that ARE chart/table/smartart
      native_shapes       — (currently 0; reserved for future shape payloads)
      chart_count         — native payloads containing <c:chart
      table_count         — native payloads containing <a:tbl
      smartart_count      — native payloads containing <dgm: or relIds
    """
    text_slots = len(_TEXT_SLOT_RE.findall(body))
    image_slots = len(_PICTURE_JINJA_RE.findall(body))

    native_lines = re.findall(r'^native\s+\S+', body, re.M)
    native_total = len(native_lines)

    xmls = _decode_native_payloads(body, pack_dir)
    chart_count = sum(1 for x in xmls if _CHART_MARKER in x)
    table_count = sum(1 for x in xmls if _TABLE_MARKER in x)
    smartart_count = sum(
        1 for x in xmls if any(m in x for m in _SMARTART_MARKERS)
    )
    data_native = chart_count + table_count + smartart_count
    illustration_native = max(0, native_total - data_native)

    return {
        "text_slots": text_slots,
        "image_slots": image_slots,
        "native_pics": illustration_native,
        "native_graphic_frames": data_native,
        "native_shapes": 0,
        "chart_count": chart_count,
        "table_count": table_count,
        "smartart_count": smartart_count,
    }


# ---------------------------------------------------------------------------
# Thumbnail / PDF discovery
# ---------------------------------------------------------------------------

def _thumbnail_candidates(pack_dir: Path, stem: str, slide_index: int | None) -> list[str]:
    """Return paths (as strings) of plausible thumbnail files that exist."""
    work = pack_dir / ".work"
    candidates: list[Path] = []

    # render-annotated/<stem>.png
    candidates.append(work / "render-annotated" / f"{stem}.png")
    # render-annotated/page-<NN>.png where NN is the 1-based slide_index
    if slide_index is not None:
        nn = str(slide_index).zfill(2)
        candidates.append(work / "render-annotated" / f"page-{nn}.png")
    # showcase/<stem>.png
    candidates.append(work / "showcase" / f"{stem}.png")

    return [str(p) for p in candidates if p.is_file()]


def _annotated_pdf(pack_dir: Path) -> str | None:
    """Return path to annotated PDF if present, else None."""
    pack_name = pack_dir.name
    for candidate in (
        pack_dir / ".work" / f"{pack_name}-annotated.pdf",
        pack_dir / ".work" / "annotated.pdf",
    ):
        if candidate.is_file():
            return str(candidate)
    return None


# ---------------------------------------------------------------------------
# manifest_for_pack
# ---------------------------------------------------------------------------

def manifest_for_pack(pack_dir: Path) -> list[dict[str, Any]]:
    """Walk ``<pack_dir>/layouts/*.slide.dsl`` and return a manifest list.

    Each item is a dict with keys:

    ``stem``
        Filename without ``.slide.dsl``.
    ``path``
        Absolute path string.
    ``current_role``, ``current_family``, ``current_data_band``
        Values from frontmatter, empty string when missing.
    ``current_description``, ``current_when_to_use``, ``current_when_not_to_use``,
    ``current_chrome_subject``, ``current_primary_message``
        Annotation values from frontmatter, empty string when missing/absent.
    ``slot_inventory``
        Dict of element counts (see :func:`_slot_inventory`).
    ``thumbnail_candidates``
        List of paths to thumbnail PNGs that exist on disk.
    ``annotated_pdf``
        Path to the annotated PDF, or ``None``.
    """
    pack_dir = pack_dir.resolve()
    layouts_dir = pack_dir / "layouts"
    if not layouts_dir.is_dir():
        return []

    result: list[dict[str, Any]] = []
    for dsl_path in sorted(layouts_dir.glob("*.slide.dsl")):
        stem = dsl_path.name.removesuffix(".slide.dsl")
        try:
            dsl_text = dsl_path.read_text(encoding="utf-8")
        except OSError:
            continue

        fm_text, body = split_frontmatter(dsl_text)
        fm: dict = {}
        if fm_text:
            try:
                parsed = yaml.safe_load(fm_text)
                if isinstance(parsed, dict):
                    fm = parsed
            except yaml.YAMLError:
                pass

        slide_index: int | None = fm.get("slide_index")

        entry: dict[str, Any] = {
            "stem": stem,
            "path": str(dsl_path),
            # Heuristic classifier fields
            "current_role": fm.get("role", ""),
            "current_family": fm.get("family", ""),
            "current_data_band": fm.get("data_band", ""),
            # Annotation fields
            "current_description": fm.get("description", ""),
            "current_when_to_use": fm.get("when_to_use", ""),
            "current_when_not_to_use": fm.get("when_not_to_use", ""),
            "current_chrome_subject": fm.get("chrome_subject", ""),
            "current_primary_message": fm.get("primary_message", ""),
            # Slot inventory from body
            "slot_inventory": _slot_inventory(body, pack_dir),
            # Visual evidence
            "thumbnail_candidates": _thumbnail_candidates(pack_dir, stem, slide_index),
            "annotated_pdf": _annotated_pdf(pack_dir),
        }
        result.append(entry)

    return result


# ---------------------------------------------------------------------------
# apply_annotation
# ---------------------------------------------------------------------------

def apply_annotation(layout_path: Path, annotation: dict[str, Any]) -> None:
    """Write *annotation* fields into the YAML frontmatter of *layout_path*.

    Only keys present in *annotation* and recognised as annotation fields
    (``description``, ``when_to_use``, ``when_not_to_use``, ``chrome_subject``,
    ``primary_message``) are written.  All other frontmatter fields and the
    body are preserved byte-for-byte.

    If the layout has no frontmatter yet a minimal fence is created containing
    only the annotation fields.

    Raises ``ValueError`` if the YAML rewrite would produce invalid YAML.
    Raises ``OSError`` if the file cannot be read or written.
    """
    dsl_text = layout_path.read_text(encoding="utf-8")
    fm_text, body = split_frontmatter(dsl_text)

    # Load existing frontmatter (or start fresh).
    existing: dict = {}
    if fm_text:
        try:
            parsed = yaml.safe_load(fm_text)
            if isinstance(parsed, dict):
                existing = parsed
        except yaml.YAMLError as exc:
            raise ValueError(f"Cannot parse existing frontmatter in {layout_path}: {exc}") from exc

    # Apply only recognised, supplied keys.
    for key, val in annotation.items():
        if key in _ANNOTATION_KEYS:
            existing[key] = val

    # Serialise, verifying round-trip.
    try:
        new_fm_yaml = yaml.safe_dump(
            existing, sort_keys=False, allow_unicode=True,
            default_flow_style=None, width=120,
        )
        # Verify the YAML is parseable (catches edge cases in values).
        yaml.safe_load(new_fm_yaml)
    except yaml.YAMLError as exc:
        raise ValueError(f"Annotation YAML serialisation failed for {layout_path}: {exc}") from exc

    new_text = "---\n" + new_fm_yaml + "---\n" + _strip_fence(dsl_text)
    layout_path.write_text(new_text, encoding="utf-8")


def _strip_fence(dsl_text: str) -> str:
    """Drop the leading ``--- … ---`` fence, returning the body unchanged.

    Mirrors the private ``_strip_fence`` in ``layout_profile_gen`` but is
    kept local so this module has no internal import dependency on it.
    """
    lines = dsl_text.splitlines(keepends=True)
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines) or lines[i].strip() != "---":
        return dsl_text
    for j in range(i + 1, len(lines)):
        if lines[j].strip() == "---":
            return "".join(lines[j + 1:])
    return dsl_text  # unterminated fence — leave document alone
