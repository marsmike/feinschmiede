# Architecture

`feinschmiede` is a family of Claude Code plugins for branded media creation —
decks, images & 2D, video, and audio. This document is the map: how the pieces
fit, why the boundaries are where they are, and the rules a contributor must keep.

## The two coupling rules

Everything here follows from two deliberate constraints:

1. **Plugins are coupled by CLI capabilities, never by file paths or imports.**
   When one plugin needs another's capability (e.g. `feinschnitt` building a
   voiceover, or a deck script wanting a diagram), it calls the sibling's
   bare command (`feinklang tts …`, `feinbild excalidraw …`) — guaranteed on
   PATH by a declared plugin `dependency`. No plugin reaches into another
   plugin's files, and no plugin imports another plugin's Python package.

2. **Shared code lives in exactly one engine, vendored — not duplicated.**
   The `feinschmiede` engine package holds only what 2+ plugins need (the
   cross-media brand-token loader and the diagram pipeline). It is built once
   and vendored as a wheel into each plugin's venv, so there is a single
   source of truth and every plugin still installs independently.

## The components

| Component | Kind | Role |
|---|---|---|
| **feinschmiede** | engine (library) | Brand-token loader + the diagram engine (SVG & Excalidraw DSL expanders, render dispatcher, structural validator). Not a plugin; vendored as a wheel into feinbild. |
| **feinschliff** | plugin | Office / decks — master-template renderer that fills a brand pack's `master.pptx` via `FillPlan` / `ClonePlan`. Ships 6 in-repo brand packs with 8 themes for the eponymous pack. |
| **feinbild** | plugin | Image & 2D — AI images (Replicate/Gemini) + SVG + Excalidraw diagrams, over the engine. |
| **feinklang** | plugin | Audio — ElevenLabs voiceover. |
| **feinschnitt** | plugin | Video — Remotion videos, CLI session recordings, and plan-driven editing of talking-head footage into brand-themed cuts; composes feinbild + feinklang. |

### Dependency directions

```
feinschmiede (engine)  ◀── feinbild           feinschliff   (no engine dep)
                                                  ▲
        feinschnitt ───┘ (calls feinbild + feinklang CLIs)
        feinklang  (engine-free; standalone)
```

After the master-template migration (PRs #130–#142, 2026-06-16), `feinschliff`
no longer depends on the `feinschmiede` engine — brand styling lives in each
pack's `master.pptx`, authored once in PowerPoint and replayed by the kernel.
Only `feinbild` still imports the engine (the diagram pipeline). The engine
never imports any plugin.

Private corporate brand packs surface via sibling `feinschliff-*` plugin
directories — the `bin/feinschliff` launcher auto-discovers their `brands/`
and exports `FEINSCHLIFF_BRAND_PATH` so they appear alongside the in-repo
packs without any code change.

## Distribution & the bootstrap layer

Every distributable plugin ships a `bin/<name>` launcher. On first run it:

1. resolves a wheelhouse from `$PLUGIN_ROOT/wheels/` (dev) or fetches the
   release tarball (marketplace), then
2. provisions a self-contained venv from that wheelhouse and execs either
   the plugin's CLI (`feinbild`, `feinklang`, `feinschnitt`) or a Python shim
   (`feinschliff` — no CLI; users author a `build.py` and run it via the venv).

The venv is keyed on a content signature of **the wheelhouse + the plugin's
`pyproject.toml`**, so a plugin update (new wheels or bumped source) rebuilds
the venv instead of silently running stale code.

The launchers and each `build-wheels.sh` are **generated** from a single
manifest + templates in [`scripts/gen_launchers.py`](scripts/gen_launchers.py).
The bootstrap logic exists in exactly one place; CI runs
`gen_launchers.py --check` to keep the committed files in sync.

## The engine in more detail

```
feinschmiede/
  brand/            BrandPack — a cross-media "look" used by the diagram
                    pipeline to resolve color names against brand tokens.
  brand_discovery   discovery across env / cwd-dev / plugin / user sources
                    (priority order — working tree beats installed plugin)
  diagnostics       Defect / DiagnosticBag taxonomy
  diagrams/         svg_expand · excalidraw_expand · render (rough+cairosvg
                    primary, Playwright fallback) · brand_bridge · text_metrics
                    · structural_validator (overflow/overlap/collision checks)
  dsl/tokens        DTCG-flavoured brand-token loader used by the diagrams.
```

The diagram render dispatcher tries the pure-Python **rough + cairosvg** path
first (~150 ms, no browser) and falls back to a real headless-Chromium
Excalidraw render only for documents it can't model (freedraw / image /
frame). A missing `libcairo` surfaces an actionable libcairo message, not a
misleading "install Playwright".

## The office pipeline (feinschliff)

A skill or script imports the public surface:

```python
from feinschliff import FillPlan, ClonePlan, render, apply_theme
```

`render(brand_pack, plans, out, *, theme=None, source_deck=None)` opens the
pack's `master.pptx`, optionally overlays a `clrScheme` theme onto
`theme1.xml` in memory, strips the master's sample slides, then plays the
plan list against the pack's authored layouts. `FillPlan` fills a layout's
placeholders by index; `ClonePlan` deep-copies a bespoke source slide and
patches its text runs. The kernel is ~500 LOC across six files in
`feinschliff/feinschliff/master_template/`.

There is no `feinschliff` CLI any more — the launcher execs `python "$@"`
against the provisioned venv. Skills and scripts author a small
`.debug/<topic>/build.py` that imports the public surface and run it as
`feinschliff build.py`.

## Brand packs

A brand pack lives at `feinschliff/brands/<name>/` with three resolution
shapes for its master template:

1. `<pack>/master.pptx` (feinschliff convention).
2. `<pack>/master/master.pptx` (abzug convention — historical).
3. `<pack>/master.pptx.ref` — a text file pointing at the binary's
   absolute path. Used by gallery / corporate packs whose master file
   lives outside the repo so the binary never needs to be checked in.

Themes are `clrScheme` overlays — a small JSON under
`<pack>/themes/<name>/scheme.json` patches up to 12 color slots
(`dk1`, `lt1`, `dk2`, `lt2`, `accent1..6`, `hlink`, `folHlink`) in memory
at render time. One `master.pptx` → N visual variations.

The public gallery at <https://marsmike.github.io/feinschmiede/brands/> renders
every pack against the master-template kernel; see
[`feinschliff/CLAUDE.md`](feinschliff/CLAUDE.md) for the publish flow.

## Testing & CI

After PR 0 of the master-template migration, CI gates are minimal:

- **DCO sign-off** — every commit must carry `Signed-off-by:` (required
  status check on main).
- **`feinschliff lib tests`** — runs `claude-skills-cli validate` over
  every `SKILL.md` to enforce progressive-disclosure budgets (≤ 50 lines
  body). The display name is kept verbatim because branch protection on
  main requires that exact status string.

The Python test suite was dropped in PR #132. Validation is now visual
(open the rendered `.pptx`) and via the brand gallery published by the
Pages workflow on every push to main.

## Conventions a contributor must keep

- Don't import one plugin's Python from another. Call the sibling CLI instead.
- Don't duplicate engine code into a plugin; put shared code in `feinschmiede`.
- Don't edit `bin/<name>` or `build-wheels.sh` by hand — edit
  `scripts/gen_launchers.py` and re-run it.
- Don't add manual `version` fields to `plugin.json`/`marketplace.json`; keep
  Python package versions aligned in `pyproject.toml` (CI enforces).
- Keep `feinschliff/examples/` to user-facing artifacts only; intermediates go
  under `.debug/` (see [`feinschliff/CLAUDE.md`](feinschliff/CLAUDE.md)).
- Sign off every commit (`git commit -s`).
