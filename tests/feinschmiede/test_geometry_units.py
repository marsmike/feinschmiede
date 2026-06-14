"""Unit conversions: baseline constants, derived scales, falsy/invalid fallbacks."""
from feinschmiede.geometry import units


def test_baseline_constants():
    assert units.EMU_PER_PT == 12700.0
    assert units.EMU_PER_PX_BASELINE == 6350.0       # 12_192_000 / 1920
    assert units.PX_TO_PT_BASELINE == 0.5


def test_emu_per_px_derived():
    # corporate-style 12in slide: 10969625 EMU over a 1920px canvas.
    assert abs(units.emu_per_px(10969625, 1920) - 5713.346) < 0.01


def test_emu_per_px_falls_back_to_baseline():
    assert units.emu_per_px(0, 1920) == 6350.0
    assert units.emu_per_px(None, None) == 6350.0
    assert units.emu_per_px(12192000, 0) == 6350.0
    assert units.emu_per_px(-1, 1920) == 6350.0
    assert units.emu_per_px(10969625, -1) == 6350.0


def test_px_to_pt_derived():
    # 12in slide: 0.44987 pt per design-px.
    assert abs(units.px_to_pt_scale(10969625, 1920) - 0.44987) < 1e-4
    assert units.px_to_pt_scale(None, None) == 0.5


def test_font_round_trip():
    scale = units.px_to_pt_scale(10969625, 1920)
    px = units.font_pt_to_px(16.0, scale=scale)
    assert abs(units.font_px_to_pt(px, scale=scale) - 16.0) < 1e-9
    # Legacy default: 1pt = 2 design-px.
    assert units.font_pt_to_px(16.0) == 32.0
    assert units.font_px_to_pt(32.0) == 16.0
