---
role: content-columns
ideal_count: [1, 1]
data_band: none
comparison: false
family: organizational
description: 'Section divider: centred title on white inset over full-bleed faint molecular pattern background'
when_to_use: Light section divider — single centred title over the molecular pattern.
slide_index: 6
slots:
  text_1: {role: title, chars: 84, default: MARKET OVERVIEW}
  image: {role: image, class: replace}
image_queries: {image: market overview}
element_tree: ['image image class=replace @240,233 1440x613', 'text text_1 role=title @312,302 1296x475 54pt']
source_hash: 8697976fe01d
source: scientific
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: market-overview
canvas 1920x1080
theme scientific

rect 0,0 1920x1080 fill:theme-accent2
picture 240,233 1440x613 path:"{{ image | default(\"decompile/market-overview/image.png\") }}" cover:true

text 312,302 style:title-l color:black weight:regular size:54pt linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:1296 maxheight:475 autoshrink:true "{{ text_1 | default(\"MARKET OVERVIEW\") }}"
