#!/usr/bin/env bash
# Walk each cold-start pane's working dir, check for the expected
# artifact set, and tally pass/fail. Artifacts the deck skill MUST
# produce per references/pipeline.md:
#
#   deck_brief.yaml · commitment.yaml · content_plan.json
#   ghost_deck_report.md · title_lint_report.md · plans.yaml
#   verify_report.md · the rendered deck.pptx

set -euo pipefail

log_root="$1"

REQUIRED=(deck_brief.yaml plans.yaml verify_report.md)
NICE_TO_HAVE=(commitment.yaml content_plan.json ghost_deck_report.md title_lint_report.md)

pass=0
fail=0
for d in "$log_root"/*/; do
  brief=$(basename "$d")
  missing=()
  for f in "${REQUIRED[@]}"; do
    [[ -e "$d$f" ]] || missing+=("$f")
  done
  # also: at least one .pptx
  if ! compgen -G "$d*.pptx" > /dev/null; then
    missing+=("*.pptx")
  fi

  if [[ ${#missing[@]} -eq 0 ]]; then
    pass=$((pass+1))
    echo "  PASS  $brief"
  else
    fail=$((fail+1))
    echo "  FAIL  $brief  (missing: ${missing[*]})"
  fi

  nice_present=()
  for f in "${NICE_TO_HAVE[@]}"; do
    [[ -e "$d$f" ]] && nice_present+=("$f")
  done
  [[ ${#nice_present[@]} -gt 0 ]] && echo "        nice-to-have: ${nice_present[*]}"
done

echo
echo "summary: $pass passed, $fail failed"
[[ $fail -eq 0 ]] || exit 1
