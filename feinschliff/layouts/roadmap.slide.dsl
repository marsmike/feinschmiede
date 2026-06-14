---
role: data-timeline
ideal_count: [3, 8]
data_band: none
comparison: true
narrative_role: plan
time_axis_role: strategic
description: 'Multi-workstream roadmap grid: four rows × five quarter columns, colour-coded milestone cells, milestone diamond markers above'
source: feinschliff
source_hash: 6dfae3f1880e
---
# roadmap — strategic plan. Workstream rows × time-period columns with
# per-phase status coloring and optional milestone diamonds above the
# row band. Distinct from gantt (tactical, start/span bars) and from
# timeline (chronological narrative).
#
# Status coloring follows the "caller provides the token name in a slot"
# pattern (the DSL `if:` does not support `==`). Each phase carries a
# `color` slot with one of the literal token names "status-done",
# "status-current", "status-next", or "fog" (for skip).
#
# Slot schema:
#   logo, pgmeta, tracker, kicker, action_title — header
#   periods       array, 5 strings (e.g. "Q4 2026", "Q1 2027", "Q2", "Q3", "Q4")
#   workstreams   array, 2-4 objects:
#       name        string, ≤40
#       owner       string, ≤40, opt
#       phases      array, length 5, each:
#           status      enum "done" | "current" | "next" | "skip"
#           label       string, ≤30, opt
#           color       string token name
#                       ("status-done" | "status-current" | "status-next"
#                        | "fog")
#   milestones    array, opt, 0-2 objects:
#       at_period   int 0..4
#       label       string, ≤32
#   legend        string, ≤120, opt
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

# Title block.
rect 100,180 80x4 fill:ink
text 100,220 style:tracker    maxwidth:1720 maxheight:24 "{{ tracker }}"
text 100,260 style:act-kicker color:accent maxwidth:1720 maxheight:30 "{{ kicker }}"
text 100,300 style:act-title  maxwidth:1720 maxheight:140 "{{ action_title }}"

# Legend — right-edge band above the period headers (the title block
# claims maxheight 140 down to y=440; the legend takes the strip from
# y=440 to y=460 in the gutter).
text 100,440 style:detail maxwidth:1720 maxheight:20 align:right "{{ legend }}"

# Column geometry — 5 periods. Workstream label column: x=100 w=260.
# Period columns start at x=380, 290px wide each, ending at x=1830.
# Column centers: 525, 815, 1105, 1395, 1685.
#
# Milestone diamond x (24x24, so subtract 12 from center):
#   x = at_period*290 + 513
# Milestone label x (maxwidth=240, centered on the column → x = center - 120):
#   x = at_period*290 + 405

# Milestone band — diamond above the row band, label below it. Two
# slots supported. Each is fully `if:`-guarded on the label.
shape {{ milestones[0].at_period*290+513 }},444 24x24 kind:diamond fill:accent           if:"{{ milestones[0].label }}"
text  {{ milestones[0].at_period*290+405 }},474 style:h-idx color:accent maxwidth:240 maxheight:20 align:center if:"{{ milestones[0].label }}" "{{ milestones[0].label }}"
shape {{ milestones[1].at_period*290+513 }},444 24x24 kind:diamond fill:accent           if:"{{ milestones[1].label }}"
text  {{ milestones[1].at_period*290+405 }},474 style:h-idx color:accent maxwidth:240 maxheight:20 align:center if:"{{ milestones[1].label }}" "{{ milestones[1].label }}"

# Column headers — period labels.
text 380,520  style:h-idx maxwidth:290 maxheight:24 align:center "{{ periods[0] }}"
text 670,520  style:h-idx maxwidth:290 maxheight:24 align:center "{{ periods[1] }}"
text 960,520  style:h-idx maxwidth:290 maxheight:24 align:center "{{ periods[2] }}"
text 1250,520 style:h-idx maxwidth:290 maxheight:24 align:center "{{ periods[3] }}"
text 1540,520 style:h-idx maxwidth:290 maxheight:24 align:center "{{ periods[4] }}"

# Underline beneath the period headers, then faint vertical column
# dividers spanning the row band.
rect 100,560  1720x2  fill:ink
rect 370,560  1x420   fill:fog
rect 660,560  1x420   fill:fog
rect 950,560  1x420   fill:fog
rect 1240,560 1x420   fill:fog
rect 1530,560 1x420   fill:fog
rect 1820,560 1x420   fill:fog

# Workstream rows — 100px pitch starting at y=600. Phase cells are
# 274×64 inset 8px from the column edges.

# --- Row 0 ---
rect 100,680 1720x1 fill:fog
text 100,600 style:h-hd  color:accent maxwidth:260 maxheight:40 "{{ workstreams[0].name }}"
text 100,644 style:detail            maxwidth:260 maxheight:24 "{{ workstreams[0].owner }}"
rect 378,600  274x64 fill:"{{ workstreams[0].phases[0].color }}"
text 378,616  style:body color:paper maxwidth:274 maxheight:32 align:center "{{ workstreams[0].phases[0].label }}"
rect 668,600  274x64 fill:"{{ workstreams[0].phases[1].color }}"
text 668,616  style:body color:paper maxwidth:274 maxheight:32 align:center "{{ workstreams[0].phases[1].label }}"
rect 958,600  274x64 fill:"{{ workstreams[0].phases[2].color }}"
text 958,616  style:body color:paper maxwidth:274 maxheight:32 align:center "{{ workstreams[0].phases[2].label }}"
rect 1248,600 274x64 fill:"{{ workstreams[0].phases[3].color }}"
text 1248,616 style:body color:paper maxwidth:274 maxheight:32 align:center "{{ workstreams[0].phases[3].label }}"
rect 1538,600 274x64 fill:"{{ workstreams[0].phases[4].color }}"
text 1538,616 style:body color:paper maxwidth:274 maxheight:32 align:center "{{ workstreams[0].phases[4].label }}"

# --- Row 1 ---
rect 100,780 1720x1 fill:fog
text 100,700 style:h-hd  color:accent maxwidth:260 maxheight:40 "{{ workstreams[1].name }}"
text 100,744 style:detail            maxwidth:260 maxheight:24 "{{ workstreams[1].owner }}"
rect 378,700  274x64 fill:"{{ workstreams[1].phases[0].color }}"
text 378,716  style:body color:paper maxwidth:274 maxheight:32 align:center "{{ workstreams[1].phases[0].label }}"
rect 668,700  274x64 fill:"{{ workstreams[1].phases[1].color }}"
text 668,716  style:body color:paper maxwidth:274 maxheight:32 align:center "{{ workstreams[1].phases[1].label }}"
rect 958,700  274x64 fill:"{{ workstreams[1].phases[2].color }}"
text 958,716  style:body color:paper maxwidth:274 maxheight:32 align:center "{{ workstreams[1].phases[2].label }}"
rect 1248,700 274x64 fill:"{{ workstreams[1].phases[3].color }}"
text 1248,716 style:body color:paper maxwidth:274 maxheight:32 align:center "{{ workstreams[1].phases[3].label }}"
rect 1538,700 274x64 fill:"{{ workstreams[1].phases[4].color }}"
text 1538,716 style:body color:paper maxwidth:274 maxheight:32 align:center "{{ workstreams[1].phases[4].label }}"

# --- Row 2 ---
rect 100,880 1720x1 fill:fog
text 100,800 style:h-hd  color:accent maxwidth:260 maxheight:40 "{{ workstreams[2].name }}"
text 100,844 style:detail            maxwidth:260 maxheight:24 "{{ workstreams[2].owner }}"
rect 378,800  274x64 fill:"{{ workstreams[2].phases[0].color }}"
text 378,816  style:body color:paper maxwidth:274 maxheight:32 align:center "{{ workstreams[2].phases[0].label }}"
rect 668,800  274x64 fill:"{{ workstreams[2].phases[1].color }}"
text 668,816  style:body color:paper maxwidth:274 maxheight:32 align:center "{{ workstreams[2].phases[1].label }}"
rect 958,800  274x64 fill:"{{ workstreams[2].phases[2].color }}"
text 958,816  style:body color:paper maxwidth:274 maxheight:32 align:center "{{ workstreams[2].phases[2].label }}"
rect 1248,800 274x64 fill:"{{ workstreams[2].phases[3].color }}"
text 1248,816 style:body color:paper maxwidth:274 maxheight:32 align:center "{{ workstreams[2].phases[3].label }}"
rect 1538,800 274x64 fill:"{{ workstreams[2].phases[4].color }}"
text 1538,816 style:body color:paper maxwidth:274 maxheight:32 align:center "{{ workstreams[2].phases[4].label }}"

# --- Row 3 (optional) ---
rect 100,980 1720x1 fill:fog                                                                if:"{{ workstreams[3].name }}"
text 100,900 style:h-hd  color:accent maxwidth:260 maxheight:40                              if:"{{ workstreams[3].name }}" "{{ workstreams[3].name }}"
text 100,944 style:detail            maxwidth:260 maxheight:24                               if:"{{ workstreams[3].name }}" "{{ workstreams[3].owner }}"
rect 378,900  274x64 fill:"{{ workstreams[3].phases[0].color }}"                             if:"{{ workstreams[3].name }}"
text 378,916  style:body color:paper maxwidth:274 maxheight:32 align:center                  if:"{{ workstreams[3].name }}" "{{ workstreams[3].phases[0].label }}"
rect 668,900  274x64 fill:"{{ workstreams[3].phases[1].color }}"                             if:"{{ workstreams[3].name }}"
text 668,916  style:body color:paper maxwidth:274 maxheight:32 align:center                  if:"{{ workstreams[3].name }}" "{{ workstreams[3].phases[1].label }}"
rect 958,900  274x64 fill:"{{ workstreams[3].phases[2].color }}"                             if:"{{ workstreams[3].name }}"
text 958,916  style:body color:paper maxwidth:274 maxheight:32 align:center                  if:"{{ workstreams[3].name }}" "{{ workstreams[3].phases[2].label }}"
rect 1248,900 274x64 fill:"{{ workstreams[3].phases[3].color }}"                             if:"{{ workstreams[3].name }}"
text 1248,916 style:body color:paper maxwidth:274 maxheight:32 align:center                  if:"{{ workstreams[3].name }}" "{{ workstreams[3].phases[3].label }}"
rect 1538,900 274x64 fill:"{{ workstreams[3].phases[4].color }}"                             if:"{{ workstreams[3].name }}"
text 1538,916 style:body color:paper maxwidth:274 maxheight:32 align:center                  if:"{{ workstreams[3].name }}" "{{ workstreams[3].phases[4].label }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"