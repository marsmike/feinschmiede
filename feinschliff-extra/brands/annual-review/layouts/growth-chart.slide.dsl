---
role: data-comparison
ideal_count: [1, 1]
data_band: chart
comparison: true
family: comparison
description: 'Teal panel: bold title, black rule, horizontal grouped bar chart (3 series, 4 categories)'
when_to_use: Grouped bar chart (3 series x 4 categories) — replace data post-export.
chrome_note: 'carries native source chrome verbatim: 1 chart'
slide_index: 5
slots:
  text_1: {role: title, chars: 32, default: Growth by sector chart}
  text_2: {role: footer, chars: 17, default: Annual Review}
  text_3: {role: footer, chars: 38, default: 'September 3, 20XX'}
  text_4: {role: page-number, chars: 7, default: '5'}
element_tree: ['text text_1 role=title @162,157 1585x102 44pt', 'text text_2 role=footer @1307,991 231x29 12pt', 'text text_3
    role=footer @1548,991 252x79 12pt', 'text text_4 role=page-number @1810,991 100x29 12pt', native chart]
source_hash: 0e46987e48f3
source: annual-review
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: growth-chart
canvas 1920x1080
theme annual-review

rect 0,-1 1757x917 fill:highlight
rect 0,-1 1757x917 fill:highlight
native graphic1 b64:"PHA6Z3JhcGhpY0ZyYW1lIHhtbG5zOnA9Imh0dHA6Ly9zY2hlbWFzLm9wZW54bWxmb3JtYXRzLm9yZy9wcmVzZW50YXRpb25tbC8yMDA2L21haW4iIHhtbG5zOmE9Imh0dHA6Ly9zY2hlbWFzLm9wZW54bWxmb3JtYXRzLm9yZy9kcmF3aW5nbWwvMjAwNi9tYWluIj48cDpudkdyYXBoaWNGcmFtZVByPjxwOmNOdlByIGlkPSI0IiBuYW1lPSJDaGFydCBQbGFjZWhvbGRlciAzIiBkZXNjcj0iR3Jvd3RoIENoYXJ0Ij48YTpleHRMc3Q+PGE6ZXh0IHVyaT0ie0ZGMkI1RUY0LUZGRjItNDBCNC1CRTQ5LUYyMzhFMjdGQzIzNn0iPjxhMTY6Y3JlYXRpb25JZCB4bWxuczphMTY9Imh0dHA6Ly9zY2hlbWFzLm1pY3Jvc29mdC5jb20vb2ZmaWNlL2RyYXdpbmcvMjAxNC9tYWluIiBpZD0ie0M2NjZCN0I1LTBERDAtMUY0MS04OUQ0LTU2MDRCMDkzOTEyRn0iLz48L2E6ZXh0PjwvYTpleHRMc3Q+PC9wOmNOdlByPjxwOmNOdkdyYXBoaWNGcmFtZVByPjxhOmdyYXBoaWNGcmFtZUxvY2tzIG5vR3JwPSIxIi8+PC9wOmNOdkdyYXBoaWNGcmFtZVByPjxwOm52UHI+PHA6cGggdHlwZT0iY2hhcnQiIHN6PSJxdWFydGVyIiBpZHg9IjExIi8+PHA6ZXh0THN0PjxwOmV4dCB1cmk9IntENDJBMjdEQi1CRDMxLTRCOEMtODNBMS1GNkVFQ0YyNDQzMjF9Ij48cDE0Om1vZElkIHhtbG5zOnAxND0iaHR0cDovL3NjaGVtYXMubWljcm9zb2Z0LmNvbS9vZmZpY2UvcG93ZXJwb2ludC8yMDEwL21haW4iIHZhbD0iMzk5NzA3NjUxNiIvPjwvcDpleHQ+PC9wOmV4dExzdD48L3A6bnZQcj48L3A6bnZHcmFwaGljRnJhbWVQcj48cDp4ZnJtPjxhOm9mZiB4PSI5NTA5MTMiIHk9IjIyODYwMDAiLz48YTpleHQgY3g9IjkxNDU1ODciIGN5PSIzMTY1NDc1Ii8+PC9wOnhmcm0+PGE6Z3JhcGhpYz48YTpncmFwaGljRGF0YSB1cmk9Imh0dHA6Ly9zY2hlbWFzLm9wZW54bWxmb3JtYXRzLm9yZy9kcmF3aW5nbWwvMjAwNi9jaGFydCI+PGM6Y2hhcnQgeG1sbnM6Yz0iaHR0cDovL3NjaGVtYXMub3BlbnhtbGZvcm1hdHMub3JnL2RyYXdpbmdtbC8yMDA2L2NoYXJ0IiB4bWxuczpyPSJodHRwOi8vc2NoZW1hcy5vcGVueG1sZm9ybWF0cy5vcmcvb2ZmaWNlRG9jdW1lbnQvMjAwNi9yZWxhdGlvbnNoaXBzIiByOmlkPSJySWQyIi8+PC9hOmdyYXBoaWNEYXRhPjwvYTpncmFwaGljPjwvcDpncmFwaGljRnJhbWU+" parts_file:"native/ac83b247c136.json"
line 163,295 1758,296 stroke:fog stroke-width:12
line 163,295 1758,296 stroke:fog stroke-width:12

text 162,157 style:sub color:black weight:bold size:44pt linespacing:0.9 valign:bottom padding:1 maxwidth:1585 maxheight:102 autoshrink:true "{{ text_1 | default(\"Growth by sector chart\") }}"
text 1307,991 style:body-sm color:black size:12pt linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:231 maxheight:29 "{{ text_2 | default(\"Annual Review\") }}"
text 1548,991 style:body-sm color:black size:12pt linespacing:native padding:1 maxwidth:252 maxheight:79 "{{ text_3 | default(\"September 3, 20XX\") }}"
text 1810,991 style:body-sm color:black size:12pt linespacing:0.9 valign:middle padding:14,7,14,7 maxwidth:100 maxheight:29 "{{ text_4 | default(\"5\") }}"
