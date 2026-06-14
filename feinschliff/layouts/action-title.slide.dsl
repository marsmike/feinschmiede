---
role: title-primary
ideal_count: [1, 2]
data_band: kpi
comparison: false
narrative_act: resolution
description: Large action-title headline top-left, supporting paragraph left, two jumbo KPI numerals with label and caption right
follows_not: [role=closer, role=title-primary]
follows_well: [role=content-columns, role=data-comparison, role=data-quantity]
source: feinschliff
source_hash: 20d8cd96c043
---
# action-title — McKinsey-style takeaway slide. Title carries the
# so-what; supporting body + optional KPIs sit beneath; source line at
# bottom.
#
# Slot schema (data-slots from feinschliff-2026.html · 16):
#   logo               string, optional
#   pgmeta             string, ≤40, opt
#   tracker            string, ≤60, opt
#   kicker             string, ≤40, opt
#   action_title       string, ≤180
#   supporting_eyebrow string, ≤40, opt   (default "Supporting narrative"; override for i18n)
#   supporting_body    string, ≤320, opt
#   kpis               array, 0–2, opt    (value, unit, key, delta)
#   source             string, ≤160, opt
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

mck-head tracker:"{{ tracker }}" kicker:"{{ kicker }}" action_title:"{{ action_title }}"

# Two-column body: supporting narrative left, KPIs right.
rect 100,520 56x2 fill:ink
text 100,544 style:eyebrow maxwidth:760 maxheight:20 "{{ supporting_eyebrow|default(\"Supporting narrative\") }}"
text 100,584 style:body    maxwidth:780 maxheight:340 "{{ supporting_body }}"

# KPIs (right half of body row).
text 1000,540 style:kpi-value maxwidth:380 maxheight:120 "{{ kpis[0].value }}{{ kpis[0].unit }}"
text 1000,660 style:kpi-key   maxwidth:380 maxheight:24  "{{ kpis[0].key }}"
text 1000,692 style:kpi-delta maxwidth:380 maxheight:24  "{{ kpis[0].delta }}"
text 1440,540 style:kpi-value maxwidth:380 maxheight:120 "{{ kpis[1].value }}{{ kpis[1].unit }}"
text 1440,660 style:kpi-key   maxwidth:380 maxheight:24  "{{ kpis[1].key }}"
text 1440,692 style:kpi-delta maxwidth:380 maxheight:24  "{{ kpis[1].delta }}"

# Source line above footer.
text 100,940 style:detail maxwidth:1720 maxheight:24 "{{ source }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"