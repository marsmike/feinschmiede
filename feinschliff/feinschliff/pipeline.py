# feinschliff/feinschliff/pipeline.py
"""Per-slide compile pipeline — DSL path removed.

The DSL pipeline (compile_slide, expand_compounds, pptx_emit, etc.) has been
deleted as part of the master-template renderer migration. This module is kept
as a compatibility shim for any callers that import CompileResult or the helper
re-exported here, but compile_slide itself is gone.

Use ``feinschliff render-master`` / ``feinschmiede.master_template`` instead.
"""
from __future__ import annotations

import dataclasses
import re
from typing import Any

from feinschliff.defects import Defect


@dataclasses.dataclass(frozen=True)
class CompileResult:
    primitives: list[Any]
    tokens: dict[str, Any]
    canvas: tuple[int, int]
    defects: list[Defect]


# Trailing slide-counter pattern that LLMs sometimes author into pgmeta,
# e.g. "Bahncard 100 · 5 / 11" or "Cover - 3/11". Kept here for any
# surviving callers.
_PGMETA_COUNTER_RE = re.compile(r"\s*[·\-—|]\s*\d{1,3}\s*/\s*\d{1,3}\s*$")
