#!/bin/sh
# Every live gate over the traces made by runs.sh (traces are .bin.gz in $AI45_OUT). Expected counts from the pass that wrote ai.md are
# in the comments; gate_caps.sh makes its own fresh MAME calls.
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
OUT=${AI45_OUT:-$root/scratchpad/finalfight/p3/c/out}
cd "$here" || exit 1
T() { echo "$OUT/$1.bin.gz"; }
echo "== damage taken by Cody equals the ROM damage byte (record + \$60 + level + box row)"
for s in 0 1 2; do python3 gate_dmg.py $(T k4n$s) ff8c28 4 $s; done                    # 21 / 19 / 17, 0 mismatches
for f in k5m0 k5g1 k5g4 k5g5 k5u0; do python3 gate_dmg.py $(T $f) ff8c28 5 0; done      # 15, 3, 2, 4, 1
for f in k5m1 k5u1; do python3 gate_dmg.py $(T $f) ff8c28 5 1; done                    # 27, 1
python3 gate_dmg.py $(T k5L7) ff8c28 5 0 7                                              # 11 (level 7)
python3 gate_dmg.py $(T k4L20) ff8c28 4 2 20                                            # 13 (level 20)
echo "== attack zones"
python3 gate_zone.py 5 $(T k5m0) $(T k5m1) $(T k5g1) $(T k5g3) $(T k5g5) $(T k5n0) $(T k5u0) $(T k5u1)   # 20 of 22 (2 interrupted by a hit)
python3 gate_zone4.py $(T k4n0) $(T k4n1) $(T k4n2) $(T k4t0) $(T k4t1) $(T k4t2)                       # near 6/6, mid 8/8
echo "== attack box per state (kind 5)"
python3 boxmap.py ff8c28 5 $(T k5m0) $(T k5m1) $(T k5g1) $(T k5g3) $(T k5g4) $(T k5g5) $(T k5u0) $(T k5u1) $(T k5n0)
echo "== state histograms"
python3 hist.py 5 $OUT/k5*.bin.gz $(T blk5)
python3 hist.py 4 $OUT/k4*.bin.gz $(T blk4)
echo "== HUD names (tile words in gfx RAM)"
python3 gate_names.py $(T nm40) 80 G.ORIBER; python3 gate_names.py $(T nm41) 80 BILL BULL; python3 gate_names.py $(T nm42) 80 WONG WHO
python3 gate_names.py $(T nm50) 50 HOLLY WOOD; python3 gate_names.py $(T nm51) 40 EL GADO
echo "== spawn caps"
"$here/gate_caps.sh"
