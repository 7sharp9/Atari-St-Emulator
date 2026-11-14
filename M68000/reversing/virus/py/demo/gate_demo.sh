#!/bin/bash
# The Virus demo gates (reversing/virus/demo.md), run from fresh captures: bash reversing/virus/py/demo/capture.sh first.
# Each result line is followed by its labelled control.  About 8 minutes (it runs the emulator one process at a time).
cd "$(dirname "$0")/../../../.." || exit 1
W=${VIRUS_WORK:-scratchpad/virus}; O=$W/demo; M=reversing/virus/py/demo; mkdir -p $O/gate
R() { ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$1" repl 2>&1; }
echo "== timer: writers of \$62a5f from the press page, no key (12M steps)"
{ echo "watch 62a5f 1"; echo "s 12000000"; echo q; } | R $W/drive/g_press.snap | grep WATCH | sed 's/step=[0-9]* //' | uniq -c
echo "-- control: SPACE held on the press page (a human game): the writer must be the key branch, value 0"
{ echo "watch 62a5f 1"; echo "kbd 39"; echo "s 400000"; echo "kbd b9"; echo "s 2000000"; echo q; } | R $W/drive/g_press.snap | grep WATCH | sed 's/step=[0-9]* //' | uniq -c
echo "== bisect2: minimal set making the two scatter stops agree (B from c1 vs A from fl)"
uv run python $M/bisect2.py $O/c1/Q.snap $O/fl/Q1.snap | tee $O/gate/bisect2.txt | grep -E "bad as is|all ranges|minimal|06fffe"
echo "== measure: flight 1 and the seed-poked later flights (control: they must differ from flight 1, equal each other)"
uv run python $M/measure.py $O/S1b.snap $O/fl/Sp2.snap $O/fl/Sp3.snap $O/fl/Sp4.snap > $O/gate/measure.txt
python3 - "$O/gate/measure.txt" <<'PY'
import sys, re
blocks = {}; cur = None
for l in open(sys.argv[1]):
    if not l.startswith(' '): cur = l.split()[0]; blocks[cur] = [l.strip()]
    else: blocks[cur].append(l.strip())
body = {k: v[1:] for k, v in blocks.items()}
n = [k for k in body if k != 'S1b.snap']
print('Sp2 == Sp3 == Sp4 on every measure line:', all(body[n[0]] == body[k] for k in n), f'({len(body[n[0]])} lines each)')
print('control, flight 1 == Sp2:', body['S1b.snap'] == body[n[0]])
print('flight 1:', body['S1b.snap'][1]); print('Sp2     :', body[n[0]][1])
PY
echo "== flight 1 vs a demo after an idled human game (seed poked at scatter B), 100 samples of 200k steps"
uv run python $M/traj.py $O/S1b.snap 100 200000 > $O/gate/L1.txt
uv run python $M/traj.py $O/ctl/S.snap 100 200000 > $O/gate/Lctl.txt
uv run python $M/traj.py $O/fl/Sp2.snap 100 200000 > $O/gate/L2p.txt
python3 - $O/gate <<'PY'
import sys
L = lambda f: [l.split() for l in open(sys.argv[1] + '/' + f)]
a, b, c = L('L1.txt'), L('Lctl.txt'), L('L2p.txt')
print('flight 1 vs after-human-game demo: %d/%d' % (sum(p == q for p, q in zip(a, b)), len(a)))
print('control, flight 1 vs flight with the seed poked at scatter A (Sp2): %d/%d' % (sum(p == q for p, q in zip(a, c)), len(a)))
PY
