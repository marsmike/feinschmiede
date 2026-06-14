---
role: data-comparison
ideal_count: [3, 5]
data_band: table
comparison: true
description: 'Workstream × period scorecard table: four rows, four phase columns, plain text status cells, hairline separators'
source: feinschliff
source_hash: b908b502e031
---
# scorecard — grid of workstreams × periods with status cells.
#
# Slot schema:
#   logo, pgmeta, tracker, action_title — header
#   periods      array, 4 strings (column headers)
#   workstreams  array, 4 objects:
#       name    string
#       cells   array, 4 strings (cell content per period)
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30 "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:80 "{{ action_title }}"

# Header row.
text 100,440  style:h-idx maxwidth:380 maxheight:24 "Workstream"
text 500,440  style:h-idx maxwidth:280 maxheight:24 "{{ periods[0] }}"
text 820,440  style:h-idx maxwidth:280 maxheight:24 "{{ periods[1] }}"
text 1140,440 style:h-idx maxwidth:280 maxheight:24 "{{ periods[2] }}"
text 1460,440 style:h-idx maxwidth:280 maxheight:24 "{{ periods[3] }}"

# Body rows. Each row 100h with hairline.
rect 100,480 1720x1 fill:fog
text 100,500  style:h-hd maxwidth:380 maxheight:60 "{{ workstreams[0].name }}"
text 500,500  style:body maxwidth:280 maxheight:60 "{{ workstreams[0].cells[0] }}"
text 820,500  style:body maxwidth:280 maxheight:60 "{{ workstreams[0].cells[1] }}"
text 1140,500 style:body maxwidth:280 maxheight:60 "{{ workstreams[0].cells[2] }}"
text 1460,500 style:body maxwidth:280 maxheight:60 "{{ workstreams[0].cells[3] }}"

rect 100,584 1720x1 fill:fog
text 100,604  style:h-hd maxwidth:380 maxheight:60 "{{ workstreams[1].name }}"
text 500,604  style:body maxwidth:280 maxheight:60 "{{ workstreams[1].cells[0] }}"
text 820,604  style:body maxwidth:280 maxheight:60 "{{ workstreams[1].cells[1] }}"
text 1140,604 style:body maxwidth:280 maxheight:60 "{{ workstreams[1].cells[2] }}"
text 1460,604 style:body maxwidth:280 maxheight:60 "{{ workstreams[1].cells[3] }}"

rect 100,688 1720x1 fill:fog
text 100,708  style:h-hd maxwidth:380 maxheight:60 "{{ workstreams[2].name }}"
text 500,708  style:body maxwidth:280 maxheight:60 "{{ workstreams[2].cells[0] }}"
text 820,708  style:body maxwidth:280 maxheight:60 "{{ workstreams[2].cells[1] }}"
text 1140,708 style:body maxwidth:280 maxheight:60 "{{ workstreams[2].cells[2] }}"
text 1460,708 style:body maxwidth:280 maxheight:60 "{{ workstreams[2].cells[3] }}"

rect 100,792 1720x1 fill:fog
text 100,812  style:h-hd maxwidth:380 maxheight:60 "{{ workstreams[3].name }}"
text 500,812  style:body maxwidth:280 maxheight:60 "{{ workstreams[3].cells[0] }}"
text 820,812  style:body maxwidth:280 maxheight:60 "{{ workstreams[3].cells[1] }}"
text 1140,812 style:body maxwidth:280 maxheight:60 "{{ workstreams[3].cells[2] }}"
text 1460,812 style:body maxwidth:280 maxheight:60 "{{ workstreams[3].cells[3] }}"

rect 100,896 1720x1 fill:fog

text 100,920 style:detail color:graphite maxwidth:1720 maxheight:30 if:"{{ so_what }}" "So what: {{ so_what }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"