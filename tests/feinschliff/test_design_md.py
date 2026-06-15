"""Parser + schema tests for lib/design_md.py."""
from __future__ import annotations

import pytest

from feinschliff.design_md import parse_text


_MIN = """---
name: Test
colors:
  accent: "#abcdef"
---

Body.
"""


def test_minimal_parses():
    dm = parse_text(_MIN)
    assert dm.name == "Test"
    assert dm.colors == {"accent": "#abcdef"}
    assert dm.body.strip() == "Body."


def test_hex_lowercased():
    text = """---
name: T
colors:
  accent: "#ABCDEF"
---
"""
    assert parse_text(text).colors == {"accent": "#abcdef"}


def test_full_frontmatter():
    text = """---
version: alpha
name: Catppuccin Mocha
description: Dark pastel.
colors:
  accent: "#cba6f7"
  ink: "#cdd6f4"
typography:
  inherit: feinschliff
---

## Overview
Mocha.
"""
    dm = parse_text(text)
    assert dm.version == "alpha"
    assert dm.description == "Dark pastel."
    assert dm.inherits_typography_from == "feinschliff"
    assert "## Overview" in dm.body


def test_missing_frontmatter_raises():
    with pytest.raises(ValueError, match="no YAML frontmatter"):
        parse_text("Just markdown body without frontmatter.")


def test_missing_required_name_raises():
    text = """---
colors:
  accent: "#abcdef"
---
"""
    with pytest.raises(ValueError, match="validation failed"):
        parse_text(text)


def test_missing_required_colors_raises():
    text = """---
name: Foo
---
"""
    with pytest.raises(ValueError, match="validation failed"):
        parse_text(text)


def test_bad_hex_raises():
    text = """---
name: Foo
colors:
  accent: "#ggg"
---
"""
    with pytest.raises(ValueError, match="validation failed"):
        parse_text(text)


def test_unknown_top_level_field_raises():
    text = """---
name: Foo
colors:
  accent: "#abcdef"
sneaky: 1
---
"""
    with pytest.raises(ValueError, match="validation failed"):
        parse_text(text)


def test_empty_colors_raises():
    text = """---
name: Foo
colors: {}
---
"""
    with pytest.raises(ValueError, match="validation failed"):
        parse_text(text)


def test_no_typography_field_no_inherit():
    dm = parse_text(_MIN)
    assert dm.inherits_typography_from is None


