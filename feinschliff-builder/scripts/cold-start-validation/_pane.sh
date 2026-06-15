#!/usr/bin/env bash
# Run one cold-start /deck invocation in this pane.
set -euo pipefail

brief_id="$1"
work_dir="$2"
HERE="$(cd "$(dirname "$0")" && pwd)"
brief="$HERE/brief-$brief_id.yaml"

echo "── brief: $brief_id ──"
echo "── work:  $work_dir ──"
echo

# Read the brief prose for the prompt.
prompt=$(python3 -c "
import yaml,sys
d = yaml.safe_load(open('$brief'))
print(d['prompt'])
")

cd "$work_dir"
cat > brief.yaml <<EOF
$(cat "$brief")
EOF

echo "── prompt ──"
echo "$prompt"
echo
echo "── invoking claude -p (cold) ──"
echo

# Cold-start: no resume, no prior conversation. Disable plugin hooks so
# nothing leaks from the operator's other sessions.
claude --dangerously-skip-permissions -p "$prompt" 2>&1 || echo "claude exit: $?"

echo
echo "── final ls ──"
ls -la

echo
echo "── pane done ──"
