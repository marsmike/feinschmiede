---
role: reference
ideal_count: [1, 4]
data_band: none
comparison: false
description: 'Brand component sampler: button variants left, tag chips below, rule styles and dimensions catalogued right'
source: feinschliff
source_hash: 38d7c60e8576
---
# components-showcase — UI kit preview. Two paper-bg panels:
#   left   BUTTONS (3 variants: primary, default, ghost) + TAGS (4 chips)
#   right  RULES (3 rule variants: section 56×1 ink, emphasis 80×4 accent,
#                  hairline width-1 fog) with mono labels
#
# Slot schema:
#   logo, pgmeta, tracker, action_title — header
#   button_labels  array, 3 strings — primary / default / ghost
#   chips          array, 4 strings (with optional .style: primary|default|tinted|ghost)
#   accent_note    string — one-line explanation
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30 "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:80 "{{ action_title }}"

# ===== Left panel: Buttons + Tags =====
rect 100,440  820x520 fill:paper
text 140,470  style:h-idx maxwidth:740 maxheight:24 "BUTTONS"

# Primary (accent fill).
rect 140,510  240x60 fill:accent stroke:accent stroke-width:2
text 160,528  style:btn color:ink maxwidth:200 maxheight:32 "{{ button_labels[0] }}"
# Default (ink fill, light text).
rect 400,510  240x60 fill:ink stroke:ink stroke-width:2
text 420,528  style:btn color:off-white maxwidth:200 maxheight:32 "{{ button_labels[1] }}"
# Ghost (paper fill, ink border).
rect 660,510  240x60 fill:paper stroke:ink stroke-width:2
text 680,528  style:btn color:ink maxwidth:200 maxheight:32 "{{ button_labels[2] }}"

# Tags row.
text 140,610  style:h-idx maxwidth:740 maxheight:24 "TAGS"
rect 140,650  180x50 fill:ink stroke:ink stroke-width:1
text 160,664  style:chip color:off-white maxwidth:140 maxheight:24 "{{ chips[0] }}"
rect 340,650  180x50 fill:accent stroke:accent stroke-width:1
text 360,664  style:chip color:ink maxwidth:140 maxheight:24 "{{ chips[1] }}"
rect 540,650  140x50 fill:accent-hover stroke:accent-hover stroke-width:1
text 560,664  style:chip color:ink maxwidth:100 maxheight:24 "{{ chips[2] }}"
rect 700,650  180x50 fill:paper stroke:ink stroke-width:1
text 720,664  style:chip color:ink maxwidth:140 maxheight:24 "{{ chips[3] }}"

# ===== Right panel: Rules =====
rect 1000,440 820x520 fill:paper
text 1040,470 style:h-idx maxwidth:740 maxheight:24 "RULES"

# Section rule (56×1 ink) + mono label.
rect 1040,540 56x1 fill:ink
text 1040,560 style:detail maxwidth:740 maxheight:24 "SECTION · 56 × 1 · INK"

# Emphasis rule (80×4 accent) + mono label.
rect 1040,640 80x4 fill:accent
text 1040,660 style:detail maxwidth:740 maxheight:24 "EMPHASIS · 80 × 4 · ORANGE"

# Hairline (full-width fog) + mono label.
rect 1040,760 740x1 fill:fog
text 1040,780 style:detail maxwidth:740 maxheight:24 "HAIRLINE · WIDTH × 1 · FOG"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"