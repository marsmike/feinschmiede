---
role: data-comparison
ideal_count: [4, 4]
data_band: table
comparison: true
description: Four-quadrant 2×2 grid with axis labels, accent fill on priority cell; title above, legend text right
source: feinschliff
source_hash: 2973dace1625
---
# 2x2-matrix — classic prioritisation grid with axis labels and one focus
# cell flagged. Cells in reading order: TL, TR, BL, BR.
#
# Slot schema (data-slots from feinschliff-2026.html · 19):
#   logo          string, optional
#   pgmeta        string, ≤40, opt
#   tracker       string, ≤60, opt
#   kicker        string, ≤40, opt
#   action_title  string, ≤180
#   x_axis_label  string, ≤30
#   y_axis_label  string, ≤30
#   cells         array, 4 objects (TL, TR, BL, BR):
#       tag       string, ≤40
#       heading   string, ≤80
#       body      string, ≤140
#       focus     bool, optional
#   legend_title  string, ≤40, opt
#   legend_body   string, ≤240, opt
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

# Title block.
rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30 "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:160 "{{ action_title }}"

# 2x2 grid spanning columns 200..1160; y axis on the left, x axis at the
# bottom. Canonical baseline puts the focus cell at the TOP-LEFT position
# (cells[0]); we honour that by giving cells[0] the accent fill.
# y-axis label rotated -90° so it reads bottom-to-top alongside the
# grid's left edge. Pre-rotation rect is 140×24 centered at (180,700):
# x=110 → 250, y=688 → 712; rotation pivots around the center, putting
# the visible vertical label at x≈180 spanning y≈630..770 — aligned
# with the grid's vertical midpoint (y=700).
text 110,688 style:tracker maxwidth:140 maxheight:24 align:center rotate:-90 "{{ y_axis_label }}"

rect 200,460 480x240 fill:accent
text 220,490 style:h-idx color:ink maxwidth:440                "{{ cells[0].tag }}"
text 220,530 style:h-hd  color:ink maxwidth:440 maxheight:80    "{{ cells[0].heading }}"
text 220,620 style:body  color:ink maxwidth:440 maxheight:80    "{{ cells[0].body }}"

rect 680,460 480x240 fill:paper stroke:fog
text 700,490 style:h-idx maxwidth:440                  "{{ cells[1].tag }}"
text 700,530 style:h-hd  maxwidth:440 maxheight:80     "{{ cells[1].heading }}"
text 700,620 style:body  maxwidth:440 maxheight:80     "{{ cells[1].body }}"

rect 200,700 480x240 fill:paper stroke:fog
text 220,730 style:h-idx maxwidth:440                  "{{ cells[2].tag }}"
text 220,770 style:h-hd  maxwidth:440 maxheight:80     "{{ cells[2].heading }}"
text 220,860 style:body  maxwidth:440 maxheight:80     "{{ cells[2].body }}"

rect 680,700 480x240 fill:paper stroke:fog
text 700,730 style:h-idx maxwidth:440                  "{{ cells[3].tag }}"
text 700,770 style:h-hd  maxwidth:440 maxheight:80     "{{ cells[3].heading }}"
text 700,860 style:body  maxwidth:440 maxheight:80     "{{ cells[3].body }}"

# x axis label below the grid, centered across both columns.
text 200,960 style:tracker maxwidth:960 align:center "{{ x_axis_label }}"

# Legend on right (starts after the grid).
text 1240,470 style:h-hd  maxwidth:580 maxheight:60   "{{ legend_title }}"
rect 1240,540 80x2 fill:ink
text 1240,560 style:body  maxwidth:580 maxheight:240  "{{ legend_body }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"