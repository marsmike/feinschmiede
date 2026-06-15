# Layout picking — `/deck`

Pick directly from `<brand_pack>/layouts.yaml` and
`<brand_pack>/snippets.yaml`. No cascade; no separate manifest. The
catalog files are the manifest.

## The two catalogs

`layouts.yaml` lists every fillable layout in the master:

```yaml
master_theme: default            # optional — theme the master was rendered with
layouts:
  - name: "Title + Graphical Content + Text"
    role: content                # cover | chapter | content | closing | agenda | divider
    placeholders:
      - idx: 0
        type: TITLE
        role: headline
        char_budget: 80
      - idx: 1
        type: OBJECT
        role: body_or_visual
        char_budget: 600
        accepts: [text, chart, picture]
```

`snippets.yaml` lists bespoke source slides that clone losslessly:

```yaml
snippets:
  - id: timeline-12-months
    source_idx: 17
    intent: "12-month roadmap with milestone risers above and below the axis"
  - id: funnel-6-stages
    source_idx: 27
    intent: "6-stage process funnel with icon + caption per stage"
```

## Picking a fill layout

For each slide in `content_plan.json`:

1. **Filter by role** — match the slide's narrative role:
   - opener / cover → `role: cover`
   - chapter divider → `role: chapter`
   - normal content → `role: content`
   - agenda / overview → `role: agenda`
   - closing → `role: closing`
2. **Filter by visual intent** — if the slide carries a chart, picture,
   or diagram, require a placeholder with that type in `accepts`.
3. **Filter by capacity** — match the slide's column count and
   character budget against `char_budget` per placeholder.
4. **Tie-break by specificity** — narrower layouts win (3-column body
   for 3 items, not generic OBJECT for 1).

Output a `FillPlan`:

```yaml
- type: fill
  layout: "Title and 3 Contents"
  fills:
    0: "Three pillars"
    1: ["Pillar A", "Description A"]
    2: ["Pillar B", "Description B"]
    3: ["Pillar C", "Description C"]
```

## Picking a clone snippet

When the content fits a designer-authored composition (timeline,
funnel, multi-shape infographic, ribbon roadmap) and `layouts.yaml`
has nothing comparable, pick a snippet:

1. **Scan `snippets.yaml` by intent** — the `intent` field is
   prose-readable and describes the composition shape.
2. **Inspect the source slide** before composing replacements. Count
   the text-anchor inventory:

   ```python
   from collections import Counter
   from pptx import Presentation
   ns = "http://schemas.openxmlformats.org/drawingml/2006/main"
   src = Presentation("<brand_pack>/master.pptx")
   txt = [t.text for t in src.slides[17].shapes._spTree.findall(f".//{{{ns}}}t") if t.text]
   print(Counter(txt).most_common(10))
   ```

3. **Compose `text_replacements`** as an ordered list of `(old, new)`
   pairs. Repeated `old` strings are consumed in document order:

   ```yaml
   - type: clone
     snippet_id: timeline-12-months
     text_replacements:
       - ["Timeline 4", "H1 2026 — release waves"]
       - ["Milestone date", "Q1 launch"]
       - ["Milestone date", "Q1 GA"]
       - ["Milestone date", "Q2 expansion"]
   ```

The renderer's `<a:t>` XML walk catches grouped + SmartArt text that
the python-pptx shape iterator would miss.

## Image-first heuristic

Default to a picture-bearing layout when the content suits one. Pick a
`text-picture` over a plain `vertical-bullets` if the slide has a
visual angle. The `image_style` field in `deck_brief.yaml` governs
how aggressive this push is — `rich-imagery` means every slide that
can carry an image must; `concept-text` means images are optional.

## Theme overlay

The picker ignores theme. `--theme <name>` at render time recolors the
output via the brand's `themes/<name>/tokens.json`. Pick layouts as if
the default theme is in play; let the recolor pass do the rest.
