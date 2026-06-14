---
role: closer
ideal_count: [1, 2]
data_band: none
comparison: false
variety_exempt: true
family: closing
description: 'Two-column closing: left has content photo slot; right has Thank You headline, body text, contact details'
when_to_use: Closing slide — thank-you headline, body line, contact details, photo.
slide_index: 13
slots:
  text_1: {role: title, chars: 19, default: Thank you}
  text_2: {role: body, chars: 368, default: 'Thanks to your commitment and strong work ethic, we know next year will be ev…'}
  text_3: {role: body, chars: 312, default: Contoso\nsales@contoso.com}
  text_4: {role: footer, chars: 17, default: Annual Review}
  text_5: {role: footer, chars: 38, default: 'September 3, 20XX'}
  text_6: {role: page-number, chars: 7, default: '13'}
  image: {role: image, class: replace}
image_queries: {image: thank you}
element_tree: ['image image class=replace @0,156 762x762', 'text text_1 role=title @985,157 925x102 44pt', 'text text_2 role=body
    @985,360 925x367 18pt', 'text text_3 role=body @985,734 925x247 16pt', 'text text_4 role=footer @1307,991 231x29 12pt',
  'text text_5 role=footer @1548,991 252x79 12pt', 'text text_6 role=page-number @1810,991 100x29 12pt']
source_hash: 3eeb09edfcaa
source: annual-review
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: thank-you
canvas 1920x1080
theme annual-review

picture 0,156 762x762 path:"{{ image | default(\"decompile/thank-you/image.jpeg\") }}" cover:true
line 986,294 1753,295 stroke:fog stroke-width:12
line 986,294 1753,295 stroke:fog stroke-width:12

text 985,157 style:sub color:black weight:bold size:44pt linespacing:0.9 valign:bottom padding:1 maxwidth:925 maxheight:102 autoshrink:true "{{ text_1 | default(\"Thank you\") }}"
text 985,360 style:body color:black size:18pt linespacing:1 padding:1 maxwidth:925 maxheight:367 autoshrink:true "{{ text_2 | default(\"Thanks to your commitment and strong work ethic, we know next year will be even better than the last.\nWe look forward to working together.\") }}"
text 985,734 style:body color:black weight:bold size:16pt linespacing:0.9 valign:top padding:1 maxwidth:925 maxheight:247 autoshrink:true "{{ text_3 | default(\"Contoso\nsales@contoso.com\") }}"
text 1307,991 style:body-sm color:black size:12pt linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:231 maxheight:29 "{{ text_4 | default(\"Annual Review\") }}"
text 1548,991 style:body-sm color:black size:12pt linespacing:native padding:1 maxwidth:252 maxheight:79 "{{ text_5 | default(\"September 3, 20XX\") }}"
text 1810,991 style:body-sm color:black size:12pt linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:100 maxheight:29 "{{ text_6 | default(\"13\") }}"
