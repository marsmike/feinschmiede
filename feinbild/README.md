# feinbild

Image & 2D for Claude Code — AI image generation (Replicate/Gemini), SVG, and
Excalidraw diagrams behind the clean `feinbild` CLI. Part of the feinschmiede
family; consumes the shared `feinschmiede` engine as a bundled wheel.

```bash
feinbild imagine --prompt "a red bicycle" --out bike.webp
feinbild svg expand chart.svg.dsl --brand feinschliff && feinbild svg render chart.svg
feinbild excalidraw expand flow.exc.dsl && feinbild excalidraw render flow.excalidraw
feinbild verify flow.excalidraw   # structural lint: overflow, overlap, label collision, unrouted arrows
```

`feinbild verify` runs the **shared** `feinschmiede` diagram validator — a
deterministic structural lint of a rendered `.svg`/`.excalidraw` (text overflow,
shape overlap, label
collision, unrouted diagonal arrows, malformed file). Exit 1 on any error-level
defect. Any plugin/skill can call it as a bare command after rendering.

Diagram brand colors resolve through the engine; the launcher adds
`feinbild/brands/` to `FEINSCHLIFF_BRAND_PATH`. Rebuild the offline wheelhouse
with `./build-wheels.sh`.

## Install

```bash
/plugin marketplace add marsmike/feinschmiede   # once per machine
/plugin install feinbild@feinschmiede
```
