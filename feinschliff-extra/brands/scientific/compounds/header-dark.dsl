# Feinschliff header — dark-mode variant. Combined logo (light gem + off-white
# wordmark locked as one asset) top-left. Alignment baked into the SVG/PNG at
# design time — no renderer-side y-offset computation required.
#
# gem-light.png is kept for backwards-compatibility with descendant brands that
# override this compound and still reference gem-light.png explicitly.

compound header-dark(pgmeta):
  # Combined gem + wordmark logo — light variant (locked at design time — see
  # brands/feinschliff/assets/logo-light.svg). optional:true so descendant
  # brands without logo-light.png still render cleanly.
  picture 100,52 180x24 path:logo-light.png optional:true
  text 1100,56 style:pgmeta color:off-white-2 maxwidth:720 "{{ pgmeta }}" align:right
