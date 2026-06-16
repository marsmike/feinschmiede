# feinschliff

> *Feinschliff* — German for "fine polish." A master-template `.pptx`
> renderer for Claude Code: open a brand pack's `master.pptx`, optionally
> overlay a color theme, then fill its layouts (or clone bespoke source
> slides) via a small set of plan dataclasses.

[Browse the brand gallery](https://marsmike.github.io/feinschmiede/brands/) — every brand pack rendered against the master-template kernel.

## Install

```bash
/plugin marketplace add marsmike/feinschmiede
/plugin install feinschliff@feinschmiede
```

System prerequisites and API-key setup live in
[`INSTALLATION.md`](../INSTALLATION.md) at the repo root.

## What it does

Office/decks skill for Claude Code: **`/deck`** turns a brief into a
brand-perfect `.pptx`. Image/2D, video, and audio live in sibling
plugins — feinbild (`/imagine`, `/svg`, `/excalidraw`), feinschnitt
(`/video`, `/record`), feinklang (`/tts`).

There is no `feinschliff` CLI any more — the `bin/feinschliff` launcher
provisions a self-contained venv from bundled wheels and execs Python:

```bash
feinschliff path/to/build.py    # runs `python build.py` in the venv
```

A skill (or a `.debug/<topic>/build.py` script) imports the public
surface and calls `render`:

```python
from feinschliff import FillPlan, ClonePlan, render, apply_theme

render(
    brand_pack=Path("feinschliff/brands/feinschliff"),
    plans=[
        FillPlan("Title Slide", {0: "Q1 update", 1: "12 launches, 3 customers, $4.2M ARR"}),
        FillPlan("Title and Content", {0: "What's new", 1: ["…", "…", "…"]}),
    ],
    out=Path("out.pptx"),
    theme=Path("feinschliff/brands/feinschliff/themes/nord/scheme.json"),
)
```

`FillPlan` fills a layout's placeholders by index; `ClonePlan` deep-copies
a bespoke source slide and patches its text runs. See the deck skill's
[`references/clones.md`](skills/deck/references/clones.md) for the clone
flow and the `catalog` inspector that surfaces every layout + reusable
snippet:

```bash
python -m feinschliff.master_template.catalog feinschliff/brands/feinschliff
```

## Brand packs (6 in-repo, with theme overlays)

| Pack | Themes | Description |
|---|---|---|
| `feinschliff` | `default`, `catppuccin-latte`, `catppuccin-macchiato`, `claude`, `feinschliff-dark`, `gruvbox-dark`, `nord`, `solarized-dark` | Navy ramp + warm paper + single gold accent. Bauhaus register. |
| `annual-review` | — | Editorial register, hero photography, large-figure callouts. |
| `geometric` | — | Hard-edged shape vocabulary, primary palette. |
| `gs-ramspau` | — | Family / community register (high-contrast accent + photography). |
| `scientific` | — | Diagrammatic, axis + grid first, neutral palette. |
| `shapes` | — | Pure shape composition, no photography. |

Themes are `clrScheme` overlays — a single JSON file under
`themes/<name>/scheme.json` patches the master's color slots in memory
at render time, so one `master.pptx` produces N visual variations
without authoring new files. Add a `theme=` argument to `render(...)`
and the catalog colors render against the overlaid palette.

Private corporate brand packs surface via sibling `feinschliff-*`
plugin directories — the launcher auto-discovers their `brands/` and
exports `FEINSCHLIFF_BRAND_PATH` so the public surface picks them up.

## Where the code lives

The master-template kernel is ~500 LOC across six files under
`feinschliff/master_template/`:

- `fill_plan.py` — `FillPlan`, `PictureRef`, `ChartSpec`, the
  layout-fill dispatcher.
- `clone_plan.py` — `ClonePlan` and the deep-clone path.
- `render.py` — open master, optionally apply theme, play the plan
  list, save.
- `theme_overlay.py` — patch `clrScheme` in `theme1.xml` in memory.
- `catalog.py` — emit `layouts` + `snippets` YAML for a brand pack.
- `_brand.py` — shared brand-pack helpers (`master_path`, `norm`,
  `index_layouts`).

## License

MIT — see repo root [`LICENSE`](../LICENSE). Third-party attribution:
[`NOTICE.md`](../NOTICE.md).
