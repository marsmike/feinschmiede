---
role: title-with-visual
ideal_count: [1, 1]
data_band: none
comparison: false
variety_exempt: true
description: Full-bleed image placeholder cover; title block with accent rule and large headline bottom-left on accent panel
source: feinschliff
source_hash: 04b6843ed59c
---
# full-bleed-cover — editorial cover with full-bleed image and an orange
# lockup card holding the title bottom-left.
#
# Slot schema (data-slots from feinschliff-2026.html · 12):
#   logo     string, optional
#   pgmeta   string, ≤40, opt
#   image    string, path           Full-bleed background image.
#   eyebrow  string, ≤60, opt
#   title    string, ≤60            Headline inside the orange lockup.
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

# Full-bleed image background. Placeholder is paper-2 (dim warm) when absent.
rect 0,0 1920x1080 fill:paper-2
picture 0,0 1920x1080 path:{{ image }} query:{{ image_query }} cover:true

# Header chrome (chrome stays default — pgmeta is on top of pic, ink-colored).
header pgmeta:"{{ pgmeta }}"

# Orange lockup card — bottom-left, padded; contains rule, eyebrow, big title.
# Canonical: left=100, bottom=180, padding 32 40 36, max-width 820.
# Title uses style:quote (84px light) approximating the canonical 88px inline.
# Card height accommodates 2-line title at quote style (≈100px per line + padding).
rect 100,640 820x320 fill:accent
rect 140,672 80x4 fill:ink
text 140,702 style:eyebrow maxwidth:740 maxheight:24 "{{ eyebrow }}"
text 140,732 style:quote   maxwidth:740 maxheight:220 "{{ title }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"