---
role: data-timeline
ideal_count: [3, 7]
data_band: none
comparison: false
description: Five chevron/arrow steps in a row, one highlighted in accent color as active stage; title above, description in each step
source: feinschliff
source_hash: aaaf8d138c55
---
# process-flow — 5 chevron stages pointing right; one highlighted as
# active in the brand accent.
#
# Slot schema (data-slots from feinschliff-2026.html · 21):
#   logo, pgmeta, tracker, kicker, action_title — header
#   stages — array, 3–7 objects: counter, heading, body, active? bool
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30 "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:160 "{{ action_title }}"

# 5 chevrons, each 360w × 360h at y=480, pitch = 306 (no visible gap).
# Chevron geometry with adj1=0.15: notch + point insets are 54 px each
# (0.15 × min(w,h) = 0.15 × 360). For pixel-snug interlock the next
# chevron's left edge sits where the previous one's point tip lands —
# i.e. pitch = w - inset = 360 - 54 = 306. Text x shifts in lockstep.
#   ss = min(w,h) = 360
#   notch+point inset = 0.15 * 360 = 54 px each
#   body width = 360 - 108 = 252 px  (text maxwidth=220 fits with slack)
shape 80,480    360x360 kind:chevron adj1:0.15 fill:paper-2 stroke:fog
shape 386,480   360x360 kind:chevron adj1:0.15 fill:paper-2 stroke:fog
shape 692,480   360x360 kind:chevron adj1:0.15 fill:accent
shape 998,480   360x360 kind:chevron adj1:0.15 fill:paper-2 stroke:fog
shape 1304,480  360x360 kind:chevron adj1:0.15 fill:paper-2 stroke:fog

# Text x = chevron_x + inset(54) + margin(16) = chevron_x + 70 so labels
# sit inside the rectangular BODY of their own chevron, never bleeding
# into the previous chevron's point area. Step = 306 (matches pitch).
text 150,520   style:h-idx color:accent maxwidth:220 "{{ stages[0].counter }}"
text 150,560   style:h-hd  maxwidth:220 maxheight:60  "{{ stages[0].heading }}"
text 150,650   style:body  maxwidth:220 maxheight:160 "{{ stages[0].body }}"

text 456,520   style:h-idx color:accent maxwidth:220 "{{ stages[1].counter }}"
text 456,560   style:h-hd  maxwidth:220 maxheight:60  "{{ stages[1].heading }}"
text 456,650   style:body  maxwidth:220 maxheight:160 "{{ stages[1].body }}"

text 762,520   style:h-idx color:ink   maxwidth:220 "{{ stages[2].counter }}"
text 762,560   style:h-hd  color:ink   maxwidth:220 maxheight:60  "{{ stages[2].heading }}"
text 762,650   style:body  color:ink   maxwidth:220 maxheight:160 "{{ stages[2].body }}"

text 1068,520  style:h-idx color:accent maxwidth:220 "{{ stages[3].counter }}"
text 1068,560  style:h-hd  maxwidth:220 maxheight:60  "{{ stages[3].heading }}"
text 1068,650  style:body  maxwidth:220 maxheight:160 "{{ stages[3].body }}"

text 1374,520  style:h-idx color:accent maxwidth:220 "{{ stages[4].counter }}"
text 1374,560  style:h-hd  maxwidth:220 maxheight:60  "{{ stages[4].heading }}"
text 1374,650  style:body  maxwidth:220 maxheight:160 "{{ stages[4].body }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"