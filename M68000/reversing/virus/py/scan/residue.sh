#!/bin/bash
# residue.sh: does the stale bucket-buffer residue ($276fc..$2f6f4) change play? From the game-2 start of the 24-game chain,
# fly 500 samples of 200,000 steps three ways: unpoked, the whole bucket area zeroed (as at game 1), and filled with $ffffffff.
set -e
cd "$(dirname "$0")/../../../.."
# chain start snapshots: W/chain/long/starts (gate_chain.sh long 24) or the overseer copy that produced the doc's numbers
ST=scratchpad/virus/chain/long/starts; [ -d "$ST" ] || ST=scratchpad/overseer/virus_long/work/main/starts
mkdir -p scratchpad/virus/scan
S=$ST/main_g002.snap
O=scratchpad/virus/scan
T=reversing/virus/py/demo/traj.py
zero=(); ff=()
for ((a=0x276fc; a<0x2f6f4; a+=4)); do h=$(printf '%x' $a); zero+=("w $h 00000000"); ff+=("w $h ffffffff"); done
uv run python $T $S 500 200000 > $O/res_plain.txt
uv run python $T $S 500 200000 "${zero[@]}" > $O/res_zero.txt
uv run python $T $S 500 200000 "${ff[@]}" > $O/res_ff.txt
for v in zero ff; do python3 -c "
import sys;a=open('$O/res_plain.txt').read().split('\n');b=open('$O/res_$v.txt').read().split('\n')
print('$v', sum(x==y for x,y in zip(a,b) if x), 'of', sum(1 for x in a if x), 'identical; first diff', next((i for i,(x,y) in enumerate(zip(a,b)) if x!=y),None))"; done
