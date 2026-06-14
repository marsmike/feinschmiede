---
role: content-columns
ideal_count: [6, 6]
data_band: none
comparison: false
family: organizational
description: 'White panel: bold title, black rule, three-column bullet layout (business / added priorities / employee opportunities)'
when_to_use: Three-column goals — when priorities split into three streams.
slide_index: 11
slots:
  text_1: {role: title, chars: 36, default: Goals for Q2}
  text_2: {role: body, chars: 54, default: Business priorities}
  text_3: {role: body, chars: 54, default: Added priorities}
  text_4: {role: body, chars: 66, default: Employee opportunities}
  text_5: {role: body, chars: 351, default: Increase customer satisfaction by 2%\nMaintain growth}
  text_6: {role: body, chars: 351, default: Decrease the number of rotations by at least 2\nEnsure the cost of developmen…}
  text_7: {role: body, chars: 352, default: Interns begin\nIndoor rec leagues\nChess tournaments\nBig Game watching party…}
  text_8: {role: footer, chars: 17, default: Annual Review}
  text_9: {role: footer, chars: 38, default: 'September 3, 20XX'}
  text_10: {role: page-number, chars: 7, default: '11'}
element_tree: ['text text_1 role=title @162,157 1748x102 44pt', 'text text_2 role=body @148,367 545x104 18pt', 'text text_3
    role=body @703,367 536x102 18pt', 'text text_4 role=body @1249,367 661x102 18pt', 'text text_6 role=body @715,479 541x591
    18pt', 'text text_7 role=body @1266,479 644x502 18pt', 'text text_5 role=body @163,481 542x589 18pt', 'text text_8 role=footer
    @1307,991 231x29 12pt', 'text text_9 role=footer @1548,991 252x79 12pt', 'text text_10 role=page-number @1810,991 100x29
    12pt']
source_hash: bad510129bfc
source: annual-review
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: goals-q2
canvas 1920x1080
theme annual-review

line 163,295 1758,296 stroke:fog stroke-width:12
line 163,295 1758,296 stroke:fog stroke-width:12

text 162,157 style:sub color:black weight:bold size:44pt linespacing:0.9 valign:bottom padding:1 maxwidth:1748 maxheight:102 autoshrink:true "{{ text_1 | default(\"Goals for Q2\") }}"
text 148,367 style:body color:black weight:bold size:18pt linespacing:0.9 padding:14,7,14,7 maxwidth:545 maxheight:104 autoshrink:true "{{ text_2 | default(\"Business priorities\") }}"
text 703,367 style:body color:black weight:bold size:18pt linespacing:0.9 padding:14,7,14,7 maxwidth:536 maxheight:102 autoshrink:true "{{ text_3 | default(\"Added priorities\") }}"
text 1249,367 style:body color:black weight:bold size:18pt linespacing:0.9 padding:14,7,14,7 maxwidth:661 maxheight:102 autoshrink:true "{{ text_4 | default(\"Employee opportunities\") }}"
text 163,481 style:body color:black size:18pt linespacing:0.9 valign:top padding:1 maxwidth:542 maxheight:589 autoshrink:true "{{ text_5 | default(\"Increase customer satisfaction by 2%\nMaintain growth\") }}"
text 715,479 style:body color:black size:18pt linespacing:0.9 valign:top padding:1 maxwidth:541 maxheight:591 autoshrink:true "{{ text_6 | default(\"Decrease the number of rotations by at least 2\nEnsure the cost of development stays below budget\") }}"
text 1266,479 style:body color:black size:18pt linespacing:0.9 valign:top padding:1 maxwidth:644 maxheight:502 autoshrink:true "{{ text_7 | default(\"Interns begin\nIndoor rec leagues\nChess tournaments\nBig Game watching party\nFood drive\") }}"
text 1307,991 style:body-sm color:black size:12pt linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:231 maxheight:29 "{{ text_8 | default(\"Annual Review\") }}"
text 1548,991 style:body-sm color:black size:12pt linespacing:native padding:1 maxwidth:252 maxheight:79 "{{ text_9 | default(\"September 3, 20XX\") }}"
text 1810,991 style:body-sm color:black size:12pt linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:100 maxheight:29 "{{ text_10 | default(\"11\") }}"
