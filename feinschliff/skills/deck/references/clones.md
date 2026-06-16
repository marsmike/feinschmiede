# Cloning bespoke source slides

For timelines, funnels, multi-shape infographics, and other slides whose geometry can't be expressed as a layout-fill, deep-clone a source slide from the brand's `snippets.yaml`.

```python
from feinschliff import ClonePlan
ClonePlan(source_idx=17, replacements=[
    ("Timeline 4", "H1 roadmap"),
    ("Milestone", "Q1 launch"),
    ("date", "Jan 2026"),
])
```

## Read the `anchors` field first

Snippets where queue semantics matter expose an `anchors` map listing every text run with its occurrence count. Example from S17 (Timeline 4):

```yaml
- source_idx: 17
  layout: Only Title
  preview: Timeline 4
  anchors:
    date: 16
    Milestone: 9
    'Milestone ': 7    # trailing-space variant — distinct key
    Timeline 4: 1
    Jan: 1
    Feb: 1
    # ...
```

Use the counts to size the replacements list. To fill the timeline above completely, supply 16 `("date", ...)` entries, 9 `("Milestone", ...)` entries, AND 7 `("Milestone ", ...)` entries for the trailing-space variant. Under-supplying leaves originals in place.

Snippets without repeating runs (titles, body slides) don't get an `anchors` field — the `preview` line is enough to pick whether to clone or not.

## Direct inspection (fallback)

If a snippet doesn't have an `anchors` field but you still want to see its text inventory, inline:

```python
from collections import Counter
from feinschliff.master_template._brand import master_path
from pptx import Presentation
ns = "http://schemas.openxmlformats.org/drawingml/2006/main"
s = Presentation(str(master_path(brand_dir))).slides[N]
texts = [t.text for t in s.shapes._spTree.findall(f".//{{{ns}}}t") if t.text]
print(Counter(texts).most_common(20))
```

## Picking the right snippet

Brand packs vary in how many snippets they ship — six to a hundred. Scan `snippets.yaml`'s `preview` lines to find a candidate; the `layout` field tells you the parent layout (chapter divider, only-title hero, etc.); the `anchors` field tells you which text runs accept replacement.
