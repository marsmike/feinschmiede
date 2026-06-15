"""Layout validator — compatibility stub.

The DSL-era layout validators (validate_diagrams, validate_diagrams_color,
validate_diagrams_text_size, validate_deck, format_defects) have been removed
with the DSL pipeline. This module is kept as a stub so callers don't crash
at import time.

The master-template renderer path uses the feinschmiede structural validators
directly (feinschmiede.diagrams.structural_validator).
"""
from __future__ import annotations

from typing import Any


def validate_diagrams(nodes: list, *, slide_index: int = 1,
                      slide_w: int = 0, slide_h: int = 0) -> list:
    """Stub: returns empty list."""
    return []


def validate_diagrams_color(nodes: list, *, slide_index: int = 1,
                             brand_dir: Any = None) -> list:
    """Stub: returns empty list."""
    return []


def validate_diagrams_text_size(nodes: list, *, slide_index: int = 1,
                                 slide_w: int = 0, slide_h: int = 0) -> list:
    """Stub: returns empty list."""
    return []


def validate_deck(pptx_path: Any, *, ignore_out_of_bounds: bool = False) -> list:
    """Stub: returns empty list."""
    return []


def format_defects(defects: list) -> str:
    """Stub: returns empty string."""
    return ""
