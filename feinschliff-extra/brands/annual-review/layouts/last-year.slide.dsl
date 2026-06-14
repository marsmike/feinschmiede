---
role: title-with-visual
ideal_count: [1, 1]
data_band: none
comparison: false
family: image-driven
description: Full-bleed content photo with bold section title and thin rule overlaid top-left
when_to_use: Photo-led section opener — full-bleed image, short overlaid title.
slide_index: 4
slots:
  text_1: {role: title, chars: 25, default: Last year}
  image: {role: image, class: replace}
image_queries: {image: last year}
element_tree: ['image image class=replace @0,0 1920x1080', 'text text_1 role=title @162,157 1230x102 44pt']
source_hash: adc62cb58fb5
source: annual-review
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: last-year
canvas 1920x1080
theme annual-review

picture 0,0 1920x1080 path:"{{ image | default(\"decompile/last-year/image.png\") }}" cover:true
line 164,293 1755,294 stroke:fog stroke-width:12
line 164,293 1755,294 stroke:fog stroke-width:12
line 163,296 1757,297 stroke:fog stroke-width:12

text 162,157 style:sub color:black weight:bold size:44pt linespacing:0.9 valign:bottom padding:1 maxwidth:1230 maxheight:102 autoshrink:true "{{ text_1 | default(\"Last year\") }}"
