---
role: agenda
ideal_count: [1, 1]
data_band: none
comparison: false
variety_exempt: true
family: framing
description: 'White background agenda: large blue circle left bearing section title; five plain agenda items right; teal dash
  arc top-right'
when_to_use: Opening agenda — section title in the circle, up to five plain items.
slide_index: 2
slots:
  text_1: {role: body, chars: 495, default: Introduction\nBuilding confidence\nEngaging the audience\nVisual aids\nFinal …}
  text_2: {role: title, chars: 84, default: Agenda}
element_tree: ['text text_1 role=body @914,87 874x908 24pt', 'text text_2 role=title @96,176 691x728 44pt']
source_hash: b2de8adf3317
source: shapes
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: agenda
canvas 1920x1080
theme shapes

shape 77,176 728x728 kind:oval fill:theme-accent2
shape 143,753 86x86 kind:oval fill:theme-accent5
shape 77,176 728x728 kind:oval fill:theme-accent2
shape 143,753 86x86 kind:oval fill:theme-accent5

text 914,87 style:body color:black size:24pt autoshrink:true linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:874 maxheight:908 "{{ text_1 | default(\"Introduction\nBuilding confidence\nEngaging the audience\nVisual aids\nFinal tips & takeaways\") }}"
text 96,176 style:sub color:paper size:44pt autoshrink:true linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:691 maxheight:728 "{{ text_2 | default(\"Agenda\") }}"
