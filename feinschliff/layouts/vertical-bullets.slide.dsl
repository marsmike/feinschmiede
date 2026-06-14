---
role: content-columns
ideal_count: [3, 6]
data_band: none
comparison: false
description: 'Numbered list table: six rows with index counter, bold item name, and description column; subtitle above and below list'
source: feinschliff
source_hash: 82435fc66b5b
---
# vertical-bullets — title + subtitle + 6 numbered rows (counter, heading,
# description) separated by hairlines. Matches the .pptx baseline pattern.
#
# Slot schema (data-slots from feinschliff-2026.html · 18):
#   logo             string, optional
#   pgmeta           string, ≤40, opt
#   tracker          string, ≤60, opt  (rendered as eyebrow)
#   kicker           string, ≤40, opt  (unused)
#   action_title     string, ≤180      (rendered as title)
#   lede             string, ≤280      (rendered as subtitle line)
#   supporting_note  string, ≤160, opt (rendered as bottom note)
#   items            array, 3–6 objects: (counter ≤6, heading ≤60, body ≤180)
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

# Title block.
rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30  "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:80  "{{ action_title }}"

# Subtitle (lede) line under title.
text 100,360 style:body    maxwidth:1720 maxheight:40  "{{ lede }}"

# 6 rows, hairline separated. Each row ~80px.
rect 100,440 1720x1 fill:fog
text 100,464  style:h-idx maxwidth:140                  "{{ items[0].counter }}"
text 260,460  style:h-hd  maxwidth:540 maxheight:40     "{{ items[0].heading }}"
text 820,464  style:body  maxwidth:1000 maxheight:48    "{{ items[0].body }}"

rect 100,520 1720x1 fill:fog
text 100,544  style:h-idx maxwidth:140                  "{{ items[1].counter }}"
text 260,540  style:h-hd  maxwidth:540 maxheight:40     "{{ items[1].heading }}"
text 820,544  style:body  maxwidth:1000 maxheight:48    "{{ items[1].body }}"

rect 100,600 1720x1 fill:fog
text 100,624  style:h-idx maxwidth:140                  "{{ items[2].counter }}"
text 260,620  style:h-hd  maxwidth:540 maxheight:40     "{{ items[2].heading }}"
text 820,624  style:body  maxwidth:1000 maxheight:48    "{{ items[2].body }}"

rect 100,680 1720x1 fill:fog
text 100,704  style:h-idx maxwidth:140                  "{{ items[3].counter }}"
text 260,700  style:h-hd  maxwidth:540 maxheight:40     "{{ items[3].heading }}"
text 820,704  style:body  maxwidth:1000 maxheight:48    "{{ items[3].body }}"

rect 100,760 1720x1 fill:fog
text 100,784  style:h-idx maxwidth:140                  "{{ items[4].counter }}"
text 260,780  style:h-hd  maxwidth:540 maxheight:40     "{{ items[4].heading }}"
text 820,784  style:body  maxwidth:1000 maxheight:48    "{{ items[4].body }}"

rect 100,840 1720x1 fill:fog
text 100,864  style:h-idx maxwidth:140                  "{{ items[5].counter }}"
text 260,860  style:h-hd  maxwidth:540 maxheight:40     "{{ items[5].heading }}"
text 820,864  style:body  maxwidth:1000 maxheight:48    "{{ items[5].body }}"

rect 100,920 1720x1 fill:fog

# Bottom note (above footer).
text 100,948 style:detail maxwidth:1720 maxheight:30 "{{ supporting_note }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"