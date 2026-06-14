---
role: title-primary
ideal_count: [1, 1]
data_band: none
comparison: false
variety_exempt: true
description: 'Full-bleed dark navy cover: rule and eyebrow mid-left, oversized display title below, no image'
source: feinschliff
source_hash: 2036db3d618f
---
# title-ink — opener on the dark ink ground. Gold rule + eyebrow, white
# wordmark + display title.
#
# Slot schema (data-slots from feinschliff-2026.html · 02):
#   logo          string, optional   Brand wordmark (white-on-ink).
#   pgmeta        string, ≤60, opt   Top-right meta line.
#   eyebrow       string, ≤60, opt   Mono kicker above the title.
#   title         string, ≤90        Headline, 1–2 lines (\n for break).
# Deck-level (always present from context): footer_left, footer_right.

canvas 1920x1080
theme feinschliff

rect 0,0 1920x1080 fill:ink

header-dark pgmeta:"{{ pgmeta }}"

# Opener-stack.
# Title stack lifted +60px so the maxheight=400 title bbox bottoms at
# y=960 — clears the y=1000 dark-footer chrome by 40px. Allows 2-line
# display titles on big-display brands (ferrari/binance @ 200px).
rect 100,460 80x4 fill:accent
text 100,520 style:eyebrow color:accent    maxwidth:1700 maxheight:30 "{{ eyebrow }}"
text 100,560 style:display color:off-white maxwidth:1700 maxheight:400 "{{ title }}"

footer-dark left:"{{ footer_left }}" right:"{{ footer_right }}"