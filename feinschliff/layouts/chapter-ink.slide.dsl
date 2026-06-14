---
role: chapter-opener
ideal_count: [1, 1]
data_band: none
comparison: false
variety_exempt: true
description: Dark navy full-bleed left panel with large chapter number and title; right half blank paper for breathing room
follows_not: [role=chapter-opener]
follows_well: [role=agenda, role=closer, role=content-columns]
source: feinschliff
source_hash: a0c95ac86d50
---
# chapter-ink — section divider on the dark ink ground. Layout mirrors
# chapter-orange with inverted chrome plus an editorial image, right half.
#
# Slot schema (data-slots from feinschliff-2026.html · 06):
#   logo            string, optional
#   pgmeta          string, ≤40, opt   Chapter counter (e.g. "Chapter 02").
#   eyebrow         string, ≤60, opt
#   chapter_number  string, ≤8         Large numeral.
#   chapter_title   string, ≤40        Chapter name (may include \n breaks).
#   image           string, path, opt  Editorial 16:9 image, right half.
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

rect 0,0 1920x1080 fill:chapter-slab

# Optional editorial image — right half. When absent, renders as a dark
# placeholder (the brand's navy-700 surface tone) so the slide retains
# the split-frame composition. `optional:true` keeps the missing-asset
# policy from failing the build when `image` is unset (the layout is
# explicitly designed to look complete with or without the image).
rect 960,0 960x1080 fill:navy-700
picture 960,0 960x1080 path:{{ image }} query:{{ image_query }} cover:true optional:true

header-dark pgmeta:"{{ pgmeta }}"

# Opener-stack — confined to left half (width ~860 to clear the image).
rect 100,460 80x4 fill:accent
text 100,520 style:eyebrow color:accent    maxwidth:860 maxheight:30 "{{ eyebrow }}"
text 100,560 style:huge    color:off-white maxwidth:860 maxheight:440 "{{ chapter_number }}\n{{ chapter_title }}"

footer-dark left:"{{ footer_left }}" right:"{{ footer_right }}"