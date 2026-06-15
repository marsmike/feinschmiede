---
role: content-columns
ideal_count: [4, 4]
data_band: none
comparison: false
description: Four equal photo tiles in a horizontal strip, each with accent label above and two-line caption below; title above strip
source: feinschliff
source_hash: d102117803b2
---
# photo-strip-four — 4 vertical strip-cards, each with a colored accent header,
# body copy, and a hero photo at the bottom.
#
# Slot schema:
#   logo, pgmeta — header
#   eyebrow   string, ≤60, opt
#   title     string, ≤80
#   strips    array, exactly 4 objects:
#     heading string, ≤30    (appears in colored accent header block)
#     body    string, ≤140   (body copy below header)
#     image   string, path   (hero photo at bottom of strip)
# Deck-level: footer_left, footer_right.
#
# Strip geometry (1920×1080 canvas):
#   4 columns × 1 row; col-w=394, gap=48.
#   Col x-anchors: 100, 542, 984, 1426.
#   Header chrome  : y=100–160 (standard header)
#   Title block    : rule y=180, eyebrow y=220, title y=260 (maxheight 100)
#   Strip columns  : y=400–960
#     Accent header: y=400, height=60 (heading text at y=415)
#     Body copy    : y=476, maxheight=124 (≤140 chars; autoshrink + native
#                    PPT autofit). Hard 124 px ceiling forces a real
#                    shrink even when textfit's rough estimate says it
#                    fits — real font metrics typically wrap one more
#                    line than the heuristic.
#     Hero photo   : y=620, height=340 (fills to y=960). 20 px gap below
#                    text bbox protects against final-line bleed into
#                    the photo even under aggressive wrap.
#   Footer         : y=1000

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

# Title block.
rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:22 if:"{{ eyebrow }}" "{{ eyebrow }}"
text 100,260 style:title   maxwidth:1720 maxheight:100 "{{ title }}"

# ── Strip 1 (x=100) ────────────────────────────────────────────────────────────
rect 100,400 394x60 fill:accent
text 120,415 style:h-hd color:paper maxwidth:354 maxheight:32 "{{ strips[0].heading }}"
text 100,476 style:body  maxwidth:394 maxheight:124 autoshrink:true "{{ strips[0].body }}"
picture 100,620 394x340 path:{{ strips[0].image }} cover:true

# ── Strip 2 (x=542) ────────────────────────────────────────────────────────────
rect 542,400 394x60 fill:accent
text 562,415 style:h-hd color:paper maxwidth:354 maxheight:32 "{{ strips[1].heading }}"
text 542,476 style:body  maxwidth:394 maxheight:124 autoshrink:true "{{ strips[1].body }}"
picture 542,620 394x340 path:{{ strips[1].image }} cover:true

# ── Strip 3 (x=984) ────────────────────────────────────────────────────────────
rect 984,400 394x60 fill:accent
text 1004,415 style:h-hd color:paper maxwidth:354 maxheight:32 "{{ strips[2].heading }}"
text 984,476 style:body  maxwidth:394 maxheight:124 autoshrink:true "{{ strips[2].body }}"
picture 984,620 394x340 path:{{ strips[2].image }} cover:true

# ── Strip 4 (x=1426) ───────────────────────────────────────────────────────────
rect 1426,400 394x60 fill:accent
text 1446,415 style:h-hd color:paper maxwidth:354 maxheight:32 "{{ strips[3].heading }}"
text 1426,476 style:body  maxwidth:394 maxheight:124 autoshrink:true "{{ strips[3].body }}"
picture 1426,620 394x340 path:{{ strips[3].image }} cover:true

footer left:"{{ footer_left }}" right:"{{ footer_right }}"