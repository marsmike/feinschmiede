---
role: title-primary
ideal_count: [1, 2]
data_band: none
comparison: false
variety_exempt: true
when_not_to_use: [role=content-columns, role=data-quantity, role=data-comparison, role=data-timeline, role=concept-diagram]
family: framing
fixed_chrome: true
description: 'White background cover: large blue circle right with title text; scattered geometric shapes (circles, squares,
  dashes) as chrome'
when_to_use: Deck cover — short title inside the blue circle; keep it to a few words.
chrome_subject: scattered coloured geometric shapes — circles, squares, dashes; brand-neutral abstract artwork
chrome_note: 'carries native source chrome verbatim: 2 illustration'
slide_index: 1
slots:
  text_1: {role: title, chars: 60, default: Basic presentation}
chrome_bboxes:
- [0, 0, 1920, 1305]
- [0, 0, 1920, 1305]
element_tree: ['native illustration @0,0 1920x1305.02', 'native illustration @0,0 1920x1305.02', 'text text_1 role=title @816,465
    986x377 44pt']
source_hash: 6b56c39e6f0e
source: shapes
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: cover
canvas 1920x1080
theme shapes

native graphic1 xml_file:"native/c8e580750c84.xml"
native graphic2 xml_file:"native/4ec4e6f5e7f5.xml"
text 816,465 style:sub color:paper size:44pt linespacing:0.9 valign:bottom padding:14,7,14,7 maxwidth:986 maxheight:377 autoshrink:true "{{ text_1 | default(\"Basic presentation\") }}"
