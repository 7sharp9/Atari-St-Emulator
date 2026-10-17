#!/bin/bash
# Re-run every headline proof of the `residual` area from M68000/ (about 10 minutes; at most 3 emulator processes at once).
# usage: bash reversing/supersprint/py/residual/run_all.sh   (writes scratchpad/supersprint/agents/residual/out/run_all.txt)
cd "$(dirname "$0")/../../../../.." || exit 1          # -> M68000/
R=scratchpad/supersprint/agents/residual; P=reversing/supersprint/py/residual; O=$R/out; A=$PWD/scratchpad/supersprint/agents
export ATARI_NOTRACE=1
{
echo "== sound: decode, render, bug effect, durations (offline)"; uv run python $P/tune.py; uv run python $P/bugfx.py | tail -24; uv run python $P/durations.py | grep -E '^(Q|J0|M) '; uv run python $P/unused_inst.py | head -4
echo "== sound: whole-tune live ISR differential (3 emulator runs, sequential)"; uv run python $P/liveproof.py
echo "== lap panel \$158ea"; uv run python $P/proof_lap.py 60 | tail -1
echo "== HUD band rebuild from natural snapshots"
for n in 1000000 4000000 9000000; do uv run python $P/stepsnap.py $PWD/scratchpad/supersprint/ss_prep.snap $n $PWD/$R/snap/prep_$n.snap >/dev/null & done; wait
uv run python $P/hud_rebuild.py $PWD/scratchpad/supersprint/ss_prep.snap 0 | sed -n 2p
for n in 1000000 4000000 9000000; do uv run python $P/hud_rebuild.py $PWD/$R/snap/prep_$n.snap 0 | sed -n 2p; done
echo "== HUD band with poked scores/laps"; uv run python $P/proof_hud_poke.py 12 | tail -1
echo "== leader blink sweep"; uv run python $P/proof_blink_sweep.py 0 1 2 | tail -1
echo "== smoke \$afc6/\$b6f8/\$143ca, rank key \$13b34, ring \$162f2/\$16424/\$16466, flags"; uv run python $P/proof_smoke.py 40 | tail -2; uv run python $P/proof_rank.py 80 | tail -1; uv run python $P/proof_ring.py 8 | tail -5; uv run python $P/proof_flags.py | tail -6
echo "== race-end phase and session tail (live)"
for s in one two final ctl64; do echo "-- $s"; uv run python $P/live_raceend.py $s; done
for s in tail0 tail1; do (uv run python $P/live_raceend.py $s > $O/live_raceend_$s.txt 2>&1 &); done; sleep 1
wait; while pgrep -f 'live_raceend[.]py' >/dev/null; do sleep 5; done
for s in tail0 tail1; do echo "-- $s"; cat $O/live_raceend_$s.txt; done
} > $O/run_all.txt 2>&1
echo done >> $O/run_all.txt
