---
role: data-quantity
ideal_count: [2, 3]
data_band: kpi
comparison: false
description: Two stacked jumbo KPIs with label left half; large photo right half; eyebrow and title above KPIs
source: feinschliff
source_hash: a4e01a85d460
---
# kpi-photo — 2–3 KPI rows on the left half + hero photo on the right half.
# Best for metric reveals with human/scene context.
#
# Slot schema:
#   logo, pgmeta — header
#   eyebrow       string, ≤60, opt
#   title         string, ≤120               Headline, left-half max width.
#   kpis          array, 2–3 objects:
#     value       string, ≤10                Big number (may include + / − / %)
#     label       string, ≤80               Descriptive label below value
#   image         string, path               Hero photo, right half full height.
# Deck-level: footer_left, footer_right.
#
# Geometry (1920×1080 canvas):
#   Left half : x=100, width=860 (content column)
#   Right half: x=1000, width=820, y=100, height=880 (inside chrome)
#   Header   : y=0–160
#   Title    : rule y=200, eyebrow y=240, title y=280 (maxheight 160)
#   KPI rows : y=480–960; each row = 160px; accent rule + value + label
#   Footer   : y=1000

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

# Right column: hero photo (full content height, right half).
picture 1000,100 820x880 path:{{ image }} query:{{ image_query }} cover:true

# ── Left column: title block ────────────────────────────────────────────────
rect 100,200 80x4 fill:ink
text 100,240 style:eyebrow maxwidth:860 maxheight:22 if:"{{ eyebrow }}" "{{ eyebrow }}"
text 100,280 style:title   maxwidth:860 maxheight:160 "{{ title }}"

# ── KPI row 1 ───────────────────────────────────────────────────────────────
rect 100,480 860x4 fill:accent
text 100,500 style:kpi-value color:accent maxwidth:860 maxheight:120 "{{ kpis[0].value }}"
text 100,630 style:kpi-key   maxwidth:860 maxheight:30 "{{ kpis[0].label }}"

# ── KPI row 2 ───────────────────────────────────────────────────────────────
rect 100,680 860x4 fill:accent
text 100,700 style:kpi-value color:accent maxwidth:860 maxheight:120 "{{ kpis[1].value }}"
text 100,830 style:kpi-key   maxwidth:860 maxheight:30 "{{ kpis[1].label }}"

# ── KPI row 3 (optional) ────────────────────────────────────────────────────
rect 100,880 860x4 fill:accent if:"{{ kpis[2].value }}"
text 100,900 style:kpi-value color:accent maxwidth:860 maxheight:80 if:"{{ kpis[2].value }}" "{{ kpis[2].value }}"
text 100,990 style:kpi-key   maxwidth:860 maxheight:24 if:"{{ kpis[2].value }}" "{{ kpis[2].label }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"