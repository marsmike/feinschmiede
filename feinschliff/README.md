# feinschliff

> *Feinschliff* — German for "fine polish." Brand-pluggable design system that
> builds `.pptx` decks from a DSL and per-brand tokens.

[Browse the brand gallery](https://marsmike.github.io/feinschmiede/brands/) — every brand pack rendered against every layout.

## Install

```bash
/plugin marketplace add marsmike/feinschmiede
```

## What it does

Office/decks skills for Claude Code:

- **`/deck`** — create or polish a brand-compliant `.pptx` from a brief or rough
  draft. Generates speaker notes and an annotated handout PDF via `deck book`.

Image/2D, video, and audio live in sibling plugins: **feinbild** (`/imagine`,
`/svg`, `/excalidraw`), **feinschnitt** (`/video`, `/record`), and **feinklang**
(`/tts`).

Three CLI subcommands (`feinschliff <subcommand>`):

| Subcommand | What it does |
|---|---|
| `build` | Expand a single `.slide.dsl` into a `.pptx` |
| `deck` | Multi-slide composer with layout picker + speaker notes |
| `ship` | One-command build + verify + verify-quality with a single verdict |

## Quick start

```bash
# Claude Code skill
/deck "Q1 update: 12 launches, 3 customers, $4.2M ARR"

# Pick a different theme (built in — no extra install)
/deck --theme nord "..."
/deck --theme catppuccin-macchiato "..."

# Standalone CLI (no Claude Code required)
feinschliff build layouts/quote.slide.dsl \
  --brand feinschliff --content tests/fixtures/layouts/quote.yaml -o out.pptx
```

## Brand packs (1 ships in the box, with 8 themes)

| Pack | Themes | Description | License |
|---|---|---|---|
| `feinschliff` | `default`, `claude`, `catppuccin-latte`, `catppuccin-macchiato`, `feinschliff-dark`, `gruvbox-dark`, `nord`, `solarized-dark` | Navy ramp + warm paper + single gold accent. Bauhaus register | MIT |

Additional brands are available as separate plugins:

- **[feinschliff-extra](https://github.com/marsmike/feinschmiede)** — 5 more brand packs
  (MS-gallery ports, bespoke school pack).
- **[feinschliff-builder](https://github.com/marsmike/feinschmiede)** — authoring toolkit
  to compile HTML to DSL, decompile existing PPTX files, and verify brand quality.
- **[feinbild](https://github.com/marsmike/feinschmiede)** — image & 2D: AI images
  (Replicate / Gemini), SVG, and Excalidraw diagrams (`/imagine`, `/svg`, `/excalidraw`
  moved here from feinschliff).

## 50 shared layouts

The toolkit ships 50 layout templates covering title slides, chapter dividers,
content grids, charts, diagrams, and more. Every layout renders with any brand pack.
Brand packs can add or override layouts in their own `layouts/` directory.

## Documentation

- [`docs/brand-pack-contract.md`](docs/brand-pack-contract.md) — brand-pack specification

## License

MIT — see repo root [`LICENSE`](../LICENSE). Third-party attribution: [`NOTICE.md`](../NOTICE.md).
