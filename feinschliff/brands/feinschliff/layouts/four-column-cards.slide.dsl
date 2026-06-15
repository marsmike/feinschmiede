---
role: content-columns
ideal_count: [4, 4]
data_band: none
comparison: false
description: 'Four equal-width cards in a row: each has accent label, bold lead sentence, and supporting detail; no images'
source: feinschliff
source_hash: 15d698792de5
---
# four-column-cards — quarterly/phased plan across 4 equal cards.
#
# Slot schema (data-slots from feinschliff-2026.html · 10):
#   logo      string, optional
#   pgmeta    string, ≤40, opt
#   eyebrow   string, ≤60, opt
#   title     string, ≤80
#   quarters  array, 4 objects:
#       counter  string, ≤20  (e.g. "Q1 · Plan")
#       heading  string, ≤120
#       body     string, ≤80
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

# Title block.
rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1700 maxheight:30 "{{ eyebrow }}"
text 100,260 style:title   maxwidth:1700 maxheight:160 "{{ title }}"

# Four cards, each ~394w with 48px gap.
card-q x:100  y:460 w:394 h:480 counter:"{{ quarters[0].counter }}" heading:"{{ quarters[0].heading }}" body:"{{ quarters[0].body }}"
card-q x:542  y:460 w:394 h:480 counter:"{{ quarters[1].counter }}" heading:"{{ quarters[1].heading }}" body:"{{ quarters[1].body }}"
card-q x:984  y:460 w:394 h:480 counter:"{{ quarters[2].counter }}" heading:"{{ quarters[2].heading }}" body:"{{ quarters[2].body }}"
card-q x:1426 y:460 w:394 h:480 counter:"{{ quarters[3].counter }}" heading:"{{ quarters[3].heading }}" body:"{{ quarters[3].body }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"