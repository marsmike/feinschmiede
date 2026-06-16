<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/feinschmiede-mark-dark.svg">
    <img src="assets/feinschmiede-mark.svg" alt="feinschmiede mark — a forged gold ring holding the feinschliff gem" width="132">
  </picture>
</p>

<h1 align="center">feinschmiede</h1>

<p align="center">
  <strong>A family of branded media plugins for Claude Code</strong><br>
  Decks, images & 2D, video, and audio — independent plugins coupled by CLI
  capabilities, never file paths, over one shared engine.
</p>

[![CI](https://github.com/marsmike/feinschmiede/actions/workflows/ci.yml/badge.svg)](https://github.com/marsmike/feinschmiede/actions/workflows/ci.yml)
[![Pages](https://github.com/marsmike/feinschmiede/actions/workflows/pages.yml/badge.svg)](https://marsmike.github.io/feinschmiede/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin%20marketplace-orange)](https://docs.claude.com/claude-code)

[Browse the brand gallery](https://marsmike.github.io/feinschmiede/brands/) — every brand pack rendered against every layout.

## Plugins

This repo is a single Claude Code marketplace named **`feinschmiede`**. Install
the marketplace once, then install only the plugins you need.

```bash
/plugin marketplace add marsmike/feinschmiede
/plugin install feinschliff@feinschmiede
```

| Plugin | Install | What it does |
|---|---|---|
| [`feinschliff`](feinschliff/) | `feinschliff@feinschmiede` | **Office / decks** — brand-perfect PowerPoint via the master-template renderer. `/deck`. Ships 6 brand packs + 8 color themes. |
| [`feinbild`](feinbild/) | `feinbild@feinschmiede` | **Image & 2D** — AI images (Replicate/Gemini), SVG, Excalidraw diagrams. `/imagine`, `/svg`, `/excalidraw`. |
| [`feinklang`](feinklang/) | `feinklang@feinschmiede` | **Audio** — ElevenLabs voiceover. `/tts`. |
| [`feinschnitt`](feinschnitt/) | `feinschnitt@feinschmiede` | **Video** — programmatic Remotion videos + CLI session recordings. `/video`, `/record`. Composes feinbild + feinklang. |

Brand-pack authoring is now done in PowerPoint itself — design the master,
run `python -m feinschliff.master_template.catalog <pack>` to emit
`layouts.yaml` + `snippets.yaml`, drop the pack under
`feinschliff/brands/<name>/`. No separate authoring plugin required.

## Quick start

```bash
/plugin marketplace add marsmike/feinschmiede
/plugin install feinschliff@feinschmiede
/deck "Q1 update: 12 launches, 3 customers, $4.2M ARR"
```

Switch the look without authoring a new master — themes are clrScheme
overlays applied at render time:

```python
from feinschliff import render
render(brand_pack, plans, out, theme=brand_pack / "themes/nord/scheme.json")
```

Before your first run, see [`INSTALLATION.md`](INSTALLATION.md) for the
system prerequisites (Python 3.11+, `soffice`, `pdftoppm`, …) and the
API keys each plugin needs (`ELEVENLABS_API_KEY` for `feinklang`, etc.).
Keys go in `~/.env`; every plugin reads it at startup.

## How it fits together

Each plugin ships a `bin/` launcher that provisions a self-contained Python
venv from a bundled wheelhouse on first run, putting one clean CLI on PATH
(`feinschliff`, `feinbild`, `feinklang`, `feinschnitt`). Plugins
**never import or path into each other** — when one needs another's capability
(e.g. `feinschnitt` building a voiceover) it calls the sibling's bare command,
guaranteed present via plugin `dependencies`. A shared engine package,
**`feinschmiede`**, holds the cross-media brand/look system and the diagram
engine; it rides along as a vendored wheel so every plugin stays independent.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full design.

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md). All commits require a
[DCO](https://developercertificate.org/) sign-off (`git commit -s`). The
`bin/` launchers and `build-wheels.sh` are generated — edit
[`scripts/gen_launchers.py`](scripts/gen_launchers.py) and re-run it, never the
generated files (CI enforces this).

## Author

[Mike Mueller](https://marsmike.com) — `mike@objektarium.de`

## License

MIT — see [LICENSE](LICENSE). Third-party attribution: [NOTICE.md](NOTICE.md).
Security policy: [SECURITY.md](SECURITY.md).
