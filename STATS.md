# Feinschmiede — install footprint & context cost

Snapshot of what the suite ships to a user's machine, what stays in dev,
and what each skill costs in Claude's context window.

All numbers are git-tracked file sizes — what the marketplace install
actually copies into `~/.claude/plugins/cache/feinschmiede/<plugin>/<sha>/`.

## Marketplace install — what users get

After PR #91 moved tests out of the plugin directories:

| Plugin | Files | Size | What it ships |
|---|---:|---:|---|
| `feinschliff` | 190 | **1378 KB** | `bin/` launcher, 50 layouts, 3 brand packs, deck skill (1 SKILL.md + 13 references), Python source for the wheel cache |
| `feinschliff-builder` | 114 | **845 KB** | `bin/` launcher, 3 skills (autoloop, compile, improve-brand) with 27 references |
| `feinbild` | 49 | **348 KB** | `bin/` launcher, 3 skills (svg, excalidraw, imagine) with 9 references |
| `feinklang` | 13 | **28 KB** | `bin/` launcher, tts skill |
| `feinschnitt` | 151 | **797 KB** | `bin/` launcher, 3 skills (edit, cli-recorder, remotion) with 80 references |
| **Total** | **517** | **≈ 3.3 MB** | |

The `feinschliff-extra` add-on (14 additional brand packs, 58 layouts)
is an optional install for users who want more themes.

### Before vs after the test move

| Plugin | Before (with tests) | After | Saved |
|---|---:|---:|---:|
| `feinschliff` | 3.0 MB | 1.4 MB | **−1.6 MB** |
| `feinschliff-builder` | 1.6 MB | 0.8 MB | **−0.8 MB** |
| `feinbild` | 0.5 MB | 0.3 MB | **−0.2 MB** |
| `feinklang` | 76 KB | 28 KB | **−48 KB** |
| `feinschnitt` | 1.2 MB | 0.8 MB | **−0.4 MB** |
| **Suite total** | **6.4 MB** | **3.3 MB** | **−3.1 MB ≈ −48%** |

Tests now live at `tests/<plugin>/` in the repo root. They are git-
tracked (CI runs them) but never reach the marketplace plugin dir.

## Runtime install — what the launcher fetches

The `bin/<plugin>` launcher provisions a private venv from a wheelhouse
tarball hosted on the rolling `latest` GitHub release. The wheels are
**not** in git.

| Plugin | Wheel | Closure (deps) | Cached at |
|---|---:|---:|---|
| `feinschliff` | 714 KB | ~35 wheels (pillow, lxml, python-pptx, anthropic, …) | `~/.local/share/feinschmiede/feinschliff/wheels-latest/` |
| `feinschliff-builder` | ~620 KB | ~12 wheels | `~/.local/share/feinschmiede/feinschliff-builder/wheels-latest/` |
| `feinbild` | ~80 KB | ~6 wheels | `~/.local/share/feinschmiede/feinbild/wheels-latest/` |
| `feinklang` | ~12 KB | 1 wheel (`requests`) | `~/.local/share/feinschmiede/feinklang/wheels-latest/` |
| `feinschnitt` | ~28 KB | ~4 wheels (`google-generativeai`) | `~/.local/share/feinschmiede/feinschnitt/wheels-latest/` |

Wheelhouse cache is bumped by `If-Modified-Since` (curl `-z`). When a
PR lands on `main`, the release rebuilds, the next launcher invocation
detects the new tarball and rebuilds the venv. No semver, no manual
update.

## Source code — what we maintain

| Plugin | Python LOC | Notes |
|---|---:|---|
| `feinschliff` | 18,103 | DSL parser, emitter, picker, polish, intake, storyline, picker, verify, quality, CLI |
| `feinschliff-builder` | 17,137 | Brand-pack authoring, decompiler, render harness, verify gates |
| `feinschmiede` (engine) | 5,728 | Shared brand discovery, tokens, diagrams |
| `feinschnitt` | 3,282 | Video edit pipeline, recorder, Remotion glue |
| `feinbild` | 374 | Image / SVG / Excalidraw generation |
| `feinklang` | 338 | ElevenLabs TTS client |
| **Total** | **45,000** | excluding tests |

Tests at repo root: **235 files, 1.4 MB**. Pytest collects ~2,100 across
the suite; CI runs the full set on every PR.

## Skill context cost

Every plugin ships one or more skills as Claude Code prose. The
[`SKILL.md`](https://docs.anthropic.com/en/docs/claude-code/plugins#skills)
body is **always loaded** when the skill activates (Level 2 context).
References (`references/*.md`) are **lazy** — Claude reads them only
when their topic comes up.

We police every `SKILL.md` body to ≤ 40 lines via the
`claude-skills-cli` validator (`tests/.../test_skill_validator.py`).

| Skill | Body lines | references/ files | references/ size |
|---|---:|---:|---:|
| `feinschliff/deck` | 41 | 13 | 158 KB |
| `feinschliff-builder/compile` | 41 | 17 | 49 KB |
| `feinschliff-builder/improve-brand` | 39 | 6 | 41 KB |
| `feinschliff-builder/autoloop` | 36 | 4 | 7 KB |
| `feinbild/svg` | 37 | 3 | 8 KB |
| `feinbild/excalidraw` | 39 | 5 | 32 KB |
| `feinbild/imagine` | 41 | 1 | 2 KB |
| `feinklang/tts` | 39 | 1 | 1 KB |
| `feinschnitt/edit` | 39 | 4 | 9 KB |
| `feinschnitt/cli-recorder` | 41 | 1 | 5 KB |
| `feinschnitt/remotion` | 40 | 75 | 396 KB |
| **Total** | **433 lines** | **130 files** | **708 KB** |

### Context impact for the user

- **Pre-activation cost** (skill description in the picker) — every
  installed skill contributes its `description` field (typically 100–250
  chars) to the always-loaded skill list. 11 skills ≈ 1.5–2 KB of
  always-loaded context across the suite.
- **Activation cost** (SKILL.md body) — when a skill activates, its body
  joins the context window. At 40 lines × ~80 chars = ~3.2 KB per
  skill, or ~250 tokens.
- **Reference cost** (`references/*.md`) — Claude reads these on demand.
  The biggest single reference set is `feinschnitt/remotion` at 396 KB
  (Remotion is documentation-heavy by nature).

Practical rule of thumb: installing all 11 skills adds ~2 KB to your
always-loaded context. Activating a skill costs ~250 tokens of body
prose. Reading a single reference file is typically 1–10 KB
(< 2500 tokens).

## Brand packs

| Plugin | Brand packs | Layouts | Notes |
|---|---:|---:|---|
| `feinschliff` | 1 | 50 | `feinschliff` brand with 8 themes (`default`, `claude`, `catppuccin-latte`, `catppuccin-macchiato`, `feinschliff-dark`, `gruvbox-dark`, `nord`, `solarized-dark`) |
| `feinschliff-extra` | 5 | 58 | MS-gallery ports (annual-review, geometric, scientific, shapes) + bespoke school pack (gs-ramspau) |
| **Total** | **6** | **108** | |

Each brand pack is fully self-contained (no `extends` inheritance).
Tokens, fonts, and layouts live entirely within the brand's own directory.
Layouts are `.slide.dsl` files (1–5 KB each).

**Changes since last snapshot:**
- `extends:` inheritance subsystem removed (PR #97) — ~150 LOC deleted from
  `feinschmiede`, `feinschliff`, `feinschliff-builder`; brands already
  inlined parent tokens in a prior migration.
- 3 trademarked extra brands (`binance`, `spotify`, `ferrari`) deleted.
- `blank` brand (internal-only) deleted.
- 6 palette-only extra brands (catppuccin-latte, catppuccin-macchiato, feinschliff-dark,
  gruvbox-dark, nord, solarized-dark) demoted to themes under the `feinschliff` brand.

## Methodology

- All sizes from `git ls-files <path> | xargs cat | wc -c` so we count
  exactly what `git clone` puts on disk.
- Wheel sizes from `uv build --wheel` output for the latest commit.
- Skill body line count strips YAML frontmatter (the validator's count).
- LOC from `git ls-files <path> | grep '\.py$' | xargs cat | wc -l`.

Regenerate this file:

```bash
# Run from repo root after `git pull`
python3 scripts/measure_stats.py > STATS.md  # (planned — not yet wired)
```

For now the table is hand-maintained. Adding a `scripts/measure_stats.py`
that prints the same shape is a follow-up.
