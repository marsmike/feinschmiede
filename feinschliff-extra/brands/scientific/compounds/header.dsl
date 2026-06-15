# Feinschliff header — combined logo (gem + wordmark locked as one asset) top-left,
# pgmeta line top-right. Alignment is baked into the SVG/PNG at design time so
# PowerPoint and Impress never re-baseline the two shapes independently.
#
# gem.png is kept for backwards-compatibility with descendant brands that override
# this compound and still reference gem.png explicitly.

compound header(pgmeta):
  # Combined gem + wordmark logo (locked at design time — see brands/feinschliff/assets/logo.svg).
  # optional:true so descendant brands that ship their own header compound but
  # don't carry logo.png still render cleanly.
  picture 100,52 180x24 path:logo.png optional:true
  # Top-right meta line — `style:pgmeta` applies the canonical .pgmeta opacity 0.7 + uppercase
  text 1100,56 style:pgmeta maxwidth:720 "{{ pgmeta }}" align:right
