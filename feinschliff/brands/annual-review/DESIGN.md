---
version: alpha
name: Annual Review
description: 'Port of Microsoft''s free "Annual Review" presentation template — warm-yellow + pale-blue pastel section panels, black ink, heavy Arial Nova display. Source: powerpoint.cloud.microsoft.'
colors:
  accent: "#4495a2"
  accent-hover: "#37757f"
  highlight: "#a9d4db"
  panel-blue: "#a9d4db"
  panel-yellow: "#fbe284"
  ink: "#000000"
  black: "#000000"
  graphite: "#2b2b2b"
  steel: "#5e5e5e"
  silver: "#9a9a9a"
  fog: "#e4e4e4"
  paper: "#ffffff"
  paper-2: "#f4f4f4"
typography:
  display: Arial Nova
  body: Arial Nova
source_name: Microsoft PowerPoint Gallery
source_url: https://create.microsoft.com/en-us/templates
---
## Overview

Annual Review is a faithful brand-pack port of Microsoft's free **"Annual
Review"** presentation template from the PowerPoint cloud template gallery
(<https://powerpoint.cloud.microsoft/create/en/presentation-templates/>). It
is a bright, friendly corporate-review aesthetic: high black-on-pastel
contrast, generous whitespace, and a heavy geometric display face.

The deck's rhythm comes from **two signature pastel panels** that alternate as
full-bleed section backgrounds, broken up by clean white content slides and
the occasional full-bleed photo divider.

## Colors

- **panel-yellow `#fbe284`** (theme accent2) — warm-yellow section panel:
  cover, growth-table, timeline.
- **panel-blue `#a9d4db`** (theme accent1) — pale-blue section panel: agenda,
  growth-chart, quote, summary.
- **ink / black `#000000`** — every title, body run, thick title rule, and
  bullet is pure black. This template has essentially one text color, on both
  white and pastel backgrounds, which gives it its bold, high-contrast read.
- **paper `#ffffff`** — white canvas for content slides (introduction, team,
  goals, thank-you).
- **accent `#4495a2`** (theme accent3) — teal is the only saturated colour,
  reserved for chart series and small emphasis; it never carries text.
- **chart ramp** — pale-blue → teal → black, extended with yellow, mauve
  (`#aa5881`), and terracotta (`#e06742`) for additional categorical series.

Everything not listed here (the navy ramp, font sizes, slide dimensions, chart
chrome, typographic tracking) is inherited unchanged from **feinschliff**.

## Typography

**Arial Nova** throughout — a heavy, friendly geometric sans — for both display
and body, mirroring the source theme's `majorFont`/`minorFont`. Arial is the
documented fallback (and is one of the fonts the source deck itself embeds), so
renders degrade gracefully on systems without Arial Nova.

## Layout pool

Thirteen bespoke layouts decompiled 1:1 from the source deck:

| Layout | Source slide | Surface |
| --- | --- | --- |
| `cover` | 1 | yellow panel |
| `agenda` | 2 | blue panel |
| `introduction` | 3 | white + photo (right) |
| `last-year` | 4 | full-bleed photo divider |
| `growth-chart` | 5 | blue panel + bar chart |
| `growth-table` | 6 | yellow panel + table |
| `quote` | 7 | blue panel |
| `team` | 8 | white + 4 photos |
| `timeline` | 9 | yellow panel, 4 quarters |
| `goals-q1` | 10 | white, 2 columns |
| `goals-q2` | 11 | white, 3 columns |
| `summary` | 12 | blue panel, 2 columns |
| `thank-you` | 13 | white + photo (left) |

## Attribution

The source template is © Microsoft, distributed for free reuse through the
PowerPoint cloud template gallery. This pack carries a derived `master.pptx`
that the master-template renderer fills at runtime; the original source
template is not redistributed with the pack.
