# Bootstrap layouts from a source PPTX

`improve-brand` is a polishing loop — it expects layouts to already
exist. When you have a source PPTX and want to bootstrap a pack from
scratch, run the two-step capture pipeline below, then come back here.

## Bootstrap workflow

Requires:
1. `brands/<brand>/tokens.json` — brand palette + style overrides
2. `brands/<brand>/verify-map.yaml` — maps layout names to source slide
   numbers:

   ```yaml
   layouts:
     cover-orange: 5
     timeline-gantt: 22
     table: 52
     # …one entry per layout you want bootstrapped
   ```

3. Source PPTX path

Step 1 — bulk-decompile every layout via the hybrid PPTX+SVG backend:

```bash
feinschliff-builder decompile \
    --brand-pack brands/<brand> \
    --source-pptx path/to/source-deck.pptx
```

Writes one `<layout>.slide.dsl` per `verify-map.yaml` entry, snapshotting
existing files to `layouts.bak/` first. Use `--dry-run` to preview;
`--only <name> <name>` to restrict.

Step 2 — slotify + emit picker frontmatter + `deck-map.yaml`:

```bash
feinschliff-builder slotify \
    --brand-pack brands/<brand>
```

Without step 2 the picker silently drops your layouts because the
profile table builder needs the frontmatter (`role`, `ideal_count`,
`slots`, etc.).

> **Requires dev checkout:** clone the repo and run `uv sync` — both
> scripts need the full dev dependency set (numpy/scikit-image for
> downstream scoring, lxml for the decompiler).

## After bootstrap

```bash
# Measure the first-pass fidelity
python ${CLAUDE_PLUGIN_ROOT}/scripts/brand_verify_loop.py \
    --brand-pack brands/<brand> \
    --source-pptx path/to/source-deck.pptx

# Read the report
cat out/<brand>/verify-loop/diff/report.json

# Drive each above-threshold layout through the improve-brand skill
#    — see ../SKILL.md
```

## What the hybrid decompiler does *not* do

- **No asset extraction by default.** Pictures emit as placeholder slot
  expressions (`picture … path:"{{ image | default:'…' }}" cover:true`).
  Pass `--carry-images` to extract real `<p:pic>` binaries so the verify
  render shows the source photo (struct-diff then measures *chrome*,
  not raster noise).
- **No compound recognition.** Footer-region text emits as N plain
  `text` primitives. If your brand has a `footer(...)` compound,
  manually collapse the lines (or write a brand-specific post-pass).
- **SVG geometry cross-check is internal-only.** The hybrid module
  reserves the SVG path (`pdf_path` arg on `derive()`), but
  `feinschliff-builder decompile` defaults to PPTX-only hybrid mode.
  Programmatic callers can wire `pdf2svg` in for higher fidelity on
  custGeom shapes.

## Tuning the classifier

The pt-to-style classifier (`_style_for`) was empirically tuned
against a representative source deck at 1920×1080. Default thresholds:

| Source pt | DSL style |
| --------- | --------- |
| ≥ 60      | `display` |
| 40–59     | `title`   |
| 28–39     | `title-l` |
| 22–27     | `agenda-t`|
| 18–21     | `sub` (or `body` if multi-paragraph) |
| 13–17     | `body`    |
| ≤ 12      | `body-sm` |

If your brand uses materially different font-size tokens than the
feinschliff baseline (e.g. body at 26px instead of 22px), the
classifier may pick a style whose px size doesn't match the source
visual. Fix by overriding the styles in your brand's
`tokens.json` `style: { body: {...}, body-sm: {...} }` block —
the classifier picks tokens by name; tokens.json controls what those
names render as.
