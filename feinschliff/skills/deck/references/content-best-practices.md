# Content Best Practices — Feinschliff

## Cognitive principles

Three principles govern every content decision. They are not style preferences — they are how the brain processes slides:

**Signal-to-Noise Ratio.** Every element on a slide is either signal (serves the message) or noise (competes with it). Decorative shapes, unnecessary logos, dense prose, redundant labels — all noise. When in doubt, remove. A slide with five elements where four matter is worse than a slide with two elements that both matter.

**Picture Superiority Effect.** Images are recalled significantly better than words. When a visual can carry the claim, prefer it over prose. A well-chosen chart, diagram, or photo with an action title outperforms a text-heavy explanation of the same idea. This is why the assertion-evidence model works: the brain processes image and spoken word in parallel; it processes text and spoken word in competition.

**Redundancy Effect.** A slide that restates what the presenter is saying aloud forces the audience to split cognitive load between reading and listening — both channels compete for the same working memory. Slide text should complement speech, not duplicate it. If you can read the slide and deliver no additional information, the slide is acting as a teleprompter, not a visual aid.

**Billboard test (Duarte).** If a driver passing a billboard at speed can't parse it in 3 seconds, it fails. Apply the same test to every slide: title + primary visual should communicate the core point in 3 seconds without reading the body. If it can't, the title is too long or the visual is too complex.

**So-What chain (editing heuristic).** After writing any body sentence, ask "So what?" Repeat until you reach a concrete business or human impact. If you can't get there in two steps, the sentence is noise. Cut or rewrite.

## Voice

The default voice rule that ships with the feinschliff pack:

> "Write like an engineer explaining their work to a colleague they respect. Short sentences. Concrete nouns. No superlatives."

Apply this to every text slot you fill. Brand packs that ship their own voice rider override this default — check the active brand's `claude-design/<brand>-2026.html` or pack-level README for brand-specific voice guidance.

## Less is more

- **Title slot**: under 8 words, no period unless statement.
- **Eyebrow**: 2-4 words, mono uppercase. Treat as tag, not sentence.
- **Body**: one complete thought per paragraph, max 2 paragraphs.
- **Column titles**: noun phrase or short statement; max 10 words.
- **Column body**: 1-3 sentences; avoid sub-bullets.
- **KPI value**: a number only. Unit separate. No prefix symbols inside the value.
- **Bar labels**: uppercase country/region/product code. Max 10 chars.

## One idea per slide

If you catch yourself writing "and also..." in body text, split the slide.

## When to add a slide

- Before a major concept shift: chapter opener.
- For every distinct numeric comparison: its own slide.
- Never cram more than 6 items into any layout (each layout's placeholders[] in `layouts.yaml` declares the available slot count + per-slot `char_budget`).

## When to skip a layout

- No chapter opener if the deck has only one section.
- No agenda for decks under 4 content slides.
- No quote for operational / status updates (feels performative).

## Images

- Path placeholders accept absolute or project-relative paths.
- Image fills proportionally to the layout's picture frame; provide images close to the frame's aspect ratio.
- If no image is available, leave the picture placeholder empty — the striped grey placeholder is part of the design, not an error.

## Numbers

- Value and unit stay separate in KPI slots (`value="62"`, `unit="k"`). Do NOT write `value="62k"`.
- Format values without thousands separators for single digits; with separators for >3-digit figures.
- Deltas always include direction (`+3% YoY`) and period.

## Delivery context — presenter deck vs. leave-behind

A deck consumed live (projected, presented) and a deck consumed async (shared PDF, forwarded slide file) are different artifacts. Treat them differently.

**Presenter deck (live delivery):**
- Sparse text — the speaker carries the narrative; the slide carries the visual
- Action titles + visual evidence; body text is minimal or absent
- Animations and progressive reveals are appropriate
- Slides can be ambiguous in isolation — the presenter fills the gaps

**Leave-behind deck (async / standalone):**
- Body text must be complete enough to stand without a speaker; add context the presenter would have spoken
- Speaker notes are promoted into the body or a visible notes section
- No animations (flatten before exporting)
- Every slide must be self-explanatory in isolation

**At brief time (step 1):** infer or ask the delivery context. Record it in `design_brief.json` as `delivery: "live" | "async" | "both"`. If `"both"`, build the presenter deck first, then produce a leave-behind variant with expanded body text and flattened animations. Never try to serve both audiences with a single layout — the result is too dense for live and too sparse for async.

## Hybrid / virtual safe zone

When delivery is virtual (Zoom, Teams, Meet) or hybrid, meeting software chrome and webcam overlays obscure the bottom portion of the slide. Apply the safe-zone rule:

- **Keep critical content in the top 60% and centre 80%** of the slide canvas.
- Headlines, key numbers, and calls-to-action must sit in this zone.
- Decorative elements, footnotes, and source lines may extend to the lower edge.

Flag this in `design_brief.json` as `delivery_mode: "virtual" | "hybrid" | "in-person"` (default `"in-person"`). When virtual or hybrid, adjust layout placement accordingly.

## Layout variety

Limit the entire deck to **3–5 distinct layout types**. Visual consistency reduces cognitive overhead; a deck that introduces a new template every third slide makes the audience re-orient instead of absorb. Once a layout is used for a content type (data → chart-dominant, comparison → two-column-cards), apply it consistently throughout.

## Error on the side of brevity

If you're unsure whether to add detail, don't. Empty space is intentional in the default Feinschliff brand voice.

## Verbosity tier — calibrate before filling slots

Three tiers control how much text each slide should carry:

- **Concise** (~20 words): action title only, body suppressed or one short phrase. For exec audiences and live-projected decks. The visual carries the evidence; the presenter carries the narrative.
- **Standard** (~40 words): action title + 1–2 sentences of body. The default. Enough to read without a presenter but not enough to replace them.
- **Text-heavy** (~60 words): action title + 2–3 sentences, or a 3–4-item list with short descriptors. For leave-behind decks, developer audiences, or reference material.

Infer the tier from the design brief's `verbosity` field (set at Step 1). Never exceed the tier's word budget in a body slot — if the content requires more, split it across two slides.

## Speaker notes — always include, minimum 100 characters

Every content slide must carry a `speaker_notes` entry. The notes are:
- **Plain text only** — no markdown, no bullets, no emojis.
- **100–500 characters** — long enough to give a presenter a real talk track, short enough to read at a glance.
- **Additive to the slide** — notes say what the presenter would say aloud. They must not repeat the title verbatim; they must add context, nuance, or the "why this matters now."

A slide with an empty or 3-word speaker note is a red flag: either the claim on the slide isn't strong enough to talk to, or the author didn't finish the thought.

## No filler words in the so_what slot

The `so_what` slot on a data slide is the single highest-impact sentence on the slide — it is the takeaway the audience should remember. Every word must be load-bearing. Strip the following before writing anything else:

> very · really · quite · rather · somewhat · basically · actually · generally · essentially · literally · truly · incredibly · extremely · highly · absolutely

These words add emphasis while removing credibility. "Revenue grew 12% YoY" is a stronger claim than "Revenue very significantly grew by an impressive 12% YoY". The content validator flags ≥2 filler words in a so_what slot as a `filler-word` defect.
