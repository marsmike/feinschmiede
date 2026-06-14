---
role: content-columns
ideal_count: [8, 8]
data_band: none
comparison: false
family: organizational
description: 'Yellow panel: bold title, black rule, four-column quarterly timeline with period labels and body text'
when_to_use: Four-quarter timeline — period label + short body per column.
slide_index: 9
slots:
  text_1: {role: title, chars: 36, default: Timeline}
  text_2: {role: body, chars: 60, default: Q1.\nJul - Sep}
  text_3: {role: body, chars: 60, default: Q1.\nOct - Dec}
  text_4: {role: body, chars: 60, default: Q3.\nJan - Mar}
  text_5: {role: body, chars: 78, default: Q4.\nApr - Jun}
  text_6: {role: body, chars: 400, default: 'Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy ni…'}
  text_7: {role: body, chars: 416, default: 'Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy ni…'}
  text_8: {role: body, chars: 338, default: 'Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy ni…'}
  text_9: {role: body, chars: 429, default: 'Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy ni…'}
  text_10: {role: footer, chars: 17, default: Annual Review}
  text_11: {role: footer, chars: 38, default: 'September 3, 20XX'}
  text_12: {role: page-number, chars: 7, default: '9'}
element_tree: ['text text_1 role=title @162,157 1748x102 44pt', 'text text_2 role=body @148,367 405x148 18pt', 'text text_3
    role=body @563,367 404x148 18pt', 'text text_4 role=body @977,367 405x148 18pt', 'text text_5 role=body @1392,367 518x148
    18pt', 'text text_6 role=body @153,525 397x545 14pt', 'text text_7 role=body @560,525 407x545 14pt', 'text text_8 role=body
    @977,525 405x456 14pt', 'text text_9 role=body @1392,525 518x456 14pt', 'text text_10 role=footer @1307,991 231x29 12pt',
  'text text_11 role=footer @1548,991 252x79 12pt', 'text text_12 role=page-number @1810,991 100x29 12pt']
source_hash: f682598edb2a
source: annual-review
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: timeline
canvas 1920x1080
theme annual-review

rect 0,0 1920x1080 fill:chart-series-4
line 163,295 1758,296 stroke:fog stroke-width:12
line 163,295 1758,296 stroke:fog stroke-width:12

text 162,157 style:sub color:black weight:bold size:44pt linespacing:0.9 valign:bottom padding:1 maxwidth:1748 maxheight:102 autoshrink:true "{{ text_1 | default(\"Timeline\") }}"
text 148,367 style:body color:black weight:bold size:18pt linespacing:1 padding:14,7,14,7 maxwidth:405 maxheight:148 autoshrink:true "{{ text_2 | default(\"Q1.\nJul - Sep\") }}"
text 563,367 style:body color:black weight:bold size:18pt linespacing:1 padding:14,7,14,7 maxwidth:404 maxheight:148 autoshrink:true "{{ text_3 | default(\"Q1.\nOct - Dec\") }}"
text 977,367 style:body color:black weight:bold size:18pt linespacing:1 padding:14,7,14,7 maxwidth:405 maxheight:148 autoshrink:true "{{ text_4 | default(\"Q3.\nJan - Mar\") }}"
text 1392,367 style:body color:black weight:bold size:18pt linespacing:1 padding:14,7,14,7 maxwidth:518 maxheight:148 autoshrink:true "{{ text_5 | default(\"Q4.\nApr - Jun\") }}"
text 153,525 style:body-sm color:black size:14pt linespacing:1 padding:14,7,14,7 maxwidth:397 maxheight:545 autoshrink:true "{{ text_6 | default(\"Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna.\") }}"
text 560,525 style:body-sm color:black size:14pt linespacing:1 padding:14,7,14,7 maxwidth:407 maxheight:545 autoshrink:true "{{ text_7 | default(\"Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna.\") }}"
text 977,525 style:body-sm color:black size:14pt linespacing:1 padding:14,7,14,7 maxwidth:405 maxheight:456 autoshrink:true "{{ text_8 | default(\"Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna.\") }}"
text 1392,525 style:body-sm color:black size:14pt linespacing:1 padding:14,7,14,7 maxwidth:518 maxheight:456 autoshrink:true "{{ text_9 | default(\"Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna.\") }}"
text 1307,991 style:body-sm color:black size:12pt linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:231 maxheight:29 "{{ text_10 | default(\"Annual Review\") }}"
text 1548,991 style:body-sm color:black size:12pt linespacing:native padding:1 maxwidth:252 maxheight:79 "{{ text_11 | default(\"September 3, 20XX\") }}"
text 1810,991 style:body-sm color:black size:12pt linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:100 maxheight:29 "{{ text_12 | default(\"9\") }}"
