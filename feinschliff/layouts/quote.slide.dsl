---
role: quote
ideal_count: [1, 1]
data_band: none
comparison: false
description: Full-bleed accent background, oversized pull-quote centered lower-left with rule above; attribution line below quote
source: feinschliff
source_hash: 23c24e2f9499
---
# quote — single verbatim quote on the accent (gold) ground.
# Block is vertically centered: rule, 40px gap, big light quote, 48px gap,
# mono-caps attribution.
#
# Slot schema (data-slots from feinschliff-2026.html · 15):
#   logo         string, optional   Brand wordmark (default supplied by brand pack).
#   pgmeta       string, ≤40, opt   Top-right meta line (e.g. "Voice").
#   quote        string, ≤240       Verbatim quote (~40 words max).
#   attribution  string, ≤80, opt   Source / author attribution.
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

# Full-bleed accent background.
rect 0,0 1920x1080 fill:accent

# Header chrome (brand-supplied wordmark + pgmeta).
header pgmeta:"{{ pgmeta }}"

# Vertically-centered content block. Canonical .rule on .slide.orange is
# 80×4 ink (navy). Quote follows ~40px below; attribution ~48px below that.
rect 100,400 80x4 fill:ink

# Big quote — display light at 84px (style:quote).
text 100,460 style:quote maxwidth:1400 maxheight:340 "{{ quote }}"

# Attribution — mono caps, dimmed by the .slide.orange override (still ink).
text 100,840 style:quote-attr maxwidth:1400 maxheight:40 "{{ attribution }}"

# Footer (brand-supplied).
footer left:"{{ footer_left }}" right:"{{ footer_right }}"