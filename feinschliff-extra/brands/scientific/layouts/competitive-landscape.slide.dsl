---
role: content-columns
ideal_count: [2, 2]
data_band: none
comparison: false
family: organizational
description: 'White competitive analysis: title and teal accent bar top; two side-by-side tinted text boxes with bullet lists
  (Strengths / Needs)'
when_to_use: Two-way comparison — side-by-side tinted boxes (us vs. them, before/after).
slide_index: 8
slots:
  text_1: {role: title, chars: 96, default: COMPETITIVE LANDSCAPE}
  text_2: {role: body, chars: 481, default: Strong market presence\nPositioned as a market leader\nLeveraging a robust in…}
  text_3: {role: body, chars: 481, default: 'Need:\nMore agility and adaptability\nStronger competitive edge\nAbility to a…'}
element_tree: ['text text_1 role=title @202,173 1708x191 32pt', 'text text_2 role=body @202,374 734x562 18pt', 'text text_3
    role=body @994,374 734x562 18pt']
source_hash: 44369188a5c6
source: scientific
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: competitive-landscape
canvas 1920x1080
theme scientific

rect 202,374 734x562 fill:paper-2
rect 994,374 734x562 fill:paper-2
line 204,130 269,131 stroke:theme-accent1 stroke-width:14
line 204,130 269,131 stroke:theme-accent1 stroke-width:14

text 202,173 style:sub color:black size:32pt linespacing:0.9 valign:top padding:1 maxwidth:1708 maxheight:191 autoshrink:true "{{ text_1 | default(\"COMPETITIVE LANDSCAPE\") }}"
text 202,374 style:body color:black size:18pt linespacing:native maxwidth:734 maxheight:562 autoshrink:true "{{ text_2 | default(\"Strong market presence\nPositioned as a market leader\nLeveraging a robust infrastructure\nDedicated team of experts\nOutperforming competitors\nGood brand name recognition\") }}"
text 994,374 style:body color:black size:18pt linespacing:native maxwidth:734 maxheight:562 autoshrink:true "{{ text_3 | default(\"Need:\nMore agility and adaptability\nStronger competitive edge\nAbility to adapt swiftly\nStay ahead of the curve\nContinuously improve offerings\nIntegrate user feedback\") }}"
