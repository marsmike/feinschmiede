---
role: content-columns
ideal_count: [1, 1]
data_band: none
comparison: false
family: organizational
description: 'Split benefits slide: green teal vertical bar left, circular lab-dropper photo inset; title and five bullet
  items right'
when_to_use: Up to five benefit bullets with an inset product/lab photo.
slide_index: 5
slots:
  text_1: {role: title, chars: 120, default: PRODUCT BENEFITS}
  text_2: {role: body, chars: 360, default: INCREASED PRODUCTIVITY\nSEAMLESS INTEGRATION\nENHANCED USER EXPERIENCE\nSCALA…}
  image: {role: image, class: replace}
image_queries: {image: product benefits}
element_tree: ['text text_1 role=title @841,173 1069x357 32pt', 'image image class=replace @204,288 504x504', 'text text_2
    role=body @841,540 1069x530 24pt']
source_hash: 11ae9484e02a
source: scientific
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: product-benefits
canvas 1920x1080
theme scientific

rect 0,0 562x1080 fill:theme-accent4
rect 0,0 562x1080 fill:theme-accent4
picture 204,288 504x504 path:"{{ image | default(\"decompile/product-benefits/image.png\") }}" cover:true
line 841,130 906,131 stroke:theme-accent1 stroke-width:14
line 841,130 906,131 stroke:theme-accent1 stroke-width:14

text 841,173 style:sub color:black size:32pt linespacing:0.9 valign:top padding:1 maxwidth:1069 maxheight:357 autoshrink:true "{{ text_1 | default(\"PRODUCT BENEFITS\") }}"
text 841,540 style:body color:black size:24pt autoshrink:true linespacing:1 padding:1 maxwidth:1069 maxheight:530 "{{ text_2 | default(\"INCREASED PRODUCTIVITY\nSEAMLESS INTEGRATION\nENHANCED USER EXPERIENCE\nSCALABILITY FOR FUTURE GROWTH\nUSER-FRIENDLY LEARNING\") }}"
