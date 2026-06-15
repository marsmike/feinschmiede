---
role: data-timeline
ideal_count: [3, 9]
data_band: chart
comparison: false
description: 'Waterfall bridge chart: anchor bar left, five floating increment/decrement bars, net bar right; values labeled above each'
source: feinschliff
source_hash: 863bde6940a2
---
# waterfall — bridge chart: 2 anchor totals + 3-7 +/- step deltas.
# Anchors are full-height gold bars; step bars are thin strips at
# progressively rising/falling y to approximate the staircase.
#
# Slot schema (data-slots from feinschliff-2026.html · 20):
#   logo, pgmeta, tracker, kicker, action_title — header
#   bars   array, 3–9 objects: { label, value, kind: total | up | down }
#   source string, ≤160, opt
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30 "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:50 "{{ action_title }}"

# Chart area y=420..900 (480 tall). 7 columns × 240 wide @ 8px gap = 248 stride.
# Chart shifted +20px from the original y=400 baseline so that the
# staircase apex (steps 3/4) value labels at y=316 clear the
# action_title bbox (260..310 at maxheight=50). Bars compress slightly
# (height −20px on each anchor) to preserve the y=900 floor.
# bar[0] anchor (left), bar[1..5] thin steps stairstepping up then down,
# bar[6] anchor (right).

# Anchor 0 (gold full-height).
rect 100,420  240x480 fill:accent
text 100,386  style:h-idx color:ink align:center maxwidth:240 maxheight:24 "{{ bars[0].value }}"
text 100,920  style:detail align:center maxwidth:240 maxheight:24 "{{ bars[0].label }}"

# Step 1 (+0.6 — biggest up, 60 tall).
rect 348,420  240x60 fill:ink
text 348,386  style:h-idx align:center maxwidth:240 maxheight:24 "{{ bars[1].value }}"
text 348,920  style:detail align:center maxwidth:240 maxheight:24 "{{ bars[1].label }}"

# Step 2 (+0.4 — 40 tall, higher start).
rect 596,380  240x40 fill:ink
text 596,346  style:h-idx align:center maxwidth:240 maxheight:24 "{{ bars[2].value }}"
text 596,920  style:detail align:center maxwidth:240 maxheight:24 "{{ bars[2].label }}"

# Step 3 (+0.3 — 30 tall).
rect 844,350  240x30 fill:ink
text 844,316  style:h-idx align:center maxwidth:240 maxheight:24 "{{ bars[3].value }}"
text 844,920  style:detail align:center maxwidth:240 maxheight:24 "{{ bars[3].label }}"

# Step 4 (−0.3 — 30 tall, gray).
rect 1092,350 240x30 fill:steel
text 1092,316 style:h-idx align:center maxwidth:240 maxheight:24 "{{ bars[4].value }}"
text 1092,920 style:detail align:center maxwidth:240 maxheight:24 "{{ bars[4].label }}"

# Step 5 (−0.2 — 20 tall, gray).
rect 1340,380 240x20 fill:steel
text 1340,346 style:h-idx align:center maxwidth:240 maxheight:24 "{{ bars[5].value }}"
text 1340,920 style:detail align:center maxwidth:240 maxheight:24 "{{ bars[5].label }}"

# Anchor 6 (gold full-height, slightly taller than anchor 0).
rect 1588,380 240x520 fill:accent
text 1588,346 style:h-idx color:ink align:center maxwidth:240 maxheight:24 "{{ bars[6].value }}"
text 1588,920 style:detail align:center maxwidth:240 maxheight:24 "{{ bars[6].label }}"

text 100,940 style:detail color:graphite maxwidth:1720 maxheight:30 if:"{{ so_what }}" "So what: {{ so_what }}"

# Source line.
text 100,970 style:detail maxwidth:1720 "{{ source }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"