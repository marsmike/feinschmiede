#!/usr/bin/env bash
# Cold-start /deck validation harness.
#
# Launches N tmux panes, each running a fresh `claude` session with a
# different brief. Each session is captured to a log file; after they
# complete, the harness inspects the working directory for the expected
# artifacts and prints a pass/fail summary.
#
# Usage:
#   ./run.sh [BRIEF_ID ...]   # default: run all briefs
#
# Briefs are YAML files in this directory named `brief-<id>.yaml`.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SESSION="cold-deck-$(date +%s)"
LOG_ROOT="$HERE/logs/$SESSION"
mkdir -p "$LOG_ROOT"

# Discover briefs.
mapfile -t briefs < <(cd "$HERE" && ls brief-*.yaml 2>/dev/null | sed 's/^brief-//; s/\.yaml$//')

if [[ ${#briefs[@]} -eq 0 ]]; then
  echo "no briefs found at $HERE/brief-*.yaml" >&2
  exit 1
fi

# Filter to requested ones.
if [[ $# -gt 0 ]]; then
  wanted=("$@")
  filtered=()
  for b in "${briefs[@]}"; do
    for w in "${wanted[@]}"; do
      [[ "$b" == "$w" ]] && filtered+=("$b")
    done
  done
  briefs=("${filtered[@]}")
fi

echo "session: $SESSION"
echo "briefs:  ${briefs[*]}"
echo "logs:    $LOG_ROOT"
echo

# Create the tmux session with the first brief.
first="${briefs[0]}"
work="$LOG_ROOT/$first"
mkdir -p "$work"
tmux new-session -d -s "$SESSION" -c "$work" \
  "bash $HERE/_pane.sh '$first' '$work' 2>&1 | tee '$LOG_ROOT/$first.log'"

# Add a pane per remaining brief.
for b in "${briefs[@]:1}"; do
  work="$LOG_ROOT/$b"
  mkdir -p "$work"
  tmux split-window -t "$SESSION" -c "$work" \
    "bash $HERE/_pane.sh '$b' '$work' 2>&1 | tee '$LOG_ROOT/$b.log'"
  tmux select-layout -t "$SESSION" tiled
done

echo "session up — attach with: tmux attach -t $SESSION"
echo "tail any log with: tail -F $LOG_ROOT/<brief>.log"
echo
echo "waiting for all panes to finish…"

# Poll until no panes left.
while tmux list-panes -t "$SESSION" 2>/dev/null | grep -q .; do
  sleep 5
done

echo "all panes done. validating artifacts…"
bash "$HERE/_validate.sh" "$LOG_ROOT"
