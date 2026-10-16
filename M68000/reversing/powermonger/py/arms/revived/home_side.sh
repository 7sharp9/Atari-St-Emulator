#!/bin/bash
# home_side.sh: why k25's revived commander changes side twice (strategy.md "The pending word").
# His record $5608a has home word 34 = $0b52, so his home settlement is $4f916 + $b52 = $50468; $42ac (revival),
# $16874 ($16848 reconcile) and $1502c all copy that record's byte 5. Watches $5046c..$5046d over the k25a span
# (pm143/lands/k25.snap, 250M steps) and the first 2M steps of k25b (L2G_k25_c1.snap), with hits on the revival
# and the revolt ($550e/$5538) and the man's record at the end.
# Output: ${PM_WORK:-scratchpad/pm157}/k25/own_a.out/.err, own_b.out/.err (WATCH lines in .err).
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=${M68000_ROOT:-$HERE}
while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); [ "$ROOT" = / ] && { echo "no repo root"; exit 1; }; done
cd "$ROOT" || exit 1
D=${PM_WORK:-scratchpad/pm157}/k25; mkdir -p "$D"
go() {   # <tag> <snap> <steps>
  printf 'disk scratchpad/powermonger.st\nm 50468 32\nwatch 5046c 2\nhits %s 4258 42ac 16874 1502c 550e 5538\nm 50468 32\nm 5608a 50\nq\n' "$3" |
    ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$2" repl > "$D/own_$1.out" 2> "$D/own_$1.err"
  echo "== $1"; grep -E '^\s+\$0' "$D/own_$1.out"; grep WATCH "$D/own_$1.err" || echo "  (no write)"
}
go a scratchpad/pm143/lands/k25.snap 250000000
go b scratchpad/pm148/arms/long/L2G_k25_c1.snap 2000000
