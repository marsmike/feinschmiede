# Cold-start /deck validation

Launches N tmux panes, each running a fresh `claude -p` session with a
different brief. Validates that the deck skill drives the full
`interview → plan → pick → render → verify` workflow from cold (no
prior conversation context).

## Files

- `run.sh` — orchestrator. Creates a tmux session, one pane per brief.
- `_pane.sh` — single-pane driver. Reads a brief, runs `claude -p`.
- `_validate.sh` — post-run audit. Walks each pane's work dir and
  checks for the required artifact set.
- `brief-<id>.yaml` — one per scenario. Each carries the prompt + the
  brief fields the skill is expected to honor.

## Run

```bash
./run.sh                          # all briefs
./run.sh quarterly-update         # just one
tmux attach -t cold-deck-<ts>     # watch a running session
```

Each pane writes its work dir to `logs/cold-deck-<ts>/<brief>/`. After
the panes finish, the validator prints PASS / FAIL per brief.

## Required artifacts per brief

The deck skill (`feinschliff/skills/deck/SKILL.md`) declares MANDATORY
artifacts in `references/pipeline.md`. The validator checks for:

- `deck_brief.yaml` — interview output
- `plans.yaml` — FillPlan / ClonePlan list
- `verify_report.md` — verification verdict
- at least one `*.pptx` — the rendered deck

Nice-to-have artifacts surfaced when present: `commitment.yaml`,
`content_plan.json`, `ghost_deck_report.md`, `title_lint_report.md`.

## Adding a brief

Drop a new YAML next to the existing ones:

```yaml
prompt: |
  /deck "<your brief, in the same shape /deck accepts>"

audience: ...
intent: ...
topic: ...
slide_count: ...
tone: ...
image_style: ...
brand: ...
```

The harness picks it up automatically on the next `run.sh` invocation.

## Env

`claude` needs your usual `ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL`
(or `ANTHROPIC_API_KEY`) exported in the shell that runs `run.sh`. The
tmux panes inherit the parent shell's env, so no extra config is
needed beyond your normal setup.
