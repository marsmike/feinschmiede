---
role: data-comparison
ideal_count: [3, 12]
data_band: chart
comparison: true
narrative_role: custom-viz
diagram_complexity: simple
description: Title and eyebrow top-left, SVG infographic occupying central body area, so-what and source lines below
source: feinschliff
source_hash: c903e06e3a13
---
# svg-infographic — custom data viz (bars, axes, legends, stat cards) that
# doesn't fit bar-chart / stacked-bar / kpi-grid / scorecard / funnel.
#
# Slot schema:
#   logo, pgmeta, tracker, action_title, so_what, source — shared
#   diagram_dsl   string, required — SVG DSL body (no `canvas` line)

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30 "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:80 "{{ action_title }}"

svg diagram 100,360 1720x480 {
  {{ diagram_dsl }}
}

text 100,870 style:detail color:graphite maxwidth:1720 maxheight:30 if:"{{ so_what }}" "So what: {{ so_what }}"
text 100,940 style:detail maxwidth:1720 "{{ source }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"