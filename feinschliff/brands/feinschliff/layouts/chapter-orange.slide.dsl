---
role: chapter-opener
ideal_count: [1, 1]
data_band: none
comparison: false
variety_exempt: true
description: Full-bleed gold/accent background, large chapter number and title bottom-left, ghost progress counter bottom-right
follows_not: [role=chapter-opener]
follows_well: [role=agenda, role=closer, role=content-columns]
source: feinschliff
source_hash: 3105546db4c1
---
# chapter-orange — section divider on the gold ground. Section number +
# one-word chapter name in display, ghosted bignum counter bottom-right.
#
# Slot schema (data-slots from feinschliff-2026.html · 05):
#   logo            string, optional
#   pgmeta          string, ≤40, opt   Chapter counter (e.g. "Chapter 01").
#   eyebrow         string, ≤60, opt
#   chapter_number  string, ≤8         Large numeral (e.g. "01").
#   chapter_title   string, ≤30        Chapter name.
#   bignum          string, ≤10, opt   Ghosted counter (e.g. "01 / 06").
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

# Full-bleed gold ground.
rect 0,0 1920x1080 fill:accent

# Header chrome (brand-supplied).
header pgmeta:"{{ pgmeta }}"

# Opener-stack — rule + eyebrow + display (number\nname).
rect 100,460 80x4 fill:ink

text 100,520 style:eyebrow maxwidth:1700 maxheight:30 "{{ eyebrow }}"

text 100,560 style:display maxwidth:1200 maxheight:340 "{{ chapter_number }}\n{{ chapter_title }}"

# Ghosted bignum counter — bottom-right, very faded ink on gold.
# Canonical override: 220px, color rgba(0,0,0,0.22). We approximate with
# the accent-hover token (darker gold) — low-contrast ghost on the gold ground.
text 1300,720 style:display color:accent-hover maxwidth:520 maxheight:240 align:right "{{ bignum }}"

# Footer (brand-supplied).
footer left:"{{ footer_left }}" right:"{{ footer_right }}"