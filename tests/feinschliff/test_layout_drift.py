"""Regression for `load_profile` drift detection — when a layout's body
is edited after slotify wrote its frontmatter, the recorded
`source_hash` no longer matches the body's actual SHA. Emit a warning
so the operator notices and re-runs slotify; suppressible via env.
"""
from __future__ import annotations

import hashlib

from feinschliff.layout_profile import load_profile


_BODY = (
    "canvas 1920x1080\n"
    "text 132,223 style:title-l \"{{ text_1 | default(\\\"HELLO\\\") }}\"\n"
)
# load_profile hashes body.strip() so split_frontmatter's
# line-preservation padding (leading) + trailing newlines don't trip drift.
_HASH = hashlib.sha1(_BODY.strip().encode("utf-8")).hexdigest()[:12]


_FRONTMATTER = (
    "role: title-primary\n"
    "ideal_count: [1, 2]\n"
    "data_band: none\n"
    "comparison: false\n"
    "source: testpack\n"
    "source_hash: {hash}\n"
)


def _write_layout(path, body, frontmatter_hash):
    path.write_text("---\n" + _FRONTMATTER.format(hash=frontmatter_hash)
                    + "---\n" + body, encoding="utf-8")


def test_matching_hash_is_silent(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("FEINSCHLIFF_QUIET_LAYOUT_DRIFT", raising=False)
    p = tmp_path / "ok.slide.dsl"
    _write_layout(p, _BODY, _HASH)
    profile = load_profile(p)
    out = capsys.readouterr().err
    assert "layout-drift" not in out
    assert profile["source"] == "testpack"
    assert profile["source_hash"] == _HASH


def test_mismatched_hash_warns(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("FEINSCHLIFF_QUIET_LAYOUT_DRIFT", raising=False)
    p = tmp_path / "drifted.slide.dsl"
    _write_layout(p, _BODY + "text 0,0 \"extra\"\n", _HASH)
    load_profile(p)
    out = capsys.readouterr().err
    assert "layout-drift" in out
    assert _HASH in out


def test_drift_warn_suppressed_by_env(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FEINSCHLIFF_QUIET_LAYOUT_DRIFT", "1")
    p = tmp_path / "drifted.slide.dsl"
    _write_layout(p, _BODY + "text 0,0 \"extra\"\n", _HASH)
    load_profile(p)
    out = capsys.readouterr().err
    assert "layout-drift" not in out
