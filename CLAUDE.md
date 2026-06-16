# CLAUDE.md — feinschmiede repo

Working memory for AI contributors. Read before touching the master-
template renderer, the diagram pipeline, brand packs, or the gallery
publish flow.

## North Star — shrink the suite, run it in half the time

Two goals every change pursues step by step:

1. **Decrease repository size and code complexity.** Every non-trivial
   PR should leave the suite smaller or simpler than it found it, or
   have a concrete reason it cannot. Check [`STATS.md`](STATS.md)
   before and after — install footprint, source LOC, skill context
   cost. New features should subtract weight elsewhere; if the PR
   grows the install, call it out and offset it with a cut. Reject
   premature abstractions: three similar lines beats a generic helper.
2. **Speed of execution.** Default parallel-worker count for any
   batch / CPU-bound script is **`max(1, os.cpu_count() // 2)`**, with
   a `--workers N` override flag. Half the cores keeps the operator's
   machine responsive. Wired into the gallery renderer; keep it
   consistent for any new batch-style code.

## Master-template renderer

The deck pipeline is now ~500 LOC across six files under
`feinschliff/feinschliff/master_template/` (ported from `abzug`). The
brand designer owns styling — `master.pptx` is the source of truth —
the renderer plays a list of `FillPlan` / `ClonePlan` entries against
it. No DSL, no picker, no compile step.

Public surface, called directly by skills and scripts:

```python
from feinschliff import FillPlan, ClonePlan, render, apply_theme
```

The catalog inspector lives at `feinschliff.master_template.catalog`
and runs as `python -m feinschliff.master_template.catalog <pack>`.

## Brand packs

Each pack lives at `feinschliff/brands/<name>/` with three resolution
shapes for the master file:

1. `master.pptx`              — the feinschliff convention.
2. `master/master.pptx`       — the abzug convention (BSH/Bosch v5).
3. `master.pptx.ref` (text)   — an `http(s)://` URL or a local path to
   the binary, kept outside the repo. URLs are fetched once into a
   gitignored `.master.pptx` cache beside the `.ref`. Used by the
   Microsoft-gallery packs (hosted on R2, `assets.marsmike.com`) and by
   private corporate packs (local asset directory).

In-repo packs: `feinschliff` (default + 8 color themes via clrScheme
overlay) and `gs-ramspau` commit their `master.pptx`. The eight Microsoft
PowerPoint Gallery packs — `annual-review`, `geometric`, `scientific`,
`shapes`, `brand-strategy`, `pitch-deck`, `corporate`, `portfolio` — keep
their binary off-repo via `master.pptx.ref` (R2). Private corporate packs
surface via sibling `feinschliff-*` plugin directories — the
`bin/feinschliff` launcher auto-discovers their `brands/` and exports
`$FEINSCHLIFF_BRAND_PATH`.

## Themes are clrScheme overlays

`feinschliff/brands/feinschliff/themes/<name>/scheme.json` carries a
12-slot map (`dk1`, `lt1`, `dk2`, `lt2`, `accent1..6`, `hlink`,
`folHlink`). `render(..., theme=Path)` mutates the master's
`theme1.xml` in memory before plans dispatch. One `master.pptx`, N
visual variations; the file on disk is never touched. Don't author a
new master for each color variant — author a theme JSON.

## Output discipline

Repo stays small on purpose.

**Gitignored** (generated locally, not committed):

- `docs/brand-previews/`, `docs/brands/`, `docs/index.html` — Pages
  workflow regenerates them; `feinschliff/scripts/render_gallery.py`
  produces them locally.
- `feinschliff/.debug/` — every intermediate / debug / ad-hoc render.
  Build scripts render here first. No `/tmp/` or `~/Downloads`
  shortcuts — single-use renders also land in `.debug/<topic>-<date>/`.

**Allowed binary assets in git:** master.pptx files for the two house
packs (`feinschliff`, `gs-ramspau`) and the feinschmiede mark + social
card under `assets/`. The Microsoft-gallery packs keep their binary off
the public repo on R2 (`assets.marsmike.com`), reached via
`master.pptx.ref` URLs — the renderer fetches and caches them, so the
gallery still renders every pack in CI without committing third-party
templates.

## After any build — open it

Always `open` the generated `.pptx` / `.pdf` immediately after the
pipeline reports success. Type-checks and verify gates don't catch
overlapping text, missing chrome, broken Unicode, or wrong page count.
The build "verdict clean" + a visual inspection is the bar.

```bash
open feinschliff/.debug/<topic>-<date>/out.pptx
```

For headless contexts (CI), render to PNGs via `soffice` + `pdftoppm`
and inspect a sample of the slides. Don't report "done" until
something visual has been looked at.

## Verify loop

Skills wrap the verify step in `/loop` — render → soffice → read PDF
→ if defects, fix the plan and re-render. Cap at 5 iterations before
surfacing structural issues. See
[`feinschliff/skills/deck/references/verify.md`](feinschliff/skills/deck/references/verify.md)
for the defect-class table.

## Diagram pipeline

Lives in `feinschmiede/feinschmiede/diagrams/`. Consumed only by
feinbild's excalidraw / svg skills — the deck pipeline doesn't touch
it anymore. The shared `feinschmiede` package's surface after the
master-template migration is the diagram engine + `BrandPack` +
`Defect/Severity` diagnostics.

## Brand-gallery publish flow

Gallery at `https://marsmike.github.io/feinschmiede/brands/`. The
build is one script and one workflow:

1. `feinschliff feinschliff/scripts/render_gallery.py` —
   renders each in-repo brand pack (plus one tile per feinschliff
   theme variant) as a 4-slide showcase via soffice + pdftoppm + PIL,
   then writes `docs/brands/index.html`.
2. `pages.yml` runs on push to `main`: apt-install
   `libreoffice-impress + poppler-utils`, `uv sync`, run the script
   with `--workers 2` (Ubuntu runners have 4 vCPUs), upload `docs/`.

## Commit + push hygiene

- All commits require DCO sign-off: `git commit -s -m "..."`. CI
  enforces (`DCO sign-off` is a required status check).
- The other required check is `feinschliff lib tests` — kept under
  that exact name because main's branch protection requires it.
  Currently runs `npx -y claude-skills-cli validate` over every
  `SKILL.md` to enforce progressive disclosure.
- Branch protection on `main`: status checks must pass; linear
  history; no force-pushes or deletions. Solo dev — admin bypass lets
  direct-to-main land, CI runs post-hoc.
- Skills' `SKILL.md` body must pass `claude-skills-cli` (≤ 50 lines,
  good progressive-disclosure score). Heavy detail goes in
  `references/*.md`, loaded lazily.
