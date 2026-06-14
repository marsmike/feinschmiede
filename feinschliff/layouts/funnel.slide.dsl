---
role: data-comparison
ideal_count: [3, 6]
data_band: chart
comparison: false
description: Trapezoid funnel graphic left; four-stage table center with count and percentage; two drop-off annotations with delta values right
source: feinschliff
source_hash: dfc51ffabd4e
---
# funnel — 3-column composition matching the canonical baseline:
#   left   funnel silhouette (4 narrowing rects; one stage in accent)
#   middle data table (label / value / percent per row, hairlines)
#   right  drop-off annotations (mono caps + body)
#
# Slot schema (data-slots from feinschliff-2026.html · 30):
#   logo          string, optional
#   pgmeta        string, ≤40, opt
#   tracker       string, ≤60, opt
#   kicker        string, ≤40, opt  (unused)
#   action_title  string, ≤180
#   stages        array, 3–6 objects:
#       label    string, ≤30
#       value    string/number
#       percent  string, ≤8
#       body     string, ≤120, opt
#   focus_index   number 0..n-1, optional (default 2 — middle stage gold)
#   annotations   array, 0–3 objects, optional:
#       delta    string, ≤12 (e.g. "−22 pt")
#       label    string, ≤30
#       body     string, ≤180
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30 "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:80 "{{ action_title }}"

# === Left column: funnel silhouette ===
# 4 trapezoid bands centered around x=320, each h=100, taper continuous
# top→bottom: 440 → 360 → 280 → 200 → 120. MSO_SHAPE.TRAPEZOID is wider-
# at-bottom by default; rotate:180 flips each band so wide edge is at top.
# adj1 is the slanted-edge inset expressed as a fraction of min(w,h) — not
# width — so with h=100 each side inset is adj1*100 px. We want 40 px inset
# (each stage's narrow edge = next stage's wide edge), so adj1=0.4 across
# all four bands. Colors alternate through the navy ramp so adjacent bands
# never share a fill (was ink/ink/accent/ink — stages 1+2 visually merged).
shape 100,460  440x100 kind:trapezoid rotate:180 adj1:0.4 fill:ink
shape 140,560  360x100 kind:trapezoid rotate:180 adj1:0.4 fill:navy-500
shape 180,660  280x100 kind:trapezoid rotate:180 adj1:0.4 fill:accent
shape 220,760  200x100 kind:trapezoid rotate:180 adj1:0.4 fill:navy-700

# === Middle column: data table ===
rect 580,440  680x1 fill:fog
text 600,460  style:h-hd  maxwidth:380 maxheight:36  "{{ stages[0].label }}"
text 600,500  style:detail maxwidth:380 maxheight:24 "{{ stages[0].body }}"
text 1080,460 style:h-hd  maxwidth:120 maxheight:36 align:right "{{ stages[0].value }}"
text 1080,500 style:detail maxwidth:160 maxheight:24 align:right "{{ stages[0].percent }}"

rect 580,540  680x1 fill:fog
text 600,560  style:h-hd  maxwidth:380 maxheight:36  "{{ stages[1].label }}"
text 600,600  style:detail maxwidth:380 maxheight:24 "{{ stages[1].body }}"
text 1080,560 style:h-hd  maxwidth:120 maxheight:36 align:right "{{ stages[1].value }}"
text 1080,600 style:detail maxwidth:160 maxheight:24 align:right "{{ stages[1].percent }}"

rect 580,640  680x1 fill:fog
text 600,660  style:h-hd  maxwidth:380 maxheight:36  "{{ stages[2].label }}"
text 600,700  style:detail maxwidth:380 maxheight:24 "{{ stages[2].body }}"
text 1080,660 style:h-hd  maxwidth:120 maxheight:36 align:right "{{ stages[2].value }}"
text 1080,700 style:detail maxwidth:160 maxheight:24 align:right "{{ stages[2].percent }}"

rect 580,740  680x1 fill:fog
text 600,760  style:h-hd  maxwidth:380 maxheight:36  "{{ stages[3].label }}"
text 600,800  style:detail maxwidth:380 maxheight:24 "{{ stages[3].body }}"
text 1080,760 style:h-hd  maxwidth:120 maxheight:36 align:right "{{ stages[3].value }}"
text 1080,800 style:detail maxwidth:160 maxheight:24 align:right "{{ stages[3].percent }}"

rect 580,840  680x1 fill:fog

# === Right column: drop-off annotations ===
rect 1300,440  520x1 fill:fog
text 1300,460  style:h-hd  color:accent-hover maxwidth:520 maxheight:48     "{{ annotations[0].delta }}"
text 1300,510  style:h-idx color:ink maxwidth:520 maxheight:24              "{{ annotations[0].label }}"
text 1300,548  style:body  maxwidth:520 maxheight:80                       "{{ annotations[0].body }}"

rect 1300,640  520x1 fill:fog
text 1300,660  style:h-hd  color:accent-hover maxwidth:520 maxheight:48     "{{ annotations[1].delta }}"
text 1300,710  style:h-idx color:ink maxwidth:520 maxheight:24              "{{ annotations[1].label }}"
text 1300,748  style:body  maxwidth:520 maxheight:80                       "{{ annotations[1].body }}"

rect 1300,840  520x1 fill:fog

footer left:"{{ footer_left }}" right:"{{ footer_right }}"