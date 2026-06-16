# Common gotchas

## "Only Title" is a section heading, not a hero number

Big stats need `Beginning of New Chapter 1`. Split the number into idx 0, the descriptor into idx 1. `Only Title` renders text small in the title slot and leaves the rest of the slide blank.

## Picture-led layouts crop the title text

`Title Slide 3`, `Beginning of New Chapter 2`, and `Title and Picture` overlay the title as a small caption against a full-bleed photo. Keep title text very short (≤25 chars). Long titles wrap and disappear behind the image.

## Hero typography auto-wraps long titles

`Beginning of New Chapter 1` and `End Slide` use large display type. Titles longer than ~20 characters wrap to two lines, which looks fine for a chapter divider but cramped on the end slide. Keep `End Slide` titles to 1-3 words.

## "Title and 4 Contents" is a 2×2 grid, not 1×4

The four OBJECT slots are arranged top-left → top-right → bottom-left → bottom-right. Compose copy that reads as a quadrant, not a linear sequence.

## Placeholder idx is brand-convention, not type

Always reference `catalog/layouts.yaml`. Don't guess by placeholder name. The same layout in a different brand pack may use different idx assignments.

## Picture stretching

`PictureRef(crop=True)` (the default) center-crops to the placeholder's bbox aspect before insertion. Turn `crop=False` only when you know the source matches the target aspect already.

## Clone replacement queue

`ClonePlan.replacements` is a queue per old-string. Each `(old, new)` entry consumes one occurrence in document order. If you supply 6 replacements for a source slide with 12 occurrences of the same anchor, the other 6 stay as the original.

Watch for variants: `"Milestone"` and `"Milestone "` (trailing space) are different keys. See `references/clones.md` for the inspection recipe.

## Layout name lookups normalize whitespace

Corporate masters often ship layout names with stray NBSPs or trailing spaces (artifacts of the original PowerPoint authoring). The renderer normalizes both at lookup time — `FillPlan(layout="Title and Picture")` resolves regardless. Always copy names verbatim from the catalog.

## Some chapter / header layouts hide under soffice

Layouts that anchor a CENTER_TITLE inside a colored header band (common in corporate brand packs) may not render that title under `soffice --convert-to pdf` even though the renderer fills it correctly — LibreOffice's rendering of a master-authored placeholder can drop the text in PDF while PowerPoint shows it fine. If verify reports a missing title in this kind of layout: open the `.pptx` in actual PowerPoint before assuming the text is missing, or check whether the master exposes a separate BODY placeholder (often named `Chapter_title` or similar) that's the actual heading slot.

## Plan layouts can fail at render time

`render()` raises `KeyError` if a layout name isn't in the master. Validate against `<brand>/layouts.yaml` (or run `python -m feinschliff.master_template.catalog <brand>` for a live listing) before composing if you've been generative about names.
