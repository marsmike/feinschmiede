---
role: content-columns
ideal_count: [6, 6]
data_band: none
comparison: false
description: 2×3 or 3×2 photo grid with caption under each image; title and one-line summary above the grid
source: feinschliff
source_hash: d944b858fc9a
---
# photo-grid — six photo-cards (3×2) + summary headline at bottom.
# Best for "six exemplars" / case-study grids.
#
# Slot schema:
#   logo, pgmeta — header
#   eyebrow           string, ≤60, opt
#   title             string, ≤80
#   cards             array, exactly 6 objects:
#     image           string, path
#     headline        string, ≤30  (1 line h-hd 32px)
#     body            string, ≤41  (1 line body 26px at 560px wide)
#   summary_headline  string, ≤180, opt   (single line; appears bottom-left
#                                          above the footer, with an accent rule)
# Deck-level: footer_left, footer_right.
#
# Note: the spec listed an optional `summary_body` slot; it was dropped at
# author-time because the 3×2 grid + summary headline already consume the
# canvas down to y=969 (footer chrome begins at y=1000). If a second
# summary line is needed, prefer authoring a separate `key-takeaways` slide.
#
# Grid geometry (1920×1080 canvas):
#   3 columns × 2 rows; col-w=560, gap=20; photo-h=180.
#   Col x-anchors: 100, 680, 1260.
#   Row 1 photo y=360; headline y=548; body y=590.  Row 1 ends ~622.
#   Row 2 photo y=642; headline y=830; body y=872.  Row 2 ends ~904.
#   Summary headline: y=922.  Footer: y=1000.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

# Title block.
rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:22 "{{ eyebrow }}"
text 100,260 style:title   maxwidth:1720 maxheight:82 "{{ title }}"

# ── Row 1, Card 1 ──────────────────────────────────────────────────────────────
picture 100,360 560x180 path:{{ cards[0].image }} cover:true
text 100,548 style:h-hd maxwidth:560 maxheight:37 "{{ cards[0].headline }}"
text 100,590 style:body  maxwidth:560 maxheight:32 "{{ cards[0].body }}"

# ── Row 1, Card 2 ──────────────────────────────────────────────────────────────
picture 680,360 560x180 path:{{ cards[1].image }} cover:true
text 680,548 style:h-hd maxwidth:560 maxheight:37 "{{ cards[1].headline }}"
text 680,590 style:body  maxwidth:560 maxheight:32 "{{ cards[1].body }}"

# ── Row 1, Card 3 ──────────────────────────────────────────────────────────────
picture 1260,360 560x180 path:{{ cards[2].image }} cover:true
text 1260,548 style:h-hd maxwidth:560 maxheight:37 "{{ cards[2].headline }}"
text 1260,590 style:body  maxwidth:560 maxheight:32 "{{ cards[2].body }}"

# ── Row 2, Card 4 ──────────────────────────────────────────────────────────────
picture 100,642 560x180 path:{{ cards[3].image }} cover:true
text 100,830 style:h-hd maxwidth:560 maxheight:37 "{{ cards[3].headline }}"
text 100,872 style:body  maxwidth:560 maxheight:32 "{{ cards[3].body }}"

# ── Row 2, Card 5 ──────────────────────────────────────────────────────────────
picture 680,642 560x180 path:{{ cards[4].image }} cover:true
text 680,830 style:h-hd maxwidth:560 maxheight:37 "{{ cards[4].headline }}"
text 680,872 style:body  maxwidth:560 maxheight:32 "{{ cards[4].body }}"

# ── Row 2, Card 6 ──────────────────────────────────────────────────────────────
picture 1260,642 560x180 path:{{ cards[5].image }} cover:true
text 1260,830 style:h-hd maxwidth:560 maxheight:37 "{{ cards[5].headline }}"
text 1260,872 style:body  maxwidth:560 maxheight:32 "{{ cards[5].body }}"

# ── Summary headline ───────────────────────────────────────────────────────────
rect 100,922 80x4 fill:accent if:"{{ summary_headline }}"
text 100,932 style:h-hd color:accent maxwidth:1720 maxheight:37 if:"{{ summary_headline }}" "{{ summary_headline }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"