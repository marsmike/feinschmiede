---
role: closer
ideal_count: [1, 1]
data_band: none
comparison: false
variety_exempt: true
description: Full-bleed accent background, centered jumbo closing phrase with rule above and version line below
source: feinschliff
source_hash: bf053d7efc80
---
# end — closer slide. Centered "Thank you." block on the brand's accent
# (gold) background. Sole "orange" slide in the canonical deck.
#
# Slot schema (data-slots from feinschliff-2026.html · 33):
#   logo      string, optional   Brand wordmark; default supplied by brand pack.
#   pgmeta    string, ≤40, opt   Top-right meta line (e.g. "End · 33 / 33").
#   title     string, ≤30        Display headline (e.g. "Thank you.").
#   footnote  string, ≤80, opt   Deck version tag.
# Deck-level (always available from context): footer_left, footer_right.

canvas 1920x1080
theme feinschliff

# Full-bleed accent (gold) background.
rect 0,0 1920x1080 fill:accent

# Header chrome (brand-supplied wordmark + pgmeta).
header pgmeta:"{{ pgmeta }}"

# Centered end-center block: rule, big title, footnote.
# Block is roughly vertically centered around y=470 on the 1080 canvas.
# Rule is 120×4, centered → x=900.
rect 900,350 120x4 fill:ink

# Big "Thank you." — display-xl (200px) matching the canonical inline override.
text 0,400 style:display-xl align:center maxwidth:1920 maxheight:260 "{{ title }}"

# Footnote (deck version tag) — mono eyebrow, centered.
text 0,720 style:eyebrow align:center maxwidth:1920 maxheight:60 "{{ footnote }}"

# Footer (brand-supplied).
footer left:"{{ footer_left }}" right:"{{ footer_right }}"