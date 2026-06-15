---
role: data-timeline
ideal_count: [3, 8]
data_band: chart
comparison: false
description: Full-width line chart with two series (accent + ink), five x-axis periods, legend top-right, title and source flanking
source: feinschliff
source_hash: e3e3b2e5cc90
---
# line-chart — trend over time with 2 series rendered as real polyline traces.
# Series coordinates are hardcoded in the layout (DSL has no arithmetic over
# `series[N].points`) — they render representative upward-trend curves; the
# YAML `series` slot is still consumed for legend labels.
#
# Slot schema:
#   logo, pgmeta, tracker, action_title, source — as bar-chart
#   periods       array, 4–8 strings (x-axis labels)
#   series        array, 1–3 objects: { name, points: number[] }
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30 "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:160 "{{ action_title }}"

# Chart frame.
rect 100,460 1720x420 fill:paper stroke:fog
# Axis baseline.
rect 100,880 1720x2 fill:ink

# Series A (accent) — upward trend mapped from points [10, 14, 18, 22, 24].
# stroke-width 6: thick enough to read clearly when the chart frame
# (1720×420) is downscaled into thumbnails and PDF exports without
# anti-aliasing dropping a hairline trace below visibility.
polyline 270,705 610,635 950,565 1290,495 1630,460 stroke:accent stroke-width:6
# Series B (graphite) — flatter trend mapped from points [12, 12, 14, 18, 20].
polyline 270,670 610,670 950,635 1290,565 1630,530 stroke:graphite stroke-width:6

# 5 period labels along the x-axis.
text 100,890  style:detail maxwidth:340 align:center "{{ periods[0] }}"
text 440,890  style:detail maxwidth:340 align:center "{{ periods[1] }}"
text 780,890  style:detail maxwidth:340 align:center "{{ periods[2] }}"
text 1120,890 style:detail maxwidth:340 align:center "{{ periods[3] }}"
text 1480,890 style:detail maxwidth:340 align:center "{{ periods[4] }}"

# Series legend.
rect 1480,200 16x16 fill:accent
text 1500,196 style:detail maxwidth:160 "{{ series[0].name }}"
rect 1660,200 16x16 fill:graphite
text 1680,196 style:detail maxwidth:160 "{{ series[1].name }}"

text 100,940 style:detail color:graphite maxwidth:1720 maxheight:30 if:"{{ so_what }}" "So what: {{ so_what }}"

# Source.
text 100,970 style:detail maxwidth:1720 "{{ source }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"