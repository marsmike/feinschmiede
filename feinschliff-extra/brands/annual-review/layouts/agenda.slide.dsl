---
role: agenda
ideal_count: [1, 1]
data_band: none
comparison: false
variety_exempt: true
family: framing
description: 'Teal panel agenda: bold title over full-width black rule, numbered list of five agenda sections'
when_to_use: Opening agenda — five numbered review sections.
slide_index: 2
slots:
  text_1: {role: title, chars: 32, default: Agenda}
  text_2: {role: body, chars: 408, default: 01. Introduction\n02. Results from last year\n03. Team\n04. What's next\n05. …}
  text_3: {role: footer, chars: 17, default: Annual Review}
  text_4: {role: footer, chars: 38, default: 'September 3, 20XX'}
  text_5: {role: page-number, chars: 7, default: '2'}
element_tree: ['text text_1 role=title @162,157 1585x102 44pt', 'text text_2 role=body @162,360 1585x546 28pt', 'text text_3
    role=footer @1307,991 231x29 12pt', 'text text_4 role=footer @1548,991 252x79 12pt', 'text text_5 role=page-number @1810,991
    100x29 12pt']
source_hash: ad7477d39c3a
source: annual-review
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: agenda
canvas 1920x1080
theme annual-review

rect 0,-1 1757x917 fill:highlight
rect 0,-1 1757x917 fill:highlight
line 163,295 1758,296 stroke:fog stroke-width:12
line 163,295 1758,296 stroke:fog stroke-width:12

text 162,157 style:sub color:black weight:bold size:44pt linespacing:0.9 valign:bottom padding:1 maxwidth:1585 maxheight:102 autoshrink:true "{{ text_1 | default(\"Agenda\") }}"
text 162,360 style:sub color:black weight:bold size:28pt linespacing:1.1 padding:1 maxwidth:1585 maxheight:546 autoshrink:true "{{ text_2 | default(\"01. Introduction\n02. Results from last year\n03. Team\n04. What's next\n05. Closing\") }}"
text 1307,991 style:body-sm color:black size:12pt linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:231 maxheight:29 "{{ text_3 | default(\"Annual Review\") }}"
text 1548,991 style:body-sm color:black size:12pt linespacing:native padding:1 maxwidth:252 maxheight:79 "{{ text_4 | default(\"September 3, 20XX\") }}"
text 1810,991 style:body-sm color:black size:12pt linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:100 maxheight:29 "{{ text_5 | default(\"2\") }}"
