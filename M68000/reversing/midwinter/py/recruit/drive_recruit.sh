#!/bin/bash
# Driven recruitment (ai.md section 8) and its control. usage: drive_recruit.sh   (about 1 minute)
# Labelled poke on d_stark.snap: Stark's position, site +52 and building +63/+64 set to Karl Rudzinski's (character 3,
# building 0 of a free site). Then all natural: the bio's next-member arrow $3024 (which rebuilds the presence list
# through $c9e/$12be/$12f2), the face to Decisions (offers the recruit icon $489c), the icon, Rudzinski's portrait.
# Control: the same clicks on the RESISTANCE snapshot with only Rudzinski's answer to Stark ($29db9 = [3*32+14])
# poked from $46 to $f8 (a refusal). Snapshots go to scratchpad/midwinter/recruit/.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$HERE; while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); done
cd "$ROOT"
W=scratchpad/midwinter; O=$W/recruit; mkdir -p $O
SAB=reversing/midwinter/py/sabotage
r() { uv run python $SAB/repl.py "$1" "$HERE/$2" > "$O/${2%.txt}.log"; grep -q 'state saved' "$O/${2%.txt}.log" || { echo "REPL $2 failed"; tail "$O/${2%.txt}.log"; exit 1; }; }
uv run python $SAB/poke_snap.py $W/d_stark.snap $O/r3_stark.snap 2b5c2:4:28a00 2b5c6:4:3cf00 2b5d4:4:2a842 2b5df:1:3 2b5e0:1:0 > /dev/null
r $O/r3_stark.snap dnext.txt
r $O/r3_dec.snap drecruit.txt
r $O/r3_screen.snap dask.txt
uv run python $SAB/poke_snap.py $O/r3_screen.snap $O/r3c_screen.snap 29db9:1:f8 > /dev/null
r $O/r3c_screen.snap dask_c.txt
grep -h '\$0' $O/dnext.log $O/drecruit.log $O/dask.log $O/dask_c.log
uv run python - <<'PY'
import sys; sys.path.insert(0, 'tools')
from disassemble import ram_from_snap
for f in ('r3_dec', 'r3_asked', 'r3c_asked'):
    g = ram_from_snap(f'scratchpad/midwinter/recruit/{f}.snap')
    acts = [int.from_bytes(g[0x24238 + 4 * i:0x24238 + 4 * i + 4], 'big') & 0xffffff for i in range(3)]
    print(f, 'present', g[0x22da6:0x22da8].hex(), 'offers', [hex(a) for a in acts], 'team', g[0x2b16c:0x2b16f].hex(),
          bytes(g[0x2db3a:0x2db3a + 70]).split(b'\0')[0].decode())
PY
