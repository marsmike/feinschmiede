---
role: quote
ideal_count: [1, 2]
data_band: none
comparison: false
family: voice
description: 'Teal panel: large quotation marks and black rule at top, large pull-quote body text centered'
when_to_use: Single pull-quote — testimonial or leadership statement.
slide_index: 7
slots:
  text_1: {role: title, chars: 0, default: “}
  text_2: {role: body, chars: 408, default: Contoso was great to work with. Patrice was my representative and she anticip…}
  text_3: {role: footer, chars: 17, default: Annual Review}
  text_4: {role: footer, chars: 38, default: 'September 3, 20XX'}
  text_5: {role: page-number, chars: 7, default: '7'}
slot_warnings:
  text_1: ['NARROW_BOX: ~1 chars/line at 200pt in a 250px-wide box']
element_tree: ['text text_1 role=title @122,154 250x209 200pt', 'text text_2 role=body @162,363 1585x543 28pt', 'text text_3
    role=footer @1307,991 231x29 12pt', 'text text_4 role=footer @1548,991 252x79 12pt', 'text text_5 role=page-number @1810,991
    100x29 12pt']
source_hash: c516b4d778a1
source: annual-review
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: quote
canvas 1920x1080
theme annual-review

rect 0,-1 1757x917 fill:highlight
rect 0,-1 1757x917 fill:highlight
line 344,295 1757,296 stroke:fog stroke-width:12
line 344,295 1757,296 stroke:fog stroke-width:12

text 122,154 style:display color:black weight:bold size:200pt linespacing:0.9 padding:14,7,14,7 maxwidth:250 maxheight:209 autoshrink:true "{{ text_1 | default(\"“\") }}"
text 162,363 style:sub color:black size:28pt linespacing:1.5 padding:1 maxwidth:1585 maxheight:543 autoshrink:true "{{ text_2 | default(\"Contoso was great to work with. Patrice was my representative and she anticipated my needs and worked diligently to fix my issue.\") }}"
text 1307,991 style:body-sm color:black size:12pt linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:231 maxheight:29 "{{ text_3 | default(\"Annual Review\") }}"
text 1548,991 style:body-sm color:black size:12pt linespacing:native padding:1 maxwidth:252 maxheight:79 "{{ text_4 | default(\"September 3, 20XX\") }}"
text 1810,991 style:body-sm color:black size:12pt linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:100 maxheight:29 "{{ text_5 | default(\"7\") }}"
