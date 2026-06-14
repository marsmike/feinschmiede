---
role: closer
ideal_count: [1, 2]
data_band: none
comparison: false
variety_exempt: true
when_not_to_use: [role=content-columns, role=data-quantity, role=data-comparison, role=data-timeline, role=concept-diagram]
family: closing
fixed_chrome: true
description: 'Closing slide: large blue circle left bearing Thank You title; name, phone, email, URL lines right; geometric
  accents'
when_to_use: Closing slide — thank-you in the circle, contact lines right.
chrome_subject: purple circle top-left, orange square outline bottom-left, teal circle partial and blue dots; brand-neutral
chrome_note: 'carries native source chrome verbatim: 2 illustration'
slide_index: 13
slots:
  text_1: {role: title, chars: 119, default: Thank you}
  text_2: {role: body, chars: 448, default: Brita Tamm\n502-555-0152\nbrita@firstupconsultants.com\nwww.firstupconsultant…}
chrome_bboxes:
- [0, 0, 934, 1080]
- [0, 0, 934, 1080]
element_tree: ['native illustration @0,0 933.88x1080', 'native illustration @0,0 933.88x1080', 'text text_2 role=body @1040,119
    870x837 24pt', 'text text_1 role=title @60,120 837x839 44pt']
source_hash: 11cc2e66f51d
source: shapes
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: thank-you
canvas 1920x1080
theme shapes

native graphic1 xml_file:"native/5b4ca506197c.xml"
native graphic2 xml_file:"native/760da83d38f1.xml"
text 60,120 style:sub color:paper size:44pt autoshrink:true linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:837 maxheight:839 "{{ text_1 | default(\"Thank you\") }}"
text 1040,119 style:body color:black size:24pt autoshrink:true linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:870 maxheight:837 "{{ text_2 | default(\"Brita Tamm\n502-555-0152\nbrita@firstupconsultants.com\nwww.firstupconsultants.com\") }}"
