---
role: content-columns
ideal_count: [2, 2]
data_band: none
comparison: false
family: organizational
description: 'Teal panel: bold title, rule, two-column grid of four named text blocks (heading + body each)'
when_to_use: Four named text blocks in a grid — wins, learnings, risks, outlook.
slide_index: 12
slots:
  text_1: {role: title, chars: 36, default: Summary}
  text_2: {role: body, chars: 644, default: Our customers keep coming back\nWe increased customer retention by 4%\nWe’re …}
  text_3: {role: body, chars: 656, default: Our business is good\nProfits are up in the last quarter by 3%\nWe’re deliver…}
  text_4: {role: footer, chars: 17, default: Annual Review}
  text_5: {role: footer, chars: 38, default: 'September 3, 20XX'}
  text_6: {role: page-number, chars: 7, default: '12'}
element_tree: ['text text_1 role=title @162,157 1748x102 44pt', 'text text_2 role=body @984,360 926x621 18pt', 'text text_3
    role=body @162,366 812x704 18pt', 'text text_4 role=footer @1307,991 231x29 12pt', 'text text_5 role=footer @1548,991
    252x79 12pt', 'text text_6 role=page-number @1810,991 100x29 12pt']
source_hash: 7a8ff51172aa
source: annual-review
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: summary
canvas 1920x1080
theme annual-review

rect 0,0 1920x1080 fill:highlight
line 163,295 1758,296 stroke:fog stroke-width:12
line 163,295 1758,296 stroke:fog stroke-width:12

text 162,157 style:sub color:black weight:bold size:44pt linespacing:0.9 valign:bottom padding:1 maxwidth:1748 maxheight:102 autoshrink:true "{{ text_1 | default(\"Summary\") }}"
text 984,360 style:body color:black weight:bold size:18pt linespacing:0.9 padding:14,7,14,7 maxwidth:926 maxheight:621 autoshrink:true "{{ text_2 | default(\"Our customers keep coming back\nWe increased customer retention by 4%\nWe’re leaders\nWe are top leaders in the industry across the board\") }}"
text 162,366 style:body color:black weight:bold size:18pt linespacing:1 padding:14,7,14,7 maxwidth:812 maxheight:704 autoshrink:true "{{ text_3 | default(\"Our business is good\nProfits are up in the last quarter by 3%\nWe’re delivering for our customers\nLast year we supported thousands of customers and sold 60,000 units\nWe’re getting our work done\nWe finished the consolidation project\") }}"
text 1307,991 style:body-sm color:black size:12pt linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:231 maxheight:29 "{{ text_4 | default(\"Annual Review\") }}"
text 1548,991 style:body-sm color:black size:12pt linespacing:native padding:1 maxwidth:252 maxheight:79 "{{ text_5 | default(\"September 3, 20XX\") }}"
text 1810,991 style:body-sm color:black size:12pt linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:100 maxheight:29 "{{ text_6 | default(\"12\") }}"
