# Feinschliff footer compound — small mono labels left + right.
# No accent rule; the brand's footer is discreet.

compound footer(left, right):
  text 100,1000  style:footer maxwidth:800 "{{ left }}"
  text 1200,1000 style:footer maxwidth:620 "{{ right }}" align:right
