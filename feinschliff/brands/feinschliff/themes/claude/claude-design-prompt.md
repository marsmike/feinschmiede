# Feinschliff · Claude Design prompt

Paste this prompt into Claude Design to generate (or update) the Feinschliff design-system HTML that `/compile` can ingest. It embeds the layout inventory, when-to-use guidance, voice rules, and brand tokens so Claude Design produces a deck that compiles cleanly on the first try.

For the generic renderer-side contract (what `data-*` attributes must be present, what `/compile` does with them) see `feinschliff/references/claude-design-prompt.md`.

---

## The prompt (copy everything below this line)

You are generating a design-system HTML deck for **Feinschliff** (internal brand). The output is consumed by the Feinschliff `/compile` pipeline, which parses each slide's `data-*` attributes and regenerates a PowerPoint template, a catalog, and tokens from the HTML.

### Canvas + structure

- One `<section class="slide">` per named layout. Don't invent layouts — the 16 below are exhaustive for v1.
- Canvas is 1920×1080 CSS px. Full-bleed, no device chrome.
- Put design tokens (colour, typography, spacing) in `<style>` as CSS custom properties. Do not change brand values — they're fixed below.
- End the deck with the "Feinschliff · End" closer. Include a "Components Showcase" slide documenting the UI kit (buttons, chips, rules, KPI cells).

### Required `data-*` attributes (every `<section class="slide">`)

| Attribute | Required | Purpose |
|---|---|---|
| `data-label` | yes | Short human name. Matches the `NAME` shown in PowerPoint's Insert → New Slide menu (e.g. `Feinschliff · Title · Accent`). |
| `data-role` | yes | One of: `title-primary`, `title-with-visual`, `chapter-opener`, `agenda`, `data-quantity`, `data-comparison`, `content-columns`, `content-with-visual`, `quote`, `reference`, `closer`. |
| `data-concepts` | yes | Comma-separated concept tags used for layout retrieval (e.g. `cover, headline, full-slide-statement`). |
| `data-when-to-use` | yes | 1–2 sentences — when this layout is the right pick. |
| `data-when-not-to-use` | yes | 1–2 sentences — when to avoid, with the layout to use instead. **This field is non-negotiable; negative guidance is what prevents `/deck` from choosing the wrong layout.** |
| `data-slots` | yes | JSON string — JSON-Schema-ish slot definitions. See the example at the end of this prompt. |

### The 16 Feinschliff layouts

Use these exact `data-label` values, roles, concepts, and when/when-not guidance. Each layout solves one problem — don't fold two roles into one slide.

1. **`Feinschliff · Title · Accent`** · role=`title-primary` · concepts=`cover, headline, full-slide-statement`
   · **use** for deck cover, chapter opener, single-statement slides where the headline IS the content (under 8 words).
   · **don't use** when there's supporting detail, numbers, or imagery — prefer `Title + Picture`, `Chapter · Orange`, or a data layout.

2. **`Feinschliff · Title · Ink`** · role=`title-primary` · concepts=`cover, headline, dark-mode`
   · **use** for the same role as Title · Orange but on dark ink background — serious / formal contexts (earnings, safety, compliance).
   · **don't use** for light-hearted topics or anything with substantial detail.

3. **`Feinschliff · Title + Picture`** · role=`title-with-visual` · concepts=`cover, product-intro, headline-plus-context`
   · **use** for product-led openers, section intros where a single hero image reinforces the title. The right-half image frame is a fixed shape — the user replaces it via Format Shape → Fill → Picture.
   · **don't use** for data-heavy slides or when multiple visuals/columns are needed — prefer `KPI Grid`, `Text + Picture`, or a column layout.

4. **`Feinschliff · Agenda`** · role=`agenda` · concepts=`agenda, table-of-contents, section-list`
   · **use** for deck agenda with 3–6 items. Each item has a short title + one-line description.
   · **don't use** with fewer than 3 items (use Title · Orange) or more than 6 (use 3-Column or 4-Column).

5. **`Feinschliff · Chapter · Accent`** · role=`chapter-opener` · concepts=`chapter-opener, section-break`
   · **use** between major sections. Shows chapter number + title. Bold divider slide.
   · **don't use** when the deck has only one section — skip the chapter opener entirely.

6. **`Feinschliff · Chapter · Ink + Picture`** · role=`chapter-opener` · concepts=`chapter-opener, dark-mode, hero-image`
   · **use** for chapter openers in serious / formal sections; includes a right-half editorial image frame (Format Shape → Fill → Picture).
   · **don't use** for light / celebratory sections — use Chapter · Orange instead.

7. **`Feinschliff · KPI Grid`** · role=`data-quantity` · concepts=`quantity, metrics, summary-figures`
   · **use** for 2–4 high-level quantitative figures with unit + label + delta. Most scannable format for executive updates.
   · **don't use** for more than 4 figures (use a table or bar chart) or figures without clear units / time comparisons.

8. **`Feinschliff · 2-Column Cards`** · role=`content-columns` · concepts=`comparison, pair, before-after, pros-cons, product-a-vs-b`
   · **use** for two parallel concepts of equal weight — comparison, pair of principles, two-track plan.
   · **don't use** for 3+ items (use 3-Column / 4-Column) or content-heavy analysis (use Text + Picture).

9. **`Feinschliff · 3-Column`** · role=`content-columns` · concepts=`composition, triad, pillars, phases`
   · **use** for three parallel items — pillars of a strategy, three brands/products, three phases.
   · **don't use** for 2 items (use 2-Column Cards) or 4+ (use 4-Column Cards).

10. **`Feinschliff · 4-Column Cards`** · role=`content-columns` · concepts=`composition, quarters, phased-plan, roadmap`
    · **use** for four sequential or parallel items — classic Q1–Q4 plan, 4-phase roadmap.
    · **don't use** for fewer or more than 4 items, or a plan with items of unequal weight.

11. **`Feinschliff · Text + Picture`** · role=`content-with-visual` · concepts=`product-detail, hero-plus-description, story-beat`
    · **use** for one substantive idea explained with a supporting visual. Includes buttons for CTA. Image frame is a fixed shape (Format Shape → Fill → Picture).
    · **don't use** for pure text (use 2-Column Cards) or pure image (use Full-bleed Cover).

12. **`Feinschliff · Full-bleed Cover`** · role=`title-with-visual` · concepts=`cover, hero-image, statement-plus-image`
    · **use** for a strong image + short statement. Chapter opener or deck cover with high visual impact. Full-bleed image area is a fixed shape (Format Shape → Fill → Picture).
    · **don't use** for content-led slides where text carries the meaning — prefer a title or content layout.

13. **`Feinschliff · Bar Chart`** · role=`data-comparison` · concepts=`comparison, ranking, distribution`
    · **use** for 2–6 items with quantitative values to compare (e.g. revenue by region, survey responses).
    · **don't use** for continuous time-series (line chart — not yet in the Baukasten) or more than 6 items (use a table).

14. **`Feinschliff · Components Showcase`** · role=`reference` · concepts=`ui-kit, reference, design-system-demo`
    · **use** as an internal design-system reference slide — buttons, chips, rules.
    · **don't use** for regular deck content — this slide is brand-authoring reference, not for end-user decks.

15. **`Feinschliff · Quote`** · role=`quote` · concepts=`quote, statement, voice-guideline`
    · **use** for a strong voice moment — customer testimonial, leadership principle, brand tenet.
    · **don't use** for body text pretending to be a quote. It must be an actual quotation. Avoid on operational / status updates (feels performative).

16. **`Feinschliff · End`** · role=`closer` · concepts=`closer, thank-you, end`
    · **use** as the final slide of every deck.
    · **don't use** — never skip. Every deck ends with this or a similar closer.

### Brand tokens (don't deviate)

Colours (CSS custom properties in `<style>`):

```css
--orange:        #FF6840;   /* primary signature accent — scarce */
--orange-hover:  #EC6847;
--amber:         #FBAE40;   /* warning / decision */
--black:         #000000;
--ink:           #262626;   /* dark surface */
--graphite:      #666666;   /* body text */
--steel:         #969696;
--silver:        #BCBCBC;
--fog:           #E0E0E0;   /* hairlines + placeholder stripes */
--paper:         #F4F4F4;   /* card fills */
--white:         #FFFFFF;
```

Typography:

- Display / body: **Noto Sans**, weights 300 / 400 / 500 / 700.
- Mono: **Noto Sans Mono**, used for eyebrows, column numbers, KPI keys, footer. Always uppercase with 0.12em letter-spacing for eyebrows.
- Sizes (CSS px, authored on the 1920×1080 canvas): display 160 · huge 120 · quote 84 · sub 44 · slide-title 37 · body 26 · col-body 22 · eyebrow/pgmeta 18 · col-num 14 · kpi-value 120 · kpi-unit 40 · kpi-key 16 · bar-label 28 · footer 16.
- Slide padding: 100 px left/right, 100 px top, 80 px bottom.

### Voice & content rules (apply to every text slot)

Voice: *"Write like an engineer explaining their work to a colleague they respect. Short sentences. Concrete nouns. No superlatives."*

- **Title:** under 8 words, no period unless statement.
- **Eyebrow:** 2–4 words, mono uppercase. A tag, not a sentence.
- **Body:** one complete thought per paragraph, max 2 paragraphs.
- **Column title:** noun phrase or short statement; max 10 words.
- **Column body:** 1–3 sentences. No sub-bullets.
- **KPI:** value and unit stay separate (`value="62"`, `unit="k"`, never `"62k"`). No thousands-separators for single digits; use separators for >3-digit figures. Deltas always include direction and period (`+3% YoY`).
- **Bar labels:** uppercase country/region/product code, max 10 chars.
- **One idea per slide.** If you find yourself writing "and also…", split the slide.

Hard visual rules:

- **Orange is scarce.** One hero element per slide, maximum.
- **Text on orange is black.**
- **Canvas is white** unless the layout explicitly needs a dark ink background (Title · Ink, Chapter · Ink).
- **Empty image frames are intentional** — the striped grey placeholder reads as "image goes here", not as a missing asset.
- **Sharp corners** everywhere. Feinschliff is a hard-edge system; no border-radius except where already specified in existing slides.

### Example slide

```html
<section class="slide"
  data-label="Feinschliff · KPI Grid"
  data-role="data-quantity"
  data-concepts="quantity, metrics, summary-figures"
  data-when-to-use="2-4 high-level quantitative figures, each with unit + label + delta. Most scannable format for executive updates."
  data-when-not-to-use="More than 4 figures (use a table or bar chart). Figures without clear units or time-comparisons."
  data-slots='{
    "eyebrow": {"type": "string", "maxLength": 60, "optional": true},
    "title":   {"type": "string", "maxLength": 60},
    "kpis": {
      "type": "array",
      "minItems": 2, "maxItems": 4,
      "items": {
        "type": "object",
        "properties": {
          "value": {"type": "string", "description": "Big number, e.g. 62"},
          "unit":  {"type": "string", "description": "Inline unit, e.g. k, bn, %"},
          "key":   {"type": "string", "maxLength": 40},
          "delta": {"type": "string", "maxLength": 20}
        },
        "required": ["value", "key"]
      }
    }
  }'>
  <!-- existing visual HTML for the KPI grid slide -->
</section>
```

### Output expectations

- Emit all 16 layouts above, in the order listed. One `<section class="slide">` per layout.
- Each slide's visual HTML is your job — use the brand tokens. Keep it clean and hard-edged.
- Every slide carries the six `data-*` attributes exactly as specified. Missing attributes will make `/compile` hard-fail.
- No explanation prose outside the HTML — return a single `.html` file.

## Copy ends here.

---

## When to re-run this prompt

- **New brand variant / revision.** Update tokens (colour, typography) in the prompt, keep everything else, re-run. `/compile` will regenerate the catalog + renderer stubs; human edits to renderer `.py` files are preserved via the 3-way merge described in `skills/compile/SKILL.md`.
- **Adding a new layout.** Prefer `/compile --from-html` with a single-layout HTML fragment — it's additive and doesn't risk the existing 16. Only re-run this prompt with a new entry in the inventory if you're willing to regenerate the whole deck.
- **Fine-tuning a `when-to-use` for layout-selection quality.** Update the relevant entry in this prompt, re-run, merge the catalog change through `/compile`.
