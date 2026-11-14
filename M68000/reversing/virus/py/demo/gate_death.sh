#!/bin/bash
# Gates for the natural death and game over (reversing/virus/demo.md).  Run capture_death.sh first.  About 14 minutes.
cd "$(dirname "$0")/../../../.." || exit 1
W=${VIRUS_WORK:-scratchpad/virus}; D=$W/demo; O=$D/death; M=reversing/virus/py/demo; mkdir -p $O/gate
echo "== the unaided game over from the last life: lives, scatter A (stack word 5bee), scatter B reached, next demo flag"
grep -E "^[0-9a-f]{2}( |$)|breakpoint" $O/n1.log | head -8
echo "== trajectories, 500 samples of 200,000 steps (100M steps), same seed poke at scatter B"
for s in S1b death/E1 death/N1 death/N1z; do n=$(basename $s); uv run python $M/traj.py $D/$s.snap 500 200000 > $O/gate/long_$n.txt; done
python3 - $O/gate <<'PY'
import sys
L = lambda f: [l.split() for l in open(sys.argv[1] + '/' + f)]
a = L('long_S1b.txt')
for n, what in (('E1', 'after an ESC'), ('N1', 'after a natural game over'), ('N1z', 'after a natural game over, 4 stale bytes zeroed (poke)')):
    b = L(f'long_{n}.txt'); f = next((i for i, (p, q) in enumerate(zip(a, b)) if p != q), None)
    print(f'flight 1 vs {n} ({what}): {sum(p == q for p, q in zip(a, b))}/{len(a)}  first differing sample: {f}')
PY
echo "== the four bytes: bisect.py E1 vs N1 over \$27134..\$271e3 (control: N1 as is differs)"
BGAP=0 uv run python $M/bisect.py $D/death/E1.snap $D/death/N1.snap 27134 271e4 125 | grep -E "bad as is|all ranges|minimal|^  \\$"
echo "== RAM diff classes, first demo start vs the one after the natural game over"
uv run python $M/classify.py $D/S1b.snap $D/death/N1.snap | grep -E "^   |total"
echo "== life-loss tables (chunks of 100M steps; life_loss=yes is a stop on the life decrement)"
uv run python $M/deaths.py $D/S1b.snap 9 > $O/gate/deaths_g1.txt; uv run python $M/deaths.py $D/death/N1z.snap 9 > $O/gate/deaths_g2z.txt
cat $O/gate/deaths_g1.txt
echo "game 2 (after the game over, 4 bytes zeroed) equals game 1 on lives, wave, tick, score, fuel at every chunk:"
diff <(sed 's/pc=[0-9a-f]* //' $O/gate/deaths_g1.txt) <(sed 's/pc=[0-9a-f]* //' $O/gate/deaths_g2z.txt) && echo "identical 9/9"
