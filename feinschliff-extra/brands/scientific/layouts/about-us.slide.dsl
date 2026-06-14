---
role: content-columns
ideal_count: [1, 1]
data_band: none
comparison: false
family: organizational
description: 'About us: full-width lab close-up photo banner top, large centred title, blue dash rule, body tagline below'
when_to_use: Company/team intro — photo banner, one centred tagline paragraph.
slide_index: 3
slots:
  text_1: {role: title, chars: 87, default: ABOUT US}
  text_2: {role: body, chars: 134, default: Aiming to revolutionize industries through our forward-thinking solutions}
  image: {role: image, class: replace}
image_queries: {image: about us}
element_tree: ['image image class=replace @0,0 1920x373', 'text text_1 role=title @132,425 1778x410 54pt', 'text text_2 role=body
    @132,952 1778x118 24pt']
source_hash: 6ef95b0c87c2
source: scientific
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: about-us
canvas 1920x1080
theme scientific

rect 928,886 64x14 fill:theme-accent1
rect 928,886 64x14 fill:theme-accent1
picture 0,0 1920x373 path:"{{ image | default(\"decompile/about-us/image.png\") }}" cover:true

text 132,425 style:title-l color:black weight:regular size:54pt autoshrink:true linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:1778 maxheight:410 "{{ text_1 | default(\"ABOUT US\") }}"
text 132,952 style:body color:black size:24pt autoshrink:true linespacing:1 padding:1 maxwidth:1778 maxheight:118 "{{ text_2 | default(\"Aiming to revolutionize industries through our forward-thinking solutions\") }}"
