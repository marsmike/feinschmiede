---
role: content-columns
ideal_count: [3, 3]
data_band: none
comparison: false
narrative_act: resolution
description: Three-tier pyramid graphic left; tier labels right in stacked rows with accent eyebrow and description per tier
source: feinschliff
source_hash: 4c616a233930
---
# pyramid — 3 stacked tiers: apex triangle + 2 trapezoids, sized to
# the Cheops Giza ratio (base : height ≈ 230 : 147 ≈ 1.57). A pyramid
# is a low, wide silhouette — earlier 1.33-ratio version read as a
# spire. Center X = 490 (left half of canvas). Each tier is 170 px
# tall; widths step 267 → 533 → 800 px so the slope (133 px inset per
# tier per side) is constant across all three trapezoids and the
# silhouette stays continuous from apex to base.
#
# MSO TRAPEZOID defaults narrow at TOP → no rotation needed.
# adj1 = side_inset / min(w, h). For the constant-slope geometry above:
#   Middle: inset=133, min(533,170)=170 → adj1 = 133/170 = 0.7843
#   Base:   inset=133, min(800,170)=170 → adj1 = 133/170 = 0.7843
#
# Slot schema:
#   logo, pgmeta, tracker, action_title — header
#   tiers — array, 3 objects (top→bottom): label, heading, body
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30 "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:80 "{{ action_title }}"

# ── Pyramid shapes (Cheops-proportioned, base:height ≈ 1.57) ─────────
# Apex: isosceles triangle. Center X=490, half-base=133.5 → left=357.
shape 357,360  267x170 kind:triangle fill:navy-700

# Middle tier: trapezoid (narrow at top by default).
# Top edge 267 (matches apex base), bottom edge 533. Box left=224.
shape 224,530  533x170 kind:trapezoid adj1:0.7843 fill:accent

# Base tier: trapezoid (narrow at top).
# Top edge 533 (matches middle base), bottom edge 800. Box left=90.
shape 90,700   800x170 kind:trapezoid adj1:0.7843 fill:ink

# ── Tier headings centered within each band ───────────────────────────
# Apex text sits in the lower half of the triangle (wider there).
text 357,475  style:body color:off-white align:center maxwidth:267 maxheight:40 "{{ tiers[0].heading }}"
text 224,605  style:body color:ink       align:center maxwidth:533 maxheight:40 "{{ tiers[1].heading }}"
text 90,775   style:body color:off-white align:center maxwidth:800 maxheight:40 "{{ tiers[2].heading }}"

# ── Right column callouts with hairlines (aligned to tier midpoints) ─
rect 1020,340 800x1 fill:fog
text 1020,360 style:h-idx color:accent maxwidth:760 maxheight:24 "{{ tiers[0].label }}"
text 1020,400 style:body  maxwidth:760 maxheight:80              "{{ tiers[0].body }}"

rect 1020,510 800x1 fill:fog
text 1020,530 style:h-idx color:accent maxwidth:760 maxheight:24 "{{ tiers[1].label }}"
text 1020,570 style:body  maxwidth:760 maxheight:80              "{{ tiers[1].body }}"

rect 1020,680 800x1 fill:fog
text 1020,700 style:h-idx color:accent maxwidth:760 maxheight:24 "{{ tiers[2].label }}"
text 1020,740 style:body  maxwidth:760 maxheight:80              "{{ tiers[2].body }}"

rect 1020,870 800x1 fill:fog

footer left:"{{ footer_left }}" right:"{{ footer_right }}"