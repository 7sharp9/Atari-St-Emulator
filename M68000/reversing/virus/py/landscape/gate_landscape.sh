#!/bin/bash
# Gate for the wave table, the wave-end bonus and the landscape switch.  Captures afresh into $W/landscape/gate/ from
# the unpoked chain start main_g050.snap (py/chain/chain.py), so it needs scratchpad/virus/chain/long100/starts/.
# About 5 minutes: natural.sh (about 3.5), poked.sh and poked_inf.sh (under a minute together), the checks (seconds).
# Usage: bash reversing/virus/py/landscape/gate_landscape.sh
cd "$(dirname "$0")/../../../.." || exit 1
W=${VIRUS_WORK:-scratchpad/virus}; P=reversing/virus/py/landscape; G=$W/landscape/gate; PY="uv run python -I"
mkdir -p $G/natural $G/poked
bash $P/natural.sh $G/natural
bash $P/poked.sh $G/natural $G/poked
bash $P/poked_inf.sh $G/poked
N=$G/natural; K=$G/poked
echo "== wave table \$20e34 =="; $PY $P/wavetable.py $N/built_0.snap | tail -1
echo "== natural game 050: selector and counter writes (watch 32a4c 6; each line is one write) =="
grep '^WATCH' $N/out.txt | sed 's/step=[0-9]* //'
echo "== pool vs table at the build of counters 1..5 (natural) =="
for i in 0 1 2 3 4; do $PY $P/pool_check.py $N/built_$i.snap; done
echo "control: wrong n (counter 2's pool checked as n = 3)"; $PY $P/pool_check.py $N/built_1.snap 3
echo "== pool vs table at the poked builds (n = 9, 10, 15, 16) =="
for i in 9 10 15 16; do $PY $P/pool_check.py $K/pbuilt_$i.snap; done
echo "== wave-end bonus, natural (score read from the end and after snapshots) =="
for i in 0 1 2 3 4; do $PY $P/bonus_check.py $N/end_$i.snap $N/after_$i.snap; done
echo "control: infected subtracted once"; for i in 0 1 2 3 4; do $PY $P/bonus_check.py $N/end_$i.snap $N/after_$i.snap inf_once; done
echo "control: no 4-n shift"; for i in 0 1 2 3 4; do $PY $P/bonus_check.py $N/end_$i.snap $N/after_$i.snap no_shift; done
echo "== wave-end bonus on landscape 2, poked (pool emptied; infected 0, then 3000 poked cells) =="
for i in 9 10 15; do $PY $P/bonus_check.py $K/pend_$i.snap $K/pafter_$i.snap; done
$PY $P/bonus_check.py $K/inf_end.snap $K/inf_after.snap
echo "control: infected subtracted once"; $PY $P/bonus_check.py $K/inf_end.snap $K/inf_after.snap inf_once
echo "== height map vs model (virus_terrain.py), natural =="
echo "landscape 0 (counter 2):"; $PY reversing/virus/py/virus_terrain.py $N/built_1.snap | tail -1
echo "landscape 1 (counter 5):"; $PY reversing/virus/py/virus_terrain.py $N/built_4.snap | tail -1
echo "control: level 0 model on level 1 data"; $PY reversing/virus/py/virus_terrain.py $N/built_4.snap --level 0 | tail -1
echo "control: base shifted"; $PY reversing/virus/py/virus_terrain.py $N/built_4.snap --break | tail -1
echo "== height map vs model, landscape 2 (poked, counters 9 and 16) =="
for i in 9 16; do $PY reversing/virus/py/virus_terrain.py $K/pbuilt_$i.snap | tail -1; done
echo "control: level 1 variant on level 2 data"; $PY reversing/virus/py/virus_terrain.py $K/pbuilt_9.snap --level 1 | tail -1
echo "== counter 16 keeps landscape 2: \$32a4e, \$32a4c, \$32a50 =="
$PY -I - $K/pbuilt_16.snap <<'PYEOF'
import struct, sys
sys.path.insert(0, 'reversing/virus/py'); import vcommon
r = vcommon.load_ram(sys.argv[1]); w = lambda a: struct.unpack('>H', r[a:a + 2])[0]
print(f'selector {w(0x32a4e)} built {w(0x32a4c)} counter {w(0x32a50)}')
PYEOF
