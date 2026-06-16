# Storyline — plan before you render

Before composing `FillPlan` / `ClonePlan`, draft the storyline and get user approval. Zero render cost; catches arc and claim problems while they're cheap to fix.

## Two blocks, in-context (no files)

**Brief block** — emit first:

```
takeaway:  <one sentence, ≤200 chars — the deck's single top-of-pyramid claim>
audience:  exec | manager | developer | peer
frame:     SCQA | Sparkline | Man-in-Hole
verbosity: concise | standard | text-heavy
```

**Slides block** — numbered list, one row per slide:

```
1. [role] act — "title claim"
2. [role] act — "title claim"
...
```

`role` ∈ `hook, context, complication, recommendation, support, evidence, close`.
`act` ∈ `situation, complication, resolution` (use the title-only readability test below).

## Frames (role order)

- **SCQA** (default — recommendations, proposals)
  `hook → context → complication → recommendation → support → close`
- **Sparkline** (vision, roadmap, strategy)
  `hook → context → complication → recommendation → context → recommendation → close`
  (alternating problem/payoff beats)
- **Man-in-Hole** (incident, retro, war story)
  `hook → context → complication → complication → recommendation → close`

Pick from brief cues: "recommend / should / propose" → SCQA; "vision / future / 3-year" → Sparkline; "incident / outage / what went wrong" → Man-in-Hole.

## Audience → slide count

| Audience    | Target count | Why                                              |
|-------------|--------------|--------------------------------------------------|
| `exec`      | 5–7          | Decision-first; one claim per slide              |
| `manager`   | 8–12         | Context + recommendation + support               |
| `developer` | 12–20        | Mechanism, edge cases, sequencing                |
| `peer`      | 8–12         | Same as manager unless brief says otherwise      |

User-stated count overrides this; use as default when the brief is silent.

## Takeaway placement

The brief block's `takeaway` must appear verbatim (or near-verbatim) on **either the cover or the close slide**. It's the deck's top-of-pyramid claim — if a reader sees only one slide, this is the one. Check during the approval gate.

## Verbosity → fill length

Soft cap on text-run length when composing `fills={}`:

| Verbosity        | When                          | ~words per slot |
|------------------|-------------------------------|-----------------|
| `concise`        | exec audience or live delivery| 20              |
| `standard`       | manager, mixed delivery       | 40              |
| `text-heavy`     | developer or async/read-only  | 60              |

## Title rules (claim, not topic)

Every content-slide title contains a **verb or a number**. Reject:

- ❌ "Overview", "Background", "Process", "Next steps"
- ✅ "Onboarding drops 18% after step 3", "Ship gated rollout in Q3"

Structural slides (cover, chapter divider, end) are exempt.

## Title-only readability test

Read just the titles in order. The acts should march `situation → complication → resolution` per the frame. If two adjacent complication titles answer the same question, merge them. If a resolution lands before any complication, reorder.

## Variety rule

Don't reuse the same layout in two adjacent **content** slides. Structural layouts (`Title Slide *`, `Beginning of New Chapter *`, `Only Title`, `End Slide`) are exempt. Layout-by-content selection lives in [layouts.md](layouts.md).

## Examples

**SCQA — 7-slide proposal to ship a gated rollout** (audience: exec, concise)

```
takeaway:  Ship the new checkout to 10% of traffic in Q3 — full ramp by Q4.
audience:  exec
frame:     SCQA
verbosity: concise

1. [hook]           situation     — "Ship checkout v2 to 10% in Q3"
2. [context]        situation     — "Current checkout converts at 2.1%, flat 4 quarters"
3. [complication]   complication  — "Cart abandonment up 18% after step 3"
4. [recommendation] resolution    — "Gated rollout: 10% in Q3, 100% in Q4"
5. [support]        resolution    — "Rollback in <5 min; per-cohort kill switch"
6. [evidence]       resolution    — "Internal dogfood: +14% completion, 0 P1s in 6 weeks"
7. [close]          resolution    — "Ship the new checkout to 10% of traffic in Q3"
```

**Man-in-Hole — 6-slide incident retro** (audience: manager, standard)

```
takeaway:  The 4h outage was a config-rollout gap — fixed by staged config + canary.
audience:  manager
frame:     Man-in-Hole
verbosity: standard

1. [hook]           situation     — "Checkout was down for 4h on May 12"
2. [context]        situation     — "Config push fans out to all regions in <30s"
3. [complication]   complication  — "Bad timezone rule passed CI, broke all regions at once"
4. [complication]   complication  — "No staged rollout meant no early warning"
5. [recommendation] resolution    — "Stage config across 3 cohorts; 10-min canary per stage"
6. [close]          resolution    — "Staged + canary lands June 30"
```

## Approval gate

Print the brief block + slides block as a single message and ask:

> Storyline ok? (`y` to render / edit a row / redo)

Do not call `render()` until the user approves.
