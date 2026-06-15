---
role: content-columns
ideal_count: [3, 3]
data_band: none
comparison: true
description: 'Three equal columns separated by hairlines: numbered heading and three bullets each; title spans full width above'
source: feinschliff
source_hash: e767a0ce49ab
---
# horizontal-bullets — three parallel columns, each with a counter,
# heading, and short bullet stack. Columns separated by vertical fog
# rules. Match the simpler .pptx baseline (standard title block, not the
# HTML showcase's act-head triple).
#
# Slot schema (data-slots from feinschliff-2026.html · 17):
#   logo          string, optional
#   pgmeta        string, ≤40, opt
#   tracker       string, ≤60, opt  (rendered as eyebrow)
#   kicker        string, ≤40, opt  (unused in .pptx baseline)
#   action_title  string, ≤180      (rendered as title)
#   columns       array, 3 objects:
#       counter   string, ≤30
#       heading   string, ≤120
#       bullets   array, 1–5 strings ≤140
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

# Title block.
rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30 "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:80 "{{ action_title }}"

# Three columns with vertical hairlines between them. Each column ~560w.
rect 660,420  1x520 fill:fog
rect 1260,420 1x520 fill:fog

text 100,440  style:h-idx maxwidth:520 maxheight:24  "{{ columns[0].counter }}"
text 100,480  style:h-hd  maxwidth:520 maxheight:80  "{{ columns[0].heading }}"
text 104,600  style:h-li  maxwidth:512 maxheight:36  "• {{ columns[0].bullets[0] }}"
text 104,644  style:h-li  maxwidth:512 maxheight:36  "• {{ columns[0].bullets[1] }}"
text 104,688  style:h-li  maxwidth:512 maxheight:36  "• {{ columns[0].bullets[2] }}"

text 700,440  style:h-idx maxwidth:520 maxheight:24  "{{ columns[1].counter }}"
text 700,480  style:h-hd  maxwidth:520 maxheight:80  "{{ columns[1].heading }}"
text 704,600  style:h-li  maxwidth:512 maxheight:36  "• {{ columns[1].bullets[0] }}"
text 704,644  style:h-li  maxwidth:512 maxheight:36  "• {{ columns[1].bullets[1] }}"
text 704,688  style:h-li  maxwidth:512 maxheight:36  "• {{ columns[1].bullets[2] }}"

text 1300,440 style:h-idx maxwidth:520 maxheight:24  "{{ columns[2].counter }}"
text 1300,480 style:h-hd  maxwidth:520 maxheight:80  "{{ columns[2].heading }}"
text 1304,600 style:h-li  maxwidth:512 maxheight:36  "• {{ columns[2].bullets[0] }}"
text 1304,644 style:h-li  maxwidth:512 maxheight:36  "• {{ columns[2].bullets[1] }}"
text 1304,688 style:h-li  maxwidth:512 maxheight:36  "• {{ columns[2].bullets[2] }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"