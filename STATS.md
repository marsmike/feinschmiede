# Feinschmiede — install footprint & context cost

Snapshot after the master-template migration (PRs 0–10). Numbers are
git-tracked file sizes — what `git clone` puts on disk and what the
marketplace install copies into
`~/.claude/plugins/cache/feinschmiede/<plugin>/<sha>/`.

## Marketplace install — what users get

| Plugin | Files | Size | What it ships |
|---|---:|---:|---|
| `feinschliff` | 149 | **20.8 MB** | `bin/` launcher, 6 brand packs (`feinschliff` + 8 themes + 5 gallery packs), deck skill (1 SKILL.md + 5 references), master-template source, gallery script |
| `feinbild` | 45 | **347 KB** | `bin/` launcher, 3 skills (svg, excalidraw, imagine) with 9 references |
| `feinklang` | 13 | **28 KB** | `bin/` launcher, tts skill |
| `feinschnitt` | 151 | **802 KB** | `bin/` launcher, 3 skills (edit, cli-recorder, remotion) with 39 references |
| **Total** | **358** | **≈ 22.0 MB** | |

The bulk of `feinschliff` is brand-pack assets — the `feinschliff`
master.pptx alone is 8.4 MB, the gallery packs (geometric, shapes,
scientific) add ~10 MB of decompile assets. Private corporate brand
packs (BSH / Bosch) live outside the repo and are reached via the
sibling `feinschliff-*` discovery in `bin/feinschliff` — they don't
inflate the public footprint.

The `feinschmiede` workspace package (the shared engine for feinbild's
diagrams) is not a plugin and not shipped via marketplace.

## Source code — what we maintain

| Plugin | Python LOC | Notes |
|---|---:|---|
| `feinschliff` | **830** | Master-template renderer (490) + render_gallery.py (220) + theme overlay |
| `feinschmiede` | 5,677 | Diagram engine (consumed by feinbild) + brand/token helpers |
| `feinschnitt` | 3,282 | Video edit pipeline, recorder, Remotion glue |
| `feinbild` | 374 | Image / SVG / Excalidraw generation |
| `feinklang` | 338 | ElevenLabs TTS client |
| **Total** | **10,501** | (no tests — they were deleted in PR 2) |

Pre-migration total was ~45,000 LOC across the same package set.
**~77% reduction** in maintained Python, driven by:

- DSL pipeline deletion: `feinschliff/feinschliff/` dropped from
  ~10,400 LOC to 490 LOC (PR 3 + PR 4).
- `feinschliff-builder` plugin deleted entirely: ~16,400 LOC (PR 1).
- `feinschmiede` DSL-era surface trimmed: 5,891 → 5,677 LOC (PR 6).
- All tests removed: 6.1 MB / 132 files (PR 2).

## Skill context cost

| Skill | Body lines | references/ files | references/ size |
|---|---:|---:|---:|
| `feinschliff/deck` | 40 | 5 | 24 KB |
| `feinbild/svg` | 41 | 3 | 16 KB |
| `feinbild/excalidraw` | 41 | 5 | 44 KB |
| `feinbild/imagine` | 41 | 1 | 4 KB |
| `feinklang/tts` | 39 | 1 | 4 KB |
| `feinschnitt/edit` | 39 | 4 | 16 KB |
| `feinschnitt/cli-recorder` | 41 | 1 | 8 KB |
| `feinschnitt/remotion` | 40 | 34 | 540 KB |
| **Total** | **322 lines** | **54 files** | **656 KB** |

Every SKILL.md body passes `claude-skills-cli` ("Good progressive
disclosure"). The CI's required `feinschliff lib tests` check is now
purely this validation — no Python tests, just `npx -y claude-skills-cli
validate <path>` over every SKILL.md.

Pre-migration: 11 skills, 433 body lines, 130 reference files, 708 KB.
After PR 1 (builder deletion) + PR 7 (deck skill rewrite): **8 skills,
322 body lines, 54 references, 656 KB**.

## Brand packs

| Pack | Source | Layouts | Theme variants |
|---|---|---:|---:|
| `feinschliff` | repo (master.pptx 8.4 MB) | 11 | 8 (clrScheme overlays) |
| `annual-review` | `.ref` -> `~/work/pptx-templates/` | 13 | — |
| `geometric` | `.ref` -> `~/work/pptx-templates/` | 17 | — |
| `gs-ramspau` | repo (master.pptx 685 KB) | 11 | — |
| `scientific` | `.ref` -> `~/work/pptx-templates/` | 13 | — |
| `shapes` | `.ref` -> `~/work/pptx-templates/` | 13 | — |
| **In-repo total** | | **78** | 8 |

`master.pptx.ref` files keep large source pptx out of the repo while
the renderer transparently follows the pointer at lookup time. Private
corporate packs (BSH, Bosch) live in separate repos and use the same
`.ref` pattern.

## Methodology

- All sizes from `git ls-files <path> | xargs -I{} stat -f %z {}` so
  we count exactly what `git clone` puts on disk.
- LOC from `git ls-files <path> | grep '\.py$' | xargs cat | wc -l`.
- Skill body line count strips YAML frontmatter (matches the
  validator).
