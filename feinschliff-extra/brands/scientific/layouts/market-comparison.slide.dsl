---
role: content-columns
ideal_count: [1, 1]
data_band: none
comparison: false
family: organizational
description: 'Split comparison: circular stock photo left (researcher/lab worker), title and six bullet differentiators right'
when_to_use: Up to six differentiator bullets beside a circular photo.
slide_index: 7
slots:
  text_1: {role: title, chars: 406, default: STANDS OUT IN MARKET\nINNOVATIVE FEATURES\nPROVIDES UNIQUE SOLUTION\nEDGE OVE…}
  text_2: {role: body, chars: 69, default: MARKET COMPARISON}
  image: {role: image, class: replace}
image_queries: {image: market comparison stands innovative}
element_tree: ['image image class=replace @202,86 475x475', 'text text_1 role=title @1135,115 775x850 24pt', 'text text_2
    role=body @202,619 844x288 32pt']
source_hash: 89190efa6b99
source: scientific
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: market-comparison
canvas 1920x1080
theme scientific

rect 1056,0 864x1080 fill:paper-2
rect 1056,0 864x1080 fill:paper-2
picture 202,86 475x475 path:"{{ image | default(\"decompile/market-comparison/image.jpeg\") }}" cover:true
line 204,963 269,964 stroke:theme-accent1 stroke-width:14
line 204,963 269,964 stroke:theme-accent1 stroke-width:14

text 1135,115 style:body color:black size:24pt autoshrink:true linespacing:1 valign:bottom padding:14,7,14,7 maxwidth:775 maxheight:850 "{{ text_1 | default(\"STANDS OUT IN MARKET\nINNOVATIVE FEATURES\nPROVIDES UNIQUE SOLUTION\nEDGE OVER COMPETITORS\nUSER-FOCUSED DESIGN\nPRIORITIZES USER EXPERIENCE\") }}"
text 202,619 style:sub color:black size:32pt linespacing:0.9 valign:bottom padding:1 maxwidth:844 maxheight:288 autoshrink:true "{{ text_2 | default(\"MARKET COMPARISON\") }}"
