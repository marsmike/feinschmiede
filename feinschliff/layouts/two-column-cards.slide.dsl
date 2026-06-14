---
role: content-columns
ideal_count: [2, 2]
data_band: none
comparison: true
description: 'Two wide columns with hairline divider: accent label, bold lead sentence, and supporting detail paragraph each'
source: feinschliff
source_hash: c5525344e486
---
# two-column-cards — paired ideas with parallel weight. Title block + two
# .col.card panels side-by-side.
#
# Slot schema (data-slots from feinschliff-2026.html · 08):
#   logo     string, optional
#   pgmeta   string, ≤40, opt
#   eyebrow  string, ≤60, opt
#   title    string, ≤80
#   columns  array, 2 objects:
#       counter  string, ≤20   (e.g. "01 · Customer")
#       heading  string, ≤120
#       body     string, ≤200
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

# Title block.
rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1700 maxheight:30 "{{ eyebrow }}"
text 100,260 style:title   maxwidth:1700 maxheight:80 "{{ title }}"

# Two cards. Canvas-x available: 1720 (100..1820). Gap 48px. Each card 836w.
card x:100  y:460 w:836 h:480 counter:"{{ columns[0].counter }}" heading:"{{ columns[0].heading }}" body:"{{ columns[0].body }}"
card x:984  y:460 w:836 h:480 counter:"{{ columns[1].counter }}" heading:"{{ columns[1].heading }}" body:"{{ columns[1].body }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"