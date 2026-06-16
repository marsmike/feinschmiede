# Layout decision table

Match content shape to layout. Every layout's placeholder schema is in the brand's `layouts.yaml` — reference that for the actual `idx` values when composing a `FillPlan`. Layout names below come from the corporate / gallery packs we ship; brand packs may differ in naming, so always check the catalog for the live list.

| Intent | Layout | Notes |
|---|---|---|
| Cover with image | `Title Slide 3` | idx 2 = PICTURE placeholder. Title renders as small caption on the photo — keep ≤30 chars |
| Cover, text-only | `Title Slide 1` (orange) / `Title Slide 2` (black) | Hero typography on solid brand background |
| Chapter divider | `Beginning of New Chapter 1` | Hero typography, fills the slide. Title ≤30 chars; subtitle line wraps cleanly |
| Chapter with image | `Beginning of New Chapter 2` | idx 2 = PICTURE. Title overlays the photo — keep very short |
| Hero stat reveal | `Beginning of New Chapter 1` | Number in idx 0, descriptor in idx 1. The chapter layout's typography is the hero treatment |
| Section heading (small) | `Only Title` | Small section break only — not a hero slot |
| 2 / 3 / 4 columns of content | `Title and N Contents` | `idx 1..N` are OBJECT slots. **4 Contents is a 2×2 grid**, not 1×4 horizontal |
| Body + photo | `Text and Picture` (text left) / `Picture and Text` (image left) | idx 2 (or 1) = PICTURE |
| Single image, captioned | `Title and Picture` | idx 1 = PICTURE; title is a small caption above |
| Chart or table | `Title + Graphical Content + Text` | OBJECT at idx 1 — chart replaces it; theme colors auto-apply |
| Bespoke (timeline / funnel / infographic) | clone from `snippets.yaml` | layout-fill can't express |
| Closing | `End Slide` | Hero typography — keep title to 1-3 words ("Thank you", "The future is here") |

## Typography budgets

Slot typography varies by layout. Approximate character budgets at which text starts wrapping:

| Layout | Title slot | Body / subtitle slot |
|---|---|---|
| `Title Slide 1` / `Title Slide 2` | 40 | 60 |
| `Title Slide 3` | 25 (small caption on photo) | 30 |
| `Beginning of New Chapter 1` | 30 | 60 |
| `Beginning of New Chapter 2` | 25 (overlay on photo) | 40 |
| `Title + Graphical Content + Text` | 70 | n/a (OBJECT) |
| `Title and Picture` | 25 (caption above photo) | n/a (PICTURE) |
| `Title and N Contents` | 70 | ~80 per column |
| `Text and Picture` / `Picture and Text` | 70 | 200 |
| `Only Title` | 70 | n/a |
| `End Slide` | 20 (hero, wraps fast) | n/a |

## Per-layout placeholder schema

Read `<brand>/layouts.yaml` for the full schema. Each entry has:

```yaml
- name: Title and 3 Contents
  placeholders:
    - idx: 0
      type: TITLE
      name: Title Placeholder
    - idx: 1
      type: OBJECT
      name: Content Placeholder 1
    # ...
```

A `PICTURE` placeholder accepts a `PictureRef` and inherits the master-authored crop / frame. An `OBJECT` placeholder accepts a `PictureRef`, a `ChartSpec`, or text — the renderer dispatches by type.

## Layout name normalization

Corporate masters may ship layout names with embedded NBSPs or trailing spaces (artifacts of the original PowerPoint authoring). The renderer normalizes whitespace at lookup time, so `FillPlan(layout="Title and Picture")` resolves regardless. The catalog inspector emits clean names — copy them verbatim.
