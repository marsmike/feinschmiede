---
role: closer
ideal_count: [2, 4]
data_band: none
comparison: false
narrative_act: resolution
description: 'Dark navy background, four takeaway cards across: gold rule, numbered index, bold heading, two-sentence elaboration each'
follows_not: [role=title-primary, role=agenda, role=chapter-opener]
follows_well: [role=content-columns, role=data-quantity, narrative_act=complication]
source: feinschliff
source_hash: 6c5ff399ae80
---
# key-takeaways — end-of-section summary on the dark ink ground. 2–4
# takeaway columns with gold rule, mono number, white heading, gray-blue
# body, mono uppercase owner.
#
# Slot schema (data-slots from feinschliff-2026.html · 25):
#   logo          string, optional
#   pgmeta        string, ≤40, opt
#   tracker       string, ≤60, opt
#   kicker        string, ≤40, opt
#   action_title  string, ≤180
#   cards         array, 2–4 objects: (counter ≤6, heading ≤40, body ≤200, owner ≤40 opt)
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

rect 0,0 1920x1080 fill:ink

header-dark pgmeta:"{{ pgmeta }}"

# act-head (overridden for dark — text in white).
text 100,180 style:tracker    color:silver       maxwidth:1720 maxheight:24 align:right "{{ tracker }}"
text 100,220 style:act-kicker color:accent       maxwidth:1720 maxheight:30            "{{ kicker }}"
text 100,260 style:act-title  color:off-white    maxwidth:1620 maxheight:180           "{{ action_title }}"

# Four takeaway columns. Each: gold rule, mono counter, white heading, body, owner.
rect 100,460   80x4 fill:accent
text 100,500   style:h-idx color:accent      maxwidth:380 maxheight:20  "{{ cards[0].counter }}"
text 100,540   style:h-hd  color:off-white   maxwidth:380 maxheight:80  "{{ cards[0].heading }}"
text 100,640   style:body  color:silver      maxwidth:380 maxheight:240 "{{ cards[0].body }}"
text 100,940   style:detail color:off-white-2 maxwidth:380              "{{ cards[0].owner }}"

rect 560,460   80x4 fill:accent
text 560,500   style:h-idx color:accent      maxwidth:380 maxheight:20  "{{ cards[1].counter }}"
text 560,540   style:h-hd  color:off-white   maxwidth:380 maxheight:80  "{{ cards[1].heading }}"
text 560,640   style:body  color:silver      maxwidth:380 maxheight:240 "{{ cards[1].body }}"
text 560,940   style:detail color:off-white-2 maxwidth:380              "{{ cards[1].owner }}"

rect 1020,460  80x4 fill:accent
text 1020,500  style:h-idx color:accent      maxwidth:380 maxheight:20  "{{ cards[2].counter }}"
text 1020,540  style:h-hd  color:off-white   maxwidth:380 maxheight:80  "{{ cards[2].heading }}"
text 1020,640  style:body  color:silver      maxwidth:380 maxheight:240 "{{ cards[2].body }}"
text 1020,940  style:detail color:off-white-2 maxwidth:380              "{{ cards[2].owner }}"

rect 1480,460  80x4 fill:accent                                          if:"{{ cards[3].heading }}"
text 1480,500  style:h-idx color:accent      maxwidth:380 maxheight:20   if:"{{ cards[3].heading }}" "{{ cards[3].counter }}"
text 1480,540  style:h-hd  color:off-white   maxwidth:380 maxheight:80   if:"{{ cards[3].heading }}" "{{ cards[3].heading }}"
text 1480,640  style:body  color:silver      maxwidth:380 maxheight:240  if:"{{ cards[3].heading }}" "{{ cards[3].body }}"
text 1480,940  style:detail color:off-white-2 maxwidth:380               if:"{{ cards[3].heading }}" "{{ cards[3].owner }}"

footer-dark left:"{{ footer_left }}" right:"{{ footer_right }}"