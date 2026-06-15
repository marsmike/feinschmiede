---
role: reference
ideal_count: [4, 8]
data_band: table
comparison: false
narrative_role: risk
description: 'Tabular risk register: numbered rows with risk description, probability, impact, severity badge, mitigation text, and owner'
source: feinschliff
source_hash: 928694b360c4
---
# risk-register — tabular risk register. Rows × columns:
#   id, name, probability, impact, severity (colored cell), mitigation, owner.
# Severity cell is filled with one of severity-low / severity-medium /
# severity-high; caller supplies the token name as `severity_color` per
# risk because the DSL grammar's `if:` does not support `==` comparisons.
#
# Slot schema:
#   logo, pgmeta, tracker, kicker — header
#   action_title  string, ≤180
#   risks  array, 4–8 objects:
#       id              int 1..N
#       name            string, ≤80
#       probability     int 1..5
#       impact          int 1..5
#       severity        enum "low" | "medium" | "high"  (label shown in cell)
#       severity_color  string, one of "severity-low" | "severity-medium"
#                       | "severity-high"   (token name for the cell fill)
#       mitigation      string, ≤140
#       owner           string, ≤40, opt
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

# Title block.
rect 100,180 80x4 fill:ink
text 100,220 style:tracker    maxwidth:1720 maxheight:24 "{{ tracker }}"
text 100,260 style:act-kicker color:accent maxwidth:1720 maxheight:30 "{{ kicker }}"
text 100,300 style:act-title  maxwidth:1720 maxheight:140 "{{ action_title }}"

# Column geometry (1720px wide content area):
#   ID:         x=100  w=60
#   Name:       x=180  w=540
#   P:          x=740  w=60
#   I:          x=820  w=60
#   Severity:   x=900  w=160  (colored cell)
#   Mitigation: x=1080 w=620
#   Owner:      x=1720 w=100  (right edge — actually x=1700 w=120)

# Header row.
rect 100,460 1720x2 fill:ink
text 100,470  style:h-idx maxwidth:60  maxheight:24            "#"
text 180,470  style:h-idx maxwidth:540 maxheight:24            "RISK"
text 740,470  style:h-idx maxwidth:60  maxheight:24 align:center "P"
text 820,470  style:h-idx maxwidth:60  maxheight:24 align:center "I"
text 900,470  style:h-idx maxwidth:160 maxheight:24            "SEVERITY"
text 1080,470 style:h-idx maxwidth:600 maxheight:24            "MITIGATION"
text 1700,470 style:h-idx maxwidth:120 maxheight:24 align:right "OWNER"

# Data rows — 70px pitch, hairline above each row.
# Severity cell uses fill:{{ risks[N].severity_color }} (token name).

# --- Row 0 ---
rect 100,500   1720x1 fill:fog
text 100,520   style:body maxwidth:60  maxheight:30                "{{ risks[0].id }}"
text 180,520   style:body maxwidth:540 maxheight:30                "{{ risks[0].name }}"
text 740,520   style:body maxwidth:60  maxheight:30 align:center   "{{ risks[0].probability }}"
text 820,520   style:body maxwidth:60  maxheight:30 align:center   "{{ risks[0].impact }}"
rect 900,510   140x40 fill:"{{ risks[0].severity_color }}"
text 920,514   style:body color:paper maxwidth:120 maxheight:32    "{{ risks[0].severity }}"
text 1080,520  style:body maxwidth:600 maxheight:30                "{{ risks[0].mitigation }}"
text 1700,520  style:detail maxwidth:120 maxheight:30 align:right  "{{ risks[0].owner }}"

# --- Row 1 ---
rect 100,570   1720x1 fill:fog
text 100,590   style:body maxwidth:60  maxheight:30                "{{ risks[1].id }}"
text 180,590   style:body maxwidth:540 maxheight:30                "{{ risks[1].name }}"
text 740,590   style:body maxwidth:60  maxheight:30 align:center   "{{ risks[1].probability }}"
text 820,590   style:body maxwidth:60  maxheight:30 align:center   "{{ risks[1].impact }}"
rect 900,580   140x40 fill:"{{ risks[1].severity_color }}"
text 920,584   style:body color:paper maxwidth:120 maxheight:32    "{{ risks[1].severity }}"
text 1080,590  style:body maxwidth:600 maxheight:30                "{{ risks[1].mitigation }}"
text 1700,590  style:detail maxwidth:120 maxheight:30 align:right  "{{ risks[1].owner }}"

# --- Row 2 ---
rect 100,640   1720x1 fill:fog
text 100,660   style:body maxwidth:60  maxheight:30                "{{ risks[2].id }}"
text 180,660   style:body maxwidth:540 maxheight:30                "{{ risks[2].name }}"
text 740,660   style:body maxwidth:60  maxheight:30 align:center   "{{ risks[2].probability }}"
text 820,660   style:body maxwidth:60  maxheight:30 align:center   "{{ risks[2].impact }}"
rect 900,650   140x40 fill:"{{ risks[2].severity_color }}"
text 920,654   style:body color:paper maxwidth:120 maxheight:32    "{{ risks[2].severity }}"
text 1080,660  style:body maxwidth:600 maxheight:30                "{{ risks[2].mitigation }}"
text 1700,660  style:detail maxwidth:120 maxheight:30 align:right  "{{ risks[2].owner }}"

# --- Row 3 ---
rect 100,710   1720x1 fill:fog
text 100,730   style:body maxwidth:60  maxheight:30                "{{ risks[3].id }}"
text 180,730   style:body maxwidth:540 maxheight:30                "{{ risks[3].name }}"
text 740,730   style:body maxwidth:60  maxheight:30 align:center   "{{ risks[3].probability }}"
text 820,730   style:body maxwidth:60  maxheight:30 align:center   "{{ risks[3].impact }}"
rect 900,720   140x40 fill:"{{ risks[3].severity_color }}"
text 920,724   style:body color:paper maxwidth:120 maxheight:32    "{{ risks[3].severity }}"
text 1080,730  style:body maxwidth:600 maxheight:30                "{{ risks[3].mitigation }}"
text 1700,730  style:detail maxwidth:120 maxheight:30 align:right  "{{ risks[3].owner }}"

# --- Row 4 (optional) ---
rect 100,780   1720x1 fill:fog                                                  if:"{{ risks[4].name }}"
text 100,800   style:body maxwidth:60  maxheight:30                              if:"{{ risks[4].name }}" "{{ risks[4].id }}"
text 180,800   style:body maxwidth:540 maxheight:30                              if:"{{ risks[4].name }}" "{{ risks[4].name }}"
text 740,800   style:body maxwidth:60  maxheight:30 align:center                 if:"{{ risks[4].name }}" "{{ risks[4].probability }}"
text 820,800   style:body maxwidth:60  maxheight:30 align:center                 if:"{{ risks[4].name }}" "{{ risks[4].impact }}"
rect 900,790   140x40 fill:"{{ risks[4].severity_color }}"                       if:"{{ risks[4].name }}"
text 920,794   style:body color:paper maxwidth:120 maxheight:32                  if:"{{ risks[4].name }}" "{{ risks[4].severity }}"
text 1080,800  style:body maxwidth:600 maxheight:30                              if:"{{ risks[4].name }}" "{{ risks[4].mitigation }}"
text 1700,800  style:detail maxwidth:120 maxheight:30 align:right                if:"{{ risks[4].name }}" "{{ risks[4].owner }}"

# --- Row 5 (optional) ---
rect 100,850   1720x1 fill:fog                                                  if:"{{ risks[5].name }}"
text 100,870   style:body maxwidth:60  maxheight:30                              if:"{{ risks[5].name }}" "{{ risks[5].id }}"
text 180,870   style:body maxwidth:540 maxheight:30                              if:"{{ risks[5].name }}" "{{ risks[5].name }}"
text 740,870   style:body maxwidth:60  maxheight:30 align:center                 if:"{{ risks[5].name }}" "{{ risks[5].probability }}"
text 820,870   style:body maxwidth:60  maxheight:30 align:center                 if:"{{ risks[5].name }}" "{{ risks[5].impact }}"
rect 900,860   140x40 fill:"{{ risks[5].severity_color }}"                       if:"{{ risks[5].name }}"
text 920,864   style:body color:paper maxwidth:120 maxheight:32                  if:"{{ risks[5].name }}" "{{ risks[5].severity }}"
text 1080,870  style:body maxwidth:600 maxheight:30                              if:"{{ risks[5].name }}" "{{ risks[5].mitigation }}"
text 1700,870  style:detail maxwidth:120 maxheight:30 align:right                if:"{{ risks[5].name }}" "{{ risks[5].owner }}"

# --- Row 6 (optional) ---
rect 100,920   1720x1 fill:fog                                                  if:"{{ risks[6].name }}"
text 100,940   style:body maxwidth:60  maxheight:30                              if:"{{ risks[6].name }}" "{{ risks[6].id }}"
text 180,940   style:body maxwidth:540 maxheight:30                              if:"{{ risks[6].name }}" "{{ risks[6].name }}"
text 740,940   style:body maxwidth:60  maxheight:30 align:center                 if:"{{ risks[6].name }}" "{{ risks[6].probability }}"
text 820,940   style:body maxwidth:60  maxheight:30 align:center                 if:"{{ risks[6].name }}" "{{ risks[6].impact }}"
rect 900,930   140x40 fill:"{{ risks[6].severity_color }}"                       if:"{{ risks[6].name }}"
text 920,934   style:body color:paper maxwidth:120 maxheight:32                  if:"{{ risks[6].name }}" "{{ risks[6].severity }}"
text 1080,940  style:body maxwidth:600 maxheight:30                              if:"{{ risks[6].name }}" "{{ risks[6].mitigation }}"
text 1700,940  style:detail maxwidth:120 maxheight:30 align:right                if:"{{ risks[6].name }}" "{{ risks[6].owner }}"

# --- Row 7 (optional) ---
rect 100,990   1720x1 fill:fog                                                  if:"{{ risks[7].name }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"