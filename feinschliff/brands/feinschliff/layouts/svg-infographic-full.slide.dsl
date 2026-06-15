---
role: data-comparison
ideal_count: [8, 24]
data_band: chart
comparison: true
narrative_role: custom-viz
diagram_complexity: deep
description: 'Full-slide SVG infographic with minimal chrome: thin title strip top, infographic fills remaining height'
source: feinschliff
source_hash: e448e7748231
---
# svg-infographic-full — full-slide deep custom data viz / infographic.
# Use when the chart needs 8+ data points, custom annotations, callouts,
# legends, or composite primitives (stacked bars + paths + braces).
#
# Renders at virtual canvas 6880x2880 (4× the 1720x720 slot). PowerPoint
# downscales on insert for effectively high-DPI output.
#
# Slot schema:
#   logo, pgmeta, tracker, action_title — shared
#   diagram_dsl   string, required — SVG DSL body (no `canvas` line)
#   so_what       optional — embed inline callouts inside the diagram instead

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30 "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:60 "{{ action_title }}"

svg diagram 100,340 1720x720 virtual:6880x2880 {
  {{ diagram_dsl }}
}

text 100,1060 style:detail color:graphite maxwidth:1720 maxheight:20 if:"{{ so_what }}" "So what: {{ so_what }}"

# Note: `source` slot dropped — text at y=1080 overflowed canvas edge.
# Cite via speaker notes (deck-level `notes:` per slide) instead.

footer left:"{{ footer_left }}" right:"{{ footer_right }}"