---
role: data-comparison
ideal_count: [3, 3]
data_band: none
comparison: true
description: Three-circle Venn diagram left with overlap labels; intersection annotations in stacked rows right with accent eyebrow
source: feinschliff
source_hash: 38daecf46e17
---
# venn — 3 overlapping circles using real oval shapes in the brand
# palette. Right column lists named intersections + a triple-overlap.
#
# Slot schema (data-slots from feinschliff-2026.html · 31):
#   logo, pgmeta, tracker, action_title — header
#   sets        array, 3 objects: (label, body)
#   pairs       array, 3 objects: (label)  — A∩B, B∩C, A∩C
#   center      object: (label)            — A∩B∩C
#   callouts    array, 2–4 opt: (label, heading, body)
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30 "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:80 "{{ action_title }}"

# 3 overlapping circles (440px each). Centers:
#   A = (340, 580) → top-left, accent ochre
#   B = (580, 580) → top-right, navy-500
#   C = (460, 750) → bottom-center, navy-400
shape 120,360  440x440 kind:oval fill:accent     fill-opacity:0.7
shape 360,360  440x440 kind:oval fill:navy-500   fill-opacity:0.7
shape 240,530  440x440 kind:oval fill:navy-400   fill-opacity:0.7

# Set labels (outside the circles).
text 60,400   style:h-idx maxwidth:120 align:right                              "{{ sets[0].label }}"
text 60,432   style:detail color:steel maxwidth:120 align:right                 "{{ sets[0].body }}"
text 820,400  style:h-idx maxwidth:200                                          "{{ sets[1].label }}"
text 820,432  style:detail color:steel maxwidth:200                             "{{ sets[1].body }}"
text 60,890   style:h-idx maxwidth:160                                          "{{ sets[2].label }}"
text 60,922   style:detail color:steel maxwidth:160                             "{{ sets[2].body }}"

# Intersection labels in the overlap zones.
text 340,500  style:detail color:ink maxwidth:240 align:center maxheight:24 "{{ pairs[0].label }}"
text 220,720  style:detail color:ink maxwidth:240 align:center maxheight:24 "{{ pairs[2].label }}"
text 460,720  style:detail color:ink maxwidth:240 align:center maxheight:24 "{{ pairs[1].label }}"

# Triple-overlap center.
text 340,620  style:detail color:off-white maxwidth:240 align:center maxheight:24 "Center"
text 340,650  style:body color:off-white   maxwidth:240 align:center maxheight:48 "{{ center.label }}"

# Right column callouts with hairlines.
rect 1020,440 800x1 fill:fog
text 1020,460 style:h-idx color:accent maxwidth:760 maxheight:24 "{{ callouts[0].label }}"
text 1020,500 style:h-hd  maxwidth:760 maxheight:40              "{{ callouts[0].heading }}"
text 1020,560 style:body  maxwidth:760 maxheight:80              "{{ callouts[0].body }}"

rect 1020,680 800x1 fill:fog
text 1020,700 style:h-idx color:accent maxwidth:760 maxheight:24 "{{ callouts[1].label }}"
text 1020,740 style:h-hd  maxwidth:760 maxheight:40              "{{ callouts[1].heading }}"
text 1020,800 style:body  maxwidth:760 maxheight:80              "{{ callouts[1].body }}"

rect 1020,920 800x1 fill:fog

footer left:"{{ footer_left }}" right:"{{ footer_right }}"