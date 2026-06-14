---
role: data-timeline
ideal_count: [3, 8]
data_band: none
comparison: false
narrative_role: history
time_axis_role: chronological
description: Horizontal timeline rail with five dated milestones alternating above/below; phase span labels under rail; title above
source: feinschliff
source_hash: 15aafd048d5d
---
# timeline — chronological narrative. Horizontal axis with events as
# labeled markers above/below the line (alternating to reduce overlap),
# optional translucent phase bands behind the axis. Distinct from gantt
# (tactical project bars) and from roadmap (workstream × period grid):
# this layout answers "what happened when".
#
# Slot schema:
#   logo, pgmeta, tracker, kicker, action_title — header
#   axis_label    string, ≤80, opt          (e.g. "2018 → 2026")
#   events        array, exactly 5 objects:
#       date        string, ≤14   (e.g. "Q3 2024" or "May 2025")
#       label       string, ≤40
#       description string, ≤80, opt
#       side        enum "above" | "below"
#                   (advisory — this layout alternates by index: events
#                   0/2/4 render above, events 1/3 render below. Callers
#                   wanting a different placement should author their own
#                   layout. `side` is documented for caller clarity but
#                   not consulted by the DSL.)
#   phases        array, opt, 0-2 objects:
#       label       string, ≤30
#       from_event  int 0..4
#       to_event    int 0..4
#       color       string token (e.g. "paper-2", "navy-100", "fog")
# Deck-level: footer_left, footer_right.
#
# Geometry:
#   Axis runs horizontally at y=620. Events are spaced evenly across the
#   content area: x positions 180, 555, 930, 1305, 1680 (375px pitch).
#   Phase band x = from_event*375 + 180, width = (to_event - from_event)*375.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

# Title block.
rect 100,180 80x4 fill:ink
text 100,220 style:tracker    maxwidth:1720 maxheight:24 "{{ tracker }}"
text 100,260 style:act-kicker color:accent maxwidth:1720 maxheight:30 "{{ kicker }}"
text 100,300 style:act-title  maxwidth:1720 maxheight:140 "{{ action_title }}"

# Axis end-label — right-aligned strip immediately under pgmeta header
# (above the title block so it doesn't collide with the event date row).
text 100,140  style:h-idx color:graphite maxwidth:1720 maxheight:20 align:right "{{ axis_label }}"

# Phase bands — narrow translucent stripes hugging the axis (drawn
# first so the axis + markers sit on top). Bands span y=608 to y=632
# (12px above + 12px below the axis line at y=620). Phase labels live
# below the axis in their own row at y=700.
rect {{ phases[0].from_event*375+180 }},608 {{ (phases[0].to_event-phases[0].from_event)*375 }}x24 fill:"{{ phases[0].color }}" fill-opacity:0.6 if:"{{ phases[0].label }}"
text {{ phases[0].from_event*375+180 }},700 style:h-idx color:graphite maxwidth:{{ (phases[0].to_event-phases[0].from_event)*375 }} maxheight:20 align:center if:"{{ phases[0].label }}" "{{ phases[0].label }}"
rect {{ phases[1].from_event*375+180 }},608 {{ (phases[1].to_event-phases[1].from_event)*375 }}x24 fill:"{{ phases[1].color }}" fill-opacity:0.6 if:"{{ phases[1].label }}"
text {{ phases[1].from_event*375+180 }},700 style:h-idx color:graphite maxwidth:{{ (phases[1].to_event-phases[1].from_event)*375 }} maxheight:20 align:center if:"{{ phases[1].label }}" "{{ phases[1].label }}"

# Main axis rule.
rect 100,620  1720x2 fill:ink

# --- Event 0 (above, x=180) ---
# Marker on the axis (diamond, 16x16 centered).
shape 172,612  16x16 kind:diamond fill:accent
# Hairline from text block down to the marker.
rect 179,604   2x16 fill:fog
# Text above (date + label + description), bottom-aligned conceptually
# so the description sits closest to the axis.
text 50,423    style:h-idx  color:accent maxwidth:280 maxheight:20 align:center "{{ events[0].date }}"
text 50,474    style:h-hd                 maxwidth:280 maxheight:48 align:center "{{ events[0].label }}"
text 50,528    style:detail maxwidth:280 maxheight:72 align:center "{{ events[0].description }}"

# --- Event 1 (below, x=555) ---
shape 547,612  16x16 kind:diamond fill:accent
rect 554,628   2x150 fill:fog
text 425,780   style:h-idx  color:accent maxwidth:260 maxheight:20 align:center "{{ events[1].date }}"
text 425,806   style:h-hd                 maxwidth:260 maxheight:60 align:center "{{ events[1].label }}"
text 425,874   style:detail maxwidth:260 maxheight:40 align:center "{{ events[1].description }}"

# --- Event 2 (above, x=930) ---
shape 922,612  16x16 kind:diamond fill:accent
rect 929,604   2x16 fill:fog
text 800,423   style:h-idx  color:accent maxwidth:260 maxheight:20 align:center "{{ events[2].date }}"
text 800,474   style:h-hd                 maxwidth:260 maxheight:48 align:center "{{ events[2].label }}"
text 800,528   style:detail maxwidth:260 maxheight:72 align:center "{{ events[2].description }}"

# --- Event 3 (below, x=1305) ---
shape 1297,612 16x16 kind:diamond fill:accent
rect 1304,628  2x150 fill:fog
text 1175,780  style:h-idx  color:accent maxwidth:260 maxheight:20 align:center "{{ events[3].date }}"
text 1175,806  style:h-hd                 maxwidth:260 maxheight:60 align:center "{{ events[3].label }}"
text 1175,874  style:detail maxwidth:260 maxheight:40 align:center "{{ events[3].description }}"

# --- Event 4 (above, x=1680) ---
shape 1672,612 16x16 kind:diamond fill:accent
rect 1679,604  2x16 fill:fog
text 1550,423  style:h-idx  color:accent maxwidth:260 maxheight:20 align:center "{{ events[4].date }}"
text 1550,474  style:h-hd                 maxwidth:260 maxheight:48 align:center "{{ events[4].label }}"
text 1550,528  style:detail maxwidth:260 maxheight:72 align:center "{{ events[4].description }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"