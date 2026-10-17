#!/usr/bin/env bash
# man_click.sh <land> <cx> <cy> <lead hex> <tag> [A3 hex = 516c0]: sword-click a minimap cell of pm143/lands/<land>.snap that holds a
# lone foreign man (man_cells.py), capture $4a7a's entries (hits 1,2) with tools/capture_hits.py, then run each entry to $4a7a's
# return and print 24/204/216(A3).  Output ${PM_WORK:-scratchpad/pmwork}/orders/man/<tag>*.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${M68000_ROOT:-$HERE}
while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); [ "$ROOT" = / ] && { echo "no repo root"; exit 1; }; done
cd "$ROOT"
land=$1; cx=$2; cy=$3; lead=$4; tag=$5; A3=${6:-516c0}
O=${PM_WORK:-scratchpad/pmwork}/orders/man; mkdir -p "$O"
uv run python reversing/powermonger/py/arms/drive_sheep2.py scratchpad/pm143/lands/$land.snap $cx $cy "$O/$tag.cmds" 1 1000000 $A3 $lead
pre=(); [ -n "$POKE" ] && pre+=(--pre "$POKE")
while IFS= read -r line; do
  case "$line" in hits*) break ;; disk*) continue ;; esac
  pre+=(--pre "$line")
  # POKE (optional, a REPL line) is inserted after the HOME block (4 lines): a labelled claim poke 600k steps into the drive
  if [ -n "$POKE" ] && [ ${#pre[@]} -eq 8 ]; then pre+=(--pre "$POKE"); fi
done < "$O/$tag.cmds"
uv run python tools/capture_hits.py scratchpad/pm143/lands/$land.snap 4a7a 1,2 "$O" --name "n_$tag" --max 3000000 "${pre[@]}" || true
