---
role: content-columns
ideal_count: [8, 8]
data_band: none
comparison: false
family: organizational
description: 'White panel: title and rule at top, four portrait photo slots in a row each with name and role'
when_to_use: Team gallery — four portraits with name + role each.
slide_index: 8
slots:
  text_1: {role: title, chars: 36, default: Our team}
  text_2: {role: body, chars: 21, default: Ana}
  text_3: {role: body, chars: 21, default: Larissa}
  text_4: {role: body, chars: 21, default: Roman}
  text_5: {role: body, chars: 22, default: Federico}
  text_6: {role: body, chars: 192, default: CEO}
  text_7: {role: body, chars: 192, default: CFO}
  text_8: {role: body, chars: 144, default: CTO}
  text_9: {role: body, chars: 150, default: COO}
  text_10: {role: footer, chars: 17, default: Annual Review}
  text_11: {role: footer, chars: 38, default: 'September 3, 20XX'}
  text_12: {role: page-number, chars: 7, default: '8'}
  image1: {role: image, class: replace}
  image2: {role: image, class: replace}
  image3: {role: image, class: replace}
  image4: {role: image, class: replace}
image_queries: {image1: team, image2: team, image3: team, image4: team}
element_tree: ['text text_1 role=title @162,157 1748x102 44pt', 'image image1 class=replace @162,364 288x288', 'image image2
    class=replace @596,364 288x288', 'image image3 class=replace @1030,364 288x288', 'image image4 class=replace @1464,364
    288x288', 'text text_2 role=body @162,679 424x63 18pt', 'text text_4 role=body @1029,679 425x66 18pt', 'text text_3 role=body
    @596,682 423x63 18pt', 'text text_5 role=body @1464,682 446x66 18pt', 'text text_6 role=body @162,748 424x322 16pt', 'text
    text_7 role=body @596,748 423x322 16pt', 'text text_8 role=body @1029,748 425x233 16pt', 'text text_9 role=body @1464,748
    446x233 16pt', 'text text_10 role=footer @1307,991 231x29 12pt', 'text text_11 role=footer @1548,991 252x79 12pt', 'text
    text_12 role=page-number @1810,991 100x29 12pt']
source_hash: 641b0f677a11
source: annual-review
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: team
canvas 1920x1080
theme annual-review

picture 162,364 288x288 path:"{{ image1 | default(\"decompile/team/image1.jpeg\") }}" cover:true
picture 596,364 288x288 path:"{{ image2 | default(\"decompile/team/image2.jpeg\") }}" cover:true
picture 1030,364 288x288 path:"{{ image3 | default(\"decompile/team/image3.jpeg\") }}" cover:true
picture 1464,364 288x288 path:"{{ image4 | default(\"decompile/team/image4.jpeg\") }}" cover:true
line 163,295 1758,296 stroke:fog stroke-width:12
line 163,295 1758,296 stroke:fog stroke-width:12

text 162,157 style:sub color:black weight:bold size:44pt linespacing:0.9 valign:bottom padding:1 maxwidth:1748 maxheight:102 autoshrink:true "{{ text_1 | default(\"Our team\") }}"
text 162,679 style:body color:black weight:bold size:18pt linespacing:0.9 padding:1 maxwidth:424 maxheight:63 autoshrink:true "{{ text_2 | default(\"Ana\") }}"
text 596,682 style:body color:black weight:bold size:18pt linespacing:0.9 padding:1 maxwidth:423 maxheight:63 autoshrink:true "{{ text_3 | default(\"Larissa\") }}"
text 1029,679 style:body color:black weight:bold size:18pt linespacing:0.9 padding:1 maxwidth:425 maxheight:66 autoshrink:true "{{ text_4 | default(\"Roman\") }}"
text 1464,682 style:body color:black weight:bold size:18pt linespacing:0.9 padding:1 maxwidth:446 maxheight:66 autoshrink:true "{{ text_5 | default(\"Federico\") }}"
text 162,748 style:body color:black size:16pt linespacing:0.9 padding:1 maxwidth:424 maxheight:322 autoshrink:true "{{ text_6 | default(\"CEO\") }}"
text 596,748 style:body color:black size:16pt linespacing:0.9 padding:1 maxwidth:423 maxheight:322 autoshrink:true "{{ text_7 | default(\"CFO\") }}"
text 1029,748 style:body color:black size:16pt linespacing:0.9 padding:1 maxwidth:425 maxheight:233 autoshrink:true "{{ text_8 | default(\"CTO\") }}"
text 1464,748 style:body color:black size:16pt linespacing:0.9 padding:1 maxwidth:446 maxheight:233 autoshrink:true "{{ text_9 | default(\"COO\") }}"
text 1307,991 style:body-sm color:black size:12pt linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:231 maxheight:29 "{{ text_10 | default(\"Annual Review\") }}"
text 1548,991 style:body-sm color:black size:12pt linespacing:native padding:1 maxwidth:252 maxheight:79 "{{ text_11 | default(\"September 3, 20XX\") }}"
text 1810,991 style:body-sm color:black size:12pt linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:100 maxheight:29 "{{ text_12 | default(\"8\") }}"
