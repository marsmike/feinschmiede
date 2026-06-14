---
role: data-timeline
ideal_count: [3, 6]
data_band: table
comparison: false
description: 'Gantt chart: four workstream rows, four quarter columns, milestone bars with diamond markers and a legend strip below'
source: feinschliff
source_hash: 2ca18dcb2e2a
---
# gantt — workstream timeline across 4 quarters with bars and milestones.
# 4 workstream rows × 4 quarter columns; each bar has start/span driving x/width.
#
# Slot schema:
#   logo, pgmeta, tracker, kicker, action_title — header
#   periods      array, 4 strings
#   workstreams  array, 4 objects:
#       name       string (may include \n for owner)
#       start      int 0..3
#       span       int 1..4
#       label      string         (label baked into the bar)
#       color      string token   ("accent" | "ink" | etc.)
#   legend       string, ≤120, opt
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30 "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:80 "{{ action_title }}"

# Column headers — periods.
text 360,400  style:h-idx maxwidth:340  maxheight:24 "{{ periods[0] }}"
text 720,400  style:h-idx maxwidth:340  maxheight:24 "{{ periods[1] }}"
text 1080,400 style:h-idx maxwidth:340  maxheight:24 "{{ periods[2] }}"
text 1440,400 style:h-idx maxwidth:340  maxheight:24 "{{ periods[3] }}"

# Column dividers (vertical, faint fog).
rect 350,440  1x340 fill:fog
rect 710,440  1x340 fill:fog
rect 1070,440 1x340 fill:fog
rect 1430,440 1x340 fill:fog
rect 1790,440 1x340 fill:fog

# Row 1 — Workstream 1, start 0 span 2 (Q1-Q2), accent.
rect 100,440  1720x1 fill:fog
text 100,460  style:h-idx color:accent maxwidth:280 maxheight:24 "WORKSTREAM 1"
text 100,484  style:detail maxwidth:280 maxheight:24             "OWNER · TEAM A"
rect 360,460  720x40 fill:accent
text 380,470  style:detail color:ink maxwidth:680 maxheight:24   "MILESTONE 1"

# Row 2 — Workstream 2, start 0 span 3 (Q1-Q3), ink.
rect 100,520  1720x1 fill:fog
text 100,540  style:h-idx color:accent maxwidth:280 maxheight:24 "WORKSTREAM 2"
text 100,564  style:detail maxwidth:280 maxheight:24             "OWNER · TEAM B"
rect 360,540  720x40 fill:ink
text 380,550  style:detail color:off-white maxwidth:680 maxheight:24 "MILESTONE 2"
# Milestone diamond at Q3 boundary.
shape 1060,548 24x24 kind:diamond fill:accent

# Row 3 — Workstream 3, start 2 span 2 (Q3-Q4), accent.
rect 100,600  1720x1 fill:fog
text 100,620  style:h-idx color:accent maxwidth:280 maxheight:24 "WORKSTREAM 3"
text 100,644  style:detail maxwidth:280 maxheight:24             "OWNER · TEAM C"
rect 1080,620 720x40 fill:accent
text 1100,630 style:detail color:ink maxwidth:680 maxheight:24   "MILESTONE 3"

# Row 4 — Workstream 4, two segments (Q3 preview + Q4 GA).
rect 100,680  1720x1 fill:fog
text 100,700  style:h-idx color:accent maxwidth:280 maxheight:24 "WORKSTREAM 4"
text 100,724  style:detail maxwidth:280 maxheight:24             "OWNER · TEAM D"
rect 1080,700 360x40 fill:ink
text 1100,710 style:detail color:off-white maxwidth:320 maxheight:24 "PREVIEW"
rect 1440,700 360x40 fill:accent
text 1460,710 style:detail color:ink maxwidth:320 maxheight:24   "GA"

# Bottom hairline.
rect 100,760  1720x1 fill:fog

# Legend.
text 100,790  style:detail maxwidth:1720 maxheight:24 "{{ legend }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"