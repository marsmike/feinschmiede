---
role: content-with-visual
ideal_count: [1, 2]
data_band: none
comparison: false
description: 'Left half: eyebrow, large title, body paragraph, CTA button row; right half: full-height image frame'
source: feinschliff
source_hash: 24714387a52b
---
# text-picture — single feature on the left, hero image on the right.
# Title/body/buttons stacked at left; 780-wide picture column at right.
#
# Slot schema (data-slots from feinschliff-2026.html · 11):
#   logo        string, optional
#   pgmeta      string, ≤40, opt
#   eyebrow     string, ≤60, opt
#   title       string, ≤80               Headline, 1–3 lines.
#   body        string, ≤260              Supporting paragraph.
#   image       string, path              Hero product image.
#   buttons     array, 0–3 objects, opt   Each: { label, style: primary | default | ghost }.
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

# Right column: hero image (placeholder is paper-2 when path empty).
rect 1040,200 780x720 fill:paper-2 stroke:fog
picture 1040,200 780x720 path:{{ image }} query:{{ image_query }} cover:true

# Left column: rule + eyebrow + title + body + buttons.
rect 100,200 80x4 fill:ink
text 100,260 style:eyebrow maxwidth:820 maxheight:30                  "{{ eyebrow }}"
text 100,300 style:huge    maxwidth:820 maxheight:380                 "{{ title }}"
text 100,720 style:body    maxwidth:780 maxheight:140                 "{{ body }}"

# Buttons — canonical case is primary + ghost. Both button shapes AND
# their labels are `if:`-guarded on the corresponding button's `label`
# slot, so an empty `buttons: []` (or a single-button caller) won't
# emit unlabeled boxes that read as broken UI in the rendered slide.
rect 100,888  290x68 fill:accent stroke:accent stroke-width:2                  if:"{{ buttons[0].label }}"
text 132,907  style:btn color:ink   maxwidth:260 maxheight:44                   if:"{{ buttons[0].label }}" "{{ buttons[0].label }}"

rect 410,888  240x68 fill:paper stroke:ink stroke-width:2                       if:"{{ buttons[1].label }}"
text 442,907  style:btn color:ink   maxwidth:200 maxheight:44                   if:"{{ buttons[1].label }}" "{{ buttons[1].label }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"