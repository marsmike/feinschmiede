---
role: data-comparison
ideal_count: [3, 5]
data_band: chart
comparison: true
description: Five vertical stacked-bar columns with four series each, value labels in segments, total above, legend right, source below
source: feinschliff
source_hash: 2d324237618b
---
# stacked-bar — 5 periods × 4 series segments. Each bar is a stack of
# (series A bottom + series B + series C + series D top). Total labeled
# above; value labeled in each segment.
#
# Slot schema:
#   logo, pgmeta, tracker, action_title — header
#   periods    array, 5 strings
#   totals     array, 5 strings
#   series     array, 4 objects: { name, delta }
#   values     array, 5 arrays of 4 numbers (per period: [a, b, c, d])
#   source     string, ≤160, opt
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30 "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:50 "{{ action_title }}"

# 5 bars at x=140/420/700/980/1260. Each 200 wide.
# Heights are proportional to totals: scale = 480px / max-total(14.1) ≈ 34.04
# px per unit. All bars bottom-anchored at y=835. Tallest bar (P5, total
# 14.1) stops at y=355 — leaves an 11px clearance below the total-label
# row (y=320..344) so labels never overlap the gold (Series D) cap band.
# Stacking bottom→top: A (ink), B (navy-700), C (navy-500), D (accent).

# Period 1 (total 11.9): A=6.8→231, B=3.2→109, C=1.6→54, D≈0.3→10
text 140,320  style:body color:ink align:center maxwidth:200 maxheight:24 "{{ totals[0] }}"
rect 140,431  200x10  fill:accent
rect 140,441  200x54  fill:navy-500
rect 140,495  200x109 fill:navy-700
rect 140,604  200x231 fill:ink
text 140,456  style:body color:off-white align:center maxwidth:200 maxheight:24 "1.6"
text 140,538  style:body color:off-white align:center maxwidth:200 maxheight:24 "3.2"
text 140,708  style:body color:off-white align:center maxwidth:200 maxheight:24 "6.8"

# Period 2 (12.4): A=6.7→228, B=3.5→119, C=1.7→58, D=0.5→17
text 420,320  style:body color:ink align:center maxwidth:200 maxheight:24 "{{ totals[1] }}"
rect 420,413  200x17  fill:accent
rect 420,430  200x58  fill:navy-500
rect 420,488  200x119 fill:navy-700
rect 420,607  200x228 fill:ink
text 420,447  style:body color:off-white align:center maxwidth:200 maxheight:24 "1.7"
text 420,536  style:body color:off-white align:center maxwidth:200 maxheight:24 "3.5"
text 420,709  style:body color:off-white align:center maxwidth:200 maxheight:24 "6.7"

# Period 3 (12.9): A=6.6→225, B=3.7→126, C=1.8→61, D=0.8→27
text 700,320  style:body color:ink align:center maxwidth:200 maxheight:24 "{{ totals[2] }}"
rect 700,396  200x27  fill:accent
rect 700,423  200x61  fill:navy-500
rect 700,484  200x126 fill:navy-700
rect 700,610  200x225 fill:ink
text 700,442  style:body color:off-white align:center maxwidth:200 maxheight:24 "1.8"
text 700,535  style:body color:off-white align:center maxwidth:200 maxheight:24 "3.7"
text 700,710  style:body color:off-white align:center maxwidth:200 maxheight:24 "6.6"

# Period 4 (13.4): A=6.5→221, B=3.9→133, C=1.9→65, D=1.1→37
text 980,320  style:body color:ink align:center maxwidth:200 maxheight:24 "{{ totals[3] }}"
rect 980,379  200x37  fill:accent
rect 980,416  200x65  fill:navy-500
rect 980,481  200x133 fill:navy-700
rect 980,614  200x221 fill:ink
text 980,386  style:body color:ink        align:center maxwidth:200 maxheight:24 "1.1"
text 980,437  style:body color:off-white align:center maxwidth:200 maxheight:24 "1.9"
text 980,536  style:body color:off-white align:center maxwidth:200 maxheight:24 "3.9"
text 980,712  style:body color:off-white align:center maxwidth:200 maxheight:24 "6.5"

# Period 5 (14.1): A=6.4→218, B=4.2→143, C=2.1→71, D=1.4→48
text 1260,320 style:body color:ink align:center maxwidth:200 maxheight:24 "{{ totals[4] }}"
rect 1260,355 200x48  fill:accent
rect 1260,403 200x71  fill:navy-500
rect 1260,474 200x143 fill:navy-700
rect 1260,617 200x218 fill:ink
text 1260,367 style:body color:ink        align:center maxwidth:200 maxheight:24 "1.4"
text 1260,427 style:body color:off-white align:center maxwidth:200 maxheight:24 "2.1"
text 1260,534 style:body color:off-white align:center maxwidth:200 maxheight:24 "4.2"
text 1260,714 style:body color:off-white align:center maxwidth:200 maxheight:24 "6.4"

# Period labels along x-axis.
text 140,860  style:detail align:center maxwidth:200 "{{ periods[0] }}"
text 420,860  style:detail align:center maxwidth:200 "{{ periods[1] }}"
text 700,860  style:detail align:center maxwidth:200 "{{ periods[2] }}"
text 980,860  style:detail align:center maxwidth:200 "{{ periods[3] }}"
text 1260,860 style:detail align:center maxwidth:200 "{{ periods[4] }}"

# Legend block on right.
text 1540,330 style:h-idx maxwidth:280 maxheight:24 "SEGMENT"
rect 1540,360 16x16 fill:ink
text 1564,360 style:body  maxwidth:240 maxheight:24 "{{ series[0].name }}"
text 1564,380 style:detail color:steel maxwidth:240 maxheight:18 "{{ series[0].delta }}"
rect 1540,430 16x16 fill:navy-700
text 1564,430 style:body  maxwidth:240 maxheight:24 "{{ series[1].name }}"
text 1564,450 style:detail color:steel maxwidth:240 "{{ series[1].delta }}"
rect 1540,500 16x16 fill:navy-500
text 1564,500 style:body  maxwidth:240 maxheight:24 "{{ series[2].name }}"
text 1564,520 style:detail color:steel maxwidth:240 "{{ series[2].delta }}"
rect 1540,570 16x16 fill:accent
text 1564,570 style:body  maxwidth:240 maxheight:24 "{{ series[3].name }}"
text 1564,590 style:detail color:steel maxwidth:240 "{{ series[3].delta }}"

text 100,910 style:detail color:graphite maxwidth:1720 maxheight:30 if:"{{ so_what }}" "So what: {{ so_what }}"

text 100,940 style:detail maxwidth:1720 "{{ source }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"