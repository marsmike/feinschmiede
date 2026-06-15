"""Cover the slotify-time + backfill fixture-derivation flow."""
from __future__ import annotations

from pathlib import Path

import yaml

from feinschliff_builder.decompile.fixtures import derive_fixture, emit_fixture


_DSL_WITH_DEFAULTS = """\
---
role: agenda
slots:
  text_1: {role: page-number, chars: 9, default: '2'}
  text_2: {role: title, chars: 42, default: AGENDA}
  text_3: {role: body, chars: 390, default: "Item one\\nItem two"}
---
canvas 1920x1080
text 144,166 "{{ text_2 | default(\\"AGENDA\\") }}"
"""

_DSL_NO_FRONTMATTER = """\
canvas 1920x1080
text 144,166 "AGENDA"
"""

_DSL_NO_DEFAULTS = """\
---
role: cover
slots:
  text_1: {role: title, chars: 42}
---
canvas 1920x1080
"""


def test_derive_fixture_extracts_slot_defaults():
    fixture = derive_fixture(_DSL_WITH_DEFAULTS)
    assert fixture == {
        "text_1": "2",
        "text_2": "AGENDA",
        "text_3": "Item one\nItem two",
    }


def test_derive_fixture_preserves_slot_order():
    fixture = derive_fixture(_DSL_WITH_DEFAULTS)
    assert list(fixture) == ["text_1", "text_2", "text_3"]


def test_derive_fixture_returns_empty_without_frontmatter():
    assert derive_fixture(_DSL_NO_FRONTMATTER) == {}


def test_derive_fixture_skips_slots_without_default():
    assert derive_fixture(_DSL_NO_DEFAULTS) == {}


def test_emit_fixture_writes_yaml_next_to_layout(tmp_path: Path):
    dsl = tmp_path / "agenda.slide.dsl"
    dsl.write_text(_DSL_WITH_DEFAULTS)
    fixtures = tmp_path / "tests" / "fixtures" / "layouts"

    written = emit_fixture(dsl, fixtures)

    assert written == fixtures / "agenda.yaml"
    loaded = yaml.safe_load(written.read_text())
    assert loaded == {
        "text_1": "2",
        "text_2": "AGENDA",
        "text_3": "Item one\nItem two",
    }


def test_emit_fixture_returns_none_when_no_defaults(tmp_path: Path):
    dsl = tmp_path / "cover.slide.dsl"
    dsl.write_text(_DSL_NO_DEFAULTS)
    fixtures = tmp_path / "tests" / "fixtures" / "layouts"

    assert emit_fixture(dsl, fixtures) is None
    assert not fixtures.exists()
