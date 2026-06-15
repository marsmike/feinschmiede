---
role: closer
ideal_count: [1, 1]
data_band: none
comparison: false
variety_exempt: true
description: Full-bleed photo cover with closing phrase overlaid bottom-center on a dark scrim
source: feinschliff
source_hash: d344ac7256b2
---
# end-image — closer slide with hero photo above the closing line.
# Alternative to end.slide.dsl (gold ground). Hero photo fills the top ~60%
# of the canvas; centered closing block (accent rule + display-xl title +
# optional footnote) sits in the lower 432px on the brand's paper background.
#
# Slot schema:
#   logo      string, optional   Brand wordmark; default supplied by brand pack.
#   pgmeta    string, ≤40, opt   Top-right meta line (e.g. "End · 30 / 30").
#   image     string, path       Full-width hero photo (top ~60% of slide).
#   title     string, ≤18        Display headline (e.g. "Thank you." — one
#                                display-xl line at 1920px canvas width).
#   footnote  string, ≤80, opt   Deck version tag.
# Deck-level (always available from context): footer_left, footer_right.
#
# Geometry (1920×1080 canvas):
#   Hero picture : 0,0     → 1920×648
#   Paper region : 0,648   → 1920×432 (fill:paper)
#   Accent rule  : 900,720 → 120×4    (centered, fill:accent)
#   Title text   : 0,740   style:display-xl  align:center  maxwidth:1920 maxheight:220
#   Footnote text: 0,960   style:eyebrow     align:center  maxwidth:1920 maxheight:40   (opt)
#   Header       : y=0 (on top of image)
#   Footer       : y=1000 (on paper region)

canvas 1920x1080
theme feinschliff

# ── Paper base (lower 432px) ─────────────────────────────────────────────────
# Drawn first so the hero picture covers it cleanly at the seam.
rect 0,648 1920x432 fill:paper

# ── Hero picture (top 60%) ───────────────────────────────────────────────────
# Fallback placeholder when image slot is empty.
rect 0,0 1920x648 fill:paper-2
picture 0,0 1920x648 path:{{ image }} query:{{ image_query }} cover:true

# ── Header chrome (drawn on top of image) ────────────────────────────────────
header pgmeta:"{{ pgmeta }}"

# ── Centered closing block ───────────────────────────────────────────────────
# Accent rule — 120×4, centered on x=900, vertically in lower region.
rect 900,720 120x4 fill:accent

# Display-xl title — centered across full canvas width. One display-xl line
# (200px × LH 0.95 ≈ 190px) fits in maxheight:220 with minimal breathing room.
text 0,740 style:display-xl align:center maxwidth:1920 maxheight:220 "{{ title }}"

# Optional footnote (deck version tag) — mono eyebrow, centered.
# Positioned at y=960 to clear the footer chrome at y=1000.
text 0,960 style:eyebrow align:center maxwidth:1920 maxheight:40 if:"{{ footnote }}" "{{ footnote }}"

# ── Footer chrome ─────────────────────────────────────────────────────────────
footer left:"{{ footer_left }}" right:"{{ footer_right }}"