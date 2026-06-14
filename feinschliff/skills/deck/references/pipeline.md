# /deck Pipeline

The 7-step recipe that `/deck` follows for all modes. Read this before the skill body for the full detail; the skill body is a thin index over this file.

## Pipeline timing log

Every step of the pipeline emits a row to `<deck-dir>/timing.jsonl` so
you can run `feinschliff deck timing <deck-dir>` after a deck
completes and see where wall-clock time went. The Python CLI
auto-instruments `feinschliff deck build` (per-slide + total). The
orchestrator (you) is expected to bookend each step manually:

```
# before Step N:
feinschliff deck log-event step:1-ingest start --dir .debug/<deck>/

# after Step N:
feinschliff deck log-event step:1-ingest end --dir .debug/<deck>/ --elapsed-ms <ms>
```

Use phase names that match the step name (`step:0-ask`, `step:0a-intake`,
`step:0b-commitment`, `step:1-ingest`, `step:1a-ghost-deck`,
`step:1b-approve`, `step:1c-storyline`, `step:2-plan`,
`step:2a-fanout`, `step:3-build`, `step:4-verify`, `step:4a-fanout`,
`step:5-revise`).
For sub-agent work, add `--agent <id>` so the parallel windows are
distinguishable. Missing `end` events still show up as dangling `start`
in the report — useful for catching aborted phases.

## Parallel mode — default at slide_count ≥ 10

For larger decks (≥10 slides), Step 2 (authoring) and Step 4 (verify)
parallelize cleanly via subagents. Fan-out is the default; opt out with `--no-fanout`.

- **Step 2a (fan-out authoring)**: parent runs `deck plan-skeleton` to
  centrally pick layouts and emit an empty plan.yaml; parent spawns
  3–5 subagents (one per slide range) to author the `content:` blocks
  in parallel; parent runs `deck plan-merge` to collate. See
  [§ Step 2a](#step-2a--fan-out-authoring) below.
- **Step 4a (fan-out verify)**: parent spawns one subagent per
  verify aspect (`bbox`, `font`, `narrative`, `brand`, `image`,
  `content`); each runs `deck verify-aspect <name>` and emits a
  `verify-<aspect>.json`; parent runs `deck verify-collate` to fold
  them into a single `verify_report.md`. See
  [§ Step 4a](#step-4a--fan-out-verify) below.

Decks under 10 slides run serially — the coordination overhead
(extra subagent input tokens, parent-side merge) eats the wall-clock
win. Decks ≥10 slides use fan-out by default; pass `--no-fanout` to override.

## Brand layout inventory — before you do anything else

Every brand inherits the toolkit pool of 50 layouts (process-flow,
excalidraw-diagram, excalidraw-diagram-full, svg-infographic,
svg-infographic-full, kpi-grid, bar-chart, roadmap, recommendation,
etc.) from `feinschliff/layouts/`. A brand's own `layouts/` directory
is **additive**: bespoke layouts add to the pool or override toolkit
layouts by name.

Before claiming a brand can't serve a brief, run:

```
feinschliff-builder brand inspect <brand>
```

The output reports `N inherited, M overridden, K brand-only`. Treat
the total — not just brand-only — as the available pool. For example,
`gs-ramspau` ships 6 bespoke layouts and inherits 41 toolkit ones, so
diagram, chart, and framework layouts are all available even though
none of them live in `brands/gs-ramspau/layouts/`.

**Never tell the user "this brand has only N layouts" by counting
only the brand-local directory.** That's the toolkit pool not yet
queried.

## Step 0 — Pre-flight

The iteration loop runs until `out/verify_report.md` reports `Verdict: clean` OR a hard safety cap of **8 iterations** is hit. There is no user-facing iteration count — the scorer terminates the loop. Log a one-line progress note each iteration so the user sees convergence:

`iter N / 8 — Verdict: <clean|dirty> (M defects on K slides)`.

If image style is ambiguous from the brief, ask once here (bundle with any other Step 0a intake question). Skip if the brief makes it obvious.

## Step 0a — Intake

> **Required artifact:** none (this is the first step). ABORT if this step's command fails — do NOT fabricate an excuse.

Intake captures the user's target picture as a structured `deck_brief.yaml`
before any content is analyzed or planned. Previously the pipeline inferred
goal, audience, deck type, and visual style from free text; those inferences
now have an explicit first-class artifact that every downstream step reads.

Run Step 0a. Block until `deck_brief.yaml` is written and validated.

### Path A — brief present (`/deck "..."`)

1. Call `feinschliff.intake.infer_from_text(brief)` to seed a partial brief
   from the supplied text. This returns proposed values for all schema fields
   above.
2. Surface the inferred values to the user via a single `AskUserQuestion`
   round-trip. Show all fields as a compact table with the inferred values
   pre-filled, and ask: *"These are my reads — want to change any?"*
3. User accepts or edits individual fields. Commit `deck_brief.yaml` to the
   deck directory.

One `AskUserQuestion` round-trip total. High-confidence inferences (e.g.
audience obviously `exec` from the brief) may be shown but need no edit
prompt — the confirm step still catches the edge cases that kill decks.

### Path B — no brief (`/deck`)

Three `AskUserQuestion` rounds, in order:

1. **Q1:** `goal` + `audience` + `audience_prior` (three chips, one turn).
2. **Q2:** `deck_type` + `visual_style` + `length_hint`.
3. **Q3** (only when `deck_type` is `pitch` or `proposal`): `call_to_action`
   + `must_include` (free-text via "Other" option).

After answers: generate a one-paragraph brief from the answers, show it back
to the user, then commit `deck_brief.yaml`.

Maximum 3 `AskUserQuestion` turns.

### Schema

```yaml
# Written once at intake. Immutable inputs to planner, storyline gate, picker.
goal:            decision | buy-in | awareness | training | status | inspire   # required
audience:        exec | technical | mixed | external-customer | external-investor  # required
audience_prior:  none | some | expert      # how much they already know  # required
call_to_action:  "free text — what should they do next?"                  # optional
deck_type:       pitch | data-story | status-update | training | company-intro |
                 proposal | retrospective | all-hands | board-update       # required
visual_style:    rich-imagery | process-flow | org-hierarchy | data-dense |
                 concept-text | mixed                                      # required
length_hint:     short (<=8) | standard (~12) | long (>=18)               # required
must_include:    ["free text bullet", ...]   # optional anchors the picker treats as fixed
tone:            formal | confident-direct | warm | playful   # default: brand default  # optional
constraints:
  time_to_present_min: 15        # optional; informs density
  no_charts: false               # optional hard rules
```

Required fields: `goal`, `audience`, `audience_prior`, `deck_type`,
`visual_style`, `length_hint`. All others are optional.

### Validation

After writing `deck_brief.yaml`, run:

```bash
feinschliff deck intake-validate <deck-dir>/deck_brief.yaml
```

Exit 0 = all required fields present and valid. Exit 1 = validation error
with a descriptive message. Fail fast here — do not proceed to Step 0b with
a malformed brief.

**Artifact produced:** `deck_brief.yaml`. Step 0b cannot start without it.

### Skip path

Pass `--skip-intake` (or say "skip intake" at Step 0) to write a brief
populated solely from heuristic inference with no `AskUserQuestion` turns.
Useful for rapid iteration when the brief is detailed and unambiguous.
The `title-story-spine` and `vague-so-what` defect classes at Step 4 are
the backstop for any inference errors this misses.

### Wiring

| Step | Reads | Behavior |
|---|---|---|
| Step 0 (pre-flight) | — | Image-style question if ambiguous; runs before intake |
| Step 0b commitment | `deck_brief.yaml` | Writes `commitment.yaml`; validates arc alignment before per-slide planning |
| Step 1a ghost-deck | `content_plan.json` | Extracts titles; runs ghost-deck + title-lint checks; result feeds Step 1b prompt |
| Step 1 plan generation | `deck_brief.yaml` | Planner prompt takes deck_brief as primary input; brief.txt as secondary |
| Step 1c storyline gate | `deck_brief.yaml` + plan | Gate uses deck_type-specific arc schema instead of generic SCR (e.g. pitch → Raskin arc) |
| Step 2 layout picker | `deck_brief.yaml` + plan | New signals: `deck_type`, `visual_style`, `audience_prior` |
| Step 6 verify rubric | `deck_brief.yaml` | Rubric prompt mentions goal + audience → catches off-tone slides |

## Step 0b — Commitment

> **Required artifact:** `deck_brief.yaml`. ABORT if this step's command fails — do NOT fabricate an excuse.

Run Step 0b. Block until `commitment.yaml` is written and validated.

After `deck_brief.yaml` exists (Step 0a) and before per-slide content
planning starts, the orchestrating LLM writes a `commitment.yaml` to the
deck directory.

### Schema

```yaml
deck_type:        pitch | data-story | ...   # copied from deck_brief.yaml
thesis:           "One sentence: the single claim this deck must land."
key_moves:
  - "Move 1 — what argument or evidence this section advances."
  - "..."   # 3-7 moves total
evidence_anchors:               # optional
  - claim: "Retention improved 18%"
    source: "Q3 OKR tracker"
```

`deck_type` is copied from `deck_brief.yaml`. `thesis` is one sentence.
`key_moves` is a list of 3–7 sentences, each naming one argument step or
evidence block the deck will make. `evidence_anchors` is optional: each
entry pairs a specific claim with its source reference.

### Arc alignment

The orchestrating LLM compares each required narrative act in the
deck_type's arc schema
(`feinschliff/feinschliff/storyline/arcs/<deck_type>.yaml`) with the
`key_moves` list. Every required act must map to at least one move.
Unmapped acts surface as warnings in the Step 1b approval gate so the
user sees them before per-slide planning begins.

### Validation

```bash
feinschliff deck commitment-validate <deck-dir>/commitment.yaml --check-arc
```

Exit 0 = schema valid and all required arc acts covered. Exit 1 = validation
error or uncovered acts (warnings printed). The user reviews the commitment
and approves it — or requests edits — before per-slide planning starts.

**Artifact produced:** `commitment.yaml`. Step 1 cannot start without it.

## Step 1a — Ghost-deck title-strip check

> **Required artifact:** `content_plan.json`. ABORT if this step's command fails — do NOT fabricate an excuse.

Run Step 1a. Block until `ghost_deck_report.md` and `title_lint_report.md` are written.

After `content_plan.json` is generated (the initial slide list) and before
the Step 1b approval gate, extract the proposed slide titles and run two
checks.

### Ghost-deck check (LLM)

Extract titles from the plan:

```python
titles = [slide["title"] for slide in plan["slides"]]
```

Run the LLM title-strip check:

```bash
feinschliff deck ghost-deck <deck-dir>/content_plan.json \
  -o <deck-dir>/out/ghost_deck_report.md
```

The report carries a verdict of `pass`, `warn`, or `fail`.
- `warn` — one or more titles are weak (topic nouns, vague, no verb); these
  surface inline in the Step 1b approval prompt so the user can accept or
  request a rewrite.
- `fail` — the title sequence breaks the narrative arc badly enough to
  warrant a re-plan; the orchestrator runs one re-plan pass and re-checks
  (capped at 2 iterations) before proceeding.

### Deterministic title lint

```bash
feinschliff deck title-lint <deck-dir>/content_plan.json \
  -o <deck-dir>/out/title_lint_report.md
```

Checks: titles exceeding the character limit, titles with no verb, titles
that contain " and " (compound claims that should split), and empty titles.

**Artifacts produced:** `out/ghost_deck_report.md` · `out/title_lint_report.md`. Step 1b cannot start without both.

### Into Step 1b

Both reports are summarized as a single line appended to the Step 1b
approval prompt:

> Ghost-deck: warn (2 weak titles) · Title-lint: 1 long title, 0 empty

The user sees this summary alongside the brief and decides whether to
approve or request changes before the approval gate closes.

## Step 1 — Ingest

Read `deck_brief.yaml` (written at Step 0a) before inferring anything from
the brief text. The deck-brief fields (`goal`, `audience`, `audience_prior`,
`deck_type`, `visual_style`, `length_hint`, `tone`, `must_include`,
`constraints`) take precedence over heuristic inference in this step. The
`deck_type` field will drive type-specific arc validation in a later step
(PR 3 will populate it; for now, log the value and otherwise proceed with
the current generic SCR gate).

**Load brand-pack brief defaults (optional).** Before inferring anything from the user's brief, check whether the active brand ships priors via `brief_defaults` in its `tokens.json`. Use `load_brief_defaults(brand_dir)` (from `feinschmiede.dsl.tokens`) to read these. They provide a baseline only — apply the following precedence chain when setting each brief field:

```
explicit CLI/API flag > user text in prompt > brand_defaults > heuristic
```

Example: if `tokens.json` declares `"brief_defaults": {"verbosity": "concise"}` but the user says "detailed leave-behind", the user wins and `verbosity` is set to `text-heavy`. If the user says nothing and there is no flag, the brand default (`concise`) takes effect — otherwise fall through to the heuristic below.

**Infer verbosity tier.** Before generating slide content, decide how much text each slide should carry. Three tiers:

| Tier | Slide text budget | When to use |
|---|---|---|
| `concise` | ~20 words per slide (action title + minimal body) | Live presentation, exec audience, high visual-to-text ratio |
| `standard` | ~40 words per slide | Default — most internal decks, team reviews |
| `text-heavy` | ~60 words per slide | Leave-behind / async deck, developer audience, reference material |

Infer the tier from the brief: exec audience or `delivery: live` → `concise`; async deck or developer audience → `text-heavy`; otherwise → `standard`. Record as `verbosity` in `design_brief.json`. Use it when filling content slots in step 2 — a `concise` deck's body slots get one sentence; a `text-heavy` deck's get two or three. These targets apply to the **outline** phase; layout-specific slot constraints (maxItems, maxwidth) still govern the final render.

**Infer delivery context.** Decide how the deck will be consumed (`live | async | both`) and the physical setting (`in-person | virtual | hybrid`). Record as `delivery` and `delivery_mode` in `design_brief.json`. When `delivery_mode` is `virtual` or `hybrid`, apply the safe-zone rule during step 2: place critical content (headlines, KPIs, CTAs) in the top 60% and centre 80% of the slide canvas.

**Infer image style.** Before sourcing any assets, lock down a single visual style that will govern all image slots in the deck. Record as `image_style` in `design_brief.json`. Use the following heuristics:

| Brief cues | `image_style` |
|---|---|
| Technical/engineering deck, architecture, data-heavy | `data-viz` |
| Human-centred story, customer narrative, leadership pitch | `photorealistic` |
| Product UI, startup, B2B SaaS | `illustration` |
| Minimal brand pack (Nord, Solarized, Catppuccin) | `minimal` |
| Abstract / conceptual strategy deck | `abstract` |
| No images planned (data-only deck, all-chart deck) | `none` |

If the user explicitly names a style preference ("keep it clean and minimal", "use real photos"), that overrides the heuristic. If the brief is ambiguous, ask once at Step 0 ("Should the deck use photorealistic photos, illustrations, or a minimal/data-viz style?") rather than guessing. Step 4 fires `image-consistency` when image assets visually diverge from the declared style, and `image-slide-fit` when an individual image competes with the slide's action title or clashes with the brand palette.


**Create mode:** parse the brief. Identify:
- Overall deck purpose (executive update, technical review, product announcement, etc.).
- Each distinct concept / topic → one slide.
- Quantitative data → kpi-grid or bar-chart candidates.
- Comparisons → 2-column-cards or bar-chart.
- Sections → chapter-opener if >2 sections.

**Polish mode:** open the `.pptx` with python-pptx. For each slide:
- Extract: title, body text, bullet lists, image references, table data.
- Classify concept (via LLM): one of [title, chapter, agenda, data-quantity, data-comparison, content, quote, closer].
- Capture raw content verbatim — don't paraphrase.

After extraction, the mode branches on `--mode` (or the AskUserQuestion answer from the mode picker — see `modes.md`):

- **cosmetic mode** — extraction is complete; skip design-brief inference (Step 1b) and storyline gate (Step 1c). Proceed directly to the approval gate showing the slide-count and brand-map plan, then to Step 2 layout pick (brand-map only).
- **redesign mode** — extraction is complete; run the full pipeline from Step 1b onward (design-brief inference, storyline gate, full picker run). This is the original polish behavior.

**Critique mode:** same as polish ingest (content is derived from the existing `.pptx`).

**Also infer the design brief.** See `design-brief-schema.md` for fields. Write `design_brief.json` alongside `content_plan.json`.

### Brief inference — concrete procedure

Given `content_plan.json`, produce `design_brief.json` in one LLM pass:

1. **Audience:** infer per `audience-calibration.md` inference cues. Default to `manager` when ambiguous. Record a one-sentence `audience_notes`.
2. **Takeaway:** the single sentence the audience should repeat. Derive from the brief's strongest claim; if several compete, pick the one aligned with the business outcome.
3. **Frame:** apply `narrative-frames.md` inference cues. Pick ONE frame based on the cues — the planner does not maintain a separate frame registry. Candidates include the original consulting arcs (SCQA, PSSR, Sparkline, Man-in-a-Hole, ABT) plus three audience-design framings: **PPF** (Past-Present-Future, for trajectory / evolution decks), **PSE** (Problem-Solution-Evidence, for sales / pitch decks that need to convince skeptical buyers), and **KEA** (Knowledge-Emotion-Action, for change-management decks where the audience must feel urgency before they will act). If ambiguous, SCQA is the default. Name the runner-up in `frame_rationale`.
4. **Hook:** pick a technique (`startling-stat` / `provocative-question` / `brief-story` / `demonstration` / `contrast`) and draft the opener ≤20 words.
5. **Red line:** one sentence capturing the slide sequence's argument arc.
6. **Slides[]:** for each slide in `content_plan.json`, assign a `role` (from the frame's role set), a `claim` (see `slide-claim-test.md` — must be a claim, not a topic), and a one-sentence `audience_fit`.
   - **For data/chart slides** (role `evidence` with `concept_count > 1` quantitative; or any slide whose planned layout is in the data/chart set — `bar-chart`, `line-chart`, `kpi-grid`, `scorecard`, `stacked-bar`, `waterfall`), also emit a `so_what` slot in `content_plan.json` carrying the LLM-derived takeaway from the data, not just the data itself. The takeaway must name a metric AND a magnitude AND an actor or driver (e.g. `"Enterprise churn drove 12% revenue loss in Q3"`, not `"Improving customer outcomes through optimized retention"`). The downstream `vague-so-what` content lint enforces this — see `iteration-loop.md` defect #25.

Validate the result against the schema:

```python
from feinschliff.skills.deck.lib.design_brief import save_brief

save_brief(brief, Path("design_brief.json"))  # raises ValueError on invalid
```

If validation fails, the inference is broken — re-run with the error as additional context.

Output:
- `content_plan.json` — an ordered list of slide intents + raw content.
- `design_brief.json` — audience + narrative frame + takeaway + hook + red line + per-slide role and claim.

## Step 1b — Present the plan (single approval gate)

Print the `design_brief.json` as a compact summary + the planned slide order with roles and claims. Exact format in `modes.md`.

Ask once:

> Approve? (press enter) · Edit: say what to change · Redo from scratch: type 'redo'

### Handling the response

**Empty / "y" / "ok" / "approve":**
Proceed to step 2.

**Free-form edit request** — examples and handling:

| User says | Revise |
|---|---|
| "make it 6 slides" | Cap `slides[]` to 6 by merging / dropping the weakest claims. Re-print. |
| "audience is developers" | Change `audience` to `developer`, re-derive `audience_notes`, re-write each `slides[].audience_fit`, re-print. |
| "drop slide 5" | Remove `slides[4]`, renumber indices, re-print. |
| "use PSSR instead" | Change `frame` to `pssr`, re-sequence slide `role`s per the frame's role order, re-print. |
| "make the takeaway punchier" | Rewrite `takeaway`; if it shifts the whole deck, offer a redo. Re-print. |

Targeted revision preserves everything the user didn't complain about. Re-print the full summary (so the user sees the delta in context); re-ask.

**"redo" / "start over":**
Discard `design_brief.json` and `content_plan.json`, re-run step 1 from scratch, re-print.

### For `/deck critique` mode only

After step 1b displays, stop here. Don't proceed to step 2. Jump directly to step 4 on the existing `.pptx`. See `modes.md`.

## Step 1c — Storyline phase (NEW)

Between step 1b approval and step 2 plan, run a **title-only storyline
gate**. This catches broken narrative arcs *before* render budget is
spent on layouts and content. For the theory behind valid `narrative_act`
orderings and structural slide placement, see
[`references/slide-grammar.md`](slide-grammar.md).

The orchestrating LLM (you) does four things, in order:

1. **Materialize the contact sheet.** Run:

   ```bash
   feinschliff deck storyline content_plan.json -o out/storyline_report.md \
     --brief-summary "<one-line summary from design_brief.json>"
   ```

   This writes a "Verdict: pending" report with the numbered titles. If the
   user passed `--no-storyline` (skill-level flag — see modes.md), skip this
   step entirely.

2. **Judge the narrative arc.** Read `out/storyline_report.md`. Ask:

   - Do the titles **lead with the answer** (Pyramid Principle)? The first 1-3
     titles should carry the recommendation or thesis, not the lead-in data.
   - Do they form a **coherent argument** when read in order? A reader scanning
     only the titles should grasp both (a) the main conclusion and (b) how you
     got there.
   - Is each title a **claim**, not a topic? See `slide-claim-test.md`.
   - **Tag each slide with its SCR role.** Add a `narrative_act` field per
     slide in `content_plan.json` with one of `situation`, `complication`,
     or `resolution`. Slides that don't carry narrative weight (chapter
     openers, agenda, closer) may be tagged `null` or omitted. This feeds
     the deck-level `narrative-arc-missing` verify class at step 4 (see
     `iteration-loop.md` defect #20) and the picker's `narrative_act`
     signal for Phase 4 layouts.

   If problems exist, list them as one-line suggestions.

3. **Rewrite the report with a verdict.** Overwrite
   `out/storyline_report.md` with `verdict: clean` or `verdict: dirty` in the
   header (use the same shape — see step 4's `verify_report.md` for the
   pattern). If dirty, include a `## Suggestions` section with one bullet per
   issue.

4. **Surface to the user.** Print the contact sheet + verdict to the chat. If
   dirty, ask whether to revise `content_plan.json` titles now or proceed
   anyway. If clean, proceed to step 2 automatically.

**Why this gate exists.** The title-only readability test is the universal
McKinsey/BCG/Bain quality check ("read just the slide titles — does the story
make sense?"). Catching narrative breaks here is *cheap*: no layouts picked,
no content slots filled, no render. Catching them at step 4 verify is
*expensive*: one full build cycle wasted. This gate trades 30 seconds of LLM
judgment for an entire iteration of the build/verify loop.

**Skip path.** If the user invoked /deck with `--no-storyline` (or said "skip
storyline" at step 1b), proceed directly to step 2. The deck-level
`title-story-spine` verify class at step 4 still catches narrative breaks,
just later in the loop.

## Step 2 — Plan

Score candidate layouts using `feinschmiede.layout_picker.pick_layout`. The picker
consumes the planning-time signals you already have on each slide:

```python
from feinschmiede.layout_picker import pick_layout
from feinschmiede.dsl.parser import parse_file
from feinschmiede.dsl.tokens import load_tokens
from feinschmiede.slot_budget import compute_slot_budgets, format_budget_hint
from feinschmiede.brand_discovery import find_brand

brand_dir = find_brand("feinschliff").root
tokens = load_tokens(brand_dir)

for slide in content_plan["slides"]:
    candidates = pick_layout(
        role=slide.get("role"),
        concept_count=slide.get("concept_count"),
        data_quantity=slide.get("data_quantity"),
        comparison=slide.get("comparison"),
        narrative_role=slide.get("narrative_role"),
        narrative_act=slide.get("narrative_act"),
        time_axis_role=slide.get("time_axis_role"),
        audience_mode=slide.get("audience_mode"),
        diagram_kind=slide.get("diagram_kind"),
        layout_history=picked_so_far,
        top_k=3,
    )
    chosen = candidates[0]
    picked_so_far.append(chosen["layout"])
```

The picker enforces `when_not_to_use` rules declared on each layout and
applies a variety penalty over `layout_history`, so consecutive slides
don't reuse the same layout.

### Brand-pack content metadata

Decompiled brand packs carry planning metadata — consume it here:

- **`<brand>/deck-map.yaml`** names the brand's cover / agenda /
  section / quote / closer / content layouts. Use it for the deck
  skeleton picks (cover, agenda, section breaks, closer) before
  scoring the content slides.
- **`description` / `chrome_subject`** in each layout's frontmatter
  say what the baked-in chrome depicts (the picker echoes
  `description` as `desc:…` in its rationale). **Reject** brand
  layouts whose depicted subject clashes with the deck topic — e.g.
  off-topic decorative illustrations for a sports brief — and fall back to
  toolkit layouts rendered in brand tokens instead.
- **`when_to_use`** is the curated positive pick guidance (echoed as
  `use:…` in the picker rationale) and **`family`** the slide-type
  (framing / process / organizational / comparison / data /
  image-driven / voice / closing; `family_curated: true` marks a
  vision-verified type). Prefer layouts whose `when_to_use` matches the
  slide's job over a bare role match.
- **`element_tree`** lists every element on the slide in reading order
  with geometry (`text text_1 role=title @76,76 922x122 20pt`,
  `image image class=replace @1008,0 912x1080`, `native illustration …
  baked-text`). Read it to judge content fit — column widths, where the
  photo sits, what chrome surrounds the slots — before binding.
- **`fixed_chrome: true`** marks layouts whose decoration is carried
  verbatim and cannot reflow. Use at most 1–2 per deck, only as
  deliberate brand moments (section breaks, covers) — never for
  fact-heavy content. The picker already sinks these for content/data
  roles (`fixed-chrome-guard`); don't pin one over its objection
  without cause.
- **`chrome_text: true`** marks layouts whose native graphic draws its
  own text labels (e.g. a chevron process flow with baked STEP texts).
  Binding the overlapping text slots renders new copy OVER the baked
  labels (ghosting). Never bind such a layout's body slots with new
  text — leave the slot defaults, or use a toolkit equivalent
  (process-flow, …) in brand tokens. Picker tag: `baked-text-guard`.
- **Image slots** declare `class: replace` or `class: keep` in the
  frontmatter `slots:` map. For `replace` slots, bind a topical image
  (ctx var) or set a `query:` derived from the slide content — the
  emitter resolves `query:` via the image provider when the path slot
  is unbound. `keep` slots retain their default asset; leave them.
- When no brand layout fits a slide's content shape, prefer a toolkit
  layout (kpi-grid, process-flow, …) — the picker ranks both pools.

**Now automatic — no LLM action needed.** The pipeline consumes this
metadata deterministically: `deck plan-skeleton` (and the brand-aware
`LayoutPicker`) ranks the brand's own layouts and applies the deck-map
default — cover / agenda / section / quote / closer slides get the
deck-map layout as a +4 rank-1 bonus (`deck-map` in the rationale)
unless the slide pins `layout:` explicitly. At `deck build` time the
frontmatter `slots:` roles auto-bind: `footer` slots fill from the
plan's deck-level `vars:` (`footer_left` → leftmost slot, `footer_right`
→ rightmost; a single footer slot takes `footer_right`), `page-number`
slots get the slide's 1-based index, and unbound `class: replace` image
slots get a provider query derived from the slide's title/body (falling
back to the frontmatter `image_queries` hint) — only when an image
provider is configured. Explicit `content:` bindings (even an explicit
`""`) always win; `class: keep` slots are never auto-bound.

**`pgmeta` carries the deck name + year or section + year** (e.g. `"Bahncard 100 · 2026"`, `"Architecture · 2026"`). **Never author slide numbers into `pgmeta`** — the renderer stamps the slide counter `NN / TT` automatically as a bottom-right footer. Adding a counter to `pgmeta` produces a duplicate that appears twice on every slide.

**Compute slot budgets** before drafting slot values. The same call
runs at pre-render content-lint time, so honoring the budget here
avoids burning an iteration on `slot-overflow` defects:

```python
layout_path = Path("layouts") / f"{chosen['layout']}.slide.dsl"
nodes, _ = parse_file(layout_path)
budgets = compute_slot_budgets(nodes, tokens)
print(format_budget_hint(budgets))
```

In the fan-out (Step 2a) path, `deck plan-skeleton` computes and embeds
these budgets automatically — each slide's `_meta.slot_budgets` dict
carries `{chars_per_line, max_lines, max_chars}` per slot. **In serial
mode, compute the budgets yourself** using the snippet above and apply the
same constraints when filling `content` slots.

**Diagram and tech-radar layouts are first-class v2 layouts.** When
the brief mentions diagram / flowchart / architecture / system overview
/ layers / concept map / block diagram, pick a diagram layout based on
audience and complexity:

- `excalidraw-diagram` (narrow band, 1720×480 slot) — 2-8 nodes, simple
  or medium complexity, general / executive audiences.
- `excalidraw-diagram-full` (full-slide, 1720×720 slot, virtual
  6880×2880 canvas) — 10-20+ nodes, deep architecture diagrams with
  zones / typed arrows / typed callouts, technical audiences
  (firmware / embedded Linux / safety / architecture). Pass
  `diagram_complexity: deep` in the slide signals.
- `svg-infographic` / `svg-infographic-full` — same narrow/full split
  for quantitative custom infographics.
- Parameterized diagram templates (`process-flow`, `pyramid`, `venn`,
  `2x2-matrix`, `funnel`, `gantt`) when they fit the data shape.

Author the diagram DSL inline as the slide's `dsl` slot value. See
`excalidraw/references/dsl-syntax.md` (narrow) +
`excalidraw/references/examples-deep.md` (full) for the grammar and
patterns. One big diagram per slide — never split one concept across
two diagram slides; instead, pair a narrow overview slide with a
follow-on `-full` deep-dive slide.

When the brief mentions tech radar / technology radar / GenAI radar,
pick `tech-radar`. Slot args: `view` (one of
`genai-thoughtworks`, `genai-agents`, `genai-models`, `genai-skills`,
`genai-tooling`), optional `volume` (edition number), and `new_since`
(ISO date for the NEW badge).

**Image-bearing layout preference.** When the slide's content suits a picture (a customer story, a team intro, a hero metric with context, a contrast, a quote), prefer a layout that includes an image slot: `content-with-visual`, `kpi-photo`, `chart-photo`, `picture-full`, `text-picture`, `picture-text`. A no-image deck is the exception, not the default. The picker's `--strict-visual` flag warns on whitespace/balance issues that often signal an image-starved layout.

After the per-slide picker runs, run `feinschliff deck pick-deck plan.yaml -o picker_report.json` for the arc-aware rebalance. Block until `picker_report.json` is written. It forces a title-primary layout on slide 1, a closer layout on the last slide, and emits warnings when the deck_type's required `opening`/`closing` acts don't appear in the appropriate band.

**Artifact produced:** `picker_report.json`.

Output: `plan.yaml` — an ordered list of `{layout, content_inline|content_file}`
entries that `feinschliff deck build` consumes directly (see Step 3).

## Step 2a — Fan-out authoring (decks ≥ 10 slides)

**Default for slide_count ≥ 10.** The orchestrator MUST fan out at this size unless the user passed `--no-fanout`. Cut authoring wall-clock by ~3-5x.

`--no-fanout` is a CLI flag for the rare case where the orchestrator must run serial for debugging or low-quota environments. Default fan-out is correct for any production run.

**Parent (orchestrator) flow:**

1. Mark phase: `feinschliff deck log-event step:2a-fanout start --dir <deck-dir>`.
2. Run centralized layout pick:
   ```bash
   feinschliff deck plan-skeleton \
     <deck-dir>/content_plan.json \
     -o <deck-dir>/plan.skeleton.yaml \
     --out-pptx <deck-dir>/deck.pptx
   ```
   This consumes the same `layout_history` discipline as a serial pass.
   Resulting file has `layout:` filled and `content: {}` empty per slide.
3. Emit a one-page **color contract** (`<deck-dir>/color_contract.md`)
   that pins semantic→token mappings so subagents don't pick divergent
   colors. Sample contract:
   ```
   Primary callout / hero accent  → `accent`
   Problem markers / red lines    → `severity-medium`
   Secondary chrome / neutral box → `surface-2`
   Success state                  → `status-done`
   Inactive / muted               → `inactive` (auto-dashed)
   ```
4. Spawn N subagents (typically 3 for 10–15 slides, 5 for ≥18) using the
   `general-purpose` Agent type. Pass each subagent:
   - The full `design_brief.json` and `content_plan.json` content (read into the prompt).
   - The skeleton entries for **their assigned slide range** (e.g. slides 1–5).
   - The `color_contract.md` content.
   - The **picked layout DSL files** for their slides (so they know what slots exist).
   - Instruction: "Author the `content:` block for each assigned slide. Write the
     result as one YAML file per slide at `<deck-dir>/chunks/slide-NN.yaml` in
     the shape `{index: N, content: {...}}`. Use the color contract verbatim.
     Do not change the `layout:` unless you have a strong reason.
     **Honor the slot budgets.** Each skeleton entry carries
     `_meta.slot_budgets` — a mapping of slot name to
     `{chars_per_line, max_lines, max_chars}`. Keep every slot value
     within its `max_chars` limit and individual lines within
     `chars_per_line`. Violations produce `slot-overflow` defects at
     pre-render content-lint time and cost an iteration to fix."
5. Wait for all subagents to return.
6. Merge:
   ```bash
   feinschliff deck plan-merge <deck-dir>/plan.skeleton.yaml \
     --chunk <deck-dir>/chunks/slide-01.yaml \
     --chunk <deck-dir>/chunks/slide-02.yaml \
     ... \
     -o <deck-dir>/plan.yaml
   ```
7. Mark phase: `feinschliff deck log-event step:2a-fanout end --dir <deck-dir> --elapsed-ms <ms>`.
8. Continue to Step 3 with the merged `plan.yaml`.

**Why the centralized pick first?** The variety-penalty in
`feinschmiede.layout_picker.pick_layout` is a sliding window over `layout_history`.
Subagents picking layouts in parallel can't see each other's choices —
the result is monotony (three bar-charts in a row). Pre-picking on the
parent side preserves the variety guarantee.

**Overriding the picked layout is the exception, not the default.** The
picker already saw the brand's `deck-map.yaml`, every layout's slot
schema, and the slide's signals — its choice is informed. Brand layouts
*are* the brand chrome: a corporate pack's `slide-NN` (whether named
generically or semantically) carries the brand's wordmark, footer slots,
palette accents, and master-grid alignment that the toolkit layouts
don't reproduce. **Swapping a brand layout for a toolkit one removes
the brand chrome from that slide** — the deck loses cohesion and the
operator's brand-pack work is wasted.

Override only when the picked layout's slot shape **genuinely cannot
carry the content** — e.g. the picker chose `text-picture` (1 image, 1
text block) but you have 4 metrics to display, or it chose a single-
column body but you have a side-by-side comparison. Even then, prefer
another **brand** layout over a toolkit fallback: the brand pack almost
always has a closer equivalent.

When you do override, add `layout: layouts/<name>.slide.dsl` to the
chunk entry; `deck plan-merge` honors it. Build will emit a
`brand-chrome-leak` warning if your override swaps a brand layout for
a toolkit one — review those warnings before accepting the deck.

Concrete signal: the brand prefix in the path
(`brands/<name>/layouts/`) marks a layout as the brand's own — whether
named generically (`slide-NN` from an auto-decompiled corporate pack)
or semantically (`market-comparison`, `traction` in a hand-curated
pack). Protect those.

## Step 2b — Claim-evidence text gate (optional, recommended)

After content slots are filled (either serial Step 2 or fan-out Step 2a
merge), run the claim-evidence gate. This catches `title-body-coherence`
and weak-evidence defects *before* render — cheap text-only Haiku judgment
(~5 s for a 10-slide deck) replaces a full render+verify cycle for this
class.

```bash
feinschliff deck claim-evidence out/<deck>/plan.yaml \
  --design-brief out/<deck>/design_brief.json \
  -o out/<deck>/claim_evidence_report.md
```

Exit 0 = clean; exit 1 = at least one slide has a claim-evidence defect;
exit 2 = plumbing error. Use `--offline` to skip all LLM calls (testing /
CI without an API key).

The gate checks each slide whose role implies a claim (`evidence`,
`recommendation`, `resolution`, `complication`, `result`, `claim`,
`data-quantity`, `data-comparison`, `content-columns`,
`content-with-visual`). Non-claim slides (`chapter`, `agenda`, `closer`,
`title`, `cover`, `divider`, `quote`) are automatically skipped.

For each judged slide, Haiku answers two questions:
1. Does the body provide direct evidence for the title's claim?
2. Is there body content unrelated to the title's claim?

If `design_brief.json` is supplied, per-slide `claim` fields are passed as
additional context so the model can flag title drift from the intended claim.

The report at `claim_evidence_report.md` carries:
- Overall verdict (`clean` / `dirty`)
- Per-slide rationale
- Optional `suggested_title` / `suggested_body` rewrites for dirty slides

**When to use:** always for decks ≥ 5 slides before spending render budget.
Skip only when iterating on layout/DSL changes with unchanged content.

**Timing:** log this phase as `step:2b-claim-evidence`:

```bash
feinschliff deck log-event step:2b-claim-evidence start --dir out/<deck>/
feinschliff deck claim-evidence ...
feinschliff deck log-event step:2b-claim-evidence end --dir out/<deck>/ --elapsed-ms <ms>
```

## Step 2c — Static verify gate (optional, recommended)

Before burning render budget, run the pre-render static geometry verifier.
This catches slot-overflow and empty-placeholder defects from the DSL +
populated content in ~10-50 ms/slide — far cheaper than re-rendering.

```bash
feinschliff deck verify-static out/<deck>/plan.yaml
```

Exit 0 = clean; exit 1 = defects found (printed to stdout); exit 2 = plumbing
error. Use `--json` for machine-readable output (array of defect dicts).

Two defect classes are detected at this stage:

- **slot-overflow** — content exceeds the pixel budget of the DSL slot
  (`maxwidth` × `maxheight`). Prediction uses the same `textfit.fits()`
  helper as the autoshrink emitter, so the prediction matches what the
  renderer would do. Severity is **FATAL** — `deck build` always aborts before
  `compile_slide()` is called when an overflow is detected.
- **empty-placeholder** — a slot interpolated by `{{ slot }}` in the layout
  is absent from the plan's `content` dict or is an empty/whitespace string.
  Severity is WARN — the orchestrator decides whether to abort.

slot-overflow is always fatal; `deck build` runs this gate by default. The
`--strict-static` flag promotes WARN-severity defects (e.g. empty-placeholder)
to build-blockers as well. `--skip-content-lint` no longer bypasses geometry
checks.

**When to use:** always for large decks (≥ 5 slides) where an overflow costs
one full iteration to fix. Skip only when you're iterating on DSL changes
and have already reviewed the content manually.

## Step 3 — Build

The build is one CLI invocation. The orchestrator hands `feinschliff deck build`
a plan YAML; the CLI runs `compile_slide()` per slide, validates each, composes
the multi-slide deck, and writes `.pptx` + diagrams alongside.

```yaml
# out/<deck>/plan.yaml
brand: feinschliff
out: out/<deck>/deck.pptx
slides:
  - layout: layouts/title-cover.slide.dsl
    content_file: out/<deck>/slide-01.yaml
  - layout: layouts/executive-summary.slide.dsl
    content_inline:
      title: "Q1 results"
      subtitle: "What we shipped"
      body: "Three things drove the quarter..."
  - layout: layouts/excalidraw-diagram.slide.dsl
    content_file: out/<deck>/slide-03.yaml      # has a `dsl` slot with the diagram body
```

Run:

```bash
feinschliff deck build out/<deck>/plan.yaml
```

The CLI:
1. Resolves the active brand via `feinschmiede.brand_discovery.find_brand`.
2. For each slide, calls `feinschmiede.pipeline.compile_slide(...)` — parsing, interpolating, expanding diagrams (running the diagram validators), and expanding compounds.
3. Aborts on any fatal defect (defect taxonomy: see `feinschliff/docs/quality-contract.md`). Pass `--allow-diagram-warnings` to demote diagram-overflow / diagram-text-too-small. Pass `--allow-missing-assets` to ship with grey-box pictures (not recommended for final builds).
4. Composes all slides into one `.pptx`, writes `diagrams/` next to the output, and writes per-source asset locks under `out/<deck>/asset_lock.json` and credits under `out/<deck>/credits.md` whenever search-resolved assets were used.

Diagram layouts (`excalidraw-diagram.slide.dsl`,
`excalidraw-diagram-full.slide.dsl`, `svg-infographic.slide.dsl`,
`svg-infographic-full.slide.dsl`) are full first-class v2 layouts. The
agent authors the diagram DSL inline in the slide's content YAML as
the `dsl` slot value; the expander turns it into a PNG and embeds it.
The `-full` layouts use a virtual 6880×2880 canvas so the model has
16× more pixel area to compose into; PowerPoint downscales on insert.
See the `feinbild` plugin's excalidraw skill references (`dsl-syntax.md`,
`examples-deep.md`) — the standalone diagram-DSL authoring docs moved there.

Run `feinschliff deck build out/<deck>/plan.yaml --strict-craft --strict-visual` for a clean build. `--strict-craft` enforces Knaflic deterministic rules at build time: no pie charts, no 3-D charts, title word-count budgets, body word-count budgets, compound titles containing "and", titles that are topics rather than claims, chart titles that omit a claim, and palettes with too many simultaneous colors. Violations abort the build and the findings are written to `out/<deck>/craft_report.md`. `--strict-visual` runs PIL-based post-render metrics after each slide is composited: whitespace ratio, left/right balance, and element collision. Violations abort the build and the findings are written to `out/<deck>/visual_metrics_report.md`.

**Artifacts produced:** `out/<deck>/craft_report.md` · `out/<deck>/visual_metrics_report.md`.

Output: `out/<deck>/deck.pptx` (draft).

## Step 4 — Verify (visual + theory) — MANDATORY, NEVER SKIPPED

> **Required artifact:** `out/verify_report.md`. ABORT if this step's command fails — do NOT fabricate an excuse.

**This step runs at least once. No exceptions.** You do not know whether step 3 succeeded until you look at the rendered PNGs. "The build didn't error" is not verification. Even if the iteration budget is 1, you still run one verify pass before declaring completion.

Render the draft:
```bash
soffice --headless --convert-to pdf --outdir /tmp/deck-verify out/<name>.pptx
pdftoppm -r 96 -png /tmp/deck-verify/<name>.pdf /tmp/deck-verify/slide
```

For each PNG, LLM inspects (visually read the PNG file — do not skip the Read call) for all 29 defect classes per `iteration-loop.md`. The canonical visual reference for "what this layout should look like" is the active brand's `feinschliff/<brand-root>/claude-design/<brand>-2026.html` (e.g. `feinschliff/brands/feinschliff/claude-design/feinschliff-2026.html` by default) — open it alongside when uncertain whether a slide matches brand intent.

**Required artifact:** write `out/verify_report.md` — human-readable, overwritten on each verify pass. Shape:

```markdown
# Verify Report — <name>.pptx

- **Iteration:** 1 of 3
- **Verdict:** dirty — 2 defects across 1 of 8 slides
- **Rendered PNGs:** `/tmp/deck-verify/slide-*.png`
- **Reference:** `feinschliff/<brand-root>/claude-design/<brand>-2026.html`

---

## Slide 3 — "Our Approach" (layout: two-column-cards)

- **claim-title** — title "Our Approach" is a topic noun.
  **Fix:** Rewrite as a claim, e.g. "We ship daily because we test first".
- **bullet-dump** — 7 peer-level bullets, no hierarchy.
  **Fix:** Subordinate under 3 sub-headings; drop weakest two bullets.

## Slide 5 — "Q1 Results" (layout: kpi-grid) ✅

_No defects._

<!-- ...one section per slide... -->
```

The header block is the completion gate: `Verdict:` must be readable by both Claude (to decide whether to loop) and the user (to understand what's wrong). If `verdict` is `clean`, list every slide with `✅ No defects.` so the user sees the full coverage — don't silently omit passing slides.

`out/verify_report.md` is overwritten on each iteration; the file always reflects the most recent build. If you need iteration history, prior reports are recoverable from `git log` or conversation transcript.

If the file does not exist on disk, the deck is not done — regardless of how confident you feel about the build. Before telling the user "done", confirm the file exists and the header says `Verdict: clean` (or budget is exhausted and you're emitting residuals per step 5).

Never print `Verdict: clean` to the user without first writing `out/verify_report.md` containing that verdict line. If the visual rubric crashed for any reason, surface the actual error — do not silently downgrade to a header-only summary.

## Step 4a — Fan-out verify (decks ≥ 10 slides)

**Default for slide_count ≥ 10.** The orchestrator MUST fan out at this size unless the user passed `--no-fanout`. Cuts verify wall-clock from ~3-5 min to ~1-1.5 min. The verify pass is decomposed into six independent aspects, each runnable as a subagent in parallel:

| Aspect | Checks | Determinism | Time budget |
|---|---|---|---|
| `bbox` | bounding-box overflow, text-overflow, out-of-bounds, diagram-overflow | full | ~5-10s |
| `font` | text-too-small, role-mismatch, fragile-detail-role | full | ~2-5s |
| `narrative` | SCQA / claim-title / title-story-spine / MECE | LLM | ~30-60s |
| `brand` | non-canonical-token, color-contrast | partial (token check is full) | ~5-15s |
| `image` | image-style consistency, image-slide-fit | LLM | ~30-60s |
| `content` | filler-word, title-body-coherence, redundancy | partial (filler is full) | ~30-60s |

**Parent (orchestrator) flow:**

1. Mark phase: `feinschliff deck log-event step:4a-fanout start --dir <deck-dir>`.
2. Spawn 6 subagents in parallel (one per aspect). Each subagent runs:
   ```bash
   feinschliff deck verify-aspect <aspect> \
     --plan <deck-dir>/plan.yaml \
     --design-brief <deck-dir>/design_brief.json \
     --png-dir <deck-dir>/verify/ \
     -o <deck-dir>/verify-<aspect>.json
   ```
   Aspects with `needs_llm: true` (narrative, image, content) require the
   subagent to follow up with LLM judgment on the materialized data
   (contact sheet for narrative, PNG inspection for image) and append
   findings to the JSON before returning.
3. Wait for all 6 subagents to return.
4. Collate:
   ```bash
   feinschliff deck verify-collate \
     --plan <deck-dir>/plan.yaml --iteration N --budget M \
     --png-dir <deck-dir>/verify/ \
     --aspect <deck-dir>/verify-bbox.json \
     --aspect <deck-dir>/verify-font.json \
     --aspect <deck-dir>/verify-narrative.json \
     --aspect <deck-dir>/verify-brand.json \
     --aspect <deck-dir>/verify-image.json \
     --aspect <deck-dir>/verify-content.json \
     -o <deck-dir>/verify_report.md
   ```
5. Mark phase: `feinschliff deck log-event step:4a-fanout end --dir <deck-dir> --elapsed-ms <ms>`.

**Defect dedup.** Two aspects can flag the same root cause from different
angles (e.g. `bbox`/`text-overflow` and `font`/`detail-fragile` on the
same slide). The collator preserves both findings — the revise pass can
fix once and clear both flags on the next iteration.

**Token cost.** Six subagents each load the design_brief + plan.yaml
extract. Roughly 5–6× the input tokens vs serial. Worth it above
~10 slides; not worth it below.

## Step 5 — Revise (if defects)

If `verify_report.md` header says `Verdict: dirty`: adjust `deck_plan.json` (change layouts, shorten text, split slides, rewrite titles as claims) and loop back to step 3. Increment `Iteration:` in the next verify report.

**Hard stop at 8 iterations.** Default expectation is 2–3 iterations on most decks. Each iteration = one build + one verify pass. The verify pass runs on iteration 1 too — there is no "skip verify on the last happy-path build" shortcut.

If the budget is exhausted with any artifact missing, emit `out/RESIDUAL_ISSUES.md` listing exactly what's missing and what the orchestrator tried to do about it.

If the final iteration still has defects:
- Emit the current draft to `out/<name>.pptx`.
- Emit `out/RESIDUAL_ISSUES.md` listing unresolved defects (derived from the final `verify_report.md`).
- Surface both to the user, explicitly noting "budget exhausted with N defects remaining".

## Critique-mode flow (variant)

`/deck critique existing.pptx` runs a subset of the pipeline:

```
Step 0   Pre-flight (image style if ambiguous)          — SKIPPED (no iteration loop)
Step 1   INGEST existing .pptx → content_plan.json
         DERIVE design_brief.json from extracted content
Step 1b  PRESENT brief for approval / edit             — user can correct audience/frame
Step 2   PLAN                                          — SKIPPED
Step 3   BUILD                                         — SKIPPED
Step 4   VERIFY                                        — runs on the existing .pptx
Step 5   REVISE                                        — SKIPPED (read-only)
```

Outputs next to the source `.pptx`:
- `<name>-critique.md` — per-slide defect list with suggested fixes.
- `design_brief.json` — the brief Claude derived.

No mutation of the source. See `modes.md` for the critique output format.

## Out of scope

- Chart regeneration (charts in the source pptx stay embedded as pictures).
- Animations and transitions.
- Speaker-notes reformatting (copy verbatim).
- Multi-brand within a single deck (one active brand pack per `/deck` invocation, resolved from `FEINSCHLIFF_BRAND` / `--brand`).
