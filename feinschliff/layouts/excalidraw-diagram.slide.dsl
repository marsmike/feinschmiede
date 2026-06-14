---
role: concept-diagram
ideal_count: [2, 8]
data_band: none
comparison: false
narrative_role: system
diagram_complexity: simple
description: Title and eyebrow top-left, Excalidraw diagram occupying central body area, so-what line and source below
source: feinschliff
source_hash: 2c7559b4128b
---
# excalidraw-diagram — free-form concept diagram (boxes, arrows, flows,
# architectures). Use when content describes a system or relationship
# that does not fit bar/line/funnel/2x2/process-flow.
#
# Slot schema:
#   logo, pgmeta, tracker, action_title, so_what, source — shared
#   diagram_dsl   string, required — excalidraw DSL body (no `canvas` line)
#
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30 "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:80 "{{ action_title }}"

# Slot height is sized to roughly match the rendered diagram's natural aspect
# ratio. Default fixture rendering produces a ~7:1 wide PNG; a 1720×480 slot
# (3.6:1) would stretch boxes vertically into squares. 1720×320 (5.4:1) gives
# a closer fit and leaves room below for the "So what:" caption + source.
excalidraw diagram 100,400 1720x320 {
  {{ diagram_dsl }}
}

text 100,800 style:detail color:graphite maxwidth:1720 maxheight:30 if:"{{ so_what }}" "So what: {{ so_what }}"
text 100,870 style:detail maxwidth:1720 "{{ source }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"