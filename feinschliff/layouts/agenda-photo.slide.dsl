---
role: agenda
ideal_count: [3, 8]
data_band: none
comparison: false
description: 'Split agenda: numbered list with title+subtitle rows on left half, large photo filling right half'
source: feinschliff
source_hash: 7e0053e774f9
---
# agenda-photo — numbered agenda items on the left half + hero photo on the right half.
# Inviting deck-opener variant of the text-only `agenda` layout.
#
# Slot schema:
#   logo, pgmeta — header
#   eyebrow       string, ≤60, opt
#   title         string, ≤80               Headline, left-half max width.
#   items         array, 3–5 objects:
#     heading     string, ≤40               Short item title.
#     body        string, ≤80               Supporting line below heading.
#   image         string, path              Hero photo, right half full height.
# Deck-level: footer_left, footer_right.
#
# Geometry (1920×1080 canvas):
#   Left half : x=100, content width=860
#   Right half: x=1000, width=820, y=100, height=880 (inside chrome)
#   Header   : y=0–160
#   Title    : rule y=200, eyebrow y=240, title y=280 (maxheight 120)
#   Items    : y=460–860; each item ~100px (hairline + counter/heading + body)
#   Footer   : y=1000

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

# Right column: hero photo (full content height, right half).
picture 1000,100 820x880 path:{{ image }} query:{{ image_query }} cover:true

# ── Left column: title block ────────────────────────────────────────────────
rect 100,200 80x4 fill:ink
text 100,240 style:eyebrow maxwidth:860 maxheight:22 if:"{{ eyebrow }}" "{{ eyebrow }}"
text 100,280 style:title   maxwidth:860 maxheight:120 "{{ title }}"

# ── Agenda items 1–5 ────────────────────────────────────────────────────────
# agenda-item compound: counter, title (≤40), description (≤80)
# Items 4 and 5 are conditionally rendered: the compound internally guards
# all nodes with `if:"{{ title }}"`, so a missing items[3]/items[4] in ctx
# (which interpolates to "") suppresses the item entirely without leaking.
# Item heights: each 100px; positions: 460, 560, 660, 760, 860
agenda-item x:100 y:460 w:860 counter:"01" title:"{{ items[0].heading }}" description:"{{ items[0].body }}"
agenda-item x:100 y:560 w:860 counter:"02" title:"{{ items[1].heading }}" description:"{{ items[1].body }}"
agenda-item x:100 y:660 w:860 counter:"03" title:"{{ items[2].heading }}" description:"{{ items[2].body }}"
agenda-item x:100 y:760 w:860 counter:"04" title:"{{ items[3].heading }}" description:"{{ items[3].body }}"
agenda-item x:100 y:860 w:860 counter:"05" title:"{{ items[4].heading }}" description:"{{ items[4].body }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"