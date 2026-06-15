---
role: data-comparison
ideal_count: [3, 6]
data_band: chart
comparison: true
description: Horizontal bar chart on left two-thirds, large photo filling right third; title and source line above chart
source: feinschliff
source_hash: 260d8f47f7e1
---
# chart-photo — bar chart on the left half + hero photo on the right half.
# Best for data narratives with human/scene context.
#
# Slot schema:
#   logo, pgmeta — header
#   eyebrow       string, ≤60, opt
#   title         string, ≤120               Headline, left-half max width.
#   caption       string, ≤120, opt          Caption beneath the chart.
#   chart         object:
#     kind        "bar" | "line"             v1 implements bar; line deferred.
#     series      array, 3–5 objects:
#       label     string, ≤20               Category label (left of bar).
#       value     string, ≤10              Display value (right of bar, e.g. "211").
#       pct       number, 0–100            Bar fill as percent of chart width.
#   image         string, path               Hero photo, right half full height.
# Deck-level: footer_left, footer_right.
#
# Geometry (1920×1080 canvas):
#   Left half : x=100, width=880 (content column)
#   Right half: x=1000, width=820, y=100, height=880 (inside chrome)
#   Header    : y=0–160
#   Title block: rule y=200, eyebrow y=240, title y=280 (maxheight 100)
#   Chart area : y=400–850; labels x=100 (w=180), bars x=300 (w≤520), values x=830 (w=140)
#   5 bar rows : row-height=88px; bar rect height=36px; row y-offsets 400, 488, 576, 664, 752
#   Bar scale  : pct × 5.2 → pixels (520px total bar range = 100%)
#   Caption    : y=872 (detail style, opt)
#   Footer     : y=1000
#
# Note: line chart variant deferred — the DSL has no arithmetic over polyline
# coordinates relative to series data. Bar is authoritative in v1.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

# Right column: hero photo (full content height, right half).
picture 1000,100 820x880 path:{{ image }} query:{{ image_query }} cover:true

# ── Left column: title block ────────────────────────────────────────────────
rect 100,200 80x4 fill:ink
text 100,240 style:eyebrow maxwidth:880 maxheight:22 if:"{{ eyebrow }}" "{{ eyebrow }}"
text 100,280 style:title   maxwidth:880 maxheight:100 "{{ title }}"

# ── Chart: labels (x=100), bg track (x=300, w=520), fill bar, value (x=830) ──
# Bar scale: pct × 5.2 px (520px range = 100%)

# ── Row 1 ───────────────────────────────────────────────────────────────────
text 100,404  style:body  maxwidth:180 maxheight:36 if:"{{ chart.series[0].label }}" "{{ chart.series[0].label }}"
rect 300,410  520x36 fill:fog if:"{{ chart.series[0].label }}"
rect 300,410  {{ chart.series[0].pct*5.2 }}x36 fill:accent if:"{{ chart.series[0].label }}"
text 830,404  style:body  maxwidth:140 maxheight:36 if:"{{ chart.series[0].label }}" "{{ chart.series[0].value }}"

# ── Row 2 ───────────────────────────────────────────────────────────────────
text 100,492  style:body  maxwidth:180 maxheight:36 if:"{{ chart.series[1].label }}" "{{ chart.series[1].label }}"
rect 300,498  520x36 fill:fog if:"{{ chart.series[1].label }}"
rect 300,498  {{ chart.series[1].pct*5.2 }}x36 fill:accent if:"{{ chart.series[1].label }}"
text 830,492  style:body  maxwidth:140 maxheight:36 if:"{{ chart.series[1].label }}" "{{ chart.series[1].value }}"

# ── Row 3 ───────────────────────────────────────────────────────────────────
text 100,580  style:body  maxwidth:180 maxheight:36 if:"{{ chart.series[2].label }}" "{{ chart.series[2].label }}"
rect 300,586  520x36 fill:fog if:"{{ chart.series[2].label }}"
rect 300,586  {{ chart.series[2].pct*5.2 }}x36 fill:accent if:"{{ chart.series[2].label }}"
text 830,580  style:body  maxwidth:140 maxheight:36 if:"{{ chart.series[2].label }}" "{{ chart.series[2].value }}"

# ── Row 4 (optional) ────────────────────────────────────────────────────────
text 100,668  style:body  maxwidth:180 maxheight:36 if:"{{ chart.series[3].label }}" "{{ chart.series[3].label }}"
rect 300,674  520x36 fill:fog if:"{{ chart.series[3].label }}"
rect 300,674  {{ chart.series[3].pct*5.2 }}x36 fill:accent if:"{{ chart.series[3].label }}"
text 830,668  style:body  maxwidth:140 maxheight:36 if:"{{ chart.series[3].label }}" "{{ chart.series[3].value }}"

# ── Row 5 (optional) ────────────────────────────────────────────────────────
text 100,756  style:body  maxwidth:180 maxheight:36 if:"{{ chart.series[4].label }}" "{{ chart.series[4].label }}"
rect 300,762  520x36 fill:fog if:"{{ chart.series[4].label }}"
rect 300,762  {{ chart.series[4].pct*5.2 }}x36 fill:accent if:"{{ chart.series[4].label }}"
text 830,756  style:body  maxwidth:140 maxheight:36 if:"{{ chart.series[4].label }}" "{{ chart.series[4].value }}"

# ── Caption ─────────────────────────────────────────────────────────────────
text 100,820 style:detail color:graphite maxwidth:880 maxheight:30 if:"{{ caption }}" "{{ caption }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"