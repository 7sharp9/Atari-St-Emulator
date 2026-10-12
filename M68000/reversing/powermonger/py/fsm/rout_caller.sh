#!/usr/bin/env bash
# rout_caller.sh <snap> <tag> <steps>: which $56a6 caller re-engages each re-routed man.
# Counts the $56a6 calls in <steps> (hits), then reruns the same span stopping at every call
# (`bp 56a6` / `bt 1` / `s 1`): A3 is the engaged man, A1 the attacker, (A7) the return address
# ($15338 from $15332, the $2e arrival; $1536e from $15368, melee). Join with routrun.sh's watch of
# the same snapshot and span: rout_caller.py <watch> <out> <calls>.
# Output: ${PM_WORK:-scratchpad/pm157}/rout/caller/<tag>.hits, <tag>.calls.
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${M68000_ROOT:-$HERE}
while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); [ "$ROOT" = / ] && { echo "no repo root"; exit 1; }; done
cd "$ROOT" || exit 1
W=${PM_WORK:-scratchpad/pm157}/rout/caller; mkdir -p "$W"
snap=$1; tag=$2; steps=$3
run() { ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$snap" repl; }
printf 'disk scratchpad/powermonger.st\nhits %s 56a6 15332 15368\nq\n' "$steps" | run > "$W/$tag.hits" 2>&1
n=$(awk '$1=="$0056a6"{print $2}' "$W/$tag.hits")
[ -n "$n" ] || { echo "$tag: no hits line"; cat "$W/$tag.hits"; exit 1; }
{ echo "disk scratchpad/powermonger.st"; for _ in $(seq 1 "$n"); do printf 'bp 56a6 %s\nbt 1\ns 1\n' "$steps"; done; echo q; } | run > "$W/$tag.calls" 2>&1
echo "$tag: $n calls of \$56a6, $(grep -c 'return address' "$W/$tag.calls") stops"
grep -E '^\s+\$00(56a6|15332|15368)' "$W/$tag.hits"
