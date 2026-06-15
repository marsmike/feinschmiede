# feinschliff/tests/test_pipeline_compile_slide.py
from pathlib import Path

import pytest

from feinschliff.defects import DefectKind
from feinschliff.pipeline import CompileResult, compile_slide


REPO_ROOT = Path(__file__).resolve().parents[2] / "feinschliff"
SAMPLE_LAYOUT = REPO_ROOT / "brands" / "feinschliff" / "layouts" / "executive-summary.slide.dsl"
SAMPLE_BRAND = REPO_ROOT / "brands" / "feinschliff"


def _ctx_for_exec_summary():
    return {
        "title": "Q1 results",
        "subtitle": "What we shipped and what shifted",
        "body": "Three things drove the quarter: shipped, learned, planning.",
    }


def test_compile_slide_returns_primitives_and_empty_defects_on_clean_input(tmp_path):
    result = compile_slide(
        layout_path=SAMPLE_LAYOUT,
        ctx=_ctx_for_exec_summary(),
        brand_dir=SAMPLE_BRAND,
        slide_index=1,
        diagrams_out_dir=tmp_path / "diagrams",
    )
    assert isinstance(result, CompileResult)
    assert result.primitives, "expected primitives for a valid slide"
    assert result.defects == [], f"expected no defects, got {result.defects}"


def _has_render_backend() -> bool:
    """True iff at least one excalidraw render backend is importable.

    `compile_slide()` calls `expand_diagram_blocks()` which renders each
    diagram to PNG. With neither rough+cairosvg nor playwright installed,
    rendering hard-fails before validators run, so this test cannot
    exercise the overflow path.

    Catches a broad exception range because cairosvg raises `OSError`
    (not `ImportError`) when its underlying C library `libcairo` is
    missing — which is the common case in CI.
    """
    try:
        import rough  # noqa: F401
        import cairosvg  # noqa: F401
        return True
    except Exception:
        pass
    try:
        import playwright  # noqa: F401
        return True
    except Exception:
        return False


@pytest.mark.skipif(
    not _has_render_backend(),
    reason="needs rough+cairosvg or playwright to render the diagram before validators run",
)
def test_compile_slide_surfaces_fatal_diagram_overflow(tmp_path):
    # Layout with a 200x100 diagram region and content that won't fit.
    layout = tmp_path / "tiny-diagram.slide.dsl"
    layout.write_text(
        "canvas 1280x720\n"
        "excalidraw diagram 100,100 200x100 {\n"
        "  box bigbox 0,0 600x400 \"way too big\"\n"
        "}\n"
    )
    result = compile_slide(
        layout_path=layout,
        ctx={},
        brand_dir=SAMPLE_BRAND,
        slide_index=4,
        diagrams_out_dir=tmp_path / "diagrams",
    )
    kinds = {d.kind for d in result.defects}
    assert DefectKind.DIAGRAM_OVERFLOW in kinds


def test_pgmeta_slide_counter_stripped(tmp_path):
    """compile_slide must strip a trailing slide counter from pgmeta.

    LLMs occasionally author pgmeta as "Deck Name · 3 / 11" — the renderer
    stamps the slide counter separately as a bottom-right footer, so
    allowing it inside pgmeta produces a duplicate on every slide. The
    pipeline should silently strip the trailing "· NN / TT" pattern so the
    rendered text reads "Deck Name" only.
    """
    result = compile_slide(
        layout_path=SAMPLE_LAYOUT,
        ctx={
            **_ctx_for_exec_summary(),
            "pgmeta": "Cover · 3 / 11",
        },
        brand_dir=SAMPLE_BRAND,
        slide_index=3,
        diagrams_out_dir=tmp_path / "diagrams",
    )
    # Find any text primitive whose label still contains the raw counter.
    counter_labels = [
        n.label for n in result.primitives
        if getattr(n, "label", None) and "3 / 11" in str(n.label)
    ]
    assert counter_labels == [], (
        f"pgmeta slide counter was NOT stripped; found in primitives: {counter_labels}"
    )
    # Also confirm the non-counter part of pgmeta survives.
    pgmeta_labels = [
        n.label for n in result.primitives
        if getattr(n, "label", None) and "Cover" in str(n.label)
    ]
    assert pgmeta_labels, (
        "pgmeta base text 'Cover' missing from primitives after strip — "
        "the strip removed too much"
    )


def test_compile_slide_writes_only_under_diagrams_out_dir(tmp_path, monkeypatch):
    seen_writes: list[Path] = []
    real_write_bytes = Path.write_bytes

    def tracking_write_bytes(self, data, *args, **kwargs):
        seen_writes.append(Path(self))
        return real_write_bytes(self, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_bytes", tracking_write_bytes)

    diagrams_out = tmp_path / "diagrams"
    compile_slide(
        layout_path=SAMPLE_LAYOUT,
        ctx=_ctx_for_exec_summary(),
        brand_dir=SAMPLE_BRAND,
        slide_index=1,
        diagrams_out_dir=diagrams_out,
    )
    diagrams_out_resolved = diagrams_out.resolve()
    for p in seen_writes:
        assert diagrams_out_resolved in p.resolve().parents or p.resolve() == diagrams_out_resolved, (
            f"compile_slide wrote outside diagrams_out_dir: {p}"
        )
