---
role: content-columns
ideal_count: [2, 3]
data_band: none
comparison: false
narrative_role: recommendation
narrative_act: resolution
description: 'Three recommendation cards across: rule, numbered label, bold action headline, bullet evidence, accent impact KPI + owner'
follows_not: [role=title-primary, role=agenda, role=chapter-opener]
follows_well: [role=content-columns, narrative_act=complication]
source: feinschliff
source_hash: fbfdfe0e56e7
---
# recommendation — Pyramid Principle closer-but-one. 2–3 named "moves"
# side by side, each with a verb-led headline, supporting sub-initiatives,
# an impact metric in accent, and an owner tag. Lead with the answer, not
# the analysis.
#
# Slot schema:
#   logo, pgmeta, tracker, kicker — header
#   action_title     string, ≤180     (the umbrella conclusion)
#   recommendations  array, 2–3 objects:
#       verb_phrase     string, ≤60   (imperative-led: "Grow ARR by 20%")
#       sub_initiatives array, 3–7 strings (≤80 each)
#       impact_metric   string, ≤60   (e.g. "+$4.2M ARR" or "−12% churn")
#       owner           string, ≤40, opt
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

# Title block — eyebrow + kicker + action_title.
rect 100,180 80x4 fill:ink
text 100,220 style:tracker    maxwidth:1720 maxheight:24 "{{ tracker }}"
text 100,260 style:act-kicker color:accent maxwidth:1720 maxheight:30 "{{ kicker }}"
text 100,300 style:act-title  maxwidth:1720 maxheight:140 "{{ action_title }}"

# Three recommendation columns at x = 100 / 720 / 1340; each 540 wide.
# Layout per column (top-down):
#   500  gold rule
#   540  MOVE 0N counter
#   580  verb_phrase heading (h-hd, up to ~120px = 3 lines)
#   720  sub-initiative bullets, 3–7 rows × 36px = up to ~252 stack height
#   910  impact_metric (h-hd in accent)
#   956  owner (detail)
# Footer is at y=1000.

# --- Column 0 ---
rect 100,500   80x4 fill:accent
text 100,540   style:h-idx   color:accent maxwidth:540 maxheight:20 "MOVE 01"
text 100,580   style:h-hd    maxwidth:540 maxheight:120              "{{ recommendations[0].verb_phrase }}"

text 100,720   style:body    maxwidth:540 maxheight:32 if:"{{ recommendations[0].sub_initiatives[0] }}" "•  {{ recommendations[0].sub_initiatives[0] }}"
text 100,752   style:body    maxwidth:540 maxheight:32 if:"{{ recommendations[0].sub_initiatives[1] }}" "•  {{ recommendations[0].sub_initiatives[1] }}"
text 100,784   style:body    maxwidth:540 maxheight:32 if:"{{ recommendations[0].sub_initiatives[2] }}" "•  {{ recommendations[0].sub_initiatives[2] }}"
text 100,816   style:body    maxwidth:540 maxheight:32 if:"{{ recommendations[0].sub_initiatives[3] }}" "•  {{ recommendations[0].sub_initiatives[3] }}"
text 100,848   style:body    maxwidth:540 maxheight:32 if:"{{ recommendations[0].sub_initiatives[4] }}" "•  {{ recommendations[0].sub_initiatives[4] }}"
text 100,880   style:body    maxwidth:540 maxheight:32 if:"{{ recommendations[0].sub_initiatives[5] }}" "•  {{ recommendations[0].sub_initiatives[5] }}"

text 100,920   style:h-hd    color:accent maxwidth:540 maxheight:40  "{{ recommendations[0].impact_metric }}"
text 100,966   style:detail  maxwidth:540 maxheight:20               "{{ recommendations[0].owner }}"

# --- Column 1 ---
rect 720,500   80x4 fill:accent
text 720,540   style:h-idx   color:accent maxwidth:540 maxheight:20 "MOVE 02"
text 720,580   style:h-hd    maxwidth:540 maxheight:120              "{{ recommendations[1].verb_phrase }}"

text 720,720   style:body    maxwidth:540 maxheight:32 if:"{{ recommendations[1].sub_initiatives[0] }}" "•  {{ recommendations[1].sub_initiatives[0] }}"
text 720,752   style:body    maxwidth:540 maxheight:32 if:"{{ recommendations[1].sub_initiatives[1] }}" "•  {{ recommendations[1].sub_initiatives[1] }}"
text 720,784   style:body    maxwidth:540 maxheight:32 if:"{{ recommendations[1].sub_initiatives[2] }}" "•  {{ recommendations[1].sub_initiatives[2] }}"
text 720,816   style:body    maxwidth:540 maxheight:32 if:"{{ recommendations[1].sub_initiatives[3] }}" "•  {{ recommendations[1].sub_initiatives[3] }}"
text 720,848   style:body    maxwidth:540 maxheight:32 if:"{{ recommendations[1].sub_initiatives[4] }}" "•  {{ recommendations[1].sub_initiatives[4] }}"
text 720,880   style:body    maxwidth:540 maxheight:32 if:"{{ recommendations[1].sub_initiatives[5] }}" "•  {{ recommendations[1].sub_initiatives[5] }}"

text 720,920   style:h-hd    color:accent maxwidth:540 maxheight:40  "{{ recommendations[1].impact_metric }}"
text 720,966   style:detail  maxwidth:540 maxheight:20               "{{ recommendations[1].owner }}"

# --- Column 2 (optional — guarded by if:) ---
rect 1340,500  80x4 fill:accent                                       if:"{{ recommendations[2].verb_phrase }}"
text 1340,540  style:h-idx   color:accent maxwidth:540 maxheight:20   if:"{{ recommendations[2].verb_phrase }}" "MOVE 03"
text 1340,580  style:h-hd    maxwidth:540 maxheight:120               if:"{{ recommendations[2].verb_phrase }}" "{{ recommendations[2].verb_phrase }}"

text 1340,720  style:body    maxwidth:540 maxheight:32 if:"{{ recommendations[2].sub_initiatives[0] }}" "•  {{ recommendations[2].sub_initiatives[0] }}"
text 1340,752  style:body    maxwidth:540 maxheight:32 if:"{{ recommendations[2].sub_initiatives[1] }}" "•  {{ recommendations[2].sub_initiatives[1] }}"
text 1340,784  style:body    maxwidth:540 maxheight:32 if:"{{ recommendations[2].sub_initiatives[2] }}" "•  {{ recommendations[2].sub_initiatives[2] }}"
text 1340,816  style:body    maxwidth:540 maxheight:32 if:"{{ recommendations[2].sub_initiatives[3] }}" "•  {{ recommendations[2].sub_initiatives[3] }}"
text 1340,848  style:body    maxwidth:540 maxheight:32 if:"{{ recommendations[2].sub_initiatives[4] }}" "•  {{ recommendations[2].sub_initiatives[4] }}"
text 1340,880  style:body    maxwidth:540 maxheight:32 if:"{{ recommendations[2].sub_initiatives[5] }}" "•  {{ recommendations[2].sub_initiatives[5] }}"

text 1340,920  style:h-hd    color:accent maxwidth:540 maxheight:40   if:"{{ recommendations[2].verb_phrase }}" "{{ recommendations[2].impact_metric }}"
text 1340,966  style:detail  maxwidth:540 maxheight:20                if:"{{ recommendations[2].verb_phrase }}" "{{ recommendations[2].owner }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"