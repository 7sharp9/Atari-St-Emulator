#!/usr/bin/env bash
# The trade $63f4 at posture 5 against posture 3, live (not callcap). State: pm142/rand1 with gate_trade.py's order
# injection (labelled pokes: $58048 := 0400053c, $58028 := 031c2146, $5802c := 02000400: side 3 group 0 is posted a
# $1c trade at cell $2146), run to the arrival call $63f4 (side 3 group 0, A3 = $51938, lord 12 at $4e694).
# Arms, each from that one state: p5 / p3 = posture word $51974 := 5 / 3 (old 2; the longword keeps $51976 = 2);
# p5x / p3x = the same plus lord 15 byte 0 $4e6f4 := 3 and lord 14 byte 25 $4e6ed := 5 (both old 0), so the
# posture-5 buy row (the code bytes at $6522: goods $48, $41, 0, 5) finds stock past lord 12's goods.
# Each arm watches all RAM [0,$80000) from $63f4 to its rts $6500 and dumps $650a..$6541, lords 12..15, the group's
# carried goods 84(A3)+12i, its food 36(A3) and the lord's food/loyalty.
# Output: ${PM_WORK:-scratchpad/pm162}/posture/trade/{at63f4.snap,<arm>.out,<arm>.watch}
set -e
HERE=$(cd "$(dirname "$0")" && pwd); d=$HERE
while [ ! -f "$d/tools/rdis.py" ]; do d=$(dirname "$d"); done
cd "$d"
OUT=${PM_WORK:-scratchpad/pm162}/posture/trade; mkdir -p "$OUT"
run() { ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$1" repl; }
if [ ! -f "$OUT/at63f4.snap" ]; then
  printf '%s\n' 'disk scratchpad/powermonger.st' 'w 58048 0400053c' 'w 58028 031c2146' 'w 5802c 02000400' \
    'bp 63f4 60000000' "snap $OUT/at63f4.snap" q | run scratchpad/pm142/rand1.snap > "$OUT/mk.out" 2>&1
fi
dump() { printf '%s\n' 'm 650a 56' 'm 4e694 128' 'm 51974 4' 'm 5195c 2' 'm 5198c 96' 'm 4e69a 2' 'm 4e6a2 2'; }
for arm in p5 p3 p5x p3x; do
  case $arm in p5|p5x) P='w 51974 00050002';; *) P='w 51974 00030002';; esac
  X=(); case $arm in *x) X=('w 4e6f4 03000000' 'w 4e6ec 00050000');; esac
  { echo 'disk scratchpad/powermonger.st'; echo 'm 51974 4'; echo 'm 4e6ec 12'; echo "$P"; for x in "${X[@]}"; do echo "$x"; done
    dump; echo 'watch 0 524288'; echo 'bp 6500 400000'; echo 'unwatch'; dump; echo q; } \
    | run "$OUT/at63f4.snap" > "$OUT/$arm.out" 2> "$OUT/$arm.watch"
done
