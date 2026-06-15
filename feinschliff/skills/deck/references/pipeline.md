# Pipeline — `/deck`

Detailed step-by-step. Every step writes an artifact to `out/`; skipping
any of them invalidates the verdict.

## 0. Brand resolution

`--brand <id>` → `FEINSCHLIFF_BRAND` env var → `feinschliff` default.

The brand pack lives at `feinschliff/brands/<id>/` or
`feinschliff-extra/brands/<id>/`. Its master-template catalog:

```
<brand_pack>/
  master.pptx              # source of styling truth
  layouts.yaml             # named layouts + placeholder schema
  snippets.yaml            # bespoke source slides indexed for cloning
  themes/<name>/tokens.json # optional — color overlays
  assets/                  # brand images, logos, fallback photography
```

A pack without `layouts.yaml` / `snippets.yaml` / `master.pptx` is not
master-template-shaped; report that and stop.

## 1. ask

Interview the user when the brief is thin. Required fields land in
`deck_brief.yaml`:

```
audience: who reads this and what they care about
intent: what the deck must achieve (sell, brief, decide, retro)
topic: subject
slide_count: number (default 8)
tone: register (executive, technical, etc.)
image_style: rich-imagery / mixed / data-dense / concept-text / minimal
```

See `references/audience-calibration.md` and `references/design-brief-schema.md`.

## 2. intake

Pull every fact-source the user named (URLs, paths, attached files,
prior decks). Drop into `out/intake/` with a manifest. Surface sources
the user implied but didn't supply.

## 3. commit

Write `commitment.yaml`: what's in scope, what's deferred, what
verification you'll run. The user approves before any planning starts.

## 4. ingest

Convert intake into `content_plan.json` — list of slide-shaped intents
(headline + body + visual_intent) in the order they'll appear. No
layout yet, no plan yet. Pure narrative shaping.

See `references/narrative-frames.md`, `references/slide-claim-test.md`,
`references/anti-patterns.md`.

## 5. approve

Show the user the `content_plan.json` summary. Get sign-off before
spending render time.

## 6. plan

Generate `ghost_deck_report.md` — text-only paper preview. For each
slide: title + 1-line claim + intended visual. Catches narrative gaps
before commit to layout.

Run `feinschliff deck title-lint` over the plan; write
`title_lint_report.md`. Failures block render.

Run `feinschliff deck claim-evidence` if data citations matter for the
audience; the report calls out unsubstantiated quantitative claims.

## 7. pick layouts

For each slide in the content plan, pick:

- **A layout from `<brand_pack>/layouts.yaml`** by `role` and
  `placeholders[].accepts`. Match content intent to the layout's
  placeholder schema. See `references/picking.md`.
- **OR a snippet from `<brand_pack>/snippets.yaml`** when the content
  fits a designer-authored composition (timeline ribbon, funnel, multi-
  shape infographic). Snippet picking uses the `intent:` field.

Output: `plans.yaml`. One entry per slide, in slide order. Two shapes:

```yaml
plans:
  - type: fill
    layout: "Title + Graphical Content + Text"
    fills:
      0: "Q1 2026 — revenue +5.1%"
      1:
        - "Headline takeaway"
        - "Supporting bullet"
        - "Second supporting bullet"
  - type: fill
    layout: "Title and 3 Contents"
    fills:
      0: "Three growth levers"
      1: ["Speed", "Cycle time −38%"]
      2: ["Quality", "Defect rate −22%"]
      3: ["Cost", "Ops overhead −30%"]
  - type: fill
    layout: "Title + Graphical Content + Text"
    fills:
      0: "Quarterly revenue"
      1:
        chart:
          kind: column
          categories: [Q1, Q2, Q3, Q4]
          series:
            - ["Revenue (M€)", [14.2, 17.8, 19.4, 22.6]]
  - type: clone
    snippet_id: timeline-12-months
    text_replacements:
      - ["Timeline 4", "H1 2026 — release waves"]
      - ["Milestone date", "Q1 launch"]
```

Picture fills accept a path:

```yaml
2:
  picture: ./assets/team.jpg
```

## 8. render

```
feinschliff render-master \
  --brand-pack <brand_pack> \
  --plans out/plans.yaml \
  -o out/deck.pptx \
  [--theme <name>]
```

`--theme` recolors srgbClr values via the brand's
`themes/<name>/tokens.json`. Same plans, different palette.

## 9. verify

Run the verification gates. Each writes its own report; all roll up
into `verify_report.md`:

- **`feinschliff deck verify`** — visual gates: aspect, overflow,
  notes-coherence, slide-number footer.
- **`feinschliff-builder verify`** — structural gates over the
  rendered .pptx (text room, slot bounds, picture aspect).
- **`feinschliff-builder verify-quality`** — LLM rubric over a soffice
  render of each slide.
- **`feinschliff-builder verify-diagram`** — diagram artifacts
  validated against brand tokens.
- **`feinschliff deck critique`** — read-only defect analysis (no
  fixes; just calls out what's wrong).

Failures route to the next step.

## 10. revise

Iterate: edit `plans.yaml`, re-render, re-verify. See
`references/iteration-loop.md` for the loop discipline (when to stop,
what counts as ship-ready). Don't print "Verdict: clean" without a
verify_report.md on disk.

## Polish mode

For an existing rough `.pptx` (`/deck polish rough.pptx`), the
pipeline runs in `--mode cosmetic` by default:

- Preserves slide count + content.
- Fixes chrome / typography / overflow only.
- No layout swaps, no rewriting of text.

`--mode redesign` rebuilds plans from scratch using the rough as the
content_plan source. Heavier; only when the rough is structurally
wrong, not just unpolished.

## Critique mode

Read-only. `feinschliff deck critique existing.pptx` walks every slide
and emits a defect list. No render, no fixes. Use to scope a polish
job or to give the user a list to act on themselves.
