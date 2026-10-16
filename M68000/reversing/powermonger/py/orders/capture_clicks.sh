#!/usr/bin/env bash
# capture_clicks.sh [tags...]: the natural $4a7a entries of the player's sword clicks in pm148/arms/sheep (k120_a, k120_tree,
# k25_a, k56_a by default).  Each drive (<tag>.cmds, made by py/arms/run_sheep.sh / drive_sheep2.py) is replayed verbatim up
# to its first `hits` line (its last action is the minimap click), then tools/capture_hits.py stops at hits 1 and 2 of $4a7a.
# Output: ${PM_WORK:-scratchpad/pm162}/g4a7a/nat/n4a7a_<tag>.json (+ _<n>.snap/.ram, .log).
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${M68000_ROOT:-$HERE}
while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); [ "$ROOT" = / ] && { echo "no repo root"; exit 1; }; done
cd "$ROOT"
OUT=${PM_WORK:-scratchpad/pm162}/g4a7a/nat
SHEEP=scratchpad/pm148/arms/sheep
tags=${@:-k120_a k120_tree k25_a k56_a}
for t in $tags; do
  land=${t%%_*}
  pre=()
  while IFS= read -r line; do
    case "$line" in hits*) break ;; disk*) continue ;; esac
    pre+=(--pre "$line")
  done < "$SHEEP/$t.cmds"
  uv run python tools/capture_hits.py scratchpad/pm143/lands/$land.snap 4a7a 1,2 "$OUT" --name "n4a7a_$t" --max 3000000 "${pre[@]}" || true
done
