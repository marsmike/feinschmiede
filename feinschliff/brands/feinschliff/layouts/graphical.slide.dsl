---
role: data-comparison
ideal_count: [3, 6]
data_band: chart
comparison: true
description: Narrower horizontal bar chart (left-aligned, half-width), four bars with label and percentage; title above, source below
source: feinschliff
source_hash: c3fd47a8ffb3
---
# graphical — companion to bar-chart. Data-comparison slide with 4 bars
# and percent labels; structurally same as bar-chart's left half.
#
# Slot schema:
#   logo, pgmeta, tracker, action_title — header
#   bars         array, 4 objects: { label, value, width 0..100 }
#   source       string, ≤160, opt
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30 "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:160 "{{ action_title }}"

# 4 bars at left half (chart area 100..1100). Right half left for narrative.
text 100,460  style:body  maxwidth:300 maxheight:36 "{{ bars[0].label }}"
rect 420,470  680x40 fill:fog
rect 420,470  {{ bars[0].width*6.8 }}x40 fill:accent
text 1120,460 style:body  maxwidth:160 maxheight:36 "{{ bars[0].value }}"

text 100,564  style:body  maxwidth:300 maxheight:36 "{{ bars[1].label }}"
rect 420,574  680x40 fill:fog
rect 420,574  {{ bars[1].width*6.8 }}x40 fill:accent
text 1120,564 style:body  maxwidth:160 maxheight:36 "{{ bars[1].value }}"

text 100,668  style:body  maxwidth:300 maxheight:36 "{{ bars[2].label }}"
rect 420,678  680x40 fill:fog
rect 420,678  {{ bars[2].width*6.8 }}x40 fill:accent
text 1120,668 style:body  maxwidth:160 maxheight:36 "{{ bars[2].value }}"

text 100,772  style:body  maxwidth:300 maxheight:36 "{{ bars[3].label }}"
rect 420,782  680x40 fill:fog
rect 420,782  {{ bars[3].width*6.8 }}x40 fill:accent
text 1120,772 style:body  maxwidth:160 maxheight:36 "{{ bars[3].value }}"

text 100,940 style:detail maxwidth:1720 "{{ source }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"