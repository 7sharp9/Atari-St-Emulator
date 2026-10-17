#!/bin/bash
# load_diff_slot.sh: does a LOAD restore the goods-pile pool and the sound toggle $58054 from the slot? Both lie in the LOAD region
# $3f768..$58368. Three disks built by mk_savedisk.py from pm150/saveload/out/file.ram (rand1 after its first pile: pool slot 0 is a pile with
# food $03d7, $58054 = 1):  ctl = slot A unchanged;  t54 = slot A with the word $58054 := 4 (labelled poke, one word);  tpile = slot A with the
# pile's food word $4bb58 := $1234 (labelled poke, one word). Each is loaded into file.snap by season_load.sh's clicks (slot row A, LOAD) under
# `watch` of the poked word, stopped at the load's exit $1bdf8, then the live words and the 672-byte pool are dumped and compared with the slot's source.
# Output: $PM_WORK/piles/load (default scratchpad/pmwork).
ROOT=$(cd "$(dirname "$0")" && while [ ! -f tools/rdis.py ] && [ "$PWD" != / ]; do cd ..; done; pwd)
cd "$ROOT" || exit 1
W=${PM_WORK:-scratchpad/pmwork}/piles/load; mkdir -p "$W"
SRC=scratchpad/pm150/saveload/out
python3 - "$SRC/file.ram" "$W" <<'E'
import sys
d = bytearray(open(sys.argv[1], 'rb').read()); W = sys.argv[2]
print('source $58052..55', d[0x58052:0x58056].hex(), ' pile slot 0 food $4bb58', d[0x4bb58:0x4bb5a].hex())
open(W + '/ctl.ram', 'wb').write(d)
t = bytearray(d); t[0x58054:0x58056] = (4).to_bytes(2, 'big'); open(W + '/t54.ram', 'wb').write(t)
p = bytearray(d); p[0x4bb58:0x4bb5a] = (0x1234).to_bytes(2, 'big'); open(W + '/tpile.ram', 'wb').write(p)
E
for T in ctl t54 tpile; do python3 reversing/powermonger/py/saveload/mk_savedisk.py "$SRC/file.ram" "$W/$T.st" A="$W/$T.ram" > /dev/null; done
cmp -l "$W/ctl.st" "$W/t54.st"; cmp -l "$W/ctl.st" "$W/tpile.st"
home() { echo "mouse move -400 -400"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"; }
for T in ctl t54 tpile; do
  case $T in ctl) WA="58054 2";; t54) WA="58054 2";; tpile) WA="4bb58 2";; esac
  { echo "disk $W/$T.st"; echo "m 58052 4"; echo "m 4bb4e 672"
    home; echo "mouse move 147 87"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
    echo "mouse down l"; echo "mouse move 0 0"; echo "s 600000"; echo "mouse up l"; echo "mouse move 0 0"; echo "s 300000"
    home; echo "mouse move 170 81"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
    echo "watch $WA"
    echo "mouse down l"; echo "mouse move 0 0"; echo "bp 1bdf8 5000000"; echo "m 58052 4"; echo "m 4bb4e 672"; echo "snap $W/${T}_L0.snap"
    echo "mouse up l"; echo q
  } > "$W/$T.cmds"
  ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SRC/file.snap" repl < "$W/$T.cmds" > "$W/$T.txt" 2> "$W/$T.err"
  echo "== $T"; grep -E 'WATCH|DMA|breakpoint' "$W/$T.err" "$W/$T.txt" | head -8
  python3 reversing/powermonger/py/snap2ram.py "$W/${T}_L0.snap"
  python3 - "$W/$T.ram" "$W/${T}_L0.ram" <<'E'
import sys
s = open(sys.argv[1], 'rb').read(); l = open(sys.argv[2], 'rb').read()
print('  slot  $58054 =', s[0x58054:0x58056].hex(), ' pile food =', s[0x4bb58:0x4bb5a].hex())
print('  live  $58054 =', l[0x58054:0x58056].hex(), ' pile food =', l[0x4bb58:0x4bb5a].hex())
print('  pool 672 B equal to slot:', l[0x4bb4e:0x4bb4e+672] == s[0x4bb4e:0x4bb4e+672], '; $58052..55 equal:', l[0x58052:0x58056] == s[0x58052:0x58056])
d = [i for i in range(0x3f768, 0x58368) if s[i] != l[i]]
print('  bytes of the 101,376-byte block differing from the slot:', len(d), [hex(x) for x in d[:12]])
E
done
