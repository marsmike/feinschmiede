---
role: content-columns
ideal_count: [3, 3]
data_band: none
comparison: true
description: 'Three equal columns with hairline dividers: numbered heading and descriptive body paragraph each; headline above'
source: feinschliff
source_hash: 6f2aa315d0ff
---
# three-column — three parallel pillars. Stacked text in three columns
# without card bg (unlike two-column-cards).
#
# Slot schema (data-slots from feinschliff-2026.html · 09):
#   logo     string, optional
#   pgmeta   string, ≤40, opt
#   eyebrow  string, ≤60, opt
#   title    string, ≤80
#   columns  array, 3 objects:
#       counter  string, ≤10
#       heading  string, ≤40
#       body     string, ≤140
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

# Title block.
rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1700 maxheight:30 "{{ eyebrow }}"
text 100,260 style:title   maxwidth:1700 maxheight:160 "{{ title }}"

# Three columns, each ~538w with 48px gap, no card bg.
text 100,500  style:col-num   maxwidth:498 maxheight:24                "{{ columns[0].counter }}"
text 100,540  style:col-title maxwidth:498 maxheight:130               "{{ columns[0].heading }}"
text 100,680  style:col-body  maxwidth:498 maxheight:200               "{{ columns[0].body }}"

text 690,500  style:col-num   maxwidth:498 maxheight:24                "{{ columns[1].counter }}"
text 690,540  style:col-title maxwidth:498 maxheight:130               "{{ columns[1].heading }}"
text 690,680  style:col-body  maxwidth:498 maxheight:200               "{{ columns[1].body }}"

text 1280,500 style:col-num   maxwidth:498 maxheight:24                "{{ columns[2].counter }}"
text 1280,540 style:col-title maxwidth:498 maxheight:130               "{{ columns[2].heading }}"
text 1280,680 style:col-body  maxwidth:498 maxheight:200               "{{ columns[2].body }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"