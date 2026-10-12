#!/usr/bin/env bash
# rout_caller.sh <snap> <tag> <steps>: who routs a man and who re-engages him.
# Counts the $56a6 and $5590 calls in <steps> (hits), then reruns the same span once per routine stopping at
# every call (`bp` / `bt 1` / `s 1`): A3 is the engaged or struck man, A1 the attacker, (A7) the return address.
# $56a6: $15338 from $15332 (the $2e arrival), $1536e from $15368 (melee). $5590: $153a2 from $1539c (melee blow;
# $153a2 then sets the striker to $2c), $5b5e from $5b58 (arrow hit, $596a), $5a5e from $5a5a.
# Join with routrun.sh's watch of the same snapshot and span: rout_caller.py <watch> <out> <tag.calls> [<tag.rout>].
# Output: ${PM_WORK:-scratchpad/pm157}/rout/caller/<tag>.hits, <tag>.calls ($56a6), <tag>.rout ($5590),
# <tag>.after (the record array 200 steps after each $561c stamp: rout_after.py).
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${M68000_ROOT:-$HERE}
while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); [ "$ROOT" = / ] && { echo "no repo root"; exit 1; }; done
cd "$ROOT" || exit 1
W=${PM_WORK:-scratchpad/pm157}/rout/caller; mkdir -p "$W"
snap=$1; tag=$2; steps=$3
run() { ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$snap" repl; }
printf 'disk scratchpad/powermonger.st\nhits %s 56a6 15332 15368 5590 1539c 5b58 5a5a 561c\nq\n' "$steps" | run > "$W/$tag.hits" 2>&1
stops() {   # <addr> <outfile>
  n=$(awk -v a="\$00$1" '$1==a{print $2}' "$W/$tag.hits")
  [ -n "$n" ] || { echo "$tag: no hits line for $1"; cat "$W/$tag.hits"; exit 1; }
  { echo "disk scratchpad/powermonger.st"; for _ in $(seq 1 "$n"); do printf 'bp %s %s\nbt 1\ns 1\n' "$1" "$steps"; done; echo q; } | run > "$2" 2>&1
  echo "$tag: $n calls of \$$1, $(grep -c 'return address' "$2") stops"
}
stops 56a6 "$W/$tag.calls"
stops 5590 "$W/$tag.rout"
# the record array 200 steps after every rout stamp (the striker's $153a2 break-off is done by then)
n=$(awk '$1=="$00561c"{print $2}' "$W/$tag.hits")
{ echo "disk scratchpad/powermonger.st"; for _ in $(seq 1 "$n"); do printf 'bp 561c %s\ns 200\nm 51b66 25600\n' "$steps"; done; echo q; } | run > "$W/$tag.after" 2>&1
echo "$tag: $n rout stamps, $(grep -c 'hit (' "$W/$tag.after") dumps"
grep -E '^\s+\$0' "$W/$tag.hits"
