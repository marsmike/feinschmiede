---
role: title-primary
ideal_count: [1, 2]
data_band: none
comparison: false
variety_exempt: true
family: framing
description: 'Yellow panel cover: bold black display title over thick black rule, org/team/date line below'
when_to_use: Review cover — title plus org/team/date line.
slide_index: 1
slots:
  text_1: {role: title, chars: 48, default: Annual Review}
  text_2: {role: body, chars: 356, default: 'Contoso Customer Success Team September 3, 20XX'}
element_tree: ['text text_1 role=title @154,261 1593x333 60pt', 'text text_2 role=body @163,745 1584x162 16pt']
source_hash: 02a5a62d2085
source: annual-review
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: cover
canvas 1920x1080
theme annual-review

rect 0,0 1920x1080 fill:paper
rect 0,0 1757x917 fill:chart-series-4
rect 0,0 1757x917 fill:chart-series-4
line 163,655 1757,656 stroke:fog stroke-width:20
line 163,655 1757,656 stroke:fog stroke-width:20

text 154,261 style:title-l color:black size:60pt linespacing:0.9 valign:bottom padding:14,7,14,7 maxwidth:1593 maxheight:333 autoshrink:true "{{ text_1 | default(\"Annual Review\") }}"
text 163,745 style:body color:black weight:bold size:16pt linespacing:0.9 padding:1 maxwidth:1584 maxheight:162 autoshrink:true "{{ text_2 | default(\"Contoso Customer Success Team September 3, 20XX\") }}"
