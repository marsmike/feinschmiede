"""DESIGN.md parser — YAML frontmatter + markdown body, validated against schema.

DESIGN.md is the human-readable companion to a brand pack's
hand-authored ``tokens.json``. Frontmatter carries machine-readable
metadata (name, colors, typography); the markdown body holds the human
rationale (why these colors, how to use them).

This module parses and validates one DESIGN.md file and exposes the
result as a ``DesignMd`` dataclass. ``DesignMd.colors`` and
``DesignMd.typography`` mirror the frontmatter fields for tooling that
wants to compare them against ``tokens.json``.

No bake step exists in v2 — DESIGN.md is read alongside ``tokens.json``,
not used to derive it.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n(.*))?$", re.DOTALL)
_SCHEMA_PATH = Path(__file__).parent / "schemas" / "design-md.schema.json"


@dataclass(frozen=True)
class DesignMd:
    """Parsed DESIGN.md content."""

    name: str
    colors: dict[str, str]
    description: str | None
    version: str | None
    typography: dict | None
    body: str

    @property
    def inherits_typography_from(self) -> str | None:
        """Return base-brand name if frontmatter declares `typography: {inherit: <brand>}`, else None."""
        if not self.typography:
            return None
        return self.typography.get("inherit")


def _load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def parse(path: str | Path) -> DesignMd:
    """Parse DESIGN.md at `path`. Returns a DesignMd or raises ValueError on bad input."""
    text = Path(path).read_text(encoding="utf-8")
    return parse_text(text, source=str(path))


def parse_text(text: str, source: str = "<string>") -> DesignMd:
    m = _FRONTMATTER_RE.match(text)
    if m is None:
        raise ValueError(f"{source}: no YAML frontmatter (expected leading ---)")
    fm_raw, body = m.group(1), (m.group(2) or "")
    try:
        fm = yaml.safe_load(fm_raw)
    except yaml.YAMLError as exc:
        raise ValueError(f"{source}: YAML frontmatter parse error: {exc}") from exc
    if not isinstance(fm, dict):
        raise ValueError(f"{source}: frontmatter must be a mapping")
    validate(fm, source=source)
    # Normalise hex casing — schema accepts either; downstream wants lowercase.
    colors = {k: v.lower() for k, v in fm["colors"].items()}
    return DesignMd(
        name=fm["name"],
        colors=colors,
        description=fm.get("description"),
        version=fm.get("version"),
        typography=fm.get("typography"),
        body=body,
    )


def validate(frontmatter: dict, source: str = "<frontmatter>") -> None:
    """Validate parsed frontmatter against the JSON schema. Raises ValueError on fail."""
    validator = Draft202012Validator(_load_schema())
    errors = sorted(validator.iter_errors(frontmatter), key=lambda e: e.path)
    if not errors:
        return
    parts = [f"{source}: DESIGN.md frontmatter validation failed:"]
    for err in errors:
        loc = ".".join(str(p) for p in err.absolute_path) or "<root>"
        parts.append(f"  - {loc}: {err.message}")
    raise ValueError("\n".join(parts))
