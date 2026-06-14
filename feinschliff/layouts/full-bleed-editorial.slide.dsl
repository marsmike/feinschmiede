---
role: title-with-visual
ideal_count: [1, 1]
data_band: none
comparison: false
description: 'Full-bleed photo occupies entire slide; minimal text overlay bottom-left: eyebrow rule, headline, caption'
source: feinschliff
source_hash: bad7b3d642f2
---
# full-bleed-editorial — cinematic mid-deck punctuation slide.
# Full-bleed image with a small title+caption card pinned to the bottom-left
# corner. Distinct from full-bleed-cover: footer + pgmeta chrome stay visible
# and the corner card is compact (no eyebrow, no giant quote style).
#
# v1 ships BL corner only.
# Other corners (TL, TR, BR) and a `position` slot are deferred to v2.
#
# Slot schema:
#   logo     string, optional
#   pgmeta   string, ≤40, opt
#   image    string, path             Full-bleed background image.
#   title    string, ≤120            Main text in the BL corner card.
#   caption  string, ≤80, opt        Small line beneath the title.
# Deck-level: footer_left, footer_right.
#
# Geometry (1920×1080 canvas):
#   Full-bleed picture: 0,0 → 1920×1080
#   Header (on top of image): y=0–100; pgmeta at default position
#   BL card: x=80, y=740, width=760, height=240 (bottom edge=980)
#     Card rect : 80,740   760x240  fill:ink  (navy-900 dark bg)
#     Accent rule: 120,776  60x4   fill:accent
#     Title text : 120,796  style:h-hd  color:paper  maxwidth:680 maxheight:74   (2 lines)
#     Caption text: 120,890  style:body  color:silver  maxwidth:680 maxheight:64  (2 lines, opt)
#   Footer (on top of image): y=1000

canvas 1920x1080
theme feinschliff

# ── Background: full-bleed image (bottommost layer) ──────────────────────────
# Fallback placeholder fills canvas when image slot is empty.
rect 0,0 1920x1080 fill:paper-2
picture 0,0 1920x1080 path:{{ image }} query:{{ image_query }} cover:true

# ── Header chrome (drawn on top of image) ────────────────────────────────────
header pgmeta:"{{ pgmeta }}"

# ── Bottom-left corner card ───────────────────────────────────────────────────
# Dark ink rect gives contrast for paper-colored text against any photo.
# Card height: 240px — accommodates 2-line title (≈74px) + 1-line caption (64px) + padding.
rect 80,740 760x240 fill:ink

# Small gold accent rule above the title.
rect 120,776 60x4 fill:accent

# Title: h-hd style (32px / LH 1.15) — warm paper for contrast on dark card.
# maxheight=74 holds 2 lines at 36.8px/line.
text 120,796 style:h-hd color:paper maxwidth:680 maxheight:74 "{{ title }}"

# Optional caption — muted silver, body style (26px / LH 1.2 → 31.2px/line).
# maxheight=64 holds 2 lines; caption slot is ≤80 chars.
text 120,890 style:body color:silver maxwidth:680 maxheight:64 if:"{{ caption }}" "{{ caption }}"

# ── Footer chrome (drawn on top of image) ────────────────────────────────────
footer left:"{{ footer_left }}" right:"{{ footer_right }}"