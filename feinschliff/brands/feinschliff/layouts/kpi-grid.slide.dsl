---
role: data-quantity
ideal_count: [2, 4]
data_band: kpi
comparison: false
description: 'Four KPI cells in a full-width hairline grid: jumbo number, unit superscript, metric label, and accent caption each'
source: feinschliff
source_hash: 2394a91cc730
---
# kpi-grid — 2–4 high-level quantitative figures, each with unit + label
# + optional delta. Cells share a hairline grid border.
#
# Slot schema (data-slots from feinschliff-2026.html · 07):
#   logo     string, optional
#   pgmeta   string, ≤40, opt
#   eyebrow  string, ≤60, opt
#   title    string, ≤80
#   kpis     array, 2–4 objects:
#       value  string, ≤10
#       unit   string, ≤8, opt
#       key    string, ≤40
#       delta  string, ≤20, opt
#   so_what  string, ≤160, opt — LLM-derived takeaway from the KPIs.
#            Linted for vagueness (see lib.content_validator
#            _check_so_what_vagueness).
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

# Title block.
rect 100,220 80x4 fill:ink
text 100,260 style:eyebrow maxwidth:1700 maxheight:30 "{{ eyebrow }}"
text 100,300 style:title   maxwidth:1700 maxheight:160 "{{ title }}"

# Left edge of the kpi grid — vertical hairline (canonical .kpi-grid
# border-left). The kpi-cell compounds emit the right/top/bottom strokes.
rect 100,540 1x300 fill:fog

# 4 cells, each 430w × 300h (canvas 1720 ÷ 4 = 430).
kpi-cell x:100  y:540 w:430 h:300 value:"{{ kpis[0].value }}" unit:"{{ kpis[0].unit }}" label:"{{ kpis[0].key }}" delta:"{{ kpis[0].delta }}"
kpi-cell x:530  y:540 w:430 h:300 value:"{{ kpis[1].value }}" unit:"{{ kpis[1].unit }}" label:"{{ kpis[1].key }}" delta:"{{ kpis[1].delta }}"
kpi-cell x:960  y:540 w:430 h:300 value:"{{ kpis[2].value }}" unit:"{{ kpis[2].unit }}" label:"{{ kpis[2].key }}" delta:"{{ kpis[2].delta }}"
kpi-cell x:1390 y:540 w:430 h:300 value:"{{ kpis[3].value }}" unit:"{{ kpis[3].unit }}" label:"{{ kpis[3].key }}" delta:"{{ kpis[3].delta }}"

text 100,890 style:detail color:graphite maxwidth:1720 maxheight:30 if:"{{ so_what }}" "So what: {{ so_what }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"