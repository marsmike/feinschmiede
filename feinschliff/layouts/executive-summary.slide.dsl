---
role: content-columns
ideal_count: [3, 5]
data_band: kpi
comparison: false
narrative_act: situation
description: Headline + body paragraph top; two bullet columns (insights left, next steps right) below; three KPI cells across bottom strip
source: feinschliff
source_hash: 31ea38e06fdb
---
# executive-summary — one-page rollup: title + subtitle paragraph,
# 2-column insights/next-steps list, KPI strip at the bottom.
#
# Slot schema (data-slots from feinschliff-2026.html · 26, adapted to the
# .pptx baseline shape):
#   logo          string, optional
#   pgmeta        string, ≤40, opt
#   tracker       string, ≤60, opt   (rendered as eyebrow)
#   kicker        string, ≤40, opt   (unused)
#   action_title  string, ≤180       (rendered as title)
#   summary       string, ≤300       (subtitle paragraph under title)
#   insights      array, 3–5 objects (heading, body)
#   next_steps    array, 3–5 objects (heading, body)
#   kpis          array, 3 objects (value, unit, key)
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

# Title block.
rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30 "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:80 "{{ action_title }}"

# Subtitle paragraph.
text 100,360 style:body maxwidth:1720 maxheight:60 "{{ summary }}"

# Two columns with kicker + hairline + 4 items each.
text 100,500  style:h-idx color:accent maxwidth:800 maxheight:24 "INSIGHTS"
rect 100,530  840x1 fill:fog
shape 100,558 12x12 kind:rect fill:accent
text 124,544  style:h-hd  maxwidth:800 maxheight:40                "{{ insights[0].heading }}"
text 124,584  style:body  maxwidth:800 maxheight:30                "{{ insights[0].body }}"
shape 100,634 12x12 kind:rect fill:accent
text 124,620  style:h-hd  maxwidth:800 maxheight:40                "{{ insights[1].heading }}"
text 124,660  style:body  maxwidth:800 maxheight:30                "{{ insights[1].body }}"
shape 100,710 12x12 kind:rect fill:accent
text 124,696  style:h-hd  maxwidth:800 maxheight:40                "{{ insights[2].heading }}"
text 124,736  style:body  maxwidth:800 maxheight:30                "{{ insights[2].body }}"
shape 100,786 12x12 kind:rect fill:accent
text 124,772  style:h-hd  maxwidth:800 maxheight:40                "{{ insights[3].heading }}"
text 124,812  style:body  maxwidth:800 maxheight:30                "{{ insights[3].body }}"

text 1000,500 style:h-idx color:accent maxwidth:800 maxheight:24 "NEXT STEPS"
rect 1000,530 820x1 fill:fog
shape 1000,558 12x12 kind:rect fill:accent
text 1024,544 style:h-hd  maxwidth:780 maxheight:40                "{{ next_steps[0].heading }}"
text 1024,584 style:body  maxwidth:780 maxheight:30                "{{ next_steps[0].body }}"
shape 1000,634 12x12 kind:rect fill:accent
text 1024,620 style:h-hd  maxwidth:780 maxheight:40                "{{ next_steps[1].heading }}"
text 1024,660 style:body  maxwidth:780 maxheight:30                "{{ next_steps[1].body }}"
shape 1000,710 12x12 kind:rect fill:accent
text 1024,696 style:h-hd  maxwidth:780 maxheight:40                "{{ next_steps[2].heading }}"
text 1024,736 style:body  maxwidth:780 maxheight:30                "{{ next_steps[2].body }}"
shape 1000,786 12x12 kind:rect fill:accent
text 1024,772 style:h-hd  maxwidth:780 maxheight:40                "{{ next_steps[3].heading }}"
text 1024,812 style:body  maxwidth:780 maxheight:30                "{{ next_steps[3].body }}"

# KPI strip — 3 cells across bottom (top hairline + value | label).
# Positioned with 80px buffer to footer (y=1050) so the 120px kpi-value
# style doesn't bleed into the pgmeta line.
rect 100,860 1720x1 fill:fog
rect 660,860 1x80 fill:fog
rect 1220,860 1x80 fill:fog

# kpi-value renders at 120px font (line-height 0.95 ≈ 115px). The old
# maxwidth:240 was too narrow for 4-char values like "+5.1" or "−10.2",
# wrapping them onto a second line that fell past the canvas bottom; the
# old maxheight:80 was also below the actual one-line glyph height under
# the bleed-model textfit. Boxes widened to 320/120, unit pushed to x=400
# (still inside the cell that ends at x=660 / 1220 / 1820 dividers).
text 100,870  style:kpi-value maxwidth:300 maxheight:120 "{{ kpis[0].value }}"
text 400,894  style:kpi-unit  maxwidth:60 maxheight:32 "{{ kpis[0].unit }}"
text 480,894  style:h-idx maxwidth:180 maxheight:24 "{{ kpis[0].key }}"

text 700,870  style:kpi-value maxwidth:300 maxheight:120 "{{ kpis[1].value }}"
text 1000,894 style:kpi-unit  maxwidth:60 maxheight:32 "{{ kpis[1].unit }}"
text 1080,894 style:h-idx maxwidth:140 maxheight:24 "{{ kpis[1].key }}"

text 1260,870 style:kpi-value maxwidth:300 maxheight:120 "{{ kpis[2].value }}"
text 1560,894 style:kpi-unit  maxwidth:60 maxheight:32 "{{ kpis[2].unit }}"
text 1640,894 style:h-idx maxwidth:180 maxheight:24 "{{ kpis[2].key }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"