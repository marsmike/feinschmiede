"""Tests for `feinschliff brand inspect` — flat-pack output (no inheritance)."""
from __future__ import annotations

import json


from feinschliff_builder.cli.main import main


def test_inspect_prints_brand_and_root(capsys):
    """brand inspect prints brand name and root path for a real brand."""
    rc = main(["brand", "inspect", "feinschliff"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "brand: feinschliff" in out
    assert "root:" in out
    # No inheritance line — packs are flat.
    assert "inheritance:" not in out


def test_inspect_no_inheritance_line(capsys):
    """brand inspect never emits an inheritance: line (extends removed)."""
    rc = main(["brand", "inspect", "feinschliff"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "inheritance:" not in out


def test_inspect_unknown_brand_returns_nonzero(capsys):
    """brand inspect with an unknown brand name exits non-zero."""
    rc = main(["brand", "inspect", "no-such-brand-xyzzy"])
    assert rc != 0
