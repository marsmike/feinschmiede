---
role: reference
ideal_count: [3, 8]
data_band: table
comparison: true
description: 'Data table: header row with accent labels, five data rows × six columns, hairline separators, title above'
source: feinschliff
source_hash: 35d330497e7b
---
# table — 5 columns × N data rows. Header row + a `for` block that grows
# with the input. Rows pitch every 80px starting at y=500; the canonical
# content area accommodates up to ~7 rows before crowding the footer at
# y=1000. For longer datasets, split across consecutive table slides.
#
# Slot schema:
#   logo, pgmeta, tracker, action_title — header
#   columns      array, 5 strings  (column headers)
#   rows         array, N objects: { label, cells: 5 strings }
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30 "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:80 "{{ action_title }}"

# Header row.
rect 100,440 1720x2 fill:ink
text 100,460  style:h-idx maxwidth:300 maxheight:24 "Row"
text 420,460  style:h-idx maxwidth:280 maxheight:24 "{{ columns[0] }}"
text 720,460  style:h-idx maxwidth:280 maxheight:24 "{{ columns[1] }}"
text 1020,460 style:h-idx maxwidth:280 maxheight:24 "{{ columns[2] }}"
text 1320,460 style:h-idx maxwidth:280 maxheight:24 "{{ columns[3] }}"
text 1620,460 style:h-idx maxwidth:200 maxheight:24 "{{ columns[4] }}"

# Data rows — one for-block iteration per `rows[]` entry. `i` is the
# 0-based index; each row is 80px tall starting at y=500. Hairline below
# every row provides both inter-row separation and a closing border.
for row in rows:
  text 100,{{ 520+i*80 }}  style:body maxwidth:300 maxheight:36 autoshrink:true "{{ row.label }}"
  text 420,{{ 520+i*80 }}  style:body maxwidth:280 maxheight:36 autoshrink:true "{{ row.cells[0] }}"
  text 720,{{ 520+i*80 }}  style:body maxwidth:280 maxheight:36 autoshrink:true "{{ row.cells[1] }}"
  text 1020,{{ 520+i*80 }} style:body maxwidth:280 maxheight:36 autoshrink:true "{{ row.cells[2] }}"
  text 1320,{{ 520+i*80 }} style:body maxwidth:280 maxheight:36 autoshrink:true "{{ row.cells[3] }}"
  text 1620,{{ 520+i*80 }} style:body maxwidth:200 maxheight:36 autoshrink:true "{{ row.cells[4] }}"
  rect 100,{{ 580+i*80 }}  1720x1 fill:fog

footer left:"{{ footer_left }}" right:"{{ footer_right }}"