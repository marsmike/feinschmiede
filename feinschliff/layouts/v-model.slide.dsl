---
role: data-comparison
ideal_count: [3, 5]
data_band: none
comparison: true
description: 'V-model diagram: verification phases cascade left, validation phases mirror right, pivot bar at base; title above'
source: feinschliff
source_hash: d9819edbdab4
---
# v-model — paired verification (left) + validation (right) phases meeting
# at a central pivot. 3–5 pairs in a row stack with central connectors.
#
# Slot schema (data-slots from feinschliff-2026.html · 32):
#   logo          string, optional
#   pgmeta        string, ≤40, opt
#   tracker       string, ≤60, opt
#   kicker        string, ≤40, opt
#   action_title  string, ≤180
#   pairs         array, 3–5 objects:
#       left_counter, left_title, right_counter, right_title, connector (≤40, opt)
#   pivot_title   string, ≤40
#   key           array, 2–4, opt: {k, h, body}
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

mck-head tracker:"{{ tracker }}" kicker:"{{ kicker }}" action_title:"{{ action_title }}"

# Axis labels.
text 100,500  style:tracker maxwidth:340 align:right "Verification Phase"
text 1480,500 style:tracker maxwidth:340             "Validation Phase"

# Diagonal V silhouette — two lines descending toward the pivot at center.
# Left descends from (700, 540) to (920, 900); right from (1220, 540) to
# (1000, 900). The phase / test rows are stair-stepped along these lines.
line 700,540 920,900 stroke:fog stroke-width:1
line 1220,540 1000,900 stroke:fog stroke-width:1

# 4 pair rows stair-step toward the centre — each row indents 80 px and
# drops 80 px so the row pattern traces the V.
# Pair 0 (top, widest spread)
text 100,552  style:h-idx maxwidth:200                "{{ pairs[0].left_counter }}"
text 100,580  style:h-hd  maxwidth:520 maxheight:40   "{{ pairs[0].left_title }}"
text 760,572  style:tracker maxwidth:400 align:center "{{ pairs[0].connector }}"
text 1700,552 style:h-idx maxwidth:120 align:right    "{{ pairs[0].right_counter }}"
text 1300,580 style:h-hd  maxwidth:520 maxheight:40 align:right "{{ pairs[0].right_title }}"

# Pair 1
text 180,632  style:h-idx maxwidth:200                "{{ pairs[1].left_counter }}"
text 180,660  style:h-hd  maxwidth:440 maxheight:40   "{{ pairs[1].left_title }}"
text 760,652  style:tracker maxwidth:400 align:center "{{ pairs[1].connector }}"
text 1620,632 style:h-idx maxwidth:120 align:right    "{{ pairs[1].right_counter }}"
text 1300,660 style:h-hd  maxwidth:440 maxheight:40 align:right "{{ pairs[1].right_title }}"

# Pair 2
text 260,712  style:h-idx maxwidth:200                "{{ pairs[2].left_counter }}"
text 260,740  style:h-hd  maxwidth:360 maxheight:40   "{{ pairs[2].left_title }}"
text 760,732  style:tracker maxwidth:400 align:center "{{ pairs[2].connector }}"
text 1540,712 style:h-idx maxwidth:120 align:right    "{{ pairs[2].right_counter }}"
text 1300,740 style:h-hd  maxwidth:360 maxheight:40 align:right "{{ pairs[2].right_title }}"

# Pair 3 (closest to pivot)
text 340,792  style:h-idx maxwidth:200                "{{ pairs[3].left_counter }}"
text 340,820  style:h-hd  maxwidth:280 maxheight:40   "{{ pairs[3].left_title }}"
text 760,812  style:tracker maxwidth:400 align:center "{{ pairs[3].connector }}"
text 1460,792 style:h-idx maxwidth:120 align:right    "{{ pairs[3].right_counter }}"
text 1300,820 style:h-hd  maxwidth:280 maxheight:40 align:right "{{ pairs[3].right_title }}"

# Pivot at the V apex. Rect raised to 80px so both labels sit inside it
# under the bleed-model textfit: tracker (16px font + 0.12 letter-spacing)
# bled past the old maxheight:22 and printed below the 60px rect bottom.
rect 760,900 400x80 fill:accent
text 760,910 style:h-idx  color:ink align:center maxwidth:400 maxheight:18 "Pivot"
text 760,940 style:tracker color:ink align:center maxwidth:400 maxheight:24 "{{ pivot_title }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"