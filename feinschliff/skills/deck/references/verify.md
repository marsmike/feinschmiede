# Verify — look at the rendered deck, loop until clean

`render()` succeeding only means valid OOXML. It does **not** mean the slides look right. Convert to PDF and read the pages before shipping.

## Convert

```bash
soffice --headless --convert-to pdf --outdir feinschliff/.debug/<topic>-<date> out.pptx
```

Then `Read` the PDF page by page (the tool handles PDFs natively — pass `pages: "1-N"`).

## Defect classes to scan for

| Class | What it looks like | Fix |
|---|---|---|
| **Title overflow** | Title wraps to 3+ lines or runs into next element | Shorten to the layout's title budget in [layouts.md](layouts.md); often means picking a less hero-typography layout |
| **Body overflow / truncation** | Text disappears off the placeholder edge, or column heights mismatch in `Title and N Contents` | Drop to the next verbosity tier (see [storyline.md](storyline.md)) or split across two slides |
| **Stretched picture** | Faces or product shots distorted (wrong aspect) | The OBJECT-placeholder path stretches; switch to a PICTURE-placeholder layout or center-crop the source to the placeholder aspect first |
| **Chart misrender** | Legend collides with bars, category labels rotated/clipped, wrong series color | Reduce categories, shorten category strings, or move to a chart-friendly layout that gives the chart full width |
| **Clone replacement leak** | Master placeholder text shows through ("Milestone", "Lorem ipsum"), or a real value appears twice | The replacements queue was under- or over-filled. Re-run the text-anchor recipe in [clones.md](clones.md) to get the exact count |
| **Layout monotony** | Three+ adjacent content slides use the same layout | Variety rule from [storyline.md](storyline.md) — swap one for an adjacent-shape layout |

## The /loop driver

Wrap the verify step in `/loop` so iteration is automatic:

```
/loop render -> soffice convert -> read PDF -> if defects, fix the plan and re-render; else done
```

The loop's success condition is **zero defects from the table above**. Each iteration:

1. Re-render `build.py` to a new `feinschliff/.debug/<topic>/iter-NN.pptx`.
2. Convert with soffice; read the PDF.
3. If any defect class fires, edit the offending `FillPlan` / `ClonePlan` (shorter title, smaller verbosity, different layout) and bump the iteration.
4. Cap at 5 iterations — if defects survive that many passes, the issue is structural (wrong layout choice, undersized layout for the content) rather than fit-and-trim. Surface to the user before continuing.

Don't chase pixel-perfect — the `master.pptx` owns styling. You're checking content fit, not design.

## When to stop

A deck is ready when:

- Every page renders without a defect class above.
- Titles read as a claim arc (the title-only test from [storyline.md](storyline.md)).
- The takeaway from the brief block is visible on the cover or close slide.
- The user has seen the final PDF and signed off.
