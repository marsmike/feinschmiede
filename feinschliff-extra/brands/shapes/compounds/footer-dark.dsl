# Feinschliff footer — dark-mode variant. Mono labels in off-white,
# matching the .slide.ink footer color in the canonical CSS.

compound footer-dark(left, right):
  text 100,1000  style:footer color:off-white-2 maxwidth:800 "{{ left }}"
  text 1200,1000 style:footer color:off-white-2 maxwidth:620 "{{ right }}" align:right
