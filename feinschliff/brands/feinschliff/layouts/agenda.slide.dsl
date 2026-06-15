---
role: agenda
ideal_count: [3, 8]
data_band: none
comparison: false
variety_exempt: true
description: 'Two-column numbered agenda: up to 8 items split left/right, each with index, title, and one-line description'
follows_not: [role=content-columns, role=data-quantity, role=data-comparison, role=closer]
follows_well: [role=title-primary]
source: feinschliff
source_hash: ba5f26b58826
---
# agenda — table of contents on the paper ground. Title block at top,
# 2-column grid of 3–8 agenda items below.
#
# Slot schema (data-slots from feinschliff-2026.html · 04):
#   logo     string, optional
#   pgmeta   string, ≤40, opt        Top-right meta line (e.g. "Agenda").
#   eyebrow  string, ≤60, opt        Kicker above the title.
#   title    string, ≤60             Agenda headline.
#   items    array, 3–8 objects      Each item:
#       counter      string, ≤10 (e.g. "01 / 06")
#       title        string, ≤40
#       description  string, ≤80, opt
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

# Title block — rule + eyebrow + slide-title.
rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1700 maxheight:30 "{{ eyebrow }}"
text 100,260 style:sub     maxwidth:1700 maxheight:80 "{{ title }}"

# Agenda items — 2-column × 4-row grid; canonical fills left→right then
# row-by-row. Each item is 96px tall (hairline + counter/title + description).
agenda-item x:100  y:400 w:800 counter:"{{ items[0].counter }}" title:"{{ items[0].title }}" description:"{{ items[0].description }}"
agenda-item x:1020 y:400 w:800 counter:"{{ items[1].counter }}" title:"{{ items[1].title }}" description:"{{ items[1].description }}"
agenda-item x:100  y:496 w:800 counter:"{{ items[2].counter }}" title:"{{ items[2].title }}" description:"{{ items[2].description }}"
agenda-item x:1020 y:496 w:800 counter:"{{ items[3].counter }}" title:"{{ items[3].title }}" description:"{{ items[3].description }}"
agenda-item x:100  y:592 w:800 counter:"{{ items[4].counter }}" title:"{{ items[4].title }}" description:"{{ items[4].description }}"
agenda-item x:1020 y:592 w:800 counter:"{{ items[5].counter }}" title:"{{ items[5].title }}" description:"{{ items[5].description }}"
agenda-item x:100  y:688 w:800 counter:"{{ items[6].counter }}" title:"{{ items[6].title }}" description:"{{ items[6].description }}"
agenda-item x:1020 y:688 w:800 counter:"{{ items[7].counter }}" title:"{{ items[7].title }}" description:"{{ items[7].description }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"