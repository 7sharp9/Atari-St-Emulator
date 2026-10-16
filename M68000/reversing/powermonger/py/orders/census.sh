#!/usr/bin/env bash
# census.sh <steps> <snap>... : natural (no pokes) `hits` census of $4a7a's arms and of $4de2's classes, one run per snapshot,
# one emulator at a time.  Output: ${PM_WORK:-scratchpad/pm162}/g4a7a/census/<stem>.txt (+ uptime at start).
#   $4a7a entry; $4a9a non-empty cell; $4b62 foreign building (class 2); $4b12 foreign man (6); $4b30 animal 8/$14/$16 (8);
#   $4b46 no man/animal; $4b4e category 4 (class $c); $4b96 commit ($37c2 + state 8)
#   $4de2 entry; $4df2 lord (2, also the man-near-home bra $4e60); $4e62 lone man away (6); $4e9e group (4); $4eb6 cat 8 (8);
#   $4eca cat $14/$16 (class $a); $4ed8 cat 4 ($c); $4ee0 other (0)
#   $4bc8 the fight setup; $1519e its call in the mode-$30 arrival; $6c32 the march-and-engage executor; $6522 liveness
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${M68000_ROOT:-$HERE}
while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); [ "$ROOT" = / ] && { echo "no repo root"; exit 1; }; done
cd "$ROOT"
OUT=${PM_WORK:-scratchpad/pm162}/g4a7a/census; mkdir -p "$OUT"
A="4a7a 4a9a 4b62 4b12 4b30 4b46 4b4e 4b96 4de2 4df2 4e62 4e9e 4eb6 4eca 4ed8 4ee0 4bc8 1519e 6c32 6522"
steps=$1; shift
for s in "$@"; do
  stem=$(basename "$s" .snap)
  { echo "uptime: $(uptime)"; printf 'disk scratchpad/powermonger.st\nhits %s %s\nq\n' "$steps" "$A" |
    ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$s" repl 2>&1; } > "$OUT/$stem.txt"
  echo "== $stem"; grep '^  \$' "$OUT/$stem.txt" | awk '{printf "%s=%s ", $1, $2} END {print ""}'
done
