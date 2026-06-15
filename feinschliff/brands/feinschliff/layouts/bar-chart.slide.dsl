---
role: data-comparison
ideal_count: [3, 6]
data_band: chart
comparison: true
description: Full-width horizontal bar chart, four bars with label left and percentage right, accent color for top bar
source: feinschliff
source_hash: f3b818ca8257
---
# bar-chart — horizontal bars showing 4–6 categories sharing one scale.
# Each bar: label (left), bar fill, value (right of bar).
#
# Slot schema (representative — no canonical data-slots; mirrors graphical
# section pattern):
#   logo          string, optional
#   pgmeta        string, ≤40, opt
#   tracker       string, ≤60, opt
#   action_title  string, ≤180
#   bars          array, 3–6 objects:
#       label  string, ≤30
#       value  string (e.g. "62%")
#       width  number 0..100  (percent of chart area for the bar fill)
#   so_what       string, ≤160, opt — LLM-derived takeaway from the data.
#                 Linted for vagueness (see lib.content_validator
#                 _check_so_what_vagueness).
#   source        string, ≤160, opt
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30 "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:160 "{{ action_title }}"

# Chart area: labels at x=100..400, bars at 420..1620, values at 1640..1820.
# 4 rows, 80px each, gap 24.
text 100,460  style:body  maxwidth:300 maxheight:36 "{{ bars[0].label }}"
rect 420,470  1200x40 fill:fog
rect 420,470  {{ bars[0].width*12 }}x40 fill:accent
text 1640,460 style:body  maxwidth:180 maxheight:36 "{{ bars[0].value }}"

text 100,564  style:body  maxwidth:300 maxheight:36 "{{ bars[1].label }}"
rect 420,574  1200x40 fill:fog
rect 420,574  {{ bars[1].width*12 }}x40 fill:accent
text 1640,564 style:body  maxwidth:180 maxheight:36 "{{ bars[1].value }}"

text 100,668  style:body  maxwidth:300 maxheight:36 "{{ bars[2].label }}"
rect 420,678  1200x40 fill:fog
rect 420,678  {{ bars[2].width*12 }}x40 fill:accent
text 1640,668 style:body  maxwidth:180 maxheight:36 "{{ bars[2].value }}"

text 100,772  style:body  maxwidth:300 maxheight:36 "{{ bars[3].label }}"
rect 420,782  1200x40 fill:fog
rect 420,782  {{ bars[3].width*12 }}x40 fill:accent
text 1640,772 style:body  maxwidth:180 maxheight:36 "{{ bars[3].value }}"

text 100,870 style:detail color:graphite maxwidth:1720 maxheight:30 if:"{{ so_what }}" "So what: {{ so_what }}"

text 100,940 style:detail maxwidth:1720 "{{ source }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"