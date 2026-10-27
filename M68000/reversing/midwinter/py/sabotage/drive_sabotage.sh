#!/bin/bash
# Rebuild every driven sabotage snapshot the gate and the report use. usage: drive_sabotage.sh [outdir]
# outdir defaults to scratchpad/midwinter/sabotage. REPL scripts name their snapshots under
# scratchpad/midwinter/sabotage/; the copies run here are rewritten to outdir.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$HERE; while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); done
OUT=${1:-$ROOT/scratchpad/midwinter/sabotage}; mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
cd "$ROOT"
W=scratchpad/midwinter
r() {  # r <start snap> <script>
  sed "s#scratchpad/midwinter/sabotage/#$OUT/#g" "$HERE/$2" > "$OUT/.tmp_$2"
  uv run python "$HERE/repl.py" "$1" "$OUT/.tmp_$2" > "$OUT/${2%.txt}.log"
  grep -q 'state saved' "$OUT/${2%.txt}.log" || { echo "REPL $2 failed"; tail "$OUT/${2%.txt}.log"; exit 1; }
}
# 1. village node 74 (Little Plains), all natural: ENTER the Store, resupply (12 explosives), PLANT EXPLOSIVES
#    on the Church and the House, plunger; control: same clicks without the two plants
r $W/d_decisions.snap d1.txt; r "$OUT/s1_enter.snap" d2.txt; r "$OUT/s2_store.snap" d3.txt; r "$OUT/s3_resup.snap" d4.txt
r "$OUT/s4_sab.snap" d5a.txt; r "$OUT/s4_sab.snap" d5c.txt
r "$OUT/s5_planted.snap" u73.txt; r "$OUT/s5_planted.snap" ucancel.txt
# 2. held node 48 (Otter Valley, Warehouse): labelled poke of Stark's position, +52 and 47 explosives on d_stark
uv run python "$HERE/poke_snap.py" $W/d_stark.snap "$OUT/p48_stark.snap" 2b5c2:4:9b000 2b5c6:4:54000 2b5d4:4:2a3c0 2b5dc:1:2f 2446c:2:2f
r "$OUT/p48_stark.snap" dface.txt
r "$OUT/p48_dec.snap" d48a.txt; r "$OUT/p48_dec.snap" d48c.txt
r "$OUT/p48_blast.snap" dend_a.txt; r "$OUT/p48c_noblast.snap" dend_c.txt
r "$OUT/p48_planted.snap" u48.txt
# 3. held node 88 (the Headquarters): the same pokes for its site; then the period end, the win screen, a key
uv run python "$HERE/poke_snap.py" $W/d_stark.snap "$OUT/p88_stark.snap" 2b5c2:4:a8000 2b5c6:4:a3800 2b5d4:4:2a5dc 2b5dc:1:2f 2446c:2:2f
r "$OUT/p88_stark.snap" dface88.txt; r "$OUT/p88_dec.snap" d88all.txt
r "$OUT/p88_report.snap" dwin.txt; r "$OUT/p88_end2.snap" dwin2.txt
r "$OUT/p88_planted.snap" u88.txt
# 4. the three held Radio Stations blown up by the game's blast code in stserver, then the period end; control d_team
uv run python "$HERE/radio_setup.py" "$OUT/rad_team.snap" > /dev/null
r "$OUT/rad_team.snap" drad_a.txt; r $W/d_team.snap drad_c.txt
echo done
