---
role: content-columns
ideal_count: [4, 4]
data_band: none
comparison: false
family: organizational
description: 'White panel: bold title, black rule, two-column bullet layout (business priorities / employee opportunities)'
when_to_use: Two-column goals (business priorities vs. employee opportunities).
slide_index: 10
slots:
  text_1: {role: title, chars: 36, default: Goals for Q1}
  text_2: {role: body, chars: 82, default: Business priorities}
  text_3: {role: body, chars: 92, default: Employee opportunities}
  text_4: {role: body, chars: 533, default: Increase customer satisfaction by 2%\nMaintain growth\nDiversify investment i…}
  text_5: {role: body, chars: 506, default: End of fiscal celebration on July 15th\nEmployee day of learning on August 14…}
  text_6: {role: footer, chars: 17, default: Annual Review}
  text_7: {role: footer, chars: 38, default: 'September 3, 20XX'}
  text_8: {role: page-number, chars: 7, default: '10'}
element_tree: ['text text_1 role=title @162,157 1748x102 44pt', 'text text_2 role=body @148,367 828x102 18pt', 'text text_3
    role=body @986,367 924x102 18pt', 'text text_4 role=body @163,479 817x591 18pt', 'text text_5 role=body @990,479 920x502
    18pt', 'text text_6 role=footer @1307,991 231x29 12pt', 'text text_7 role=footer @1548,991 252x79 12pt', 'text text_8
    role=page-number @1810,991 100x29 12pt']
source_hash: 73434a05c1d5
source: annual-review
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: goals-q1
canvas 1920x1080
theme annual-review

line 163,295 1758,296 stroke:fog stroke-width:12
line 163,295 1758,296 stroke:fog stroke-width:12

text 162,157 style:sub color:black weight:bold size:44pt linespacing:0.9 valign:bottom padding:1 maxwidth:1748 maxheight:102 autoshrink:true "{{ text_1 | default(\"Goals for Q1\") }}"
text 148,367 style:body color:black weight:bold size:18pt linespacing:0.9 padding:14,7,14,7 maxwidth:828 maxheight:102 autoshrink:true "{{ text_2 | default(\"Business priorities\") }}"
text 986,367 style:body color:black weight:bold size:18pt linespacing:0.9 padding:14,7,14,7 maxwidth:924 maxheight:102 autoshrink:true "{{ text_3 | default(\"Employee opportunities\") }}"
text 163,479 style:body color:black size:18pt linespacing:0.9 valign:top padding:1 maxwidth:817 maxheight:591 autoshrink:true "{{ text_4 | default(\"Increase customer satisfaction by 2%\nMaintain growth\nDiversify investment in sector 2\nInitiative partnership with 3rd party organizations\") }}"
text 990,479 style:body color:black size:18pt linespacing:0.9 valign:top padding:1 maxwidth:920 maxheight:502 autoshrink:true "{{ text_5 | default(\"End of fiscal celebration on July 15th\nEmployee day of learning on August 14th\nEmployee Yoga on September 3rd\nSeminar series begins September 10th\") }}"
text 1307,991 style:body-sm color:black size:12pt linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:231 maxheight:29 "{{ text_6 | default(\"Annual Review\") }}"
text 1548,991 style:body-sm color:black size:12pt linespacing:native padding:1 maxwidth:252 maxheight:79 "{{ text_7 | default(\"September 3, 20XX\") }}"
text 1810,991 style:body-sm color:black size:12pt linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:100 maxheight:29 "{{ text_8 | default(\"10\") }}"
