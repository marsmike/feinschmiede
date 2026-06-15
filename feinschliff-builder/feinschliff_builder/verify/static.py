"""Pre-render static geometry verify — DSL path removed.

The DSL-based slot-overflow and empty-placeholder checks have been removed with
the DSL pipeline. This module is kept as a compatibility shim so callers can
still import ``static_verify`` and ``validate`` without crashing; both now
return empty results (no defects, clean bag).

The master-template renderer path (``feinschliff render-master``) does not need
a pre-render static geometry gate: the catalog's ``chars`` slot metadata is
enforced at planning time via ``feinschliff.layout_picker``'s budget-penalty
scoring, not a separate verify step.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from feinschliff.defects import Defect

if TYPE_CHECKING:
    from feinschmiede.brand import BrandPack
    from feinschmiede.diagnostics import DiagnosticBag


def static_verify(
    plan: dict,
    brand_dir: Path,
    *,
    plan_dir: Path | None = None,
) -> list[Defect]:
    """Static geometry verify — returns empty list (DSL path removed).

    The DSL pipeline and its layout-node parsing have been removed. Slot-budget
    enforcement now happens via ``feinschliff.layout_picker`` at planning time.
    This stub is kept for callers that have not yet migrated.
    """
    return []


def validate(
    plan: dict,
    brand: "BrandPack",
    bag: "DiagnosticBag | None" = None,
    *,
    plan_dir: Path | None = None,
) -> "DiagnosticBag":
    """Static geometry verify typed entry point — returns empty bag (DSL path removed)."""
    from feinschmiede.diagnostics import DiagnosticBag as _Bag
    return bag if bag is not None else _Bag()
