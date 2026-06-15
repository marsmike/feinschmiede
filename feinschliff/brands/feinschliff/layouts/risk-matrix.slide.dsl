---
role: data-comparison
ideal_count: [4, 10]
data_band: none
comparison: true
narrative_role: risk
description: 5×5 heat-map grid (impact × probability) with numbered risk bubbles plotted; numbered risk legend list right
source: feinschliff
source_hash: 9efc7de12403
---
# risk-matrix — 5×5 probability × impact grid with risks plotted as
# numbered circles. Companion to risk-register (which gives the full
# table); the matrix communicates exposure shape at a glance.
#
# Slot schema:
#   logo, pgmeta, tracker, kicker, action_title — header
#   risks  array, 4-10 objects:
#       id              int 1..N
#       name            string, ≤60   (shown in the legend, not on the grid)
#       probability     int 1..5      (X axis, 1 low → 5 high)
#       impact          int 1..5      (Y axis, 1 low → 5 high)
#       severity        enum "low" | "medium" | "high"  (advisory)
#       severity_color  string token name
#                       ("severity-low" | "severity-medium" | "severity-high")
#   legend_position enum "right" | "below", default "right"  (advisory)
# Deck-level: footer_left, footer_right.
#
# Geometry:
#   Grid: 500×500 px at x=100, y=460, cell size 100×100 (so row of cells
#   begins right where risk-register's first table row lives). Probability
#   is the X axis (1 left → 5 right); impact is the Y axis (1 bottom → 5
#   top). For a risk:
#       marker center x = probability * 100 + 50
#       marker center y = 1010 - impact * 100
#       marker top-left x = probability * 100 + 20
#       marker top-left y = 980 - impact * 100
#       text top y (centered in 60×60 oval) = 998 - impact * 100
#   Severity zones are flat low-opacity backgrounds, then grid hairlines,
#   then markers, then a right-side legend listing each risk.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

# Title block.
rect 100,180 80x4 fill:ink
text 100,220 style:tracker    maxwidth:1720 maxheight:24 "{{ tracker }}"
text 100,260 style:act-kicker color:accent maxwidth:1720 maxheight:30 "{{ kicker }}"
text 100,300 style:act-title  maxwidth:1720 maxheight:96  "{{ action_title }}"

# --- Severity zones (drawn first as flat backgrounds, low opacity) ---
# Low zone: bottom-left 3×3 block (prob 1-3 × impact 1-3).
rect 100,660 300x300 fill:severity-low    fill-opacity:0.2
# High zone: top-right 2×2 block (prob 4-5 × impact 4-5).
rect 400,460 200x200 fill:severity-high   fill-opacity:0.25
# Medium zone 1: top-left strip (prob 1-3 × impact 4-5).
rect 100,460 300x200 fill:severity-medium fill-opacity:0.18
# Medium zone 2: bottom-right strip (prob 4-5 × impact 1-3).
rect 400,660 200x300 fill:severity-medium fill-opacity:0.18

# --- Grid hairlines (5×5 cells, 100px each) ---
# Outer border.
rect 100,460 500x2   fill:ink
rect 100,958 500x2   fill:ink
rect 100,460 2x500   fill:ink
rect 598,460 2x500   fill:ink
# Inner vertical lines at x=200, 300, 400, 500.
rect 200,460 1x500   fill:fog
rect 300,460 1x500   fill:fog
rect 400,460 1x500   fill:fog
rect 500,460 1x500   fill:fog
# Inner horizontal lines at y=560, 660, 760, 860.
rect 100,560 500x1   fill:fog
rect 100,660 500x1   fill:fog
rect 100,760 500x1   fill:fog
rect 100,860 500x1   fill:fog

# --- Axis tick labels (placed outside the grid edges) ---
# X axis (probability): below the grid at y=970. Cell centers: 150, 250, 350, 450, 550.
text 100,970 style:h-idx color:graphite maxwidth:100 maxheight:20 align:center "1"
text 200,970 style:h-idx color:graphite maxwidth:100 maxheight:20 align:center "2"
text 300,970 style:h-idx color:graphite maxwidth:100 maxheight:20 align:center "3"
text 400,970 style:h-idx color:graphite maxwidth:100 maxheight:20 align:center "4"
text 500,970 style:h-idx color:graphite maxwidth:100 maxheight:20 align:center "5"
# Y axis (impact): left of the grid at x=40. Cell centers (top→bottom): 510, 610, 710, 810, 910.
text 40,500 style:h-idx color:graphite maxwidth:50 maxheight:20 align:right "5"
text 40,600 style:h-idx color:graphite maxwidth:50 maxheight:20 align:right "4"
text 40,700 style:h-idx color:graphite maxwidth:50 maxheight:20 align:right "3"
text 40,800 style:h-idx color:graphite maxwidth:50 maxheight:20 align:right "2"
text 40,900 style:h-idx color:graphite maxwidth:50 maxheight:20 align:right "1"

# Axis-label combined caption above the grid, left-aligned with it. The
# bleed-model textfit (PR #78) lets tracker glyphs (~16px line, ~20px
# em-with-leading) extend past their declared box; placing the caption
# flush at y=440 over a grid border at y=460 visibly overprinted the
# border. Sit 24px above the grid (caption renders y=410–428), with 14px
# clearance from the action_title — which is itself shrunk to maxheight:96
# (single-line act-title at 50pt fits in ~70px under the bleed model).
text 100,410 style:tracker color:graphite maxwidth:500 maxheight:24 "IMPACT (Y) × PROBABILITY (X) — 1 LOW → 5 HIGH"

# --- Risk markers (60×60 ovals at computed centers) ---
# Every marker is `if:`-guarded on `risks[N].name` because the marker
# position is computed from `risks[N].probability` / `risks[N].impact`
# — if a risk slot is absent in content the arithmetic resolves to
# empty, which would otherwise fail parse_xy. First 4 rows are
# required per the slot schema but the guard keeps the smoke-test
# fallback context (with no `risks` key) safe.

# --- Risk 0 (required) ---
shape {{ risks[0].probability*100+20 }},{{ 980-risks[0].impact*100 }} 60x60 kind:oval fill:"{{ risks[0].severity_color }}" stroke:paper stroke-width:3            if:"{{ risks[0].name }}"
text  {{ risks[0].probability*100+20 }},{{ 980-risks[0].impact*100 }} style:h-hd color:paper maxwidth:60 maxheight:60 align:center valign:middle                                if:"{{ risks[0].name }}" "{{ risks[0].id }}"

# --- Risk 1 (required) ---
shape {{ risks[1].probability*100+20 }},{{ 980-risks[1].impact*100 }} 60x60 kind:oval fill:"{{ risks[1].severity_color }}" stroke:paper stroke-width:3                                       if:"{{ risks[1].name }}"
text  {{ risks[1].probability*100+20 }},{{ 980-risks[1].impact*100 }} style:h-hd color:paper maxwidth:60 maxheight:60 align:center valign:middle                                if:"{{ risks[1].name }}" "{{ risks[1].id }}"

# --- Risk 2 (required) ---
shape {{ risks[2].probability*100+20 }},{{ 980-risks[2].impact*100 }} 60x60 kind:oval fill:"{{ risks[2].severity_color }}" stroke:paper stroke-width:3                                       if:"{{ risks[2].name }}"
text  {{ risks[2].probability*100+20 }},{{ 980-risks[2].impact*100 }} style:h-hd color:paper maxwidth:60 maxheight:60 align:center valign:middle                                if:"{{ risks[2].name }}" "{{ risks[2].id }}"

# --- Risk 3 (required) ---
shape {{ risks[3].probability*100+20 }},{{ 980-risks[3].impact*100 }} 60x60 kind:oval fill:"{{ risks[3].severity_color }}" stroke:paper stroke-width:3                                       if:"{{ risks[3].name }}"
text  {{ risks[3].probability*100+20 }},{{ 980-risks[3].impact*100 }} style:h-hd color:paper maxwidth:60 maxheight:60 align:center valign:middle                                if:"{{ risks[3].name }}" "{{ risks[3].id }}"

# --- Risk 4 (optional) ---
shape {{ risks[4].probability*100+20 }},{{ 980-risks[4].impact*100 }} 60x60 kind:oval fill:"{{ risks[4].severity_color }}" stroke:paper stroke-width:3                                       if:"{{ risks[4].name }}"
text  {{ risks[4].probability*100+20 }},{{ 980-risks[4].impact*100 }} style:h-hd color:paper maxwidth:60 maxheight:60 align:center valign:middle                                if:"{{ risks[4].name }}" "{{ risks[4].id }}"

# --- Risk 5 (optional) ---
shape {{ risks[5].probability*100+20 }},{{ 980-risks[5].impact*100 }} 60x60 kind:oval fill:"{{ risks[5].severity_color }}" stroke:paper stroke-width:3                                       if:"{{ risks[5].name }}"
text  {{ risks[5].probability*100+20 }},{{ 980-risks[5].impact*100 }} style:h-hd color:paper maxwidth:60 maxheight:60 align:center valign:middle                                if:"{{ risks[5].name }}" "{{ risks[5].id }}"

# --- Risk 6 (optional) ---
shape {{ risks[6].probability*100+20 }},{{ 980-risks[6].impact*100 }} 60x60 kind:oval fill:"{{ risks[6].severity_color }}" stroke:paper stroke-width:3                                       if:"{{ risks[6].name }}"
text  {{ risks[6].probability*100+20 }},{{ 980-risks[6].impact*100 }} style:h-hd color:paper maxwidth:60 maxheight:60 align:center valign:middle                                if:"{{ risks[6].name }}" "{{ risks[6].id }}"

# --- Risk 7 (optional) ---
shape {{ risks[7].probability*100+20 }},{{ 980-risks[7].impact*100 }} 60x60 kind:oval fill:"{{ risks[7].severity_color }}" stroke:paper stroke-width:3                                       if:"{{ risks[7].name }}"
text  {{ risks[7].probability*100+20 }},{{ 980-risks[7].impact*100 }} style:h-hd color:paper maxwidth:60 maxheight:60 align:center valign:middle                                if:"{{ risks[7].name }}" "{{ risks[7].id }}"

# --- Risk 8 (optional) ---
shape {{ risks[8].probability*100+20 }},{{ 980-risks[8].impact*100 }} 60x60 kind:oval fill:"{{ risks[8].severity_color }}" stroke:paper stroke-width:3                                       if:"{{ risks[8].name }}"
text  {{ risks[8].probability*100+20 }},{{ 980-risks[8].impact*100 }} style:h-hd color:paper maxwidth:60 maxheight:60 align:center valign:middle                                if:"{{ risks[8].name }}" "{{ risks[8].id }}"

# --- Risk 9 (optional) ---
shape {{ risks[9].probability*100+20 }},{{ 980-risks[9].impact*100 }} 60x60 kind:oval fill:"{{ risks[9].severity_color }}" stroke:paper stroke-width:3                                       if:"{{ risks[9].name }}"
text  {{ risks[9].probability*100+20 }},{{ 980-risks[9].impact*100 }} style:h-hd color:paper maxwidth:60 maxheight:60 align:center valign:middle                                if:"{{ risks[9].name }}" "{{ risks[9].id }}"

# --- Legend on the right (x=700..1820), one row per risk, 50px pitch ---
text 700,460 style:tracker maxwidth:1120 maxheight:20 "RISKS"
rect 700,490 1120x2 fill:ink

# Row 0 — required (but if-guarded so the smoke-test fallback ctx
# without any `risks` key doesn't leak empty ovals).
shape 700,510  32x32 kind:oval fill:"{{ risks[0].severity_color }}"          if:"{{ risks[0].name }}"
text  700,510  style:h-idx color:paper maxwidth:32 maxheight:32 align:center valign:middle  if:"{{ risks[0].name }}" "{{ risks[0].id }}"
text  750,510  style:body maxwidth:1070 maxheight:32 valign:middle                          if:"{{ risks[0].name }}" "{{ risks[0].name }}"

# Row 1.
shape 700,560  32x32 kind:oval fill:"{{ risks[1].severity_color }}"          if:"{{ risks[1].name }}"
text  700,560  style:h-idx color:paper maxwidth:32 maxheight:32 align:center valign:middle  if:"{{ risks[1].name }}" "{{ risks[1].id }}"
text  750,560  style:body maxwidth:1070 maxheight:32 valign:middle                          if:"{{ risks[1].name }}" "{{ risks[1].name }}"

# Row 2.
shape 700,610  32x32 kind:oval fill:"{{ risks[2].severity_color }}"          if:"{{ risks[2].name }}"
text  700,610  style:h-idx color:paper maxwidth:32 maxheight:32 align:center valign:middle  if:"{{ risks[2].name }}" "{{ risks[2].id }}"
text  750,610  style:body maxwidth:1070 maxheight:32 valign:middle                          if:"{{ risks[2].name }}" "{{ risks[2].name }}"

# Row 3.
shape 700,660  32x32 kind:oval fill:"{{ risks[3].severity_color }}"          if:"{{ risks[3].name }}"
text  700,660  style:h-idx color:paper maxwidth:32 maxheight:32 align:center valign:middle  if:"{{ risks[3].name }}" "{{ risks[3].id }}"
text  750,660  style:body maxwidth:1070 maxheight:32 valign:middle                          if:"{{ risks[3].name }}" "{{ risks[3].name }}"

# Row 4 (optional).
shape 700,710  32x32 kind:oval fill:"{{ risks[4].severity_color }}"          if:"{{ risks[4].name }}"
text  700,710  style:h-idx color:paper maxwidth:32 maxheight:32 align:center valign:middle  if:"{{ risks[4].name }}" "{{ risks[4].id }}"
text  750,710  style:body maxwidth:1070 maxheight:32 valign:middle                          if:"{{ risks[4].name }}" "{{ risks[4].name }}"

# Row 5 (optional).
shape 700,760  32x32 kind:oval fill:"{{ risks[5].severity_color }}"          if:"{{ risks[5].name }}"
text  700,760  style:h-idx color:paper maxwidth:32 maxheight:32 align:center valign:middle  if:"{{ risks[5].name }}" "{{ risks[5].id }}"
text  750,760  style:body maxwidth:1070 maxheight:32 valign:middle                          if:"{{ risks[5].name }}" "{{ risks[5].name }}"

# Row 6 (optional).
shape 700,810  32x32 kind:oval fill:"{{ risks[6].severity_color }}"          if:"{{ risks[6].name }}"
text  700,810  style:h-idx color:paper maxwidth:32 maxheight:32 align:center valign:middle  if:"{{ risks[6].name }}" "{{ risks[6].id }}"
text  750,810  style:body maxwidth:1070 maxheight:32 valign:middle                          if:"{{ risks[6].name }}" "{{ risks[6].name }}"

# Row 7 (optional).
shape 700,860  32x32 kind:oval fill:"{{ risks[7].severity_color }}"          if:"{{ risks[7].name }}"
text  700,860  style:h-idx color:paper maxwidth:32 maxheight:32 align:center valign:middle  if:"{{ risks[7].name }}" "{{ risks[7].id }}"
text  750,860  style:body maxwidth:1070 maxheight:32 valign:middle                          if:"{{ risks[7].name }}" "{{ risks[7].name }}"

# Row 8 (optional).
shape 700,910  32x32 kind:oval fill:"{{ risks[8].severity_color }}"          if:"{{ risks[8].name }}"
text  700,910  style:h-idx color:paper maxwidth:32 maxheight:32 align:center valign:middle  if:"{{ risks[8].name }}" "{{ risks[8].id }}"
text  750,910  style:body maxwidth:1070 maxheight:32 valign:middle                          if:"{{ risks[8].name }}" "{{ risks[8].name }}"

# Row 9 (optional).
shape 700,960  32x32 kind:oval fill:"{{ risks[9].severity_color }}"          if:"{{ risks[9].name }}"
text  700,960  style:h-idx color:paper maxwidth:32 maxheight:32 align:center valign:middle  if:"{{ risks[9].name }}" "{{ risks[9].id }}"
text  750,960  style:body maxwidth:1070 maxheight:32 valign:middle                          if:"{{ risks[9].name }}" "{{ risks[9].name }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"