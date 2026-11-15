#!/bin/bash
# The computer god (side 2) on later conquest battles. For each battle N: resume p2_title, poke the battle number
# $473a0 = N before the CONQUEST GAME click (the setup $22bb8 -> $22e8c reads battle N's record from CONQUEST.PAK
# right after that click), drive to the first play frame with drive.txt's clicks, snapshot <out>/b<N>_start.snap,
# then `hits` over STEPS steps (default 30,000,000) on the god's stages. Battle 0 is the unpoked control
# (byte-identical drive to anchors/p2_game_start).
# Prints per battle: side 2's plan entries (w148 - 1) and the counts of the tick $29226, computer branch $25670,
# cascade $25690, the post sites ($25756 mailbox raise, $25878 level, $25a18 release, $25b5e power, $25d08 command 8,
# $25dac mode byte), the plan stage $25a32 and executed commands $292e4.
# Run from M68000/:  bash reversing/populous2/py/god/battle_census.sh [outdir] [steps] [battle ...]
set -e
d=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$d/tools/rdis.py" ] && [ "$d" != / ]; do d=$(dirname "$d"); done; cd "$d"
OUT=${1:-scratchpad/populous2/battle}
STEPS=${2:-30000000}
shift 2 2>/dev/null || shift $#
BATTLES=${*:-0 10 40 100}
mkdir -p "$OUT"
sed -n '/^mouse move 100 60/,/^snap p2_game_start.snap/p' reversing/populous2/drive.txt \
  | grep -v '^snap ' > "$OUT/to_start.txt"
ADDRS="29226 25670 25690 25756 25878 25a18 25b5e 25d08 25dac 25a32 292e4"
for n in $BATTLES; do
  { printf 'ww 473a0 %04x\n' "$n"; cat "$OUT/to_start.txt"; echo "snap $OUT/b${n}_start.snap"
    echo "hits $STEPS $ADDRS"; echo q; } \
    | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/populous2/anchors/p2_title.snap repl \
      > "$OUT/b$n.log" 2>&1 &
done
wait
for n in $BATTLES; do
  plan=$(uv run python -c "
import sys; sys.path.insert(0,'tools')
from gfxview import load_ram
r,_=load_ram('$OUT/b${n}_start.snap'); S=0x46fc4+2*0x13a
print(((r[S+148]<<8)|r[S+149])-1, (r[0x473a0]<<8)|r[0x473a1])")
  awk -v n="$n" -v plan="$plan" '/^  \$0/ { c[$1] = $2 }
    END { split(plan, p, " ");
          printf "battle %s (read %s): side2 plan entries %s; ticks %d branch %d cascade %d posts mailbox %d level %d release %d power %d cmd8 %d mode %d; plan stage %d; commands %d\n",
          n, p[2], p[1], c["$029226"], c["$025670"], c["$025690"], c["$025756"], c["$025878"], c["$025a18"],
          c["$025b5e"], c["$025d08"], c["$025dac"], c["$025a32"], c["$0292e4"] }' "$OUT/b$n.log"
done
