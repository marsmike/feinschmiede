"""Layout-discovery silent-shadowing warning regression.

`discover_layout_paths` is the picker's universe — first-source-wins by
priority. When a name appears in more than one source, the picker
silently uses the priority winner and the operator has no signal that
the second source was shadowed. Warn once per (name, winner) per
process, suppressible via FEINSCHLIFF_QUIET_LAYOUT_SHADOW.
"""
from __future__ import annotations

from pathlib import Path

from feinschliff import layout_discovery


def _make_layout(d: Path, name: str, body: str = "canvas 1920x1080\n") -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.slide.dsl").write_text(body, encoding="utf-8")


def test_collision_warning_fires_once_per_name(tmp_path, monkeypatch, capsys):
    src1 = tmp_path / "a"
    src2 = tmp_path / "b"
    _make_layout(src1, "cover")
    _make_layout(src2, "cover")  # collision
    _make_layout(src2, "agenda")  # unique to src2 (no collision)

    layout_discovery._WARNED_COLLISIONS.clear()
    monkeypatch.delenv("FEINSCHLIFF_QUIET_LAYOUT_SHADOW", raising=False)
    monkeypatch.setattr(
        layout_discovery,
        "discover_layouts",
        lambda: [
            layout_discovery.LayoutSource(kind="env", path=src1),
            layout_discovery.LayoutSource(kind="env", path=src2),
        ],
    )

    layout_discovery.discover_layout_paths()
    out = capsys.readouterr().err
    assert "'cover'" in out, "should warn on the collision"
    assert "agenda" not in out, "should not warn on the unique name"

    # Second call in the same process: no re-warn for the same key.
    layout_discovery.discover_layout_paths()
    out = capsys.readouterr().err
    assert "'cover'" not in out, "should not re-warn for the same (name, winner) pair"


def test_collision_warning_suppressed_by_env(tmp_path, monkeypatch, capsys):
    src1 = tmp_path / "a"
    src2 = tmp_path / "b"
    _make_layout(src1, "cover")
    _make_layout(src2, "cover")

    layout_discovery._WARNED_COLLISIONS.clear()
    monkeypatch.setenv("FEINSCHLIFF_QUIET_LAYOUT_SHADOW", "1")
    monkeypatch.setattr(
        layout_discovery,
        "discover_layouts",
        lambda: [
            layout_discovery.LayoutSource(kind="env", path=src1),
            layout_discovery.LayoutSource(kind="env", path=src2),
        ],
    )

    layout_discovery.discover_layout_paths()
    out = capsys.readouterr().err
    assert "'cover'" not in out
