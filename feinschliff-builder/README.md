# feinschliff-builder

Brand-pack authoring + QA toolkit for [feinschliff](https://github.com/marsmike/feinschmiede).
Capture a brand from a PPTX or HTML reference, score how close the pack
renders to the source, and iterate via an AI-assisted improvement loop.

**Requires:** `feinschliff` installed first.

## Install

```bash
/plugin marketplace add marsmike/feinschmiede   # once per machine
/plugin install feinschliff@feinschmiede        # required dependency
/plugin install feinschliff-builder@feinschmiede
```

## Canonical pipeline

```
1 · Capture                2 · Verify                  3 · Improve
   ─────────                  ────────                     ────────
                                                       struct_diff
  source.pptx                 build + render             > threshold?
     │                            │                           │
  feinschliff-builder decompile     brand_verify_loop.py    /improve-brand skill
     │                            │                           │
  feinschliff-builder slotify         report.json                 fan-out edits
     │                       (per-layout                      │
  brands/<name>/              struct_diff,             re-verify, plateau
     │                        block_diff,                     │
   ready                      edge_diff, ssim)               done
```

**Bootstrap a new brand from a source PPTX (Capture → ready scaffold):**

```bash
feinschliff-builder decompile \
    --brand-pack feinschliff-extra/brands/<name> \
    --source-pptx path/to/source.pptx

feinschliff-builder slotify \
    --brand-pack feinschliff-extra/brands/<name>
```

Step 1 emits the slotified DSL bodies under `layouts/` AND writes
`<brand>-annotated.pdf` alongside (one page-set per layout: render +
slot coverage + frontmatter detail — the reviewer document). Pass
`--no-annotate` to skip the PDF. Step 2 adds the picker frontmatter
(`role`, `ideal_count`, `slots`, etc.) and writes `deck-map.yaml`. Run
them in this order — step 2 is what the `/deck` picker reads.

**Score an existing brand pack against its source PPTX (Verify):**

```bash
uv run python feinschliff-builder/scripts/brand_verify_loop.py \
    --brand-pack feinschliff-extra/brands/<name> \
    --source-pptx path/to/source.pptx
```

Writes per-layout `struct_diff_ratio` + overlay PNGs under
`out/<brand>/verify-loop/`. Treat ≤5% as clean; above that, run improve.

**Close the gap with an AI-assisted loop (Improve):**

```
/feinschliff-builder:improve-brand <brand-dir> <source.pptx>
```

The skill runs the verify loop, fans out one sub-agent per
above-threshold layout (one message, all parallel), and iterates until
all layouts are ≤ threshold or plateau. Full detail:
[`skills/improve-brand/SKILL.md`](skills/improve-brand/SKILL.md).

## CLI subcommands

```bash
feinschliff-builder <subcommand> [options]
```

| Subcommand | What it does |
|---|---|
| `decompile` | **Step 1 of bootstrap** — bulk-decompile every layout in a brand's `verify-map.yaml` from a source PPTX; also emits the annotated documentation PDF (`--no-annotate` to skip) |
| `slotify` | **Step 2 of bootstrap** — add picker frontmatter to each layout + emit `deck-map.yaml` |
| `audit` | Slot-coverage acceptance check for a brand pack |
| `brand list` / `brand inspect <name>` | Brand pack utilities |
| `compile-html` | Compile a `claude-design` HTML to `.slide.dsl` skeletons |
| `verify` | Structural validation of a built `.pptx` deck |
| `verify-quality` | LLM quality rubric (spacing, contrast, typography) |
| `verify-diagram` | Validate diagram DSL files for syntax and token references |
| `eval` | Grade generated artifacts (`.excalidraw`/`.svg`) against a skill's `evals/evals.json` — the deterministic scorer behind `/autoloop` |

## Skills

| Skill | When to use |
|---|---|
| **`/compile`** | Scaffold `.slide.dsl` skeletons from a Claude-Design HTML reference |
| **`/improve-brand`** | Drive a brand pack toward source-PPTX fidelity — parallel per-layout fan-out, verify-revise loop |
| **`/autoloop`** | Iteratively improve a target toward any measurable goal — `measure → mutate → keep/revert → consolidate`, scored by `feinschliff-builder eval`; rides Claude Code's built-in `/goal`. See [`skills/autoloop/README.md`](skills/autoloop/README.md) |

## Deep dives

- [`docs/improvement-and-verification-loops.md`](docs/improvement-and-verification-loops.md) — the full pipeline philosophy: graders, loops, all built-in scoring mechanisms.
- [`../feinschliff/docs/brand-pack-contract.md`](../feinschliff/docs/brand-pack-contract.md) — what a brand pack must contain to be discoverable + buildable.
- [`skills/improve-brand/references/`](skills/improve-brand/references/) — per-slide prompts, plateau handling, decompile-from-source walkthrough.

## License

MIT — see repo root [`LICENSE`](../LICENSE).
