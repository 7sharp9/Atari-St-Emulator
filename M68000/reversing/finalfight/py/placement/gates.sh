#!/bin/sh
# gates.sh: two cold-boot runs of the played stage 0 (about 30 s and 45 s) with every log of the placement pass, then the checks (README.md here).
#   run 1: to the boss trigger (camera $aa0, frame 8298) with -debug breakpoints, write taps, the early census and saved states bb_<frame>
#   run 2: to the stage byte 1 (frame 11595), no debugger
# BB_RUN / BB_OUT: own MAME run and output directories (defaults scratchpad/finalfight/placement/{run,out}). ROMs: ~/mame-roms ($FF_ROMS).
# Expected: 44 matched, 1 blocked, 1 unmatched (the two-player-only entry); 118 of 118 attributed; 6 of 6 patches; 159 of 159; work RAM a0cb6b52...4837.
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
out=${BB_OUT:-$root/scratchpad/finalfight/placement/out}; mkdir -p "$out"
py=$root/.venv/bin/python
BP='60da:A3=%x:a3;6072:A3=%x:a3;61e8:K=%x:d0;61ec:D0=%x cnt=%x rank=%x:d0,b@ff1154,w@ff80a8'
for a in 4872 4840 47ea 4814 493a 490e; do BP="$BP;$a:A6=%x ch=%x:a6,b@(a6+14)"; done
BB_OUT=$out FF_MAMEARGS="-debug -debugger none" FF_BOT_BP="$BP" FF_BOT_BPLOG=$out/bp_all.log \
FF_BOT_TAP=ff12de-ff12ef,ffb1a8-ffb1e7,ff8284-ff8383,ff1300-ff14ff FF_BOT_TAPLOG=$out/tap_all.log \
FF_BOT_SLOG=$out/boss_early.log FF_BOT_SAVEAT=1325,1400,2500,3070,3600,4380,5570,7830 sh $here/run.sh boss > $out/gates_run1.txt 2>&1
BB_OUT=$out sh $here/run.sh full > $out/gates_run2.txt 2>&1
echo "== placement entries against live records (match.py)"; $py $here/match.py $out/bp_all.log $out/boss_early.log $out/boss.w | sed -n 1p
echo "== records first seen from frame 1316 to the boss trigger, by creator pc (classify.py)"; $py $here/classify.py $out/boss_early.log $out/boss.w | tail -1
echo "== to stage byte 1 (classify.py)"; $py $here/classify.py $out/full_early.log $out/full.w | tail -1
echo "== tile patch flags (flagcheck.py)"; $py $here/flagcheck.py $out/tap_all.log $out/bp_all.log | tail -1
echo "== HUD name writes (hudnames2.py)"; $py $here/hudnames2.py $out/tap_all.log | wc -l
echo "== work RAM of the saved boss state"; shasum -a 256 $out/b_boss_ram.bin | cut -c1-64
