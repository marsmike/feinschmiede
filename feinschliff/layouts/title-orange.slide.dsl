---
role: title-primary
ideal_count: [1, 1]
data_band: none
comparison: false
variety_exempt: true
description: 'Full-bleed gold/accent cover: rule and eyebrow mid-left, oversized display title below, no image'
source: feinschliff
source_hash: 096cfa663c27
---
# title-orange — opener on the gold ground. Same dark-text chrome as
# `end` and `quote`; differs by carrying a large 1–2 line title.
#
# Slot schema (data-slots from feinschliff-2026.html · 01):
#   logo          string, optional   Brand wordmark (default supplied by brand pack).
#   pgmeta        string, ≤60, opt   Top-right meta line (e.g. deck name + year).
#   eyebrow       string, ≤60, opt   Mono kicker above the title.
#   title         string, ≤90        Headline, 1–2 lines (\n for break).
#   footer_left   string, ≤40, opt   Footer left (date / audience).
#   footer_right  string, ≤40, opt   Footer right (slide counter).
# Note: footer_left/right also appear here per the canonical schema; on
# layouts where the schema omits them, the same slots remain available
# from deck-level context.

canvas 1920x1080
theme feinschliff

# Full-bleed gold ground.
rect 0,0 1920x1080 fill:accent

# Header chrome (brand-supplied wordmark + pgmeta).
header pgmeta:"{{ pgmeta }}"

# Opener-stack — anchored visually low-left. Rule + eyebrow + display title.
# Block bottom ~y=900; stack height varies with title line count (~360px for 2 lines).
# Title stack lifted +60px from y=520/580/620 → y=460/520/560 so the
# title bbox (now maxheight=400) reaches at most y=960 — clearing the
# y=1000 footer chrome by 40px. Enables 2-line display titles even on
# brands that author display at 200px (ferrari, binance).
rect 100,460 80x4 fill:ink

text 100,520 style:eyebrow maxwidth:1700 maxheight:30 "{{ eyebrow }}"

text 100,560 style:display maxwidth:1700 maxheight:400 "{{ title }}"

# Footer (brand-supplied).
footer left:"{{ footer_left }}" right:"{{ footer_right }}"