---
role: closer
ideal_count: [3, 7]
data_band: none
comparison: false
narrative_role: close-action
narrative_act: resolution
description: 'Action table: up to five rows with accent verb, description, and right-aligned owner+date; eyebrow above title'
follows_not: [role=title-primary, role=agenda, narrative_act=situation]
follows_well: [layout=recommendation, narrative_act=resolution]
source: feinschliff
source_hash: 9124ffc0d290
---
# next-steps — closing slide. 3–7 immediate actions stacked vertically.
# Each row leads with a verb in accent, body of what, and right-aligned
# category eyebrow above who · when in detail style. Verb-first
# satisfies the action-verb-leading content lint.
#
# Slot schema:
#   logo, pgmeta, tracker, kicker — header
#   action_title  string, ≤180
#   actions  array, 3–7 objects:
#       verb     string, ≤24   (imperative — "Implement", "Hire", "Ship")
#       what     string, ≤120
#       who      string, ≤40, opt
#       when     string, ≤24, opt   (e.g. "EOQ", "2026-Q4", "Week of 03 Jun")
#       category string, ≤24, opt   (e.g. "TECH", "FINANCE", "PEOPLE")
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

# Title block.
rect 100,180 80x4 fill:ink
text 100,220 style:tracker    maxwidth:1720 maxheight:24 "{{ tracker }}"
text 100,260 style:act-kicker color:accent maxwidth:1720 maxheight:30 "{{ kicker }}"
text 100,300 style:act-title  maxwidth:1720 maxheight:140 "{{ action_title }}"

# Action rows — y = 500 + row_idx * 70. Hairline at top, verb (accent
# h-hd) on the left, what (body) in the middle, category + who·when on
# the right.
# Verb column:  x=100  w=260
# What column:  x=380  w=940
# Right column: x=1340 w=480

# --- Row 0 ---
rect 100,500   1720x1 fill:fog
text 100,514   style:h-hd   color:accent maxwidth:260 maxheight:40            "{{ actions[0].verb }}"
text 380,518   style:body   maxwidth:940 maxheight:40                          "{{ actions[0].what }}"
text 1340,514  style:h-idx  color:accent maxwidth:480 maxheight:20 align:right "{{ actions[0].category }}"
text 1340,540  style:detail maxwidth:480 maxheight:20 align:right              "{{ actions[0].who }} · {{ actions[0].when }}"

# --- Row 1 ---
rect 100,570   1720x1 fill:fog
text 100,584   style:h-hd   color:accent maxwidth:260 maxheight:40            "{{ actions[1].verb }}"
text 380,588   style:body   maxwidth:940 maxheight:40                          "{{ actions[1].what }}"
text 1340,584  style:h-idx  color:accent maxwidth:480 maxheight:20 align:right "{{ actions[1].category }}"
text 1340,610  style:detail maxwidth:480 maxheight:20 align:right              "{{ actions[1].who }} · {{ actions[1].when }}"

# --- Row 2 ---
rect 100,640   1720x1 fill:fog
text 100,654   style:h-hd   color:accent maxwidth:260 maxheight:40            "{{ actions[2].verb }}"
text 380,658   style:body   maxwidth:940 maxheight:40                          "{{ actions[2].what }}"
text 1340,654  style:h-idx  color:accent maxwidth:480 maxheight:20 align:right "{{ actions[2].category }}"
text 1340,680  style:detail maxwidth:480 maxheight:20 align:right              "{{ actions[2].who }} · {{ actions[2].when }}"

# --- Row 3 (optional) ---
rect 100,710   1720x1 fill:fog                                                  if:"{{ actions[3].verb }}"
text 100,724   style:h-hd   color:accent maxwidth:260 maxheight:40              if:"{{ actions[3].verb }}" "{{ actions[3].verb }}"
text 380,728   style:body   maxwidth:940 maxheight:40                            if:"{{ actions[3].verb }}" "{{ actions[3].what }}"
text 1340,724  style:h-idx  color:accent maxwidth:480 maxheight:20 align:right   if:"{{ actions[3].verb }}" "{{ actions[3].category }}"
text 1340,750  style:detail maxwidth:480 maxheight:20 align:right                if:"{{ actions[3].verb }}" "{{ actions[3].who }} · {{ actions[3].when }}"

# --- Row 4 (optional) ---
rect 100,780   1720x1 fill:fog                                                  if:"{{ actions[4].verb }}"
text 100,794   style:h-hd   color:accent maxwidth:260 maxheight:40              if:"{{ actions[4].verb }}" "{{ actions[4].verb }}"
text 380,798   style:body   maxwidth:940 maxheight:40                            if:"{{ actions[4].verb }}" "{{ actions[4].what }}"
text 1340,794  style:h-idx  color:accent maxwidth:480 maxheight:20 align:right   if:"{{ actions[4].verb }}" "{{ actions[4].category }}"
text 1340,820  style:detail maxwidth:480 maxheight:20 align:right                if:"{{ actions[4].verb }}" "{{ actions[4].who }} · {{ actions[4].when }}"

# --- Row 5 (optional) ---
rect 100,850   1720x1 fill:fog                                                  if:"{{ actions[5].verb }}"
text 100,864   style:h-hd   color:accent maxwidth:260 maxheight:40              if:"{{ actions[5].verb }}" "{{ actions[5].verb }}"
text 380,868   style:body   maxwidth:940 maxheight:40                            if:"{{ actions[5].verb }}" "{{ actions[5].what }}"
text 1340,864  style:h-idx  color:accent maxwidth:480 maxheight:20 align:right   if:"{{ actions[5].verb }}" "{{ actions[5].category }}"
text 1340,890  style:detail maxwidth:480 maxheight:20 align:right                if:"{{ actions[5].verb }}" "{{ actions[5].who }} · {{ actions[5].when }}"

# --- Row 6 (optional) ---
rect 100,920   1720x1 fill:fog                                                  if:"{{ actions[6].verb }}"
text 100,934   style:h-hd   color:accent maxwidth:260 maxheight:40              if:"{{ actions[6].verb }}" "{{ actions[6].verb }}"
text 380,938   style:body   maxwidth:940 maxheight:40                            if:"{{ actions[6].verb }}" "{{ actions[6].what }}"
text 1340,934  style:h-idx  color:accent maxwidth:480 maxheight:20 align:right   if:"{{ actions[6].verb }}" "{{ actions[6].category }}"
text 1340,960  style:detail maxwidth:480 maxheight:20 align:right                if:"{{ actions[6].verb }}" "{{ actions[6].who }} · {{ actions[6].when }}"

# Bottom hairline closes the grid.
rect 100,990   1720x1 fill:fog

footer left:"{{ footer_left }}" right:"{{ footer_right }}"