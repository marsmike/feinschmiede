---
role: closer
ideal_count: [1, 2]
data_band: none
comparison: false
variety_exempt: true
family: closing
description: 'Closing slide: circular lab-dropper photo centre top, large centred THANK YOU title, teal accent bar, name/email/URL
  line'
when_to_use: Closing slide — thank-you title and photo; optionally contact line.
slide_index: 13
slots:
  text_1: {role: title, chars: 87, default: THANK YOU}
  text_2: {role: body, chars: 124, default: AIDYN ZHANBOLAT | AIDYN@ADATUM.COM | WWW.ADATUM.COM}
  image: {role: image, class: replace}
image_queries: {image: thank you}
element_tree: ['image image class=replace @780,86 360x360', 'text text_1 role=title @132,498 1778x366 54pt', 'text text_2
    role=body @248,952 1662x118 24pt']
source_hash: 157f3dc82dc8
source: scientific
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: thank-you
canvas 1920x1080
theme scientific

rect 0,0 1920x1080 fill:paper
rect 928,886 64x14 fill:theme-accent1
rect 928,886 64x14 fill:theme-accent1
picture 780,86 360x360 path:"{{ image | default(\"decompile/thank-you/image.jpeg\") }}" cover:true

text 132,498 style:title-l color:black weight:regular size:54pt linespacing:0.9 valign:middle padding:1 maxwidth:1778 maxheight:366 autoshrink:true "{{ text_1 | default(\"THANK YOU\") }}"
text 248,952 style:body color:black size:24pt linespacing:0.9 valign:top padding:1 maxwidth:1662 maxheight:118 autoshrink:true "{{ text_2 | default(\"AIDYN ZHANBOLAT | AIDYN@ADATUM.COM | WWW.ADATUM.COM\") }}"
